#!/usr/bin/env python3
"""
Improvement #1: is the P-star price-gap coefficient stable, and if not, what
governs the regime?

The paper reports gamma ~ 0.10 "strikingly consistent" across six specifications
on 1967Q1-2026Q1 and offers it as a rule of thumb. Splitting the sample shows
gamma is ~0 and insignificant on 1990-2019 in all six. This module asks whether
that is a real break and whether the switch is predictable.

TESTS
-----
1. Rolling 60-quarter gamma.
2. Quandt-Andrews sup-Wald test for a single break in gamma at an unknown date,
   15% trimming, p-value by wild bootstrap under the no-break null (so no
   tabulated critical values are needed).
3. Threshold regression: gamma differs above and below a threshold in a state
   variable, threshold chosen by grid search over the 15th-85th percentile, with
   a Hansen-style bootstrap p-value for H0: gamma_low = gamma_high.

The state variables are a small pre-specified set, all reported, so the
threshold search is not a fishing expedition dressed up as a finding.

    python diagnostics/regime.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get("CFS_XLSX", "data/Divisia.xlsx")

from pstar_replication import (fetch_fred, load_cfs, price_gap, pstar_regression,
                               OLSResult, ONE_SIDED, LAMBDA_HP, SPECS)

RNG = np.random.default_rng(20260728)
NBOOT = 999
TRIM = 0.15


def design(df, price_col, gap):
    """Regression matrices for the P-star equation."""
    _, d = pstar_regression(df, price_col, gap)
    X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"]].copy()
    X.insert(0, "const", 1.0)
    return d["dpi"], X


def _ssr(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    return r @ r, b, r


def sup_wald_break(y, X, col="gap_l1", nboot=NBOOT):
    """
    Sup-Wald for a break in one coefficient at an unknown date. The p-value comes
    from a wild bootstrap: regenerate the data under the no-break fit with
    Rademacher-weighted residuals and re-run the whole search.
    """
    yv, Xv = y.values, X.values
    n, k = Xv.shape
    j = list(X.columns).index(col)
    lo, hi = int(TRIM * n), int((1 - TRIM) * n)

    def stat(yy):
        ssr0, b0, r0 = _ssr(yy, Xv)
        best, at = -np.inf, None
        for t in range(lo, hi):
            Z = np.zeros((n, 1))
            Z[t:, 0] = Xv[t:, j]          # post-break shift in the gap coefficient
            Xa = np.hstack([Xv, Z])
            ssr1, _, _ = _ssr(yy, Xa)
            f = (ssr0 - ssr1) / (ssr1 / (n - k - 1))
            if f > best:
                best, at = f, t
        return best, at, r0, b0

    obs, at, r0, b0 = stat(yv)
    fit0 = Xv @ b0
    count = 0
    for _ in range(nboot):
        yb = fit0 + r0 * RNG.choice([-1.0, 1.0], size=n)
        if stat(yb)[0] >= obs:
            count += 1
    return obs, y.index[at], (count + 1) / (nboot + 1)


def chow_known(y, X, date, col="gap_l1", nboot=NBOOT):
    """
    Break in gamma at a PRE-SPECIFIED date. Needed because sup-Wald trims the
    last 15% of the sample, which puts a 2020 break outside the search window
    entirely. Choosing the date on narrative grounds rather than by search is
    what makes this legitimate; the bootstrap p-value is not search-corrected
    because there is no search.
    """
    yv, Xv = y.values, X.values
    n, k = Xv.shape
    j = list(X.columns).index(col)
    t = int(np.searchsorted(y.index.values, np.datetime64(date)))
    if not (k + 2 < t < n - 2):
        return np.nan, np.nan, np.nan, np.nan

    def stat(yy):
        ssr0, b0, r0 = _ssr(yy, Xv)
        Z = np.zeros((n, 1))
        Z[t:, 0] = Xv[t:, j]
        ssr1, b1, _ = _ssr(yy, np.hstack([Xv, Z]))
        return (ssr0 - ssr1) / (ssr1 / (n - k - 1)), b1, r0, b0

    obs, b1, r0, b0 = stat(yv)
    fit0 = Xv @ b0
    count = sum(1 for _ in range(nboot)
                if stat(fit0 + r0 * RNG.choice([-1.0, 1.0], size=n))[0] >= obs)
    return b1[j], b1[j] + b1[-1], obs, (count + 1) / (nboot + 1)


def threshold_gamma(y, X, s, col="gap_l1", nboot=NBOOT):
    """
    gamma switches on a state variable s (aligned to X, already lagged).
    Returns (gamma_low, gamma_high, threshold, sup-Wald, bootstrap p).
    """
    yv, Xv = y.values, X.values
    n, k = Xv.shape
    j = list(X.columns).index(col)
    sv = s.reindex(X.index).values
    grid = np.unique(np.quantile(sv[~np.isnan(sv)], np.linspace(TRIM, 1 - TRIM, 40)))

    def stat(yy):
        ssr0, b0, r0 = _ssr(yy, Xv)
        best, bt, bb = -np.inf, None, None
        for tau in grid:
            hi_mask = (sv > tau).astype(float)
            Z = (Xv[:, j] * hi_mask).reshape(-1, 1)
            Xa = np.hstack([Xv, Z])
            ssr1, b1, _ = _ssr(yy, Xa)
            f = (ssr0 - ssr1) / (ssr1 / (n - k - 1))
            if f > best:
                best, bt, bb = f, tau, b1
        return best, bt, bb, r0, b0

    obs, tau, b1, r0, b0 = stat(yv)
    fit0 = Xv @ b0
    count = sum(1 for _ in range(nboot)
                if stat(fit0 + r0 * RNG.choice([-1.0, 1.0], size=n))[0] >= obs)
    g_low = b1[j]
    g_high = b1[j] + b1[-1]
    return g_low, g_high, tau, obs, (count + 1) / (nboot + 1)


def main():
    df = fetch_fred().join(load_cfs(CFS), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]

    # state variables, all built from information available at t-1
    xstar = pd.Series(ONE_SIDED["recursive"](np.log(df["rgdp"]).values, LAMBDA_HP),
                      index=df.index)
    pot = 400 * xstar.diff()                       # annualized potential growth
    states = {}
    mg = 100 * (df["DM2"] / df["DM2"].shift(4) - 1)
    states["|excess money growth|"] = (mg - (pot + 2.0)).abs().shift(1)
    states["money growth volatility (12q sd)"] = mg.rolling(12).std().shift(1)
    states["|price gap|"] = None                   # filled per specification

    print("=" * 100)
    print("ROLLING 60-QUARTER GAMMA  (Divisia M2 / GDP)")
    print("=" * 100)
    g = price_gap(df, "DM2", "rgdp", "p_gdp")["gap"]
    y, X = design(df, "p_gdp", g)
    roll = []
    for i in range(60, len(y) + 1):
        r = OLSResult(y.iloc[i - 60:i], X.iloc[i - 60:i])
        roll.append((y.index[i - 1], r.params["gap_l1"], r.tvalues["gap_l1"]))
    roll = pd.DataFrame(roll, columns=["date", "gamma", "t"]).set_index("date")
    print(roll.resample("5AS").first().round(3).to_string())
    print(f"\n  range {roll['gamma'].min():+.3f} to {roll['gamma'].max():+.3f}; "
          f"{100 * (roll['t'] > 2).mean():.0f}% of windows have t > 2")

    print("\n" + "=" * 100)
    print(f"QUANDT-ANDREWS SUP-WALD, break in gamma, {TRIM:.0%} trimming, "
          f"wild bootstrap p ({NBOOT} reps)")
    print("=" * 100)
    n = len(y)
    print(f"search window: {y.index[int(TRIM * n)].date()} to "
          f"{y.index[int((1 - TRIM) * n)].date()}   "
          f"(trimming puts a 2020 break OUT of reach -- see the next table)\n")
    print(f"{'spec':18s} {'sup-Wald':>9s} {'break date':>12s} {'p':>7s}")
    for label, mcol, rcol, pcol, tag in SPECS:
        gg = price_gap(df, mcol, rcol, pcol)["gap"]
        yy, XX = design(df, pcol, gg)
        w, at, p = sup_wald_break(yy, XX)
        print(f"{label + '/' + tag:18s} {w:9.2f} {str(at.date()):>12s} {p:7.3f}")

    print("\n" + "=" * 100)
    print("BREAK IN GAMMA AT A PRE-SPECIFIED DATE (no search, so no search correction)")
    print("=" * 100)
    for date, why in [("1984-01-01", "start of the Great Moderation"),
                      ("2020-01-01", "pandemic money surge")]:
        print(f"\n--- break at {date}  ({why}) ---")
        print(f"{'spec':18s} {'g(before)':>10s} {'g(after)':>10s} {'Wald':>8s} {'p':>7s}")
        for label, mcol, rcol, pcol, tag in SPECS:
            gg = price_gap(df, mcol, rcol, pcol)["gap"]
            yy, XX = design(df, pcol, gg)
            g0, g1, w, p = chow_known(yy, XX, date)
            print(f"{label + '/' + tag:18s} {g0:10.3f} {g1:10.3f} {w:8.2f} {p:7.3f}")

    print("\n" + "=" * 100)
    print("IS IT INSTABILITY, OR JUST IMPRECISION?  95% CI on gamma, Newey-West (4 lags)")
    print("=" * 100)
    print(f"{'spec':18s} {'window':12s} {'gamma':>7s} {'HAC se':>8s} {'95% CI':>18s}"
          f"   {'0 in CI?':>9s} {'0.10 in CI?':>12s}")
    for label, mcol, rcol, pcol, tag in SPECS:
        gg = price_gap(df, mcol, rcol, pcol)["gap"]
        for a, b, nm in [("1967-01-01", "2026-03-31", "full"),
                         ("1990-01-01", "2019-12-31", "1990-2019"),
                         ("2020-01-01", "2026-03-31", "2020-2026")]:
            _, d = pstar_regression(df, pcol, gg, start=a, end=b)
            Xd = d[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"]].copy()
            Xd.insert(0, "const", 1.0)
            r = OLSResult(d["dpi"], Xd, hac_lags=4)
            gam, se = r.params["gap_l1"], r.bse["gap_l1"]
            lo, hi = gam - 1.96 * se, gam + 1.96 * se
            print(f"{label + '/' + tag:18s} {nm:12s} {gam:7.3f} {se:8.3f} "
                  f"{'[' + f'{lo:+.3f}, {hi:+.3f}' + ']':>18s}   "
                  f"{('yes' if lo < 0 < hi else 'NO'):>9s} "
                  f"{('yes' if lo < 0.10 < hi else 'NO'):>12s}")

    print("\n" + "=" * 100)
    print("THRESHOLD REGRESSION: does gamma switch on the state of money?")
    print("=" * 100)
    for label, mcol, rcol, pcol, tag in [("Divisia M2", "DM2", "rgdp", "p_gdp", "GDP"),
                                         ("Divisia M2", "DM2", "rpce", "p_pce", "PCE"),
                                         ("M2", "M2", "rgdp", "p_gdp", "GDP")]:
        gg = price_gap(df, mcol, rcol, pcol)["gap"]
        yy, XX = design(df, pcol, gg)
        st = dict(states)
        st["|price gap|"] = gg.abs().shift(1)
        print(f"\n--- {label}/{tag} ---")
        print(f"{'state variable':36s} {'threshold':>10s} {'g(low)':>8s} "
              f"{'g(high)':>8s} {'sup-Wald':>9s} {'p':>7s}")
        for nm, s in st.items():
            gl, gh, tau, w, p = threshold_gamma(yy, XX, s)
            print(f"{nm:36s} {tau:10.2f} {gl:8.3f} {gh:8.3f} {w:9.2f} {p:7.3f}")


if __name__ == "__main__":
    main()
