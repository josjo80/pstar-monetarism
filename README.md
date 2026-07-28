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

3. **The "strikingly consistent 0.10" is rejected for 1990–2019 — but the model does have
   signal now.** Estimated on 1990–2019 the price-gap coefficient is ~0 in all six
   specifications, and for the three GDP-based ones a Newey-West 95% interval **excludes
   0.10**. Over 2020–2026 the interval excludes zero in all six. Out of sample since 1990
   the gap beats a plain AR(4) by only 3.3% on RMSE (Diebold-Mariano t = −1.02, not
   significant). The rule of thumb is not a constant of nature, but the current reading
   does come from a window where the model demonstrably works.

See **Findings on model structure** below for what did and did not fix this.

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

## Findings on model structure

Two extensions, both reported whether or not they worked.

### Is γ regime-dependent? (`diagnostics/regime.py`)

**Yes in the sense that matters, no in the sense that is testable.** The subsample point
estimates differ dramatically, but no formal test of *constancy* rejects:

| Test | Result |
|---|---|
| Quandt-Andrews sup-Wald, unknown break, wild bootstrap | p = 0.30–0.81, all six specs |
| Chow at a pre-specified 1984Q1 | p = 0.64–0.98 |
| Chow at a pre-specified 2020Q1 | p = 0.11–0.76 |
| Threshold on excess money growth / money-growth volatility / \|gap\| | p = 0.05–0.91 across 9 combinations |

Note the sup-Wald search window is only 1980Q1–2018Q1: 15% trimming puts a 2020 break out
of reach entirely, which is why the pre-specified Chow tests are there.

The break tests fail because they must detect a change against noise in *both* windows.
Asking a narrower question is more informative — is the paper's 0.10 consistent with the
1990–2019 data? Newey-West (4 lags) 95% intervals on γ:

| Spec | 1990–2019 | contains 0? | contains 0.10? | 2020–2026 | contains 0? |
|---|---|---|---|---|---|
| M2/GDP | [−0.093, +0.076] | yes | **no** | [+0.089, +0.296] | **no** |
| Divisia M2/GDP | [−0.078, +0.081] | yes | **no** | [+0.075, +0.268] | **no** |
| Divisia M4/GDP | [−0.144, +0.034] | yes | **no** | [+0.089, +0.227] | **no** |
| M2/PCE | [−0.048, +0.188] | yes | yes | [+0.103, +0.231] | **no** |
| Divisia M2/PCE | [−0.044, +0.190] | yes | yes | [+0.090, +0.211] | **no** |
| Divisia M4/PCE | [−0.119, +0.106] | yes | yes | [+0.092, +0.185] | **no** |

So: for the GDP-based specifications the 1990–2019 data reject γ = 0.10 outright. The
PCE-based ones are simply uninformative over that window — wide enough to contain both 0
and 0.10. All six are solidly positive over 2020–2026. What *triggers* the switch remains
unidentified; none of the three state variables tested gives a significant threshold.

### Does a money-demand V* fix it? (`money_demand.py`, `diagnostics/velocity_comparison.py`)

**No.** The hypothesis was that the 1990–2019 collapse comes from the HP filter
mis-measuring equilibrium velocity — treating rate-driven shifts in money demand as cycle
rather than as movements in equilibrium — and that a structural V* would repair it. Eight
variants were tried, crossing two opportunity-cost measures (the CFS Divisia user-cost
aggregate; the 3-month T-bill less the CFS own-rate aggregate), current vs HP-trended
opportunity cost, and full-sample vs recursive DOLS estimation of the cointegrating vector.

- **Nothing is cointegrated.** Engle-Granger ADF on the residual ranges −1.68 to −2.17
  against a 5% critical value of −3.34. There is no stable long-run money-demand relation
  in these data to substitute for the filter.
- **No variant repairs 1990–2019.** γ over that window across all eight: −0.035 to +0.029,
  none significant.
- **The best-behaved variant just reproduces the baseline.** T-bill-less-own-rate with
  fixed β gives full-sample γ = 0.081 against the HP baseline's 0.079, and 2020–2026
  0.179 against 0.171. Adding money-demand structure changes essentially nothing.
- **The CFS user-cost variants are actively worse**, flipping γ negative over 2020–2026
  (−0.15 to −0.22). The user cost spikes during hiking cycles, dragging V* with it, so
  tightening registers as expansionary — backwards for a policy-stance indicator.
- A first attempt estimating the trend as a state-space local level with the
  signal-to-noise ratio chosen by MLE degenerated (q → 7, τ tracks v one-for-one, β → 0.04,
  all six specs collapse onto the output gap). Documented in `money_demand.py`.

The useful conclusion is a narrowing one: the 1990–2019 hole is **not** an artifact of how
V* is estimated. It is in the data.

## Known caveats

**γ is not a constant.** See *Findings on model structure* above. The headline 0.10 is
rejected for 1990–2019 in the GDP-based specifications, and the model's out-of-sample
edge over an AR(4) since 1990 is not statistically significant.

**Standard errors still understate uncertainty.** `OLSResult` now supports Newey-West via
`hac_lags`, but nothing corrects for the price gap being a *generated* regressor — it is
built from filtered estimates of v* and x* and then treated as observed data. A bootstrap
through the whole pipeline (filter included) is the outstanding fix.

**The gap itself has no confidence band.** It is reported as a point estimate. Given the
current signal is +1 to +2 against a historical range of ±5, the band may well swamp it.

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
| `diagnostics/regime.py` | Break tests, threshold models, HAC confidence intervals on γ. |
| `diagnostics/velocity_comparison.py` | Does a money-demand V* beat the HP-trend V*? |

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
