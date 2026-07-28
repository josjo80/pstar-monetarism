#!/usr/bin/env python3
"""
Replication: Ireland, Miran & Roubini (2026), "A return to monetarism?"
Hudson Bay Capital Research, July 2026.

Reproduces Table 1 (six P-star regressions), Figure 3 (price gaps),
Figure 4 (output gaps) and Table 2 (potential-growth sensitivity).

MODEL
-----
Equation of exchange, transactions variable x (real GDP or real PCE):
    M_t * V_t = P_t * x_t          =>   V_t = P_t x_t / M_t

Equilibrium price level:
    P*_t = M_t * V*_t / x*_t
where V* and x* are one-sided HP trends.

KEY IDENTITY (in logs) -- makes the Divisia index base year irrelevant:
    p*_t - p_t = (v*_t - v_t) + (x_t - x*_t)
i.e. price gap = velocity gap + output gap. M drops out entirely. This
is why you can use a Divisia INDEX (1967=100) with no rescaling.

Regression (Hallman-Porter-Small 1991, as re-estimated in the paper):
    dpi_t = c + sum_{i=1..4} b_i * dpi_{t-i} + lam * gap_{t-1} + e_t
    pi_t  = 400 * (log P_t - log P_{t-1})
    dpi_t = pi_t - pi_{t-1}
    gap_t = 100 * (log P*_t - log P_t)

Sample in the paper: 1967Q1 - 2026Q1.

DATA
----
FRED (no key needed via pandas_datareader):
    GDP       nominal GDP, quarterly SAAR
    GDPC1     real GDP, quarterly SAAR chained
    PCECC96   real PCE, quarterly SAAR chained
    PCECTPI   PCE chain-type price index, quarterly
    M2SL      M2, monthly SA  -> quarterly average
CFS (manual download, free):
    https://centerforfinancialstability.org/amfm_data.php
    Monthly Divisia M2 and M4 index levels -> quarterly average.

USAGE
-----
    python pstar_replication.py --selftest              # synthetic data, no network
    python pstar_replication.py --cfs CFS_Divisia.xlsx  # real run
    python pstar_replication.py --cfs f.xlsx --filter kalman
    python pstar_replication.py --inspect-cfs f.xlsx    # list sheets/columns
"""

import argparse
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

LAMBDA_HP = 1600.0  # quarterly
SAMPLE_START = "1967-01-01"
SAMPLE_END = "2026-03-31"


# ----------------------------------------------------------------------
# One-sided HP filters
# ----------------------------------------------------------------------
def hp_two_sided(x, lam=LAMBDA_HP):
    """Standard (two-sided) HP trend. Direct sparse-free solve."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 5:
        return x.copy()
    I = np.eye(n)
    D = np.zeros((n - 2, n))
    for i in range(n - 2):
        D[i, i], D[i, i + 1], D[i, i + 2] = 1.0, -2.0, 1.0
    return np.linalg.solve(I + lam * D.T @ D, x)


def hp_one_sided_recursive(x, lam=LAMBDA_HP, min_obs=20):
    """
    Recursive/expanding-window one-sided HP trend.

    At each date t, run the standard HP filter on data through t and keep
    only the LAST trend value. This is the implementation Kirchner (2026)
    criticises: it applies an endpoint calculation at every date, so the
    trend absorbs part of the cycle and lags structural breaks.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    for t in range(min_obs - 1, n):
        out[t] = hp_two_sided(x[: t + 1], lam)[-1]
    return out


