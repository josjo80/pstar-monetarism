#!/usr/bin/env python3
"""
Does the paper's supply-shock explanation actually hold up?

THE CLAIM BEING TESTED
----------------------
The paper's policy recommendation rests entirely on an attribution it never
estimates. Having found the price gap near zero, it concludes that recent high
inflation "is more likely to reflect a combination of adverse supply shocks --
for instance, energy shocks, deglobalization shocks like concerns over supply
chain security, and more -- and measurement error", and therefore that the Fed
should look through it. The word "supply" appears throughout; no supply variable
appears in any regression. The residual is simply assigned a name.

This module puts supply variables into the Hallman-Porter-Small regression and
asks three questions:

  1. Does the price-gap coefficient survive? If gamma collapses once supply is
     controlled for, the money signal was partly proxying for supply all along.
  2. Is the supply block jointly significant, and how much of the paper's
     unexplained 80% does it recover?
  3. Decomposed over 2025Q1-2026Q1, how much of the actual rise in inflation do
     supply shocks account for, versus money, versus inertia, versus nothing?

VARIABLES
---------
Two exogenous-ish measures available over the whole 1967-2026 sample:

  NOPI      Hamilton (1996) net oil price increase: 100*(log P_t - log of the
            max over the previous four quarters), floored at zero. The
            asymmetry matters -- oil price rises pass into inflation, falls
            largely do not.
  d_tariff  Change in the effective tariff rate, customs duties (BEA
            B235RC1Q027SBEA) over imports of goods and services (IMPGS). This
            is the paper's "deglobalization shock", measured.

Two more, as robustness on shorter or less exogenous ground:

  dlog_import   import price index (IR), 1983 onward
  dlog_ppi      all-commodities PPI -- a cost-push proxy, but explaining prices
                with prices, so treated as weaker evidence

CAVEAT WORTH STATING LOUDLY
---------------------------
The 2025Q2 tariff move (+4.30pp) is the largest quarterly change in the effective
tariff rate since the series begins in 1959; the next largest is +1.50pp in
1971Q4. The coefficient on d_tariff is therefore identified off a handful of
small historical episodes and extrapolated to an event far outside their range.
Treat the tariff contributions below as indicative, not measured.

    python supply_shocks.py
"""

import numpy as np
import pandas as pd

from pstar_replication import (fetch_fred, load_cfs, price_gap, OLSResult,
                               _fred_series, SPECS, SAMPLE_START, SAMPLE_END)

SUPPLY_LAGS = range(0, 4)      # attribution, so contemporaneous is included
CORE = ["NOPI", "d_tariff"]


def supply_data():
    """Quarterly supply-shock variables."""
    oil = _fred_series("WTISPLC").resample("QS").mean()
    lo = np.log(oil)
    prev_max = pd.concat([lo.shift(i) for i in range(1, 5)], axis=1).max(axis=1)
    nopi = (100.0 * (lo - prev_max)).clip(lower=0.0)

    tariff = 100.0 * _fred_series("B235RC1Q027SBEA") / _fred_series("IMPGS")
    ir = _fred_series("IR").resample("QS").mean()
    ppi = _fred_series("PPIACO").resample("QS").mean()

    return pd.DataFrame({
        "NOPI": nopi,
        "d_tariff": tariff.diff(),
        "dlog_import": 400.0 * np.log(ir).diff(),
        "dlog_ppi": 400.0 * np.log(ppi).diff(),
    })


def augmented(df, price_col, gap, supply, extra=(), lags=SUPPLY_LAGS,
              start=SAMPLE_START, end=SAMPLE_END, hac=4):
    """
    Baseline P-star regression plus a supply block. Returns (result, frame,
    supply column names).
    """
    pi = 400.0 * np.log(df[price_col]).diff()
    dpi = pi.diff()

    d = pd.DataFrame({"dpi": dpi, "gap_l1": gap.shift(1)})
    for i in range(1, 5):
        d[f"dpi_l{i}"] = dpi.shift(i)

    scols = []
    for v in list(CORE) + list(extra):
        for j in lags:
            name = f"{v}_l{j}"
            d[name] = supply[v].reindex(df.index).shift(j)
            scols.append(name)

    d = d.loc[start:end].dropna()
    X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"] + scols].copy()
    X.insert(0, "const", 1.0)
    return OLSResult(d["dpi"], X, hac_lags=hac), d, scols


