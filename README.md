# P-star replication — Ireland, Miran & Roubini (2026)

Replication and extension of the P-star monetarist model in **"A return to monetarism?"**
(Peter Ireland, Stephen Miran, Nouriel Roubini, Hudson Bay Research, July 2026),
built from public FRED and Center for Financial Stability data.

## Summary

The paper argues that monetary aggregates still carry information about future
inflation, and applies a Greenspan-era P-star model to current data. Its headline
result: as of 2026Q1 the price gap is close to zero across all six specifications, so
monetary policy is "approximately neutral," recent high inflation must be supply-driven,
and the Fed should wait rather than hike.

This repo reproduces that result and then pushes on it. Three findings:

1. **The replication holds.** All six price-gap coefficients land within 0.01–0.02 of the
   published values, with matching t-statistics and R². The paper's stated potential-growth
   diagnostics reproduce to within 0.03pp. The 2026Q1 gap *levels* run ~0.2pp high, which
   traces to data vintage (a +0.115% revision to 2026Q1 real GDP after publication), not
   to method.

2. **The conclusion has already expired.** Using data available at 2026-07-28, the gaps
   have crossed zero: 2026Q2 sits at +0.4 to +2.2 depending on specification. Money is
   growing 7.7–8.7% annualized over three months against a "speed limit" (potential + 2%
   target) of 4.25–5.0%. The source is bank lending, not the Fed — the balance sheet is
   flat and reserves are down 10% year-over-year, while C&I loans are growing at a 13.9%
   annualized rate. This is the exact contingency the authors named as the trigger to
   revisit their recommendation.

3. **But the model may not be trustworthy in the regime that matters.** Estimated on
   1990–2019, the price-gap coefficient is ~0 and insignificant in *all six*
   specifications, including the Divisia ones meant to fix precisely that problem. The
   full-sample coefficient is carried entirely by 1967–1983 and 2020–2026. Out of sample
   since 1990 the gap beats a plain AR(4) by 3.3% on RMSE (Diebold-Mariano t = −1.02, not
   significant). The model is plausibly a regime-dependent indicator that works when money
   is moving a lot — which it now is — but the paper reports a stable 0.10 and does not
   test this.

Work in progress on (a) modelling the regime dependence explicitly and (b) replacing the
atheoretic HP velocity trend with a money-demand equation estimated on the CFS user-cost
data, which is the most likely fix for finding 3.

## The model

Equation of exchange with transactions variable `x` (real GDP or real PCE):

```
M_t V_t = P_t x_t                    =>   V_t = P_t x_t / M_t
P*_t    = M_t V*_t / x*_t            (equilibrium price level)
```

where `V*` and `x*` are one-sided Hodrick-Prescott trends (λ = 1600).

In logs the money stock drops out entirely:

```
price gap = (v* - v) + (x - x*)      i.e.  velocity gap + output gap
```

which is why a Divisia **index** (1967 = 100) needs no rescaling.

Hallman-Porter-Small (1991) regression, as re-estimated in the paper:

```
Δπ_t = α + Σ_{i=1..4} β_i Δπ_{t-i} + γ (p*_{t-1} - p_{t-1}) + ε_t
```

A positive `γ` means a positive price gap predicts accelerating inflation.

## Replication status

Table 1 reproduces closely on the paper's 1967Q1–2026Q1 sample (n = 217):

| Transactions | Money | γ (this repo) | γ (paper) | t | paper t | R² | paper R² |
|---|---|---|---|---|---|---|---|
| GDP | M2 | 0.100 | 0.10 | 3.97 | 3.95 | 0.180 | 0.18 |
| GDP | Divisia M2 | 0.079 | 0.08 | 3.70 | 3.94 | 0.173 | 0.18 |
| GDP | Divisia M4 | 0.084 | 0.09 | 3.78 | 3.91 | 0.175 | 0.18 |
| PCE | M2 | 0.125 | 0.12 | 3.81 | 3.88 | 0.193 | 0.19 |
| PCE | Divisia M2 | 0.101 | 0.11 | 3.66 | 3.91 | 0.188 | 0.19 |
| PCE | Divisia M4 | 0.101 | 0.10 | 3.46 | 3.63 | 0.183 | 0.19 |

