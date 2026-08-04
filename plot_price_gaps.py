#!/usr/bin/env python3
"""
Plot the P-star price gaps from pstar_replication.py.

    python plot_price_gaps.py --cfs Divisia.xlsx

Top panel:    full history, GDP-based gaps for M2, Divisia M2, Divisia M4.
Bottom panel: 2023Q1 onward, with the paper's published 2026Q1 values marked
              and the 2026Q2 nowcast drawn as a dotted, hollow-marker segment.

Positive gap = P* above the actual price level = money is pushing inflation up.
"""

import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pstar_replication import (fetch_fred, load_cfs, _cfs_monthly, _fred_series,
                               price_gap)

# dataviz reference palette, categorical slots 1-3 (validated all-pairs, light)
SERIES = [("M2", "#2a78d6"), ("DM2", "#eb6834"), ("DM4", "#1baf7a")]
NAMES = {"M2": "M2", "DM2": "Divisia M2", "DM4": "Divisia M4"}
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, BAND = "#e1e0d9", "#c3c2b7", "#f0efec"

# Published 2026Q1 GDP-based gaps, Ireland-Miran-Roubini Table 2
PAPER_2026Q1 = {"M2": -0.25, "DM2": 0.41, "DM4": 0.79}

NOWCAST_Q = pd.Timestamp("2026-04-01")
DEFLATOR_SAAR = 3.24   # trailing 4-quarter mean of annualized GDP deflator inflation
JUNE_DIVISIA_MM = 0.00432   # June Divisia unpublished; carry M2's June m/m rate


