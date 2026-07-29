#!/usr/bin/env python3
"""
Improvement C: fewer latent trends.

THE ARGUMENT
------------
Every problem this repo has found traces to one source. The P-star gap requires
estimating two unobserved trends -- equilibrium velocity V* and potential output
Y* -- at the sample endpoint, where a one-sided filter is weakest. That endpoint
noise (sd 3.13pp, vintages.py) is what produces the 33% real-time sign errors,
what attenuates gamma, and hence what produces the apparent regime dependence
(diagnostics/attenuation.py). Trying to estimate V* *better* already failed
(money_demand.py). This tries to need it less.

Note the identity. With n = log(nominal GDP) = p + x and n* = m + v*,

    nominal gap  =  n* - n  =  (m + v*) - (p + x)  =  v* - v

so a nominal-GDP framing drops Y* entirely and leaves the velocity gap. Going
one rung further, money growth relative to nominal GDP growth needs no trend at
all. That gives a ladder of indicators with strictly decreasing latent content:

    price gap                    V* and Y*     (the paper)
    velocity gap = nominal gap   V* only
    money growth, 4q             none
    money growth less nominal GDP growth   none

The paper itself points this way in its conclusion: "steady-state money growth
should equal growth in potential nominal output."

THE TEST
--------
All four are judged on the same three questions, against machinery already built:

  1. In sample, do they predict the change in inflation, and is the coefficient
     stable across the windows where the price gap falls apart?
  2. Out of sample from 1990, do they beat an AR(4) that has no monetary
     information at all?
  3. Reconstructed from ALFRED vintages, how badly does each get revised? This
     is the question the whole exercise exists to answer -- if the trend-free
     indicators are stable in real time, the endpoint problem was the binding
     constraint and it is avoidable.

    python nominal_gdp.py
"""

import numpy as np
import pandas as pd

from pstar_replication import (fetch_fred, load_cfs, OLSResult, LAMBDA_HP,
                               hp_one_sided_kalman, hp_two_sided, SAMPLE_START,
                               SAMPLE_END)
from vintages import fetch_vintage, vintage_dates

INDICATORS = ["price gap", "velocity gap", "money growth", "money less nGDP"]
LATENT = {"price gap": "V*, Y*", "velocity gap": "V*", "money growth": "none",
          "money less nGDP": "none"}


def build_indicators(ngdp, rgdp, money, two_sided=False):
    """The four monetary indicators from a single data vintage."""
    filt = hp_two_sided if two_sided else hp_one_sided_kalman
    v = np.log(ngdp / money)
    x = np.log(rgdp)
    vstar = pd.Series(filt(v.values, LAMBDA_HP), index=v.index)
    xstar = pd.Series(filt(x.values, LAMBDA_HP), index=x.index)

    vel_gap = 100.0 * (vstar - v)
    out_gap = 100.0 * (x - xstar)
    gm = 100.0 * (money / money.shift(4) - 1.0)
    gn = 100.0 * (ngdp / ngdp.shift(4) - 1.0)

    return pd.DataFrame({
        "price gap": vel_gap + out_gap,
        "velocity gap": vel_gap,
        "money growth": gm,
        "money less nGDP": gm - gn,
    })


def regress(df, price_col, ind, start=SAMPLE_START, end=SAMPLE_END, hac=4):
    """Hallman-Porter-Small with `ind` in place of the price gap."""
    pi = 400.0 * np.log(df[price_col]).diff()
    dpi = pi.diff()
    d = pd.DataFrame({"dpi": dpi, "ind_l1": ind.shift(1)})
    for i in range(1, 5):
        d[f"dpi_l{i}"] = dpi.shift(i)
    d = d.loc[start:end].dropna()
    X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["ind_l1"]].copy()
    X.insert(0, "const", 1.0)
    return OLSResult(d["dpi"], X, hac_lags=hac), d


def oos(df, price_col, ind, first="1990-01-01"):
    """Expanding-window 1-step-ahead RMSE against an AR(4) with no money."""
    _, d = regress(df, price_col, ind)
    X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["ind_l1"]].copy()
    X.insert(0, "const", 1.0)
    y = d["dpi"]
    ef, ea = [], []
    for i in range(len(y)):
        if y.index[i] < pd.Timestamp(first):
            continue
        Xtr, ytr = X.iloc[:i], y.iloc[:i]
        bf, *_ = np.linalg.lstsq(Xtr.values, ytr.values, rcond=None)
        Xa = Xtr.drop(columns=["ind_l1"])
        ba, *_ = np.linalg.lstsq(Xa.values, ytr.values, rcond=None)
        ef.append(y.iloc[i] - X.iloc[i].values @ bf)
        ea.append(y.iloc[i] - X.iloc[i].drop("ind_l1").values @ ba)
    ef, ea = np.array(ef), np.array(ea)
    dm_num = (ef ** 2 - ea ** 2)
    dm = dm_num.mean() / (dm_num.std(ddof=1) / np.sqrt(len(dm_num)))
    return np.sqrt((ef ** 2).mean()), np.sqrt((ea ** 2).mean()), dm, len(ef)


