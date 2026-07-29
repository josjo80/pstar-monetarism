#!/usr/bin/env python3
"""
Chart the real-time reliability of the P-star gap.

Top:    what a policymaker saw at the time versus what the data say in
        hindsight, M2/GDP, 1992-2026.
Bottom: the current signal with a 90% band from the revision distribution.

    python plot_uncertainty.py            # needs output/realtime_gaps.csv
"""

import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pstar_replication import fetch_fred, load_cfs, price_gap
from filters import gaps_from, hamilton_recursive

RT, FINAL = "#2a78d6", "#eb6834"
BANDC = "#1baf7a"
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SHADE = "#e1e0d9", "#c3c2b7", "#f0efec"


def titled(ax, title, subtitle):
    ax.text(0, 1.155, title, transform=ax.transAxes, color=INK,
            fontsize=13.5, fontweight="bold", va="bottom")
    ax.text(0, 1.035, subtitle, transform=ax.transAxes, color=INK2,
            fontsize=9.5, va="bottom", linespacing=1.5)


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(BASELINE)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.axhline(0, color=BASELINE, lw=1.4, zorder=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfs", default="data/Divisia.xlsx")
    ap.add_argument("--rt", default="output/realtime_gaps.csv")
    ap.add_argument("--out", default="uncertainty.png")
    args = ap.parse_args()

    rt = pd.read_csv(args.rt, parse_dates=["date"], index_col="date")
    rev = (rt["gap_2sided"] - rt["gap_realtime"]).dropna()
    lo_q, hi_q = np.percentile(rev - rev.mean(), [5, 95])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 9.2), dpi=150,
        gridspec_kw=dict(height_ratios=[1, 1], hspace=0.55,
                         left=0.075, right=0.975, top=0.90, bottom=0.075))
    fig.patch.set_facecolor(SURFACE)

    # ---- top: real-time vs hindsight ----
    style(ax1)
    ax1.plot(rt.index, rt["gap_realtime"], color=RT, lw=1.9,
             label="HP(1600), real time", zorder=3)
    ax1.plot(rt.index, rt["gap_2sided"], color=FINAL, lw=1.9,
             label="HP(1600), hindsight", zorder=3)
    rf = pd.read_csv("output/realtime_filters.csv", parse_dates=["date"], index_col="date")
    ax1.plot(rf.index, rf["Hamilton (2018)"], color=BANDC, lw=2.1,
             label="Hamilton (2018), real time", zorder=4)
    titled(ax1, "The HP filter loses the signal in real time; the Hamilton filter keeps it",
           "M2/GDP price gap. HP(1600) revises by 3.13pp against a gap varying by 2.88pp and gets the "
           "sign wrong in 33% of\nquarters; Hamilton (2018) revises by 1.65pp and errs on sign in 11%.")
    ax1.set_ylabel("percentage points", color=MUTED, fontsize=9.5)
    ax1.set_ylim(-20, 28)
    leg = ax1.legend(frameon=False, fontsize=9.5, loc="upper left", handlelength=1.6,
                     borderaxespad=0.8)
    for t in leg.get_texts():
        t.set_color(INK2)
    ax1.annotate("2021Q4: HP real time reads +2.2 and calls\nthe all-clear. Hamilton reads +18.7 and holds\nthe warning. Inflation was about to peak.",
                 xy=(pd.Timestamp("2021-10-01"), 10.0),
                 xytext=(pd.Timestamp("1992-06-01"), -16.5),
                 color=INK2, fontsize=9, linespacing=1.45, va="center",
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))

    # ---- bottom: current signal against the band ----
    style(ax2)
    from pstar_replication import build_nowcast_row
    df = fetch_fred().join(load_cfs(args.cfs), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    df2, qn, _info = build_nowcast_row(df, args.cfs, verbose=False)
    g = hamilton_recursive(df2["ngdp"], df2["rgdp"], df2["DM2"]).loc["2023-01-01":]
    finH = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hamilton", None), two_sided=True)
    revH = (finH - rf["Hamilton (2018)"]).dropna()
    revH = revH - revH.mean()
    lo_q, hi_q = np.percentile(revH, [5, 95])

    ax2.fill_between(g.index, g + lo_q, g + hi_q, color=BANDC, alpha=0.16,
                     lw=0, zorder=2, label="90% band from the revision distribution")
    ax2.plot(g.index[:-1], g.iloc[:-1], color=BANDC, lw=2.2, marker="o", ms=4.5,
             mec=SURFACE, mew=1.2, zorder=4, label="Divisia M2 / GDP, Hamilton filter")
    ax2.plot(g.index[-2:], g.iloc[-2:], color=BANDC, lw=2.2, ls=":", zorder=4)
    ax2.plot([g.index[-1]], [g.iloc[-1]], marker="o", ms=7.5, mfc=SURFACE, mec=BANDC,
             mew=2.0, ls="none", color=BANDC, zorder=5,
             label="2026Q2 nowcast (Q2 NIPAs not yet released)")
    ax2.annotate(f"  {g.iloc[-1]:+.2f}\n  90% band\n  [{g.iloc[-1] + lo_q:+.2f}, "
                 f"{g.iloc[-1] + hi_q:+.2f}]", xy=(g.index[-1], g.iloc[-1]),
                 color=INK2, fontsize=9, va="center", linespacing=1.5)
    titled(ax2, "On the better filter, the current signal clears zero",
           "Divisia M2 / GDP on the Hamilton filter, with a 90% band from its own revision "
           "distribution.\nTwo of the six specifications now exclude zero; on HP(1600) none of "
           "them did.")
    ax2.set_ylabel("percentage points", color=MUTED, fontsize=9.5)
    ax2.set_xlim(pd.Timestamp("2022-11-15"), pd.Timestamp("2026-12-01"))
    leg2 = ax2.legend(frameon=False, fontsize=9.5, loc="lower right", handlelength=1.6)
    for t in leg2.get_texts():
        t.set_color(INK2)

    fig.text(0.075, 0.018,
             "Sources: ALFRED vintages of GDP, GDPC1, M2SL (1992-2026); FRED; CFS Divisia. "
             "Revision distribution measured on M2/GDP, the only\nspecification with a public "
             "vintage archive. Hamilton (2018) filter, h = 8, p = 4.",
             color=MUTED, fontsize=8, linespacing=1.5)

    fig.savefig(args.out, facecolor=SURFACE)
    print(f"wrote {args.out}")
    print(f"band applied: [{lo_q:+.2f}, {hi_q:+.2f}] pp")


if __name__ == "__main__":
    main()
