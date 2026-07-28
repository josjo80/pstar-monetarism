#!/usr/bin/env python3
"""
Real-time (vintage) reconstruction of the P-star price gap.

WHY
---
The paper's case for the one-sided HP filter is that it "can be used to produce
estimates of equilibrium velocity in real time, which can then be used by
policymakers in practice." But the estimates themselves are computed on
*final, revised* data. That is not a real-time exercise -- it is a one-sided
filter applied to information nobody had at the time.

This module rebuilds the gap the way a policymaker would actually have seen it:
at each quarter t, using only the data vintage published shortly after t.

The gap for quarter t is dated to a vintage two months after the quarter closes,
which is roughly when the FOMC would first have quarter t's national accounts.

DECOMPOSITION
-------------
The difference between what you see now and what you saw then splits in two:

    final_2sided - realtime  =  (final_2sided - final_1sided)   <- filter endpoint
                             +  (final_1sided - realtime)       <- data revision

Orphanides & van Norden (2002) showed the first term alone makes real-time output
gaps close to useless for policy. The P-star price gap contains an output gap as
one of its two components, so the same problem should carry over -- and this
measures how much of it does.

LIMITATION
----------
ALFRED archives FRED series only. The CFS does not publish a vintage archive for
the Divisia aggregates, so a genuine real-time reconstruction is possible only
for the simple-sum M2 specifications. That is the paper's own baseline (and the
spec where the 1990-2019 rejection of gamma = 0.10 is sharpest), but it does mean
the Divisia results cannot be checked this way.

    python vintages.py --fetch      # populate the cache (~400 requests)
    python vintages.py              # report, using the cache
"""

import argparse
import io
import os
import time

import numpy as np
import pandas as pd

from pstar_replication import LAMBDA_HP, hp_one_sided_kalman, hp_two_sided

CACHE = os.environ.get("VINTAGE_CACHE", "data/vintages")
ALFRED = ("https://alfred.stlouisfed.org/graph/alfredgraph.csv"
          "?id={sid}&vintage_date={vin}&cosd=1959-01-01")
SERIES = ["GDP", "GDPC1", "M2SL"]


def vintage_dates(first="1992-01-01", last="2026-04-01"):
    """
    (quarter, vintage) pairs. The vintage is the end of the month two months
    after the quarter closes -- about when quarter t's GDP first exists.
    """
    out = []
    for q in pd.date_range(first, last, freq="QS"):
        v = (q + pd.DateOffset(months=5)) + pd.offsets.MonthEnd(0)
        out.append((q, v))
    return out


