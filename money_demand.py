#!/usr/bin/env python3
"""
Improvement #4: equilibrium velocity from a money-demand relation instead of an
atheoretic HP trend.

MOTIVATION
----------
In the paper, V* is whatever a one-sided HP filter calls "trend" in measured
velocity. That throws away the one thing money-demand theory actually tells us:
velocity depends on the opportunity cost of holding money. When the Fed cuts
rates, holding money gets cheaper, desired money balances rise, and equilibrium
velocity *falls*. The HP filter cannot see this -- it treats a rate-driven move
in velocity as cycle, to be filtered away, rather than as a shift in equilibrium.

The paper is explicit that this is the gap to fill: "one of our purposes in
writing this article is to call for a renewal of this line of economic research."
The CFS workbook already ships the required data -- a Divisia user-cost price
aggregate (the dual price index of monetary services) for every aggregate.

MODEL
-----
Long-run money demand with unit income elasticity, in velocity form:

    v_t = tau_t + beta * log(u_t) + eps_t

where v = log(P x / M) is log velocity and u is the real user-cost aggregate.
beta > 0: a higher opportunity cost of holding money means less money held for a
given level of transactions, hence higher velocity. tau_t is the slow drift in
long-run money demand that opportunity cost does not explain -- financial
innovation, sweep accounts, regulatory change.

Estimation is deliberately kept parallel to the paper so the comparison isolates
one change:

  1. beta from Stock-Watson dynamic OLS (leads and lags of d.log(u)), which is
     consistent and efficient for a cointegrating vector. Optionally recursive,
     so beta_t uses only data through t.
  2. tau from the SAME one-sided HP filter the paper uses, applied to the
     residual v - beta*log(u) instead of to v itself.
  3. v*_t = tau_t + beta_t * log(u_t).

So the filter, its lambda, and its real-time property are all unchanged. The
only difference from the paper is *what gets filtered*: the paper filters all of
velocity into "trend", this filters only the part opportunity cost cannot
explain, and treats the rate-driven component as a genuine shift in equilibrium.

WHAT DIDN'T WORK
----------------
The first attempt put tau in a state-space local-level model and estimated the
signal-to-noise ratio by maximum likelihood jointly with beta. It degenerates:
the MLE drives q to ~7 so that tau tracks v one-for-one, leaving v* ~ v, a
velocity gap of ~0, and beta ~ 0.04. All six specifications then collapse onto
the output gap. This is the standard local-level pathology on a near-random-walk
series, and it is why the smoothness here is imposed (via the HP lambda the
paper already commits to) rather than estimated.

CAVEAT
------
The paper's price gap is exactly invariant to the level of real GDP, because the
one-sided HP gains on v* and x* cancel. That invariance survives here only for
the tau component; the beta*log(u) term does not depend on output at all, so the
gap remains close to invariant but is no longer exactly so.
"""

import numpy as np
import pandas as pd
from pstar_replication import LAMBDA_HP, ONE_SIDED

USERCOST_COL = {  # 'UserCost' sheet, 0-indexed columns
    "M1": 1, "M2M": 3, "MZM": 5, "M2": 7, "ALL": 9, "M3": 11, "M4-": 13, "M4": 15,
}
# Which Divisia user-cost aggregate to pair with each money measure. Simple-sum
# M2 has no user-cost dual of its own, so it borrows Divisia M2's -- the
# opportunity cost of the same basket of assets.
USERCOST_FOR = {"M2": "M2", "DM2": "M2", "DM4": "M4"}


def load_usercost(path, aggregates=("M2", "M4")):
    """Quarterly average of the CFS real user-cost price aggregates."""
    raw = pd.read_excel(path, sheet_name="UserCost", header=None)
    d = raw.iloc[2:, :].copy()
    d[0] = pd.to_datetime(d[0], errors="coerce")
    d = d.dropna(subset=[0]).set_index(0)
    out = pd.DataFrame({a: d[USERCOST_COL[a]].astype(float) for a in aggregates})
    out.index.name = "date"
    return out.resample("QS").mean()