def block_f(y, X, drop):
    """F test that the `drop` columns are jointly zero."""
    def ssr(Xa):
        b, *_ = np.linalg.lstsq(Xa.values, y.values, rcond=None)
        r = y.values - Xa.values @ b
        return r @ r
    n, k = X.shape
    u, rstr = ssr(X), ssr(X.drop(columns=drop))
    q = len(drop)
    return ((rstr - u) / q) / (u / (n - k))


def main():
    df = fetch_fred().join(load_cfs("data/Divisia.xlsx"), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    S = supply_data()

    print("=" * 100)
    print("1. DOES THE MONEY SIGNAL SURVIVE SUPPLY CONTROLS?  (1967Q1-2026Q1, HAC 4)")
    print("=" * 100)
    print(f"{'spec':18s} {'gamma base':>11s} {'gamma +supply':>14s} {'t':>7s} "
          f"{'R2 base':>8s} {'R2 +sup':>8s} {'F(supply)':>10s}")
    for label, mcol, rcol, pcol, tag in SPECS:
        g = price_gap(df, mcol, rcol, pcol)["gap"]
        base, d0, _ = augmented(df, pcol, g, S, lags=[])       # no supply block
        aug, d1, sc = augmented(df, pcol, g, S)
        X1 = d1[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"] + sc].copy()
        X1.insert(0, "const", 1.0)
        F = block_f(d1["dpi"], X1, sc)
        print(f"{label + '/' + tag:18s} {base.params['gap_l1']:11.3f} "
              f"{aug.params['gap_l1']:14.3f} {aug.tvalues['gap_l1']:7.2f} "
              f"{base.rsquared:8.3f} {aug.rsquared:8.3f} {F:10.2f}")

    print("\n(5% critical value for F(8, ~200) is about 1.98)")

    print("\n" + "=" * 100)
    print("2. WHICH SUPPLY VARIABLES MATTER?   Divisia M2 / GDP, HAC t-statistics")
    print("=" * 100)
    g = price_gap(df, "DM2", "rgdp", "p_gdp")["gap"]
    aug, d1, sc = augmented(df, "p_gdp", g, S)
    for nm in ["gap_l1"] + sc:
        print(f"  {nm:16s} {aug.params[nm]:+8.4f}   t = {aug.tvalues[nm]:6.2f}")
    print(f"\n  sum of NOPI coefficients      "
          f"{sum(aug.params[f'NOPI_l{j}'] for j in SUPPLY_LAGS):+.4f}")
    print(f"  sum of d_tariff coefficients  "
          f"{sum(aug.params[f'd_tariff_l{j}'] for j in SUPPLY_LAGS):+.4f}")

    print("\n" + "=" * 100)
    print("3. WHAT ACTUALLY DROVE INFLATION IN 2025Q1-2026Q1?")
    print("=" * 100)
    for label, mcol, rcol, pcol, tag in [("Divisia M2", "DM2", "rgdp", "p_gdp", "GDP"),
                                         ("Divisia M2", "DM2", "rpce", "p_pce", "PCE")]:
        g = price_gap(df, mcol, rcol, pcol)["gap"]
        aug, d1, sc = augmented(df, pcol, g, S)
        b = aug.params
        win = d1.loc["2025-01-01":"2026-01-01"]
        parts = pd.DataFrame(index=win.index)
        parts["inertia"] = sum(b[f"dpi_l{i}"] * win[f"dpi_l{i}"] for i in range(1, 5))
        parts["money (gap)"] = b["gap_l1"] * win["gap_l1"]
        parts["oil"] = sum(b[f"NOPI_l{j}"] * win[f"NOPI_l{j}"] for j in SUPPLY_LAGS)
        parts["tariffs"] = sum(b[f"d_tariff_l{j}"] * win[f"d_tariff_l{j}"]
                               for j in SUPPLY_LAGS)
        parts["constant"] = b["const"]
        parts["unexplained"] = win["dpi"] - parts.sum(axis=1)
        parts["ACTUAL dInfl"] = win["dpi"]

        pi = 400.0 * np.log(df[pcol]).diff()
        print(f"\n--- {tag} inflation, {label} gap ---")
        print(f"    inflation {pi.loc['2024-10-01']:.2f}% (2024Q4) -> "
              f"{pi.loc['2026-01-01']:.2f}% (2026Q1)")
        print(parts.round(2).to_string())
        tot = parts.sum()
        print(f"\n    cumulated over the five quarters (pp of inflation):")
        for k in ["inertia", "money (gap)", "oil", "tariffs", "constant",
                  "unexplained", "ACTUAL dInfl"]:
            print(f"      {k:16s} {tot[k]:+6.2f}")

    print("\n" + "=" * 100)
    print("4. ROBUSTNESS: adding import prices (1983+) and PPI")
    print("=" * 100)
    g = price_gap(df, "DM2", "rgdp", "p_gdp")["gap"]
    for extra, start, nm in [((), "1967-01-01", "core only (oil + tariffs)"),
                             (("dlog_import",), "1983-10-01", "+ import prices"),
                             (("dlog_ppi",), "1967-01-01", "+ PPI"),
                             (("dlog_import", "dlog_ppi"), "1983-10-01", "+ both")]:
        r, dd, scc = augmented(df, "p_gdp", g, S, extra=extra, start=start)
        print(f"  {nm:28s} n={int(r.nobs):3d}  gamma={r.params['gap_l1']:+.3f} "
              f"(t {r.tvalues['gap_l1']:5.2f})  R2={r.rsquared:.3f}")

    print("\n" + "=" * 100)
    print("5. FORECASTING VARIANT: supply block lagged 1-4 only (no contemporaneous)")
    print("=" * 100)
    for label, mcol, rcol, pcol, tag in SPECS:
        g = price_gap(df, mcol, rcol, pcol)["gap"]
        r, _dd, _sc = augmented(df, pcol, g, S, lags=range(1, 5))
        print(f"  {label + '/' + tag:18s} gamma={r.params['gap_l1']:+.3f} "
              f"(t {r.tvalues['gap_l1']:5.2f})  R2={r.rsquared:.3f}")

    print("\n" + "=" * 100)
    print("6. THE OIL SHOCK NOW UNDERWAY, AND WHAT IT IMPLIES FORWARD")
    print("=" * 100)
    nopi_now = float(S["NOPI"].loc["2026-04-01"])
    rank = int((S["NOPI"] > nopi_now).sum()) + 1
    print(f"  2026Q2 NOPI = {nopi_now:.1f}  (rank {rank} of {S['NOPI'].notna().sum()} "
          f"quarters since 1946)")
    oilq = _fred_series("WTISPLC").resample("QS").mean()
    print("  quarterly average WTI: " + " -> ".join(
        f"{d:%YQ}{(d.month - 1) // 3 + 1} ${oilq.loc[d]:.2f}"
        for d in pd.date_range("2025-10-01", "2026-04-01", freq="QS")) + "\n")
    for label, mcol, rcol, pcol, tag in [("Divisia M2", "DM2", "rgdp", "p_gdp", "GDP"),
                                         ("Divisia M2", "DM2", "rpce", "p_pce", "PCE")]:
        g = price_gap(df, mcol, rcol, pcol)["gap"]
        aug, _d, _s = augmented(df, pcol, g, S)
        gap_now = float(g.loc["2026-01-01"])
        path = [aug.params[f"NOPI_l{j}"] * nopi_now for j in SUPPLY_LAGS]
        print(f"  --- {tag} inflation ---")
        for j, q in enumerate(["2026Q2", "2026Q3", "2026Q4", "2027Q1"]):
            print(f"     {q} contribution to the change in inflation: {path[j]:+.2f} pp")
        print(f"     cumulated effect on the LEVEL of inflation by 2027Q1: "
              f"{sum(path):+.2f} pp")
        print(f"     for comparison, the money signal (gamma x gap): "
              f"{aug.params['gap_l1'] * gap_now:+.2f} pp\n")
    print("  The oil shock is an order of magnitude larger than the monetary signal,")
    print("  and it is arriving roughly a year earlier than the paper's own hedge")
    print("  ('if oil prices continue to climb in the second half of 2027') assumed.")
    print("  NOPI is asymmetric, so a partial reversal in oil would not net this off.")


if __name__ == "__main__":
    main()