def fetch_vintage(sid, vintage, session=None, pause=0.15):
    """One ALFRED vintage of one series, cached on disk as CSV."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{sid}_{vintage:%Y%m%d}.csv")
    if os.path.exists(path):
        s = pd.read_csv(path, parse_dates=["date"], index_col="date")
        return s.iloc[:, 0].dropna() if len(s) else None

    import requests
    get = session.get if session else requests.get
    r = get(ALFRED.format(sid=sid, vin=f"{vintage:%Y-%m-%d}"), timeout=60)
    r.raise_for_status()
    time.sleep(pause)
    d = pd.read_csv(io.StringIO(r.text), na_values=["."])
    if d.shape[1] < 2:
        pd.DataFrame({"date": [], sid: []}).to_csv(path, index=False)
        return None
    d.columns = ["date", sid]
    d["date"] = pd.to_datetime(d["date"])
    d = d.dropna().set_index("date")
    d.to_csv(path)
    return d[sid].astype(float)


def build_cache(verbose=True):
    import requests
    ses = requests.Session()
    pairs = vintage_dates()
    for i, (q, v) in enumerate(pairs, 1):
        for sid in SERIES:
            fetch_vintage(sid, v, session=ses)
        if verbose and i % 10 == 0:
            print(f"  {i}/{len(pairs)} vintages ({q.date()} -> {v.date()})", flush=True)
    return len(pairs)


def realtime_gap(first="1992-01-01", last="2026-04-01"):
    """
    Price gap for each quarter t computed only from the vintage available just
    after t. Uses the Kalman one-sided filter (identical to the recursive HP
    endpoint, ~100x faster).
    """
    rows = []
    for q, v in vintage_dates(first, last):
        try:
            ngdp = fetch_vintage("GDP", v)
            rgdp = fetch_vintage("GDPC1", v)
            m2 = fetch_vintage("M2SL", v)
        except Exception:
            continue
        if ngdp is None or rgdp is None or m2 is None:
            continue

        m2q = m2.resample("QS").mean()
        d = pd.DataFrame({"ngdp": ngdp, "rgdp": rgdp, "M2": m2q}).dropna()
        d = d.loc[:q]                                 # nothing after quarter t
        if len(d) < 60 or d.index[-1] != q:
            continue

        vlog = np.log(d["ngdp"] / d["M2"])
        x = np.log(d["rgdp"])
        vstar = hp_one_sided_kalman(vlog.values, LAMBDA_HP)
        xstar = hp_one_sided_kalman(x.values, LAMBDA_HP)
        gap = 100.0 * ((vstar[-1] - vlog.values[-1]) + (x.values[-1] - xstar[-1]))
        rows.append({"date": q, "vintage": v, "gap_realtime": gap,
                     "n_obs": len(d), "rgdp_rt": d["rgdp"].iloc[-1]})

    return pd.DataFrame(rows).set_index("date")


def hindsight_gaps(df, h_years=5):
    """
    Two-sided filter applied to data through t + h_years, read at t. A less
    contaminated benchmark than the full-sample two-sided estimate, which smears
    the 2020 collapse backwards over the preceding years.
    """
    k = 4 * h_years
    v = np.log(df["ngdp"] / df["M2"]).values
    x = np.log(df["rgdp"]).values
    out = np.full(len(df), np.nan)
    for i in range(len(df)):
        e = i + k + 1
        if e > len(df):
            break
        vs = hp_two_sided(v[:e], LAMBDA_HP)
        xs = hp_two_sided(x[:e], LAMBDA_HP)
        out[i] = 100.0 * ((vs[i] - v[i]) + (x[i] - xs[i]))
    return pd.Series(out, index=df.index)


def final_gaps(df):
    """One-sided and two-sided gaps on the current data vintage."""
    vlog = np.log(df["ngdp"] / df["M2"])
    x = np.log(df["rgdp"])
    one = 100.0 * ((hp_one_sided_kalman(vlog.values, LAMBDA_HP) - vlog.values)
                   + (x.values - hp_one_sided_kalman(x.values, LAMBDA_HP)))
    two = 100.0 * ((hp_two_sided(vlog.values, LAMBDA_HP) - vlog.values)
                   + (x.values - hp_two_sided(x.values, LAMBDA_HP)))
    return pd.DataFrame({"gap_1sided": one, "gap_2sided": two}, index=df.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="populate the vintage cache")
    args = ap.parse_args()

    if args.fetch:
        n = build_cache()
        print(f"cached {n} vintages x {len(SERIES)} series in {CACHE}")
        return

    from pstar_replication import fetch_fred
    cur = fetch_fred().dropna(subset=["rgdp", "p_gdp", "M2"]).loc["1967-01-01":"2026-03-31"]
    fin = final_gaps(cur)
    rt = realtime_gap()
    j = fin.join(rt, how="inner").dropna(subset=["gap_realtime"])

    j["gap_5yr"] = hindsight_gaps(cur, 5).reindex(j.index)
    j["revision_total"] = j["gap_2sided"] - j["gap_realtime"]
    j["revision_5yr"] = j["gap_5yr"] - j["gap_realtime"]
    j["revision_filter"] = j["gap_2sided"] - j["gap_1sided"]
    j["revision_data"] = j["gap_1sided"] - j["gap_realtime"]

    print(f"Real-time vs final P-star gap, M2/GDP, {j.index[0].date()} to "
          f"{j.index[-1].date()}  (n = {len(j)})\n")
    print("Standard deviation of the revision (percentage points):")
    print(f"  total          final(2-sided) - real-time   {j['revision_total'].std():6.2f}")
    print(f"    filter end   final(2-sided) - final(1-sided) {j['revision_filter'].std():6.2f}")
    print(f"    data         final(1-sided) - real-time      {j['revision_data'].std():6.2f}")
    print(f"\n  sd of the gap itself (final, 2-sided):        {j['gap_2sided'].std():6.2f}")
    print(f"  noise-to-signal (sd revision / sd gap):        "
          f"{j['revision_total'].std() / j['gap_2sided'].std():6.2f}")
    print(f"  correlation(real-time, final):                 "
          f"{j['gap_realtime'].corr(j['gap_2sided']):6.2f}")
    print(f"  sign disagreements:  "
          f"{100 * (np.sign(j['gap_realtime']) != np.sign(j['gap_2sided'])).mean():.0f}% of quarters")
    h = j[["gap_5yr", "gap_realtime"]].dropna()
    print(f"\nRobustness -- against a 5-year-hindsight benchmark instead of full two-sided:")
    print(f"  sd of revision {j['revision_5yr'].std():.2f}   "
          f"noise-to-signal {j['revision_5yr'].std() / j['gap_5yr'].std():.2f}   "
          f"corr {h['gap_5yr'].corr(h['gap_realtime']):.2f}   "
          f"sign disagreements {100 * (np.sign(h['gap_5yr']) != np.sign(h['gap_realtime'])).mean():.0f}%")

    print("\nThe 2020-21 test -- would this have flagged the money surge in real time?")
    print(j.loc["2019-10-01":"2022-04-01",
                ["gap_realtime", "gap_1sided", "gap_2sided"]].round(2).to_string())

    os.makedirs("output", exist_ok=True)
    j.to_csv("output/realtime_gaps.csv")
    print("\nwrote output/realtime_gaps.csv")


if __name__ == "__main__":
    main()
