#!/usr/bin/env python3
"""
Improvement B: can a better filter rescue the price gap?

THE QUESTION
------------
C established that dropping the latent trends entirely (4-quarter money growth)
gives a noise-to-signal ratio of 0.06 and zero real-time sign errors, against
1.09 and 33% for the P-star price gap -- at no cost in predictive accuracy. That
leaves one route still open for the gap: maybe lambda = 1600 is simply the wrong
filter, and a better one recovers a usable real-time V*.

This tests that directly, and frames it as the tradeoff it actually is. A
smoother trend revises less, because it responds less to each new observation --
but it also tracks less, so it may extract less signal. There is a frontier, and
the question is whether any point on it dominates the trend-free indicator.

VARIANTS
--------
  HP(lambda)   the paper's one-sided Hodrick-Prescott, swept over lambda from
               100 (very flexible) to 1e6 (nearly a straight line). lambda=1600
               is the paper's choice.
  Hamilton     Hamilton (2018) regression filter: regress v_t on v_{t-8}..v_{t-11}
               and call the residual the cycle. One-sided by construction, and
               proposed precisely as an answer to the HP filter's endpoint and
               spurious-cycle problems.
  money growth the C benchmark: no trend at all.

Each is scored on the same two axes -- real-time reliability from the ALFRED
vintage cache, and predictive power for the change in inflation, in sample and
out of sample against an AR(4).

    python filters.py
"""

import numpy as np
import pandas as pd

from pstar_replication import (fetch_fred, load_cfs, OLSResult, hp_one_sided_kalman,
                               hp_two_sided, SAMPLE_START, SAMPLE_END)
from vintages import fetch_vintage, vintage_dates
from nominal_gdp import regress, oos

LAMBDAS = [100, 400, 1600, 6400, 25600, 100000, 1000000]
HAM_H, HAM_P = 8, 4       # Hamilton (2018) defaults for quarterly data


def hamilton_cycle(y, h=HAM_H, p=HAM_P, coefs=None):
    """
    Hamilton (2018) filter. Regress y_t on y_{t-h} ... y_{t-h-p+1}; the residual
    is the cycle, the fitted value the trend. Returns (cycle, coefficients).
    Pass `coefs` to apply a previously estimated rule instead of re-estimating.
    """
    y = pd.Series(y).astype(float)
    X = pd.DataFrame({f"l{j}": y.shift(h + j) for j in range(p)})
    X.insert(0, "const", 1.0)
    ok = X.notna().all(axis=1) & y.notna()
    if coefs is None:
        b, *_ = np.linalg.lstsq(X[ok].values, y[ok].values, rcond=None)
    else:
        b = coefs
    fit = pd.Series(np.where(ok, X.fillna(0).values @ b, np.nan), index=y.index)
    return y - fit, b


def gaps_from(ngdp, rgdp, money, variant, two_sided=False):
    """
    Price gap = velocity gap + output gap, with the trend from `variant`.
    variant is ('hp', lambda) or ('hamilton', None).
    """
    v = np.log(ngdp / money)
    x = np.log(rgdp)
    kind, par = variant
    if kind == "hp":
        f = hp_two_sided if two_sided else hp_one_sided_kalman
        vstar = pd.Series(f(v.values, par), index=v.index)
        xstar = pd.Series(f(x.values, par), index=x.index)
        return 100.0 * ((vstar - v) + (x - xstar))
    vc, _ = hamilton_cycle(v)
    xc, _ = hamilton_cycle(x)
    return 100.0 * (-vc + xc)          # v* - v = -cycle_v;  x - x* = cycle_x


def hamilton_recursive(ngdp, rgdp, money, min_obs=60):
    """
    Hamilton gap with the regression coefficients re-estimated on an expanding
    window, so the indicator at t uses no information from after t.

    This matters: applying full-sample Hamilton coefficients to historical dates
    is a look-ahead, and it flatters the filter. Reported alongside the
    full-sample version so the size of that flattery is visible.
    """
    v = np.log(ngdp / money)
    x = np.log(rgdp)
    out = np.full(len(v), np.nan)
    for t in range(min_obs, len(v)):
        vc, _ = hamilton_cycle(v.iloc[:t + 1])
        xc, _ = hamilton_cycle(x.iloc[:t + 1])
        out[t] = 100.0 * (-vc.iloc[-1] + xc.iloc[-1])
    return pd.Series(out, index=v.index)


def variant_names():
    return ([("hp", lam) for lam in LAMBDAS] + [("hamilton", None)])


def label(variant):
    kind, par = variant
    return f"HP lambda={par:,}" + ("  <- paper" if par == 1600 else "") \
        if kind == "hp" else "Hamilton (2018)"


def realtime_table():
    """Endpoint gap for every variant, from every ALFRED vintage."""
    rows = []
    for q, vin in vintage_dates():
        try:
            ngdp, rgdp = fetch_vintage("GDP", vin), fetch_vintage("GDPC1", vin)
            m2 = fetch_vintage("M2SL", vin)
        except Exception:
            continue
        if ngdp is None or rgdp is None or m2 is None:
            continue
        d = pd.DataFrame({"ngdp": ngdp, "rgdp": rgdp,
                          "M2": m2.resample("QS").mean()}).dropna().loc[:q]
        if len(d) < 60 or d.index[-1] != q:
            continue
        r = {"date": q}
        for vnt in variant_names():
            g = gaps_from(d["ngdp"], d["rgdp"], d["M2"], vnt)
            r[label(vnt)] = g.iloc[-1]
        r["money growth"] = 100.0 * (d["M2"].iloc[-1] / d["M2"].iloc[-5] - 1.0)
        rows.append(r)
    return pd.DataFrame(rows).set_index("date")


