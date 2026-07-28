#!/usr/bin/env python3
"""
How much do we actually know about the current price gap?

Everything this repo (and the paper) reports downstream of the gap is a point
estimate: "policy is approximately neutral", "the gaps have crossed zero",
"+17bp on inflation". This puts a band on those statements.

THREE SOURCES OF UNCERTAINTY
----------------------------
1. Filter endpoint. The one-sided HP estimate of v* and x* at the sample end is
   revised heavily as data arrives. Measured empirically in `vintages.py`:
   sd 3.13pp against a final two-sided benchmark, 2.16pp against a 5-year
   hindsight benchmark. This dominates everything else.
2. Data revision. Also from `vintages.py`, and small by comparison: sd 0.31pp.
3. Parameter uncertainty in gamma, which is itself understated by textbook
   standard errors because the gap is a *generated* regressor -- built from
   filtered estimates, then handed to the regression as if observed.

TWO DIFFERENT QUESTIONS
-----------------------
These need separating, and conflating them produces nonsense.

Q1. *What is the stance of policy right now?* That is a question about the true
    gap, of which the published number is a noisy estimate. The revision
    distribution above is exactly the right band. This is the headline.

Q2. *What does the model forecast for next quarter's inflation?* That question
    conditions on the gap we actually observe. gamma_hat is the projection of
    d.inflation on the *measured* gap, so gamma_hat x measured_gap is already
    the right point forecast -- the attenuation in gamma_hat from noisy
    historical gaps is what makes it right. Adding revision noise on top would
    double-count. The uncertainty here is gamma's sampling error, and it is
    dwarfed by the regression's own residual spread.

METHOD
------
Q1: percentiles of gap_now + moving-block draws from the revision residuals.
    Revisions are strongly serially correlated (see 2019, where real-time read
    ~0 for three straight quarters against a final estimate near -7), so draws
    are blocks, not iid.

Q2: block-wild bootstrap of the regression (Rademacher weights held constant
    within blocks, design matrix fixed), giving gamma's sampling distribution
    under heteroskedasticity and serial correlation.

Reported separately: an attenuation diagnostic. Re-estimating gamma on a gap
deliberately contaminated with extra revision noise shows how much measurement
error is already pulling gamma_hat toward zero -- relevant to the *structural*
reading of gamma, not to forecasting with it.

CAVEAT
------
ALFRED archives FRED series only, so the revision distribution is measured on
the simple-sum M2/GDP specification. Applying it to the Divisia specifications
assumes their filter-endpoint revisions behave similarly. That is plausible --
the endpoint problem is a property of the filter, not of the aggregate -- but it
is an assumption, and Divisia rows below are labelled accordingly.

    python diagnostics/uncertainty.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get("CFS_XLSX", "data/Divisia.xlsx")

from pstar_replication import (fetch_fred, load_cfs, price_gap, pstar_regression,
                               OLSResult, SPECS)

RNG = np.random.default_rng(20260728)
NBOOT = 2000
BLOCK = 12          # quarters; revisions are highly persistent
RT_FILE = "output/realtime_gaps.csv"


def moving_block(resid, n, rng=RNG, block=BLOCK):
    """Moving-block bootstrap draw of length n from a residual series."""
    r = np.asarray(resid, float)
    m = len(r)
    out = []
    while len(out) < n:
        s = rng.integers(0, m - block)
        out.extend(r[s:s + block])
    return np.array(out[:n])


def main():
    if not os.path.exists(RT_FILE):
        raise SystemExit(f"{RT_FILE} missing -- run `python vintages.py --fetch` "
                         "then `python vintages.py` first.")
    rt = pd.read_csv(RT_FILE, parse_dates=["date"], index_col="date")

    # Revision residuals, demeaned so the bootstrap adds dispersion, not bias.
    rev = (rt["gap_2sided"] - rt["gap_realtime"]).dropna()
    rev = rev - rev.mean()
    rev5 = (rt["gap_5yr"] - rt["gap_realtime"]).dropna() if "gap_5yr" in rt else None
    if rev5 is not None:
        rev5 = rev5 - rev5.mean()

    print("=" * 92)
    print("REVISION DISTRIBUTION OF THE REAL-TIME PRICE GAP  (M2/GDP, 1992-2026)")
    print("=" * 92)
    print(f"  vs final two-sided      sd {rev.std():.2f}pp   "
          f"5th/95th pct [{np.percentile(rev, 5):+.2f}, {np.percentile(rev, 95):+.2f}]")
    if rev5 is not None:
        print(f"  vs 5-year hindsight     sd {rev5.std():.2f}pp   "
              f"5th/95th pct [{np.percentile(rev5, 5):+.2f}, {np.percentile(rev5, 95):+.2f}]")
    print(f"  sd of the gap itself    {rt['gap_2sided'].std():.2f}pp")
    print(f"  -> noise-to-signal      {rev.std() / rt['gap_2sided'].std():.2f}")

    df = fetch_fred().join(load_cfs(CFS), how="left")
    df = df.dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]

    print("\n" + "=" * 92)
    print("Q1. WHAT IS THE STANCE OF POLICY?   true gap, 90% band from the revision"
          " distribution")
    print("=" * 92)
    print(f"{'spec':18s} {'2026Q1':>9s} {'90% band':>20s} {'sign certain?':>15s}")
    for label, mcol, rcol, pcol, tag in SPECS:
        g = price_gap(df, mcol, rcol, pcol)["gap"]
        now = float(g.loc["2026-01-01"])
        draws = now + moving_block(rev.values, NBOOT)
        lo, hi = np.percentile(draws, [5, 95])
        certain = "yes" if lo > 0 or hi < 0 else "NO -- spans 0"
        note = "" if mcol == "M2" else "*"
        print(f"{label + '/' + tag + note:18s} {now:+9.2f} "
              f"{'[' + f'{lo:+.2f}, {hi:+.2f}' + ']':>20s} {certain:>15s}")

    print("\n" + "=" * 92)
    print(f"Q2. WHAT DOES IT FORECAST?   gamma sampling error, block-wild bootstrap "
          f"({NBOOT} reps)")
    print("=" * 92)
    print(f"{'spec':18s} {'gamma':>7s} {'90% CI':>18s} {'dInfl(bp)':>11s} "
          f"{'90% CI':>16s} {'resid sd (bp)':>14s}")

    for label, mcol, rcol, pcol, tag in SPECS:
        gseries = price_gap(df, mcol, rcol, pcol)["gap"]
        base, d = pstar_regression(df, pcol, gseries)
        gap_now = float(gseries.loc["2026-01-01"])
        X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"]].copy()
        X.insert(0, "const", 1.0)
        Xv, yv = X.values, d["dpi"].values
        b0, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
        r0 = yv - Xv @ b0
        fit0, n = Xv @ b0, len(yv)
        j = list(X.columns).index("gap_l1")

        gams = []
        for _ in range(NBOOT):
            w = np.repeat(RNG.choice([-1.0, 1.0], size=n // BLOCK + 1), BLOCK)[:n]
            bb, *_ = np.linalg.lstsq(Xv, fit0 + r0 * w, rcond=None)
            gams.append(bb[j])
        gq = np.percentile(gams, [5, 95])
        print(f"{label + '/' + tag:18s} {base.params['gap_l1']:7.3f} "
              f"{'[' + f'{gq[0]:+.3f}, {gq[1]:+.3f}' + ']':>18s} "
              f"{100 * base.params['gap_l1'] * gap_now:+11.0f} "
              f"{'[' + f'{100 * gq[0] * gap_now:+.0f}, {100 * gq[1] * gap_now:+.0f}' + ']':>16s} "
              f"{100 * r0.std():14.0f}")
        pd.DataFrame({"gamma": gams}).to_csv(f"output/boot_{mcol}_{tag}.csv", index=False)

    print("\n" + "=" * 92)
    print("ATTENUATION DIAGNOSTIC: how much is measurement error already shrinking gamma?")
    print("=" * 92)
    gseries = price_gap(df, "M2", "rgdp", "p_gdp")["gap"]
    base, _ = pstar_regression(df, "p_gdp", gseries)
    att = []
    for _ in range(400):
        pert = pd.Series(moving_block(rev.values, len(gseries)), index=gseries.index)
        r, _dd = pstar_regression(df, "p_gdp", gseries + pert)
        att.append(r.params["gap_l1"])
    print(f"  M2/GDP gamma on the published gap                 {base.params['gap_l1']:.3f}")
    print(f"  ... after adding one more revision's worth of noise {np.mean(att):.3f}")
    print(f"  -> each extra dose of gap noise shrinks gamma by ~"
          f"{100 * (1 - np.mean(att) / base.params['gap_l1']):.0f}%, so the structural")
    print("     coefficient is larger than the fitted one. That matters for reading")
    print("     gamma as economics; it does not change the forecast, which conditions")
    print("     on the measured gap and wants the attenuated coefficient.")

    print("\n* revision distribution borrowed from M2/GDP; ALFRED has no Divisia vintages.")
    print("None of these bands include uncertainty about the model itself.")


if __name__ == "__main__":
    main()
