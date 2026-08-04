#!/usr/bin/env python3
"""
The surviving indicators, with uncertainty bands.

Top row     Hamilton price gap by monetary aggregate, each with a 90% band from
            its own revision distribution. Small multiples rather than one panel,
            because three overlapping uncertainty bands are unreadable.
Bottom left Why the aggregates disagree. The Hamilton velocity gap decomposes
            exactly into an expected 8-quarter velocity change (from the series'
            own fitted dynamics) plus actual 8-quarter excess money growth.
Bottom right The trend-free reading: 4-quarter money growth against the speed
            limit, which carries almost no measurement error.

    python plot_models.py
"""

import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pstar_replication import fetch_fred, load_cfs
from filters import hamilton_cycle, hamilton_recursive, gaps_from, HAM_H, HAM_P

# dataviz reference palette, categorical slots 1-3 (validated all-pairs, light)
COLS = {"M2": "#2a78d6", "DM2": "#eb6834", "DM4": "#1baf7a"}
NAMES = {"M2": "M2", "DM2": "Divisia M2", "DM4": "Divisia M4"}
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SHADE = "#e1e0d9", "#c3c2b7", "#f0efec"
SPEED_LO, SPEED_HI = 4.25, 5.0


def style(ax, zero=True):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(BASELINE)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
    if zero:
        ax.axhline(0, color=BASELINE, lw=1.3, zorder=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfs", default="data/Divisia.xlsx")
    ap.add_argument("--out", default="models.png")
    args = ap.parse_args()

    df = fetch_fred().join(load_cfs(args.cfs), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":]
    df2, q = df, df.index[-1]

    rf = pd.read_csv("output/realtime_filters.csv", parse_dates=["date"], index_col="date")
    finH = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hamilton", None), two_sided=True)
    rev = (finH - rf["Hamilton (2018)"]).dropna()
    rev = rev - rev.mean()
    lo_q, hi_q = np.percentile(rev, [5, 95])

    fig = plt.figure(figsize=(12.4, 9.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.95], hspace=0.62, wspace=0.28,
                          left=0.06, right=0.975, top=0.87, bottom=0.085)

    # ---------------- top row: small multiples with bands ----------------
    fig.text(0.06, 0.955, "The Hamilton price gap, by monetary aggregate",
             color=INK, fontsize=14, fontweight="bold", va="bottom")
    fig.text(0.06, 0.905,
             "90% bands from the filter's own revision distribution (sd 1.65pp, against 3.13pp for the "
             "paper's HP filter).\nPublished data through 2026Q2. No specification now clears zero, and the "
             "bottom-left panel shows why the aggregates disagree.",
             color=INK2, fontsize=9.5, va="bottom", linespacing=1.5)

    gaps = {}
    for i, m in enumerate(["M2", "DM2", "DM4"]):
        ax = fig.add_subplot(gs[0, i])
        style(ax)
        g = hamilton_recursive(df2["ngdp"], df2["rgdp"], df2[m]).loc["2015-01-01":]
        gaps[m] = g
        c = COLS[m]
        ax.fill_between(g.index, g + lo_q, g + hi_q, color=c, alpha=0.15, lw=0, zorder=2)
        ax.plot(g.index, g, color=c, lw=1.9, zorder=3)
        ax.plot([g.index[-1]], [g.iloc[-1]], marker="o", ms=6, color=c,
                mec=SURFACE, mew=1.4, zorder=4)
        ax.set_ylim(-22, 32)
        ax.set_xlim(pd.Timestamp("2014-10-01"), pd.Timestamp("2026-10-01"))
        ax.set_title(f"{NAMES[m]}   2026Q2 {g.iloc[-1]:+.2f}  "
                     f"[{g.iloc[-1] + lo_q:+.1f}, {g.iloc[-1] + hi_q:+.1f}]",
                     color=INK2, fontsize=9.5, loc="left", pad=8)
        if i == 0:
            ax.set_ylabel("percentage points", color=MUTED, fontsize=9)
        clears = (g.iloc[-1] + lo_q) > 0
        ax.text(0.97, 0.05, "clears zero" if clears else "spans zero",
                transform=ax.transAxes, ha="right", color=INK2 if clears else MUTED,
                fontsize=9, fontweight="bold" if clears else "normal")

    # ---------------- bottom left: the decomposition ----------------
    ax = fig.add_subplot(gs[1, 0:2])
    style(ax)
    n = np.log(df2["ngdp"])
    dec = []
    for m in ["M2", "DM2", "DM4"]:
        v = (n - np.log(df2[m])).dropna()
        _vc, b = hamilton_cycle(v)
        X = pd.DataFrame({f"l{j}": v.shift(HAM_H + j) for j in range(HAM_P)})
        X.insert(0, "const", 1.0)
        fit = pd.Series(X.values @ b, index=v.index)
        drift = 100 * (fit.loc[q] - v.shift(HAM_H).loc[q])
        lm = np.log(df2[m])
        excess = 100 * ((lm.loc[q] - lm.shift(8).loc[q]) - (n.loc[q] - n.shift(8).loc[q]))
        dec.append((m, drift, excess))

    xs = np.arange(3)
    w = 0.34
    ax.bar(xs - w / 2, [d[1] for d in dec], w, color="#4a3aa7", zorder=3,
           label="expected 8q velocity change (the filter's extrapolation)")
    ax.bar(xs + w / 2, [d[2] for d in dec], w, color="#eda100", zorder=3,
           label="8q excess money growth (what money actually did)")
    for k, (m, dr, ex) in enumerate(dec):
        ax.plot([xs[k]], [dr + ex], marker="D", ms=8, color=COLS[m], mec=SURFACE,
                mew=1.4, zorder=5)
        ax.annotate(f"  gap {dr + ex:+.2f}", xy=(xs[k], dr + ex), color=INK2,
                    fontsize=9, va="center")
    ax.set_xticks(xs)
    ax.set_xticklabels([NAMES[d[0]] for d in dec], color=INK2, fontsize=9.5)
    ax.set_ylim(-2.5, 5.6)
    ax.set_ylabel("percentage points", color=MUTED, fontsize=9)
    ax.text(0, 1.19, "Why the aggregates disagree", transform=ax.transAxes,
            color=INK, fontsize=12.5, fontweight="bold", va="bottom")
    ax.text(0, 1.04,
            "The Hamilton velocity gap splits exactly into these two pieces. Excess money growth is "
            "negative for all three and\ndiffers by 1.1pp; the filter's extrapolation of each series' own "
            "velocity history differs by 3.6pp.",
            transform=ax.transAxes, color=INK2, fontsize=9, va="bottom", linespacing=1.5)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper right", handlelength=1.4)
    for t_ in leg.get_texts():
        t_.set_color(INK2)

    # ---------------- bottom right: trend-free reading ----------------
    ax = fig.add_subplot(gs[1, 2])
    style(ax, zero=False)
    ax.axhspan(SPEED_LO, SPEED_HI, color=SHADE, zorder=1)
    for m in ["M2", "DM2", "DM4"]:
        g4 = (100 * (df2[m] / df2[m].shift(4) - 1)).loc["2015-01-01":]
        ax.plot(g4.index, g4, color=COLS[m], lw=1.9, zorder=3, label=NAMES[m])
        ax.plot([g4.index[-1]], [g4.iloc[-1]], marker="o", ms=6, color=COLS[m],
                mec=SURFACE, mew=1.4, zorder=4)
    ax.set_xlim(pd.Timestamp("2014-10-01"), pd.Timestamp("2026-10-01"))
    ax.annotate("shaded = speed limit\n(potential + 2%)",
                xy=(pd.Timestamp("2017-06-01"), (SPEED_LO + SPEED_HI) / 2),
                xytext=(pd.Timestamp("2015-03-01"), 21),
                color=MUTED, fontsize=8.5, linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_ylabel("%, 4-quarter", color=MUTED, fontsize=9)
    ax.text(0, 1.19, "The reading that needs no filter", transform=ax.transAxes,
            color=INK, fontsize=12.5, fontweight="bold", va="bottom")
    ax.text(0, 1.04,
            "Money growth against potential nominal\ngrowth. Noise-to-signal 0.06.",
            transform=ax.transAxes, color=INK2, fontsize=9, va="bottom", linespacing=1.5)
    leg = ax.legend(frameon=False, fontsize=8.5, loc="lower left", handlelength=1.4)
    for t_ in leg.get_texts():
        t_.set_color(INK2)

    fig.text(0.06, 0.02,
             "Sources: FRED; CFS Divisia; ALFRED vintages 1992-2026. Hamilton (2018) filter, h = 8, p = 4, "
             "coefficients estimated on an expanding window.\nPublished data through 2026Q2.",
             color=MUTED, fontsize=8, linespacing=1.5)

    fig.savefig(args.out, facecolor=SURFACE)
    print(f"wrote {args.out}")
    for m, dr, ex in dec:
        print(f"  {NAMES[m]:12s} extrapolation {dr:+.2f} + excess money {ex:+.2f} "
              f"= gap {dr + ex:+.2f}")


if __name__ == "__main__":
    main()
