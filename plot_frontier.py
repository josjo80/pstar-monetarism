#!/usr/bin/env python3
"""
The filter frontier: real-time reliability against predictive power.

One scatter, because the central methodological claim of the paper we are
commenting on rests on a filter choice, and the choice turns out not to sit on
the efficient frontier of its own family -- let alone the overall one.

    python plot_frontier.py          # reads output/realtime_filters.csv
"""

import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pstar_replication import fetch_fred, load_cfs
from filters import (LAMBDAS, variant_names, label, gaps_from, hamilton_recursive)
from nominal_gdp import regress, oos

BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfs", default="data/Divisia.xlsx")
    ap.add_argument("--out", default="frontier.png")
    args = ap.parse_args()

    df = fetch_fred().join(load_cfs(args.cfs), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    rt = pd.read_csv("output/realtime_filters.csv", parse_dates=["date"], index_col="date")

    pts = []
    for vnt in variant_names():
        nm = label(vnt)
        fin = gaps_from(df["ngdp"], df["rgdp"], df["M2"], vnt, two_sided=True)
        j = pd.DataFrame({"rt": rt[nm], "fin": fin}).dropna()
        ns = (j["fin"] - j["rt"]).std() / j["fin"].std()
        g = gaps_from(df["ngdp"], df["rgdp"], df["DM2"], vnt)
        r, d = regress(df, "p_gdp", g)
        pts.append((nm, ns, r.params["ind_l1"] * d["ind_l1"].std(),
                    "hp" if vnt[0] == "hp" else "ham"))

    hrec = hamilton_recursive(df["ngdp"], df["rgdp"], df["DM2"])
    r, d = regress(df, "p_gdp", hrec)
    nmh = label(("hamilton", None))
    finh = gaps_from(df["ngdp"], df["rgdp"], df["M2"], ("hamilton", None), two_sided=True)
    jh = pd.DataFrame({"rt": rt[nmh], "fin": finh}).dropna()
    pts.append(("Hamilton, recursive", (jh["fin"] - jh["rt"]).std() / jh["fin"].std(),
                r.params["ind_l1"] * d["ind_l1"].std(), "hamrec"))

    gm = 100 * (df["DM2"] / df["DM2"].shift(4) - 1)
    gm2 = 100 * (df["M2"] / df["M2"].shift(4) - 1)
    jm = pd.DataFrame({"rt": rt["money growth"], "fin": gm2}).dropna()
    r, d = regress(df, "p_gdp", gm)
    pts.append(("money growth\n(no latent trend)",
                (jm["fin"] - jm["rt"]).std() / jm["fin"].std(),
                r.params["ind_l1"] * d["ind_l1"].std(), "money"))

    P = pd.DataFrame(pts, columns=["name", "ns", "eff", "kind"])

    fig, ax = plt.subplots(figsize=(10.6, 7.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(BASELINE)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)

    hp = P[P["kind"] == "hp"].sort_values("ns")
    ax.plot(hp["ns"], hp["eff"], color=BLUE, lw=1.6, alpha=0.55, zorder=2,
            label="HP filter, $\\lambda$ from 100 to $10^6$")
    ax.scatter(hp["ns"], hp["eff"], s=70, color=BLUE, zorder=3, edgecolor=SURFACE,
               linewidth=1.2)
    for _, r_ in hp.iterrows():
        lam = r_["name"].split("=")[1].split(" ")[0]
        paper = "paper" in r_["name"]
        ax.annotate(f"  $\\lambda$={lam}" + ("  ← the paper" if paper else ""),
                    xy=(r_["ns"], r_["eff"]), color=INK if paper else MUTED,
                    fontsize=9.5 if paper else 8.5, va="center",
                    fontweight="bold" if paper else "normal")

    for kind, col, mk, txt in [("ham", ORANGE, "s", "Hamilton (2018),\nfull-sample coefs"),
                               ("hamrec", ORANGE, "D", "Hamilton (2018), recursive\ncoefs (the honest one)"),
                               ("money", AQUA, "o", "money growth,\nno latent trend")]:
        row = P[P["kind"] == kind].iloc[0]
        ax.scatter([row["ns"]], [row["eff"]], s=150, color=col, marker=mk, zorder=4,
                   edgecolor=SURFACE, linewidth=1.6)
        dx, dy = {"ham": (0.11, 0.008), "hamrec": (0.11, -0.020),
                  "money": (0.11, 0.018)}[kind]
        ax.annotate(txt, xy=(row["ns"], row["eff"]),
                    xytext=(row["ns"] + dx, row["eff"] + dy),
                    color=INK2, fontsize=9.5, linespacing=1.4, va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    ax.set_xlabel("← better        real-time noise-to-signal ratio        worse →",
                  color=INK2, fontsize=10)
    ax.set_ylabel("worse ←   predictive power for inflation   → better",
                  color=INK2, fontsize=10)
    ax.text(0, 1.115, "The paper's filter choice is not on the frontier",
            transform=ax.transAxes, color=INK, fontsize=14, fontweight="bold",
            va="bottom")
    ax.text(0, 1.02,
            "Real-time reliability is measured against ALFRED vintages, 1992–2026 (M2/GDP); predictive power is the "
            "standardised\ncoefficient on the change in GDP inflation, 1967Q1–2026Q1 (Divisia M2). Up and to the "
            "left is better on both axes.",
            transform=ax.transAxes, color=INK2, fontsize=9.5, va="bottom", linespacing=1.5)
    ax.set_xlim(-0.04, 1.55)
    ax.set_ylim(0.165, 0.445)
    leg = ax.legend(frameon=False, fontsize=9.5, loc="lower right")
    for t in leg.get_texts():
        t.set_color(INK2)

    fig.text(0.008, 0.015,
             "Sources: FRED; ALFRED; Center for Financial Stability Divisia aggregates.",
             color=MUTED, fontsize=8)
    fig.savefig(args.out, facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {args.out}")
    print(P.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
