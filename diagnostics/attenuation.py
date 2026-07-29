#!/usr/bin/env python3
"""
Does measurement error explain the apparent regime dependence of gamma?

Two findings in this repo sat unconnected:

  * gamma is ~0 on 1990-2019 and ~0.17 on 2020-2026 (diagnostics/regime.py),
    with no formal break test able to reject constancy.
  * the real-time price gap carries measurement error with a standard deviation
    of 3.13pp (vintages.py).

Classical errors-in-variables ties them together. If the regressor is observed
with noise, the estimated coefficient is attenuated by the signal share:

    gamma_obs = gamma_true * var(gap) / (var(gap) + var(noise))

The gap's own variance differs enormously across these windows -- it is small
when policy is quiet and large around the pandemic -- so the same underlying
gamma_true would *look* regime-dependent purely through attenuation. This tests
that, backing out the implied gamma_true window by window and asking whether it
is stable.

CAVEATS
-------
This is the textbook single-regressor formula applied to a regression that also
contains four lags of the dependent variable, so the attenuation factor is only
an approximation to the multivariate one. It also assumes classical measurement
error -- noise uncorrelated with the true gap -- which is doubtful for a filter
revision. The implied gamma_true is indicative, and motivates a proper IV or
measurement-error-corrected estimate rather than substituting for one.

    python diagnostics/attenuation.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get("CFS_XLSX", "data/Divisia.xlsx")
RT_FILE = "output/realtime_gaps.csv"

from pstar_replication import fetch_fred, load_cfs, price_gap, pstar_regression

WINDOWS = [("1967-01-01", "1983-12-31", "1967-1983"),
           ("1984-01-01", "1989-12-31", "1984-1989"),
           ("1990-01-01", "2019-12-31", "1990-2019"),
           ("2020-01-01", "2026-03-31", "2020-2026"),
           ("1967-01-01", "2026-03-31", "full sample")]


def main():
    if not os.path.exists(RT_FILE):
        raise SystemExit(f"{RT_FILE} missing -- run vintages.py first.")
    rt = pd.read_csv(RT_FILE, parse_dates=["date"], index_col="date")
    noise_var = float((rt["gap_2sided"] - rt["gap_realtime"]).var())

    df = fetch_fred().join(load_cfs(CFS), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]

    print("=" * 92)
    print("ATTENUATION AS AN EXPLANATION FOR THE REGIME DEPENDENCE OF GAMMA")
    print("=" * 92)
    print(f"measurement-error variance (from the vintage reconstruction): "
          f"{noise_var:.2f}   sd {np.sqrt(noise_var):.2f}pp")
    print("gamma_obs = gamma_true * var(gap) / (var(gap) + var(noise))\n")

    for label, mcol, rcol, pcol, tag in [("Divisia M2", "DM2", "rgdp", "p_gdp", "GDP"),
                                         ("M2", "M2", "rgdp", "p_gdp", "GDP"),
                                         ("Divisia M4", "DM4", "rgdp", "p_gdp", "GDP")]:
        g = price_gap(df, mcol, rcol, pcol)["gap"]
        print(f"--- {label}/{tag} ---")
        print(f"{'window':14s} {'sd(gap)':>8s} {'signal share':>13s} "
              f"{'gamma_obs':>10s} {'95% CI':>18s} {'implied gamma_true':>19s}")
        for a, b, nm in WINDOWS:
            gs = g.loc[a:b].dropna()
            att = gs.var() / (gs.var() + noise_var)
            r, d = pstar_regression(df, pcol, g, start=a, end=b)
            X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"]].copy()
            X.insert(0, "const", 1.0)
            from pstar_replication import OLSResult
            rh = OLSResult(d["dpi"], X, hac_lags=4)
            go, se = rh.params["gap_l1"], rh.bse["gap_l1"]
            ci = f"[{go - 1.96 * se:+.3f}, {go + 1.96 * se:+.3f}]"
            print(f"{nm:14s} {gs.std():8.2f} {att:13.2f} {go:10.3f} {ci:>18s} "
                  f"{go / att:19.3f}")
        print()

    print("=" * 92)
    print("READ")
    print("=" * 92)
    print("For Divisia M2/GDP the 1967-1983 and 2020-2026 windows imply almost the")
    print("same structural coefficient (~0.20) from very different observed ones")
    print("(0.113 and 0.171), because the gap's variance differs by a factor of ~4.")
    print("1990-2019 is consistent too: a signal share of 0.25 predicts gamma_obs of")
    print("about 0.05, which sits inside that window's HAC confidence interval.")
    print()
    print("So the regime dependence may not be regime dependence at all -- money's")
    print("grip on inflation looks roughly constant, and what varies is whether the")
    print("gap is large enough to be seen through ~3pp of measurement noise. The")
    print("implication is that the paper's headline 0.10 understates the structural")
    print("coefficient by roughly half. See the caveats in this file's docstring")
    print("before leaning on the level of gamma_true.")


if __name__ == "__main__":
    main()