Two of the paper's prose diagnostics also reproduce: one-sided HP potential growth over
the four quarters to 2026Q1 is 2.48% (paper: 2.45%) and CBO's is 2.27% (paper: 2.24%).

The 2026Q1 **gap levels** run about +0.2pp above the published values (e.g. Divisia
M4/GDP +1.02 here vs +0.79 in the paper). This is data vintage, not method — 2026Q1
real GDP was revised +0.115% after publication, and the CFS workbook revises monthly.
Filter start date, implicit vs chain-type deflator, and recursive vs Kalman one-sided
HP were all ruled out (see `diagnostics/spec_sensitivity.py`).

## Current reading (as of 2026-07-28)

All six gaps have crossed zero. 2026Q2 (nowcast — Q2 NIPAs not yet released, June
Divisia not yet published) sits at +0.4 to +2.2, implying +5 to +18bp on inflation.
Money growth is running 7.7–8.7% annualized over three months against a "speed limit"
(potential + 2% target) of roughly 4.25–5.0%.

See `price_gaps.png`.

## Known caveats

**γ is not stable.** This is the most important open issue and it is not addressed in
the paper. Estimated on 1990–2019 the price-gap coefficient is ~0 and insignificant in
all six specifications; the full-sample result is carried by 1967–1983 and 2020–2026.
A pseudo-out-of-sample test since 1990 has the gap beating a plain AR(4) by only 3.3%
on RMSE, Diebold-Mariano t = −1.02 (not significant). Run
`python diagnostics/gamma_stability.py`.

**Standard errors are classical.** No HAC correction, and no allowance for the price
gap being a generated regressor.

## Usage

```bash
pip install -r requirements.txt

# replication, downloading the CFS workbook
python pstar_replication.py --download-cfs data/Divisia.xlsx --out output/pstar.csv

# extend one quarter past the last NIPA release
python pstar_replication.py --cfs data/Divisia.xlsx --nowcast

# check the one-sided filter implementations against each other
python pstar_replication.py --cfs data/Divisia.xlsx --compare-filters

# pipeline check on synthetic data, no network
python pstar_replication.py --selftest

# chart
python plot_price_gaps.py --cfs data/Divisia.xlsx --out price_gaps.png
```

Diagnostics (each takes the CFS path from `$CFS_XLSX`, default `data/Divisia.xlsx`):

| Script | Question |
|---|---|
| `diagnostics/gamma_stability.py` | Is γ stable? Does the gap beat an AR(4) out of sample? |
| `diagnostics/inflation_decomposition.py` | What did the model actually predict in 2024–2026? |
| `diagnostics/money_sources.py` | Which money components and credit aggregates are driving growth? |
| `diagnostics/spec_sensitivity.py` | How much do filter start / deflator choice move the 2026Q1 gaps? |

## Data

| Source | Series |
|---|---|
| FRED | `GDP`, `GDPC1`, `PCECC96`, `PCECTPI`, `M2SL`, `GDPPOT`, `GDPNOW`, `PCEPI`, `PCEC96`, `USREC` |
| FRED (H.8 / H.4.1) | `TOTBKCR`, `BUSLOANS`, `REALLN`, `CONSUMER`, `TOTLL`, `WALCL`, `WRESBAL` |
| ALFRED | vintage checks |
| [CFS](https://centerforfinancialstability.org/amfm_data.php) | Divisia M2, M3, M4-, M4 (`Divisia.xlsx`) |

No API key required — everything comes through public CSV endpoints.

## Implementation notes

- `hp_one_sided_recursive` (expanding-window HP endpoint) and `hp_one_sided_kalman`
  (Stock-Watson 1999 filtered local-linear trend) agree to ~1e-8, as they must.
- The price gap is **exactly invariant to the level of real GDP/PCE**: the one-sided
  filter gains on `v*` and `x*` cancel, so `d(gap)/dx = (k-1) + (1-k) = 0`. Only the
  price index and the money stock move it. This is why the paper needs Table 2 —
  imposing constant potential growth is the only channel through which output re-enters.