# ----------------------------------------------------------------------
# The cointegrating vector: Stock-Watson dynamic OLS
# ----------------------------------------------------------------------
def dols_beta(v, lu, leads=4, lags=4):
    """
    Long-run coefficient of log velocity on log user cost, by dynamic OLS:

        v_t = a + beta*lu_t + sum_j c_j * d.lu_{t-j} + e_t,  j = -leads..lags

    The leads and lags of the differenced regressor purge endogeneity and serial
    correlation from the levels estimate, which is what makes it a consistent
    estimator of the cointegrating vector rather than a spurious regression.
    """
    d = pd.DataFrame({"v": v, "lu": lu}).dropna()
    dlu = d["lu"].diff()
    cols = {"lu": d["lu"]}
    for j in range(-leads, lags + 1):
        cols[f"d{j}"] = dlu.shift(j)
    X = pd.DataFrame(cols).dropna()
    y = d["v"].reindex(X.index)
    Xv = np.column_stack([np.ones(len(X)), X.values])
    b, *_ = np.linalg.lstsq(Xv, y.values, rcond=None)
    return float(b[1])


def adf(series, lags=4):
    """Augmented Dickey-Fuller t-statistic (no trend). For a cointegration check."""
    y = pd.Series(series).dropna()
    dy = y.diff()
    cols = {"lev": y.shift(1)}
    for j in range(1, lags + 1):
        cols[f"d{j}"] = dy.shift(j)
    X = pd.DataFrame(cols).dropna()
    yy = dy.reindex(X.index)
    Xv = np.column_stack([np.ones(len(X)), X.values])
    b, *_ = np.linalg.lstsq(Xv, yy.values, rcond=None)
    r = yy.values - Xv @ b
    s2 = r @ r / (len(yy) - Xv.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(Xv.T @ Xv) * s2))
    return float(b[1] / se[1])


def fit_velocity(v, lu, filt="recursive", recursive_beta=True, min_obs=60,
                 leads=4, lags=4):
    """
    Equilibrium velocity from money demand.

    recursive_beta=True re-estimates the cointegrating vector on an expanding
    window so that beta_t, like the filter, uses only data through t. Before
    `min_obs` observations are available beta is held at its first estimate.

    Returns a frame with `beta`, the filtered residual trend `tau`, and
    `vstar` = tau + beta*lu.
    """
    v, lu = pd.Series(v).astype(float), pd.Series(lu).astype(float)
    n = len(v)

    if recursive_beta:
        betas = np.full(n, np.nan)
        first = None
        for t in range(min_obs - 1, n):
            b = dols_beta(v.iloc[: t + 1], lu.iloc[: t + 1], leads, lags)
            betas[t] = b
            if first is None:
                first = b
        betas[: min_obs - 1] = first
        beta = pd.Series(betas, index=v.index)
    else:
        beta = pd.Series(dols_beta(v, lu, leads, lags), index=v.index)

    resid = v - beta * lu
    tau = pd.Series(ONE_SIDED[filt](resid.values, LAMBDA_HP), index=v.index)

    out = pd.DataFrame({"beta": beta, "tau": tau}, index=v.index)
    out["vstar"] = out["tau"] + out["beta"] * lu
    out.attrs["beta_final"] = float(beta.iloc[-1])
    out.attrs["adf_resid"] = adf(v - beta.iloc[-1] * lu)
    return out


# ----------------------------------------------------------------------
# Price gap using the money-demand V*
# ----------------------------------------------------------------------
def price_gap_md(df, usercost, money_col, real_col, price_col, filt="recursive"):
    """
    P-star price gap with equilibrium velocity from money demand and equilibrium
    output still from the one-sided HP filter (so the only thing that changes
    versus the paper is V*).

        gap = 100 * [ (v* - v) + (x - x*) ]
    """
    uc = usercost[USERCOST_FOR[money_col]].reindex(df.index)
    nominal = df[real_col] * df[price_col]
    v = np.log(nominal / df[money_col])
    x = np.log(df[real_col])

    ok = v.notna() & uc.notna()
    fit = fit_velocity(v[ok], np.log(uc[ok]), filt=filt)
    vstar = fit["vstar"].reindex(df.index)

    xstar = pd.Series(ONE_SIDED[filt](x.values, LAMBDA_HP), index=df.index)

    out = pd.DataFrame(index=df.index)
    out["v"], out["vstar"] = v, vstar
    out["x"], out["xstar"] = x, xstar
    out["beta"] = fit["beta"].reindex(df.index)
    out["velocity_gap"] = 100.0 * (vstar - v)
    out["output_gap"] = 100.0 * (x - xstar)
    out["gap"] = out["velocity_gap"] + out["output_gap"]
    out.attrs.update(fit.attrs)
    return out