def hp_one_sided_kalman(x, lam=LAMBDA_HP):
    """
    Stock-Watson (1999) one-sided HP: Kalman FILTER (not smoother) applied
    to the local-linear-trend model whose smoother equals the HP filter.

        tau_t  = tau_{t-1} + beta_{t-1}
        beta_t = beta_{t-1} + zeta_t,  Var = sig2_z
        x_t    = tau_t + eps_t,        Var = sig2_e
        lam    = sig2_e / sig2_z

    Returns filtered tau_{t|t}. Diffuse-ish initialisation.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    sig2_e, sig2_z = 1.0, 1.0 / lam

    T = np.array([[1.0, 1.0], [0.0, 1.0]])
    Z = np.array([[1.0, 0.0]])
    Q = np.array([[0.0, 0.0], [0.0, sig2_z]])

    a = np.array([x[0], 0.0])
    P = np.eye(2) * 1e7
    out = np.full(n, np.nan)

    for t in range(n):
        if t > 0:
            a = T @ a
            P = T @ P @ T.T + Q
        v = x[t] - (Z @ a)[0]
        F = (Z @ P @ Z.T)[0, 0] + sig2_e
        K = (P @ Z.T)[:, 0] / F
        a = a + K * v
        P = P - np.outer(K, Z @ P)
        out[t] = a[0]
    return out


ONE_SIDED = {
    "recursive": hp_one_sided_recursive,
    "kalman": hp_one_sided_kalman,
    "twosided": lambda x, lam=LAMBDA_HP: hp_two_sided(x, lam),  # diagnostic only
}


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def _fred_series(name):
    """Fetch one FRED series via the public fredgraph.csv endpoint (no API key)."""
    import io
    import requests

    r = requests.get(FRED_CSV.format(name), timeout=60)
    r.raise_for_status()
    s = pd.read_csv(io.StringIO(r.text), na_values=["."])
    s.columns = ["date", name]
    s["date"] = pd.to_datetime(s["date"])
    return s.set_index("date")[name].astype(float).dropna()


def fetch_fred(start="1959-01-01"):
    q = pd.concat([_fred_series(s) for s in
                   ("GDP", "GDPC1", "PCECC96", "PCECTPI")], axis=1).loc[start:]
    m2q = _fred_series("M2SL").loc[start:].resample("QS").mean()

    df = pd.DataFrame(index=q.index)
    df["ngdp"] = q["GDP"]
    df["rgdp"] = q["GDPC1"]
    df["p_gdp"] = q["GDP"] / q["GDPC1"]
    df["rpce"] = q["PCECC96"]
    df["p_pce"] = q["PCECTPI"] / 100.0
    df["npce"] = df["rpce"] * df["p_pce"]
    df["M2"] = m2q
    return df


def inspect_cfs(path):
    xl = pd.ExcelFile(path)
    for s in xl.sheet_names:
        d = xl.parse(s, nrows=6)
        print(f"\n--- sheet: {s} ---")
        print(list(d.columns)[:25])
    print("\nPass the right sheet/columns via --cfs-sheet/--dm2-col/--dm4-col.")


CFS_URL = "https://www.centerforfinancialstability.org/amfm/Divisia.xlsx"


def download_cfs(path="Divisia.xlsx"):
    """Fetch the CFS Advances in Monetary and Financial Measurement workbook."""
    import requests

    r = requests.get(CFS_URL, timeout=120)
    r.raise_for_status()
    with open(path, "wb") as fh:
        fh.write(r.content)
    return path


def load_cfs_workbook(path):
    """
    Load the CFS 'Divisia.xlsx' workbook as published.

    Layout (as of the June 2026 vintage): two header rows, then monthly data.
      sheet 'Broad'  col 0 = Date, col 1 = Divisia M4 level (Jan-1967 = 100)
      sheet 'Narrow' col 0 = Date, col 13 = Divisia M2 level (Jan-1967 = 100)

    Columns are located by matching the row-1 header text rather than by
    position, so the loader survives the workbook being reordered.
    """
    def grab(sheet, want):
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        hdr = raw.iloc[1].astype(str)
        hits = [i for i, h in enumerate(hdr) if h.strip().lower().startswith(want)]
        if not hits:
            raise SystemExit(f"'{want}' not found on sheet {sheet}: {list(hdr)}")
        d = raw.iloc[2:, [0, hits[0]]].copy()
        d.columns = ["date", "v"]
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna().set_index("date")["v"].astype(float)
        return d

    dm2 = grab("Narrow", "divisia m2 level")
    dm4 = grab("Broad", "divisia m4 level")
    m = pd.DataFrame({"DM2": dm2, "DM4": dm4})
    return m.resample("QS").mean()


def load_cfs(path, sheet=0, date_col=None, dm2_col=None, dm4_col=None):
    """Load monthly CFS Divisia index levels and average to quarters."""
    if sheet == 0 and date_col is None and dm2_col is None and dm4_col is None:
        try:
            return load_cfs_workbook(path)
        except SystemExit:
            pass  # not the standard CFS workbook; fall through to generic reader
    raw = pd.read_excel(path, sheet_name=sheet)
    cols = {str(c).strip().lower(): c for c in raw.columns}

    def pick(explicit, *keys):
        if explicit:
            return explicit
        for k in keys:
            for lc, orig in cols.items():
                if k in lc:
                    return orig
        return None

    dc = pick(date_col, "date", "month", "period")
    c2 = pick(dm2_col, "dm2", "divisia m2", "m2")
    c4 = pick(dm4_col, "dm4", "divisia m4", "m4")
    if dc is None or c2 is None or c4 is None:
        raise SystemExit(
            f"Could not identify columns. Found: {list(raw.columns)[:25]}\n"
            "Re-run with --inspect-cfs, then pass --date-col/--dm2-col/--dm4-col."
        )

    d = raw[[dc, c2, c4]].copy()
    d.columns = ["date", "DM2", "DM4"]
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).set_index("date").astype(float)
    return d.resample("QS").mean()


def make_synthetic(n=240):
    """Self-test data with a known structure. NOT real economics."""
    rng = np.random.default_rng(7)
    idx = pd.date_range("1967-01-01", periods=n, freq="QS")
    rgdp = 3000 * np.exp(np.cumsum(rng.normal(0.008, 0.006, n)))
    p = 20 * np.exp(np.cumsum(rng.normal(0.008, 0.004, n)))
    m = 300 * np.exp(np.cumsum(rng.normal(0.014, 0.008, n)))
    df = pd.DataFrame(index=idx)
    df["rgdp"] = rgdp
    df["p_gdp"] = p
    df["ngdp"] = rgdp * p
    df["rpce"] = 0.67 * rgdp
    df["p_pce"] = p * 0.98
    df["npce"] = df["rpce"] * df["p_pce"]
    df["M2"] = m
    df["DM2"] = m / m[0] * 100
    df["DM4"] = (m * np.exp(np.cumsum(rng.normal(0.001, 0.004, n)))) / m[0] * 100
    return df


# ----------------------------------------------------------------------
# Nowcast: extend the panel one quarter past the last NIPA release
# ----------------------------------------------------------------------
def _monthly_to_quarter(s, q):
    """
    Average the three months of quarter `q`. Months not yet published are
    filled by extrapolating the last observed month-over-month growth rate.
    Returns (value, n_months_actual).
    """
    months = pd.date_range(q, periods=3, freq="MS")
    have = s.reindex(months).dropna()
    if len(have) == 0:
        return np.nan, 0
    g = s.pct_change().dropna()
    rate = g.iloc[-1] if len(g) else 0.0
    vals, last = list(have.values), have.values[-1]
    for _ in range(3 - len(have)):
        last = last * (1.0 + rate)
        vals.append(last)
    return float(np.mean(vals)), len(have)


def build_nowcast_row(df, cfs_path, rgdp_growth=None, deflator_infl=None,
                      verbose=True):
    """
    Append one nowcast quarter to `df`.

    Money and PCE come from published monthly data (partial quarters are
    extrapolated at the last monthly growth rate). Real GDP comes from the
    Atlanta Fed's GDPNow (FRED series GDPNOW) unless `rgdp_growth` is given.
    The GDP deflator has no monthly analogue, so it is an assumption --
    default is the trailing four-quarter mean of annualized deflator
    inflation. Both are exposed so the sensitivity can be shown.
    """
    q = df.index[-1] + pd.DateOffset(months=3)

    m2 = _fred_series("M2SL")
    dm2_m, dm4_m = _cfs_monthly(cfs_path)
    pcepi, pcec96 = _fred_series("PCEPI"), _fred_series("PCEC96")

    row, cover = {}, {}
    for name, s in (("M2", m2), ("DM2", dm2_m), ("DM4", dm4_m),
                    ("p_pce_idx", pcepi), ("rpce", pcec96)):
        row[name], cover[name] = _monthly_to_quarter(s, q)
    row["p_pce"] = row.pop("p_pce_idx") / 100.0

    if rgdp_growth is None:
        rgdp_growth = float(_fred_series("GDPNOW").iloc[-1])
    if deflator_infl is None:
        deflator_infl = float((400 * np.log(df["p_gdp"]).diff()).tail(4).mean())

    row["rgdp"] = df["rgdp"].iloc[-1] * (1.0 + rgdp_growth / 100.0) ** 0.25
    row["p_gdp"] = df["p_gdp"].iloc[-1] * np.exp(deflator_infl / 400.0)
    row["ngdp"] = row["rgdp"] * row["p_gdp"]
    row["npce"] = row["rpce"] * row["p_pce"]

    if verbose:
        print(f"\nNOWCAST for {q.date()} (quarter not yet in the NIPAs)")
        print(f"  real GDP growth   {rgdp_growth:5.2f}% SAAR   "
              f"({'GDPNow' if rgdp_growth is not None else 'assumed'})")
        print(f"  GDP deflator      {deflator_infl:5.2f}% SAAR   (assumption)")
        for k in ("M2", "DM2", "DM4", "rpce"):
            print(f"  {k:5s} {row[k]:12.2f}   ({cover[k]}/3 months published)")

    out = df.copy()
    for c in out.columns:
        out.loc[q, c] = row.get(c, np.nan)
    return out, q, dict(rgdp_growth=rgdp_growth, deflator_infl=deflator_infl,
                        coverage=cover)


def _cfs_monthly(path):
    """Monthly Divisia M2 and M4 levels from the CFS workbook."""
    def grab(sheet, want):
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        hdr = raw.iloc[1].astype(str)
        i = [j for j, h in enumerate(hdr) if h.strip().lower().startswith(want)][0]
        d = raw.iloc[2:, [0, i]].copy()
        d.columns = ["date", "v"]
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        return d.dropna().set_index("date")["v"].astype(float)

    return grab("Narrow", "divisia m2 level"), grab("Broad", "divisia m4 level")


# ----------------------------------------------------------------------
# P-star construction
# ----------------------------------------------------------------------
def price_gap(df, money_col, real_col, price_col, filt="recursive"):
    """
    Returns the P-star price gap in percentage points, plus components.

    gap = 100 * [ (v* - v) + (x - x*) ]
    """
    f = ONE_SIDED[filt]
    nominal = df[real_col] * df[price_col]
    v = np.log(nominal / df[money_col])          # log velocity
    x = np.log(df[real_col])                     # log real transactions var

    vstar = f(v.values, LAMBDA_HP)
    xstar = f(x.values, LAMBDA_HP)

    gap = 100.0 * ((vstar - v.values) + (x.values - xstar))
    out = pd.DataFrame(index=df.index)
    out["v"] = v
    out["vstar"] = vstar
    out["x"] = x
    out["xstar"] = xstar
    out["velocity_gap"] = 100.0 * (vstar - v.values)
    out["output_gap"] = 100.0 * (x.values - xstar)
    out["gap"] = gap
    return out


class OLSResult:
    """
    Minimal OLS output. Classical (homoskedastic) standard errors by default;
    `hac_lags` switches to Newey-West, which is the honest choice here since the
    regressand is a change in inflation with obvious heteroskedasticity across
    the 1970s and the 2010s.

    Note that even the HAC errors understate uncertainty: the price gap is a
    *generated* regressor built from filtered estimates of v* and x*, and the
    regression treats it as observed data.
    """

    def __init__(self, y, X, hac_lags=None):
        from scipy import stats

        names = list(X.columns)
        Xv, yv = X.values.astype(float), y.values.astype(float)
        n, k = Xv.shape
        beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
        resid = yv - Xv @ beta
        dof = n - k
        s2 = resid @ resid / dof
        XtXi = np.linalg.inv(Xv.T @ Xv)
        if hac_lags is None:
            se = np.sqrt(np.diag(XtXi) * s2)
        else:
            u = Xv * resid[:, None]
            S = u.T @ u
            for L in range(1, hac_lags + 1):
                G = u[L:].T @ u[:-L]
                S += (1.0 - L / (hac_lags + 1.0)) * (G + G.T)
            se = np.sqrt(np.diag(XtXi @ S @ XtXi) * n / dof)
        tss = ((yv - yv.mean()) ** 2).sum()

        self.params = pd.Series(beta, index=names)
        self.bse = pd.Series(se, index=names)
        self.tvalues = self.params / self.bse
        self.pvalues = pd.Series(
            2.0 * stats.t.sf(np.abs(self.tvalues.values), dof), index=names)
        self.rsquared = 1.0 - (resid @ resid) / tss
        self.nobs = n
        self.resid = pd.Series(resid, index=y.index)


def pstar_regression(df, price_col, gap, start=SAMPLE_START, end=SAMPLE_END):
    """dpi_t = c + sum b_i dpi_{t-i} + lam * gap_{t-1} + e_t"""
    pi = 400.0 * np.log(df[price_col]).diff()
    dpi = pi.diff()

    d = pd.DataFrame({"dpi": dpi, "gap": gap})
    for i in range(1, 5):
        d[f"dpi_l{i}"] = dpi.shift(i)
    d["gap_l1"] = d["gap"].shift(1)
    d = d.loc[start:end].dropna()

    X = d[[f"dpi_l{i}" for i in range(1, 5)] + ["gap_l1"]].copy()
    X.insert(0, "const", 1.0)
    return OLSResult(d["dpi"], X), d


# ----------------------------------------------------------------------
# Sensitivity: constant potential growth from 2025Q1 (paper Table 2)
# ----------------------------------------------------------------------
def gap_with_constant_potential(df, money_col, real_col, price_col,
                                annual_growth, anchor="2025-01-01",
                                filt="recursive"):
    f = ONE_SIDED[filt]
    nominal = df[real_col] * df[price_col]
    v = np.log(nominal / df[money_col])
    x = np.log(df[real_col])

    vstar = f(v.values, LAMBDA_HP)
    xstar = f(x.values, LAMBDA_HP).copy()

    idx = df.index
    if pd.Timestamp(anchor) not in idx:
        return pd.Series(np.nan, index=idx)
    a = idx.get_loc(pd.Timestamp(anchor))
    g = np.log(1.0 + annual_growth / 100.0) / 4.0
    for k in range(a + 1, len(xstar)):
        xstar[k] = xstar[a] + g * (k - a)

    return pd.Series(100.0 * ((vstar - v.values) + (x.values - xstar)), index=idx)


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------
SPECS = [
    ("M2", "M2", "rgdp", "p_gdp", "GDP"),
    ("Divisia M2", "DM2", "rgdp", "p_gdp", "GDP"),
    ("Divisia M4", "DM4", "rgdp", "p_gdp", "GDP"),
    ("M2", "M2", "rpce", "p_pce", "PCE"),
    ("Divisia M2", "DM2", "rpce", "p_pce", "PCE"),
    ("Divisia M4", "DM4", "rpce", "p_pce", "PCE"),
]


def run(df, filt="recursive"):
    print(f"\n{'='*74}")
    print(f"P-STAR REGRESSIONS  |  one-sided filter: {filt}  |  lambda_HP={LAMBDA_HP:.0f}")
    print(f"sample: {SAMPLE_START[:7]} to {SAMPLE_END[:7]}")
    print("=" * 74)

    gaps = {}
    rows = []
    full = {}
    for label, mcol, rcol, pcol, tag in SPECS:
        if mcol not in df.columns:
            continue
        g = price_gap(df, mcol, rcol, pcol, filt=filt)
        gaps[(label, tag)] = g["gap"]
        res, _ = pstar_regression(df, pcol, g["gap"])
        full[(tag, label)] = res
        rows.append({
            "transactions": tag,
            "money": label,
            "lambda(gap)": res.params["gap_l1"],
            "t": res.tvalues["gap_l1"],
            "p": res.pvalues["gap_l1"],
            "R2": res.rsquared,
            "n": int(res.nobs),
        })

    # Full coefficient tables, laid out like the paper's Table 1.
    labels = {"const": "Constant", "dpi_l1": "dpi(t-1)", "dpi_l2": "dpi(t-2)",
              "dpi_l3": "dpi(t-3)", "dpi_l4": "dpi(t-4)", "gap_l1": "price gap(t-1)"}
    for tag in ("GDP", "PCE"):
        specs = [(m, r) for (t, m), r in full.items() if t == tag]
        if not specs:
            continue
        print(f"\n\nTABLE 1  |  Dependent variable: change in {tag} price inflation")
        block = {}
        for m, r in specs:
            for stat, ser in (("est", r.params), ("t", r.tvalues), ("p", r.pvalues)):
                block[(m, stat)] = ser.rename(index=labels)
        t1 = pd.DataFrame(block)
        t1.loc["R2"] = [full[(tag, m)].rsquared if s == "est" else np.nan
                        for (m, s) in t1.columns]
        t1.loc["n"] = [full[(tag, m)].nobs if s == "est" else np.nan
                       for (m, s) in t1.columns]
        print(t1.to_string(float_format=lambda v: f"{v:7.2f}", na_rep=""))

    tab = pd.DataFrame(rows)
    print("\n\nPrice-gap coefficient (paper: ~0.10 across all six; R2 ~0.18-0.19)\n")
    print(tab.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))

    print("\n\nPRICE GAPS, last 6 quarters (percentage points)")
    print("positive = expansionary, negative = contractionary\n")
    gp = pd.DataFrame(gaps).dropna(how="all").tail(6)
    gp.columns = [f"{m}/{t}" for (m, t) in gp.columns]
    print(gp.to_string(float_format=lambda v: f"{v:8.2f}"))
    print("\nPaper's 2026Q1 range: -0.36 (M2/PCE) to +0.79 (Divisia M4/GDP)")

    # Table 2 sensitivity
    print("\n\nGDP PRICE GAPS UNDER ALTERNATIVE POTENTIAL-GROWTH ASSUMPTIONS")
    print("(constant potential growth imposed from 2025Q1)\n")
    for label, mcol in [("M2", "M2"), ("Divisia M2", "DM2"), ("Divisia M4", "DM4")]:
        if mcol not in df.columns:
            continue
        cols = {"Benchmark": price_gap(df, mcol, "rgdp", "p_gdp", filt)["gap"]}
        for gr in (2.25, 2.50, 2.75, 3.00):
            cols[f"{gr:.2f}%"] = gap_with_constant_potential(
                df, mcol, "rgdp", "p_gdp", gr, anchor="2025-01-01", filt=filt)
        t2 = pd.DataFrame(cols).loc["2025-01-01":].round(2)
        print(f"--- {label} ---")
        print(t2.to_string(float_format=lambda v: f"{v:7.2f}"))
        print()

    return tab, pd.DataFrame(gaps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfs", help="Path to CFS Divisia Excel file")
    ap.add_argument("--download-cfs", metavar="PATH", nargs="?", const="Divisia.xlsx",
                    help="Download Divisia.xlsx from the CFS and use it")
    ap.add_argument("--filter-start", default=SAMPLE_START,
                    help="First date fed to the one-sided filters "
                         "(default = sample start, 1967Q1)")
    ap.add_argument("--cfs-sheet", default=0)
    ap.add_argument("--date-col")
    ap.add_argument("--dm2-col")
    ap.add_argument("--dm4-col")
    ap.add_argument("--inspect-cfs")
    ap.add_argument("--filter", default="recursive",
                    choices=["recursive", "kalman", "twosided"])
    ap.add_argument("--compare-filters", action="store_true")
    ap.add_argument("--nowcast", action="store_true",
                    help="Extend one quarter past the last NIPA release using "
                         "monthly money/PCE data and GDPNow")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="pstar_output.csv")
    args = ap.parse_args()

    if args.inspect_cfs:
        inspect_cfs(args.inspect_cfs)
        return

    if args.selftest:
        print("SELF-TEST on synthetic data (numbers are meaningless; "
              "this only checks the pipeline runs).")
        df = make_synthetic()
    else:
        print("Fetching FRED...")
        df = fetch_fred()
        cfs_path = args.cfs
        if args.download_cfs:
            print(f"Downloading CFS Divisia workbook -> {args.download_cfs}")
            cfs_path = download_cfs(args.download_cfs)
        if not cfs_path:
            print("\nNo --cfs supplied: running M2-only specifications.\n"
                  "Download Divisia data free from "
                  "centerforfinancialstability.org/amfm_data.php")
        else:
            cfs = load_cfs(cfs_path, args.cfs_sheet, args.date_col,
                           args.dm2_col, args.dm4_col)
            df = df.join(cfs, how="left")
        df = df.dropna(subset=["rgdp", "p_gdp", "M2"])
        # Trim to the quarters with complete source data, then restrict the
        # window fed to the one-sided filters (paper: CFS data start 1967Q1).
        df = df.loc[args.filter_start:SAMPLE_END]
        print(f"Data: {df.index[0].date()} to {df.index[-1].date()}  "
              f"({len(df)} quarters); columns: {list(df.columns)}")

    if args.compare_filters:
        # Correctness check: the expanding-window HP endpoint and the Kalman
        # filtered LLT trend are the same object (smoother at the endpoint =
        # filter). They should agree to ~1e-9. If they don't, something broke.
        a = price_gap(df, "M2", "rgdp", "p_gdp", "recursive")["gap"]
        b = price_gap(df, "M2", "rgdp", "p_gdp", "kalman")["gap"]
        print(f"\n[check] recursive vs Kalman one-sided max abs diff: "
              f"{(a - b).abs().max():.2e}  (should be ~0)")

        # The economically meaningful contrast is real-time (one-sided) vs
        # full-sample (two-sided). This is the Kirchner (2026) endpoint point.
        for f in ("recursive", "twosided"):
            run(df, filt=f)
    else:
        tab, gaps = run(df, filt=args.filter)

        if args.nowcast:
            if not cfs_path:
                raise SystemExit("--nowcast needs the CFS workbook (--cfs/--download-cfs)")
            df2, q, info = build_nowcast_row(df, cfs_path)
            print(f"\n{'='*74}\nNOWCAST PRICE GAPS (last row = {q.date()}, not yet in the NIPAs)")
            print("Note: the gap is invariant to the level of real GDP/PCE -- the")
            print("one-sided filter gains on v* and x* cancel -- so only the price")
            print("index and the money stock move it.\n" + "=" * 74)
            ng = {}
            for label, mcol, rcol, pcol, tag in SPECS:
                if mcol in df2.columns:
                    ng[f"{label}/{tag}"] = price_gap(df2, mcol, rcol, pcol,
                                                     filt=args.filter)["gap"]
            nt = pd.DataFrame(ng)
            print(nt.tail(6).to_string(float_format=lambda v: f"{v:8.2f}"))
            print("\nImplied change in inflation next quarter (gamma x gap, basis points):")
            for label, mcol, rcol, pcol, tag in SPECS:
                key = f"{label}/{tag}"
                if key not in nt:
                    continue
                gm = tab.loc[(tab["money"] == label) & (tab["transactions"] == tag),
                             "lambda(gap)"].iloc[0]
                print(f"  {key:18s} gap={nt[key].loc[q]:6.2f}  ->  "
                      f"{100 * gm * nt[key].loc[q]:+6.1f} bp")
            gaps = nt

        gaps.to_csv(args.out)
        print(f"\nPrice gap series written to {args.out}")


if __name__ == "__main__":
    main()