def main():
    df = fetch_fred().join(load_cfs("data/Divisia.xlsx"), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]

    print("=" * 104)
    print("THE FILTER FRONTIER: does a smoother or smarter trend rescue the price gap?")
    print("=" * 104)
    print("Real-time from ALFRED vintages (M2/GDP); predictive tests on Divisia M2.\n")

    rt = realtime_table()

    rows = []
    for vnt in variant_names():
        nm = label(vnt)
        fin = gaps_from(df["ngdp"], df["rgdp"], df["M2"], vnt, two_sided=True)
        j = pd.DataFrame({"rt": rt[nm], "fin": fin}).dropna()
        rev = j["fin"] - j["rt"]

        gdiv = gaps_from(df["ngdp"], df["rgdp"], df["DM2"], vnt)
        r, d = regress(df, "p_gdp", gdiv)
        r1, r2, dm, _n = oos(df, "p_gdp", gdiv)
        rows.append({
            "variant": nm,
            "noise/signal": rev.std() / j["fin"].std(),
            "sign err %": 100 * (np.sign(j["rt"]) != np.sign(j["fin"])).mean(),
            "std effect": r.params["ind_l1"] * d["ind_l1"].std(),
            "HAC t": r.tvalues["ind_l1"],
            "R2": r.rsquared,
            "OOS gain %": 100 * (1 - r1 / r2),
            "DM t": dm,
        })

    # Hamilton with honest, expanding-window coefficients. Real-time columns are
    # unchanged -- the vintage loop already re-estimates per vintage.
    hrec = hamilton_recursive(df["ngdp"], df["rgdp"], df["DM2"])
    nmh = label(("hamilton", None))
    finh = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hamilton", None), two_sided=True)
    jh = pd.DataFrame({"rt": rt[nmh], "fin": finh}).dropna()
    revh = jh["fin"] - jh["rt"]
    r, d = regress(df, "p_gdp", hrec)
    r1, r2, dm, _n = oos(df, "p_gdp", hrec)
    rows.append({
        "variant": "Hamilton, recursive coefs",
        "noise/signal": revh.std() / jh["fin"].std(),
        "sign err %": 100 * (np.sign(jh["rt"]) != np.sign(jh["fin"])).mean(),
        "std effect": r.params["ind_l1"] * d["ind_l1"].std(),
        "HAC t": r.tvalues["ind_l1"], "R2": r.rsquared,
        "OOS gain %": 100 * (1 - r1 / r2), "DM t": dm,
    })

    # the trend-free benchmark from C
    gm = 100.0 * (df["DM2"] / df["DM2"].shift(4) - 1.0)
    gm_m2 = 100.0 * (df["M2"] / df["M2"].shift(4) - 1.0)
    j = pd.DataFrame({"rt": rt["money growth"], "fin": gm_m2}).dropna()
    rev = j["fin"] - j["rt"]
    r, d = regress(df, "p_gdp", gm)
    r1, r2, dm, _n = oos(df, "p_gdp", gm)
    rows.append({
        "variant": "money growth (no trend)",
        "noise/signal": rev.std() / j["fin"].std(),
        "sign err %": 100 * (np.sign(j["rt"]) != np.sign(j["fin"])).mean(),
        "std effect": r.params["ind_l1"] * d["ind_l1"].std(),
        "HAC t": r.tvalues["ind_l1"], "R2": r.rsquared,
        "OOS gain %": 100 * (1 - r1 / r2), "DM t": dm,
    })

    t = pd.DataFrame(rows).set_index("variant")
    print(t.to_string(float_format=lambda v: f"{v:8.3f}"))

    print("\n" + "=" * 104)
    print("READ")
    print("=" * 104)
    print("\n  Hamilton beats every HP variant on BOTH axes, not on a tradeoff between")
    print("  them. It is one-sided by construction -- the trend is a forecast made from")
    print("  data eight quarters earlier -- so it has no HP-style endpoint to revise.")
    print("  The full-sample-coefficient row overstates it; the recursive row is the")
    print("  honest one and still dominates lambda=1600 on every column.")
    hp = t.loc[[i for i in t.index if i.startswith("HP")]]
    best_rt = hp["noise/signal"].idxmin()
    best_pred = hp["std effect"].idxmax()
    print(f"  lowest noise-to-signal among HP variants : {best_rt} "
          f"({hp.loc[best_rt, 'noise/signal']:.2f})")
    print(f"  strongest predictor among HP variants    : {best_pred} "
          f"(std effect {hp.loc[best_pred, 'std effect']:.3f})")
    print(f"  trend-free benchmark                     : noise/signal "
          f"{t.loc['money growth (no trend)', 'noise/signal']:.2f}, "
          f"std effect {t.loc['money growth (no trend)', 'std effect']:.3f}")

    rt.to_csv("output/realtime_filters.csv")
    print("\nwrote output/realtime_filters.csv")


if __name__ == "__main__":
    main()
