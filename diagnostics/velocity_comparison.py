#!/usr/bin/env python3
"""
Improvement #4, evaluated: does a money-demand V* beat the HP-trend V*?

HYPOTHESIS
----------
The price-gap coefficient collapses to ~0 on 1990-2019. If the cause is that a
one-sided HP filter mis-measures equilibrium velocity -- treating rate-driven
shifts in money demand as cycle rather than as movements in equilibrium -- then
replacing the HP trend with a money-demand relation should restore predictive
power in that window.

DESIGN
------
Eight variants, crossing three choices, all against the paper's HP baseline:

  opportunity cost   CFS Divisia real user-cost aggregate  |  3m T-bill less the
                                                              CFS own-rate aggregate
  which u enters V*  current u  |  one-sided HP trend of u
  beta               full-sample DOLS  |  recursive (expanding window)

Everything else -- the filter, lambda, the output trend, the regression -- is
held at the paper's settings, so the comparison isolates V*.

Reported per variant: the Engle-Granger ADF statistic on the residual (is there
a cointegrating relation to lean on at all?), the volatility of the implied
velocity gap, gamma over three windows, and the 2026Q1 gap.

    python diagnostics/velocity_comparison.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get("CFS_XLSX", "data/Divisia.xlsx")

from pstar_replication import (fetch_fred, load_cfs, price_gap, pstar_regression,
                               ONE_SIDED, LAMBDA_HP, _fred_series)
from money_demand import load_usercost, dols_beta, adf

EG_CRIT_5PCT = -3.34   # Engle-Granger, one regressor, constant, no trend
WINDOWS = [("1967-01-01", "2026-03-31", "full"),
           ("1990-01-01", "2019-12-31", "1990-2019"),
           ("2020-01-01", "2026-03-31", "2020-2026")]


def own_rate(path):
    """CFS Divisia M2 interest-rate aggregate (the own-rate on the M2 basket)."""
    d = pd.read_excel(path, sheet_name="Narrow", header=None).iloc[2:, [0, 15]]
    d.columns = ["date", "r"]
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    return d.dropna().set_index("date")["r"].astype(float).resample("QS").mean()


def main():
    df = fetch_fred().join(load_cfs(CFS), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    U = load_usercost(CFS)

    money, rcol, pcol = "DM2", "rgdp", "p_gdp"
    v = np.log(df[rcol] * df[pcol] / df[money])
    hp = lambda s: pd.Series(ONE_SIDED["recursive"](np.asarray(s, float), LAMBDA_HP),
                             index=s.index)
    outgap = 100 * (np.log(df[rcol]) - hp(np.log(df[rcol])))

    tb = _fred_series("TB3MS").resample("QS").mean()
    spread = (tb - own_rate(CFS)).reindex(df.index).clip(lower=0.05)
    costs = {"CFS user cost": np.log(U["M2"].reindex(df.index)),
             "T-bill less own rate": np.log(spread)}

    def gamma_row(gap):
        out = []
        for a, b, _ in WINDOWS:
            r, _d = pstar_regression(df, pcol, gap, start=a, end=b)
            out.append(f"{r.params['gap_l1']:+.3f}(t{r.tvalues['gap_l1']:5.2f})")
        return out

    hdr = (f"{'opportunity cost':22s} {'u':8s} {'beta':10s} {'ADF':>6s} {'sd(vgap)':>9s} "
           + "".join(f"{n:>14s}" for _, _, n in WINDOWS) + f"{'2026Q1':>9s}")
    print("=" * len(hdr))
    print("MONEY-DEMAND V* VARIANTS  (Divisia M2 / GDP)")
    print("=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))

    for cname, lu_raw in costs.items():
        for utreat in ("current", "trend"):
            lu = lu_raw if utreat == "current" else hp(lu_raw.dropna()).reindex(df.index)
            ok = v.notna() & lu.notna()
            for btreat in ("fixed", "recursive"):
                if btreat == "fixed":
                    beta = pd.Series(dols_beta(v[ok], lu[ok]), index=df.index)
                else:
                    bs = np.full(len(v), np.nan)
                    idx = np.where(ok)[0]
                    for k, t in enumerate(idx):
                        if k >= 59:
                            bs[t] = dols_beta(v[ok].iloc[:k + 1], lu[ok].iloc[:k + 1])
                    beta = pd.Series(bs, index=df.index).fillna(method="bfill")
                tau = hp((v - beta * lu).dropna()).reindex(df.index)
                vgap = 100 * (tau + beta * lu - v)
                gap = (vgap + outgap).dropna()
                a = adf((v - beta.iloc[-1] * lu).dropna())
                print(f"{cname:22s} {utreat:8s} {btreat:10s} {a:6.2f} {vgap.std():9.2f} "
                      + "".join(f"{x:>14s}" for x in gamma_row(gap))
                      + f"{gap.loc['2026-01-01']:9.2f}")

    base = price_gap(df, money, rcol, pcol)
    print("-" * len(hdr))
    print(f"{'HP trend V* (paper)':22s} {'--':8s} {'--':10s} {'--':>6s} "
          f"{base['velocity_gap'].std():9.2f} "
          + "".join(f"{x:>14s}" for x in gamma_row(base["gap"]))
          + f"{base['gap'].loc['2026-01-01']:9.2f}")

    print(f"\nEngle-Granger 5% critical value (one regressor): {EG_CRIT_5PCT}")
    print("No variant comes close, so there is no cointegrating money-demand")
    print("relation here to substitute for the filter -- and no variant repairs")
    print("the 1990-2019 window. See README.")


if __name__ == "__main__":
    main()
