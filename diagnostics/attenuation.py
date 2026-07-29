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

    # ---- the falsification test -------------------------------------------
    # If attenuation were the whole story, an indicator measured almost without
    # error should show no regime dependence. Money growth is such an indicator
    # (noise-to-signal 0.06, nominal_gdp.py). Run the same windows on it.
    from nominal_gdp import build_indicators, regress
    ind = build_indicators(df["ngdp"], df["rgdp"], df["DM2"])
    rt_i = pd.read_csv("output/realtime_indicators.csv", parse_dates=["date"],
                       index_col="date")
    fin2 = build_indicators(df["ngdp"], df["rgdp"], df["M2"], two_sided=True)

    print("=" * 92)
    print("FALSIFICATION: does the pattern survive in a near-noise-free indicator?")
    print("=" * 92)
    for k in ["price gap", "money growth"]:
        jj = pd.DataFrame({"rt": rt_i[k], "fin": fin2[k]}).dropna()
        nv = float((jj["fin"] - jj["rt"]).var())
        print(f"\n--- {k}   (measurement-error variance {nv:.3f}) ---")
        print(f"{'window':14s} {'sd':>7s} {'signal share':>13s} {'coef':>9s} "
              f"{'HAC se':>8s} {'implied true':>13s}")
        keep = {}
        for a, b, nm in WINDOWS[:1] + WINDOWS[2:4]:
            ss = ind[k].loc[a:b].dropna()
            att = ss.var() / (ss.var() + nv)
            rr, dd = regress(df, "p_gdp", ind[k], start=a, end=b)
            c, se = rr.params["ind_l1"], rr.bse["ind_l1"]
            keep[nm] = (c, se)
            print(f"{nm:14s} {ss.std():7.2f} {att:13.3f} {c:+9.4f} {se:8.4f} "
                  f"{c / att:13.4f}")
        c1, s1 = keep["1990-2019"]
        c2, s2 = keep["2020-2026"]
        t = (c2 - c1) / np.sqrt(s1 ** 2 + s2 ** 2)
        print(f"  difference 2020-2026 minus 1990-2019: {c2 - c1:+.4f}  t = {t:.2f}")

    print("\n" + "=" * 92)
    print("READ")
    print("=" * 92)
    print("Attenuation is real for the price gap: the 1967-1983 and 2020-2026 windows")
    print("imply almost the same structural coefficient (~0.20) from very different")
    print("observed ones, because the gap's variance differs by a factor of ~4, and")
    print("1990-2019 is consistent with it too.")
    print()
    print("But it is NOT the whole story. Money growth carries almost no measurement")
    print("error -- signal shares of 0.985 to 0.999, so essentially no attenuation --")
    print("and it shows the same regime pattern, with the 2020-2026 vs 1990-2019")
    print("difference significant at t ~ 3.1. Cleaning up the measurement error makes")
    print("the regime dependence sharper, not weaker.")
    print()
    print("So: measurement error inflates how unstable the *price gap* coefficient")
    print("looks, and correcting for it does suggest the paper's 0.10 understates the")
    print("structural coefficient. But there is genuine regime dependence in the")
    print("money-inflation relationship underneath, which attenuation cannot explain")
    print("away. Both things are true.")


if __name__ == "__main__":
    main()
