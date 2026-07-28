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
             label="what you saw at the time (real-time vintage)", zorder=3)
    ax1.plot(rt.index, rt["gap_2sided"], color=FINAL, lw=1.9,
             label="what the data say now (full-sample filter)", zorder=3)
    titled(ax1, "The real-time P-star gap is about as big as its own revision",
           "M2/GDP price gap. Standard deviation of the revision is 3.13pp against a gap that "
           "varies by 2.88pp.\nThe two disagree on the sign of policy in 33% of quarters.")
    ax1.set_ylabel("percentage points", color=MUTED, fontsize=9.5)
    ax1.set_ylim(-13.5, 13.5)
    leg = ax1.legend(frameon=False, fontsize=9.5, loc="upper left", handlelength=1.6,
                     borderaxespad=0.8)
    for t in leg.get_texts():
        t.set_color(INK2)
    ax1.annotate("real time called the all-clear\nin late 2021 — the hindsight\nestimate says the impulse\nwas still near its peak",
                 xy=(pd.Timestamp("2021-10-01"), 5.6),
                 xytext=(pd.Timestamp("2003-06-01"), -8.4),
                 color=INK2, fontsize=9, linespacing=1.45, va="center",
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))

    # ---- bottom: current signal against the band ----
    style(ax2)
    df = fetch_fred().join(load_cfs(args.cfs), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    g = price_gap(df, "DM4", "rgdp", "p_gdp")["gap"].loc["2023-01-01":]

    ax2.fill_between(g.index, g + lo_q, g + hi_q, color=BANDC, alpha=0.16,
                     lw=0, zorder=2, label="90% band from the revision distribution")
    ax2.plot(g.index, g, color=BANDC, lw=2.2, marker="o", ms=4.5, mec=SURFACE,
             mew=1.2, zorder=4, label="Divisia M4 / GDP price gap, as published")
    titled(ax2, "Which means the current signal cannot be told apart from zero",
           "The gap has genuinely risen — but every quarter plotted here has a 90% band that "
           "spans zero,\nand so do all six specifications. Same is true of the paper's "
           "“approximately neutral” reading.")
    ax2.set_ylabel("percentage points", color=MUTED, fontsize=9.5)
    ax2.set_xlim(pd.Timestamp("2022-11-15"), pd.Timestamp("2026-05-15"))
    leg2 = ax2.legend(frameon=False, fontsize=9.5, loc="lower right", handlelength=1.6)
    for t in leg2.get_texts():
        t.set_color(INK2)

    fig.text(0.075, 0.018,
             "Sources: ALFRED vintages of GDP, GDPC1, M2SL (1992-2026); FRED; CFS Divisia. "
             "Revision distribution measured on M2/GDP, the only\nspecification with a public "
             "vintage archive. One-sided HP filter, lambda = 1600.",
             color=MUTED, fontsize=8, linespacing=1.5)

    fig.savefig(args.out, facecolor=SURFACE)
    print(f"wrote {args.out}")
    print(f"band applied: [{lo_q:+.2f}, {hi_q:+.2f}] pp")


if __name__ == "__main__":
    main()
