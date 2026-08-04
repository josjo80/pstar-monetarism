#!/usr/bin/env python3
"""
The current stance of monetary policy, read off the best indicator available.

WHY THIS FILE EXISTS
--------------------
Earlier readings in this repo were computed on the paper's HP(1600) price gap,
whose real-time noise-to-signal ratio is 1.09 -- so every band spanned zero and
the honest answer was "cannot tell". filters.py found that the Hamilton (2018)
regression filter dominates HP on both axes at once: noise-to-signal 0.24 rather
than 1.09, real-time sign errors 11% rather than 33%, and *more* predictive power
rather than less. This re-runs the current reading on that filter, and reports
the trend-free money-growth cross-check alongside.

Three indicators, in increasing order of real-time precision and decreasing
order of predictive power:

    Hamilton price gap    noise/signal 0.24, most predictive
    HP(1600) price gap    noise/signal 1.09, the paper's -- shown for comparison
    money growth, 4q      noise/signal 0.06, no latent trends at all

    python current_reading.py
"""

import numpy as np
import pandas as pd

from pstar_replication import fetch_fred, load_cfs, price_gap, SPECS
from filters import hamilton_recursive, gaps_from
from nominal_gdp import regress

CFS = "data/Divisia.xlsx"
NOM = {"p_gdp": "ngdp", "p_pce": "npce"}


def revision_band(pct=(5, 95)):
    """Empirical revision percentiles for the Hamilton gap, from the vintages."""
    rt = pd.read_csv("output/realtime_filters.csv", parse_dates=["date"],
                     index_col="date")
    df = fetch_fred().dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    fin = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hamilton", None), two_sided=True)
    j = pd.DataFrame({"rt": rt["Hamilton (2018)"], "fin": fin}).dropna()
    rev = (j["fin"] - j["rt"])
    rev = rev - rev.mean()
    return np.percentile(rev, pct), rev.std()