def realtime_indicators():
    """Endpoint value of every indicator, from each ALFRED vintage."""
    rows = []
    for q, vin in vintage_dates():
        try:
            ngdp = fetch_vintage("GDP", vin)
            rgdp = fetch_vintage("GDPC1", vin)
            m2 = fetch_vintage("M2SL", vin)
        except Exception:
            continue
        if ngdp is None or rgdp is None or m2 is None:
            continue
        d = pd.DataFrame({"ngdp": ngdp, "rgdp": rgdp,
                          "M2": m2.resample("QS").mean()}).dropna().loc[:q]
        if len(d) < 60 or d.index[-1] != q:
            continue
        ind = build_indicators(d["ngdp"], d["rgdp"], d["M2"])
        rows.append(dict({"date": q}, **ind.iloc[-1].to_dict()))
    return pd.DataFrame(rows).set_index("date")


def main():
    df = fetch_fred().join(load_cfs("data/Divisia.xlsx"), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]

    fin = {}
    for mlab, mcol in [("M2", "M2"), ("Divisia M2", "DM2")]:
        fin[mlab] = build_indicators(df["ngdp"], df["rgdp"], df[mcol])

    print("=" * 100)
    print("1. IN SAMPLE: predicting the change in GDP inflation, 1967Q1-2026Q1 (HAC 4)")
    print("=" * 100)
    print(f"{'indicator':20s} {'latent':10s} {'coef':>8s} {'t':>7s} {'R2':>7s} "
          f"{'std. effect':>12s}")
    for mlab in fin:
        print(f"\n--- money = {mlab} ---")
        for k in INDICATORS:
            ind = fin[mlab][k]
            r, d = regress(df, "p_gdp", ind)
            std_eff = r.params["ind_l1"] * d["ind_l1"].std()
            print(f"{k:20s} {LATENT[k]:10s} {r.params['ind_l1']:8.4f} "
                  f"{r.tvalues['ind_l1']:7.2f} {r.rsquared:7.3f} {std_eff:12.3f}")

    print("\n('std. effect' = coefficient x sd of the indicator, so the columns are")
    print(" comparable across indicators measured in different units)")

    print("\n" + "=" * 100)
    print("2. SUBSAMPLE STABILITY: coefficient by window (Divisia M2)")
    print("=" * 100)
    wins = [("1967-01-01", "1983-12-31", "1967-1983"),
            ("1990-01-01", "2019-12-31", "1990-2019"),
            ("2020-01-01", "2026-03-31", "2020-2026")]
    print(f"{'indicator':20s}" + "".join(f"{n:>22s}" for _, _, n in wins))
    for k in INDICATORS:
        ind = fin["Divisia M2"][k]
        cells = []
        for a, b, _ in wins:
            r, d = regress(df, "p_gdp", ind, start=a, end=b)
            cells.append(f"{r.params['ind_l1']:+.4f} (t{r.tvalues['ind_l1']:5.2f})")
        print(f"{k:20s}" + "".join(f"{c:>22s}" for c in cells))

    print("\n" + "=" * 100)
    print("3. OUT OF SAMPLE from 1990: does the indicator beat an AR(4) with no money?")
    print("=" * 100)
    print(f"{'indicator':20s} {'RMSE w/':>9s} {'RMSE AR4':>9s} {'improvement':>12s} "
          f"{'DM t':>7s}  {'n':>4s}")
    for k in INDICATORS:
        r1, r2, dm, n = oos(df, "p_gdp", fin["Divisia M2"][k])
        print(f"{k:20s} {r1:9.4f} {r2:9.4f} {100 * (1 - r1 / r2):11.2f}% "
              f"{dm:7.2f}  {n:4d}")
    print("\n(negative DM t means the indicator helps; |t| > 2 is significant)")

    print("\n" + "=" * 100)
    print("4. REAL-TIME RELIABILITY: how badly is each indicator revised?")
    print("=" * 100)
    rt = realtime_indicators()
    fin2 = build_indicators(df["ngdp"], df["rgdp"], df["M2"], two_sided=True)
    print(f"{'indicator':20s} {'latent':10s} {'sd(revision)':>13s} {'sd(level)':>10s} "
          f"{'noise/signal':>13s} {'corr':>6s} {'sign errors':>12s}")
    for k in INDICATORS:
        j = pd.DataFrame({"rt": rt[k], "fin": fin2[k]}).dropna()
        rev = j["fin"] - j["rt"]
        print(f"{k:20s} {LATENT[k]:10s} {rev.std():13.2f} {j['fin'].std():10.2f} "
              f"{rev.std() / j['fin'].std():13.2f} {j['rt'].corr(j['fin']):6.2f} "
              f"{100 * (np.sign(j['rt']) != np.sign(j['fin'])).mean():11.0f}%")

    rt.to_csv("output/realtime_indicators.csv")
    print("\nwrote output/realtime_indicators.csv")


if __name__ == "__main__":
    main()