def build(cfs_path):
    """Published data through the last complete quarter."""
    df = fetch_fred().join(load_cfs(cfs_path), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":]
    return pd.DataFrame({m: price_gap(df, m, "rgdp", "p_gdp")["gap"]
                         for m, _ in SERIES})


def _unused_nowcast(cfs_path):
    df = fetch_fred().join(load_cfs(cfs_path), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]

    def qavg(s, fill=None):
        mo = pd.date_range(NOWCAST_Q, periods=3, freq="MS")
        have = s.reindex(mo).dropna()
        g = float(s.pct_change().iloc[-1]) if fill is None else fill
        vals, last = list(have.values), have.values[-1]
        for _ in range(3 - len(have)):
            last *= 1.0 + g
            vals.append(last)
        return float(np.mean(vals))

    dm2_m, dm4_m = _cfs_monthly(cfs_path)
    nc = df.copy()
    nc.loc[NOWCAST_Q, "M2"] = qavg(_fred_series("M2SL"))
    nc.loc[NOWCAST_Q, "DM2"] = qavg(dm2_m, JUNE_DIVISIA_MM)
    nc.loc[NOWCAST_Q, "DM4"] = qavg(dm4_m, JUNE_DIVISIA_MM)
    nc.loc[NOWCAST_Q, "rgdp"] = df["rgdp"].iloc[-1] * 1.0154 ** 0.25  # irrelevant to gap
    nc.loc[NOWCAST_Q, "p_gdp"] = df["p_gdp"].iloc[-1] * np.exp(DEFLATOR_SAAR / 400)

    return pd.DataFrame({m: price_gap(nc, m, "rgdp", "p_gdp")["gap"]
                         for m, _ in SERIES})


def recessions():
    r = _fred_series("USREC")
    on = r.diff().fillna(r)
    starts = r.index[on == 1]
    ends = r.index[on == -1]
    if len(ends) < len(starts):
        ends = ends.append(pd.Index([r.index[-1]]))
    return list(zip(starts, ends))


def titled(ax, title, subtitle):
    """Title + subtitle stacked above the axes without colliding."""
    ax.text(0, 1.155, title, transform=ax.transAxes, color=INK,
            fontsize=13.5, fontweight="bold", va="bottom")
    ax.text(0, 1.035, subtitle, transform=ax.transAxes, color=INK2,
            fontsize=9.5, va="bottom", linespacing=1.5)


def declutter(items, span, min_frac=0.055):
    """Nudge (y, label, color) rows apart so right-edge labels don't overlap."""
    items = sorted(items, key=lambda r: -r[0])
    gap = span * min_frac
    for i in range(1, len(items)):
        if items[i - 1][0] - items[i][0] < gap:
            items[i] = (items[i - 1][0] - gap,) + items[i][1:]
    return items


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
    ap.add_argument("--cfs", default="Divisia.xlsx")
    ap.add_argument("--out", default="price_gaps.png")
    args = ap.parse_args()

    gaps = build(args.cfs)
    hist = gaps

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 9.6), dpi=150,
        gridspec_kw=dict(height_ratios=[1.05, 1], hspace=0.52,
                         left=0.075, right=0.975, top=0.90, bottom=0.075))
    fig.patch.set_facecolor(SURFACE)

    # ---------------- top: full history ----------------
    style(ax1)
    for m, c in SERIES:
        ax1.plot(hist.index, hist[m], color=c, lw=1.6, zorder=3, label=NAMES[m])
    for a, b in recessions():          # after the lines: registers the date converter
        if b >= hist.index[0]:
            ax1.axvspan(a, b, color=BAND, zorder=0)

    titled(ax1, "P-star price gaps, 1967Q1–2026Q2",
           "How far the money-implied equilibrium price level sits above (+) or below (−) the actual\n"
           "price level, GDP basis. Above zero, money is pushing inflation up. Shaded = NBER recessions.")
    ax1.set_ylabel("percentage points", color=MUTED, fontsize=9.5)
    ax1.set_ylim(-15, 19)
    leg = ax1.legend(frameon=False, fontsize=9.5, loc="upper left", ncol=3,
                     handlelength=1.6, borderaxespad=0.8)
    for t in leg.get_texts():
        t.set_color(INK2)

    ax1.annotate("2020–21 money surge:\nbiggest gap in 59 years",
                 xy=(pd.Timestamp("2021-04-01"), 15.6),
                 xytext=(pd.Timestamp("2005-01-01"), 16.2),
                 color=INK2, fontsize=9, ha="left", va="center", linespacing=1.4,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))
    ax1.annotate("Volcker disinflation", xy=(pd.Timestamp("1981-10-01"), -8.2),
                 xytext=(pd.Timestamp("1986-01-01"), -12.0), color=INK2, fontsize=9,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))
    ax1.annotate("2022–23 tightening", xy=(pd.Timestamp("2023-01-01"), -11.4),
                 xytext=(pd.Timestamp("2007-01-01"), -13.6), color=INK2, fontsize=9,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))

    # ---------------- bottom: recent zoom ----------------
    style(ax2)
    z = gaps.loc["2023-01-01":]
    solid = z
    for m, c in SERIES:
        ax2.plot(solid.index, solid[m], color=c, lw=2.0, marker="o", ms=4.5,
                 mec=SURFACE, mew=1.2, zorder=3)
        ax2.plot([pd.Timestamp("2026-01-01")], [PAPER_2026Q1[m]], marker="x", ms=7,
                 color=MUTED, mew=1.8, zorder=5)

    # direct labels at the right edge (text in ink; the colored dot carries identity)
    ax2.set_ylim(-13, 4)
    ax2.set_xlim(pd.Timestamp("2022-11-15"), pd.Timestamp("2027-01-15"))

    lx = pd.Timestamp("2026-07-15")
    for y, m, c in declutter([(z[m].iloc[-1], m, c) for m, c in SERIES], span=17.0):
        ax2.plot([lx], [y], marker="o", ms=5, color=c, zorder=4)
        ax2.annotate(f"   {NAMES[m]}  {z[m].iloc[-1]:+.1f}", xy=(lx, y),
                     color=INK2, fontsize=9.5, va="center")

    titled(ax2, "Zoom: the gaps have just crossed zero",
           "Grey ×  = the values published in the paper for 2026Q1. All points are published data;\n"
           "the 2026Q2 national accounts were released on 30 July 2026.")
    ax2.set_ylabel("percentage points", color=MUTED, fontsize=9.5)

    fig.text(0.075, 0.018,
             "Sources: FRED (GDP, GDPC1, M2SL, GDPNOW); Center for Financial Stability "
             "Divisia aggregates. Replication of Ireland, Miran & Roubini (July 2026), "
             "one-sided HP filter, lambda = 1600.",
             color=MUTED, fontsize=8)

    fig.savefig(args.out, facecolor=SURFACE)
    print(f"wrote {args.out}")
    print(gaps.tail(6).round(2).to_string())


if __name__ == "__main__":
    main()