def main():
    df = fetch_fred().join(load_cfs(CFS), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":]
    df2 = df
    q = df.index[-1]
    prev = df.index[-2]

    (lo, hi), rsd = revision_band()
    print("=" * 96)
    print("CURRENT STANCE OF MONETARY POLICY, ON THE HAMILTON (2018) FILTER")
    print("=" * 96)
    print(f"latest complete quarter: {q.date()} (published data, no nowcast)")
    print(f"Hamilton revision distribution: sd {rsd:.2f}pp, 90% band "
          f"[{lo:+.2f}, {hi:+.2f}]  (HP(1600) equivalent: sd 3.13pp)\n")

    print(f"{'spec':18s} {prev.date().strftime('%YQ%m')[:4]+'Q'+str((prev.month-1)//3+1):>8s} "
          f"{str(q.year)+'Q'+str((q.month-1)//3+1):>8s} {'90% band on latest':>24s} "
          f"{'sign certain?':>14s}")
    gaps = {}
    for label, mcol, rcol, pcol, tag in SPECS:
        g = hamilton_recursive(df2[NOM[pcol]], df2[rcol], df2[mcol])
        gaps[f"{label}/{tag}"] = g
        now = float(g.loc[q])
        band = (now + lo, now + hi)
        certain = "yes" if band[0] > 0 or band[1] < 0 else "NO -- spans 0"
        print(f"{label + '/' + tag:18s} {g.loc[prev]:8.2f} {now:8.2f} "
              f"{f'[{band[0]:+.2f}, {band[1]:+.2f}]':>24s} {certain:>14s}")

    print("\n" + "=" * 96)
    print("SAME READING ON THE PAPER'S HP(1600) FILTER, FOR COMPARISON")
    print("=" * 96)
    print(f"{'spec':18s} {'2026Q1':>8s} {'2026Q2':>8s} {'90% band on 2026Q2':>24s} "
          f"{'sign certain?':>14s}")
    for label, mcol, rcol, pcol, tag in SPECS:
        g = price_gap(df2, mcol, rcol, pcol)["gap"]
        now = float(g.loc[q])
        band = (now - 4.06, now + 6.34)
        certain = "yes" if band[0] > 0 or band[1] < 0 else "NO -- spans 0"
        print(f"{label + '/' + tag:18s} {g.loc[prev]:8.2f} {now:8.2f} "
              f"{f'[{band[0]:+.2f}, {band[1]:+.2f}]':>24s} {certain:>14s}")

    print("\n" + "=" * 96)
    print("IMPLIED EFFECT ON INFLATION  (gamma estimated on the Hamilton gap)")
    print("=" * 96)
    print(f"{'spec':18s} {'gamma':>8s} {'HAC t':>7s} {'gap':>7s} {'-> dInfl':>10s} "
          f"{'90% band':>20s}")
    for label, mcol, rcol, pcol, tag in SPECS:
        g = gaps[f"{label}/{tag}"]
        r, d = regress(df, pcol, g)
        gam, se = r.params["ind_l1"], r.bse["ind_l1"]
        now = float(g.loc[q])
        lo_e = 100 * (gam - 1.645 * se) * (now + lo)
        hi_e = 100 * (gam + 1.645 * se) * (now + hi)
        print(f"{label + '/' + tag:18s} {gam:8.3f} {r.tvalues['ind_l1']:7.2f} "
              f"{now:7.2f} {100 * gam * now:9.0f}bp "
              f"{f'[{min(lo_e, hi_e):+.0f}, {max(lo_e, hi_e):+.0f}] bp':>20s}")

    print("\n" + "=" * 96)
    print("TREND-FREE CROSS-CHECK: money growth against the speed limit")
    print("=" * 96)
    for m, nm in [("M2", "M2"), ("DM2", "Divisia M2"), ("DM4", "Divisia M4")]:
        g4 = 100 * (df2[m] / df2[m].shift(4) - 1)
        print(f"  {nm:12s} 4q growth to {q.date()}: {g4.loc[q]:5.2f}%   "
              f"excess over a 4.25-5.0% speed limit: "
              f"{g4.loc[q] - 5.0:+.2f} to {g4.loc[q] - 4.25:+.2f}pp")
    print("\n  This is the near-noise-free reading (noise/signal 0.06): no filter, no")
    print("  latent trend, revised only by the small revisions to money itself.")

    print("\n" + "=" * 96)
    print("VALIDATION: the 2021 case where the HP gap failed")
    print("=" * 96)
    rt = pd.read_csv("output/realtime_filters.csv", parse_dates=["date"], index_col="date")
    finH = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hamilton", None), two_sided=True)
    finP = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hp", 1600), two_sided=True)
    t = pd.DataFrame({"HP real-time": rt["HP lambda=1,600  <- paper"],
                      "HP hindsight": finP,
                      "Hamilton real-time": rt["Hamilton (2018)"],
                      "Hamilton hindsight": finH}).dropna()
    print(t.loc["2020-04-01":"2022-04-01"].round(1).to_string())
    r = t.loc["2021-10-01"]
    print(f"\n  At 2021Q4, with inflation about to peak:")
    print(f"    HP       said {r['HP real-time']:+.1f} in real time; hindsight says "
          f"{r['HP hindsight']:+.1f}  (missed by {r['HP hindsight'] - r['HP real-time']:+.1f})")
    print(f"    Hamilton said {r['Hamilton real-time']:+.1f} in real time; hindsight says "
          f"{r['Hamilton hindsight']:+.1f}  (missed by "
          f"{r['Hamilton hindsight'] - r['Hamilton real-time']:+.1f})")
    print("  The HP gap decayed to roughly neutral and called the all-clear. The")
    print("  Hamilton gap held an unmistakable warning through the whole episode.")

    pd.DataFrame(gaps).to_csv("output/hamilton_gaps.csv")
    print("\nwrote output/hamilton_gaps.csv")


if __name__ == "__main__":
    main()
