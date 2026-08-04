# P-star replication — Ireland, Miran & Roubini (2026)

[![SSRN](https://img.shields.io/badge/SSRN-7206999-0f5257)](https://ssrn.com/abstract=7206999)

Replication and extension of the P-star monetarist model in **"A return to monetarism?"**
(Peter Ireland, Stephen Miran, Nouriel Roubini, Hudson Bay Research, July 2026),
built from public FRED and Center for Financial Stability data.

## Paper

**SSRN working paper: [ssrn.com/abstract=7206999](https://ssrn.com/abstract=7206999)**

A write-up of this work is in **[PAPER.md](PAPER.md)** — *"The P-Star Price Gap Is Not
Identified in Real Time: A replication and extension of Ireland, Miran and Roubini (2026)."*
Renders with figures on GitHub. Also generated for circulation:

Run `make paper` to generate circulation copies (requires `pandoc`):

| file | use |
|---|---|
| [`PAPER.md`](PAPER.md) | source; renders with figures on GitHub |
| `paper/pstar-comment.docx` | for reviewer comments / track changes |
| `paper/pstar-comment.html` | standalone read |
| `paper/Johnson-2026-pstar-real-time.pdf` | print-ready, for SSRN (`make pdf`) |
| [shareable web page](https://claude.ai/code/artifact/bfd94648-c540-4bf9-8797-1dc0b087ba95) | typeset read-only version, figures embedded |

The generated documents are gitignored — `PAPER.md` and the figures are the versioned
source.

Figures: `price_gaps.png` (replication), `frontier.png` (filter frontier),
`uncertainty.png` (real-time reliability), `models.png` (current reading with bands).

## Summary

The paper argues that monetary aggregates still carry information about future
inflation, and applies a Greenspan-era P-star model to current data. Its headline
result: as of 2026Q1 the price gap is close to zero across all six specifications, so
monetary policy is "approximately neutral," recent high inflation must be supply-driven,
and the Fed should wait rather than hike.

This repo reproduces that result and then pushes on it. Six findings:

1. **The replication holds.** All six price-gap coefficients land within 0.01–0.02 of the
   published values, with matching t-statistics and R². The paper's stated potential-growth
   diagnostics reproduce to within 0.03pp. The 2026Q1 gap *levels* run ~0.2pp high, which
   traces to data vintage (a +0.115% revision to 2026Q1 real GDP after publication), not
   to method.

2. **The conclusion has already expired.** On published 2026Q2 data the gaps have risen
   about 3pp from their 2023 trough, though the level remains within the noise band. Money is
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

4. **And the gap cannot be told apart from zero in real time.** Rebuilt from ALFRED
   vintages, the gap a policymaker would have seen at the time has a revision standard
   deviation of **3.13pp against a gap that varies by 2.88pp** — a noise-to-signal ratio
   of 1.09. Real-time and hindsight estimates disagree on the *sign* of policy in 33% of
   quarters. Applying that revision distribution, the 90% band on every one of the six
   2026Q1 gaps spans zero. So does the paper's "approximately neutral" reading, and so
   does finding 2 above. The gap has genuinely risen; the level is not identified.

5. **The paper's supply-shock explanation is half right, and the half that is right
   isn't the half it emphasises.** Putting measured supply variables into the regression
   for the first time: the price gap **survives** (γ rises slightly, 0.077 → 0.091, HAC
   t = 2.7), so the money signal was not proxying for supply. But over 2025Q1–2026Q1,
   **oil contributes ~0.00pp** — oil *fell* through 2025 — while **tariffs contribute
   +1.17pp of the +2.03pp rise in PCE inflation** (and nothing in the GDP deflator, which
   excludes imports). A residual of +4.0 to +4.7pp is explained by neither money nor
   measured supply. Meanwhile the energy shock the paper hedged about has now arrived:
   2026Q2 is the **third-largest oil shock since 1946**, implying +1.5 to +2.1pp on
   inflation by 2027Q1 — an order of magnitude larger than the monetary signal.

6. **The whole P-star construction can be replaced by 4-quarter money growth, at no cost
   in accuracy and an 18-fold gain in precision.** Every problem above traces to estimating
   two unobserved trends at the sample endpoint. Dropping potential output (the nominal-GDP
   framing) buys almost nothing — equilibrium velocity was doing the damage — but dropping
   both is transformative: noise-to-signal falls from **1.09 to 0.06** and real-time sign
   errors from **33% to zero**. And nothing is given up for it: raw money growth matches
   the price gap in sample (standardised effect 0.262 vs 0.262, R² 0.167 vs 0.169) and
   slightly beats it out of sample. On this evidence the filtering machinery adds
   measurement noise without adding information.

7. **And the one thing that does rescue the gap is a different filter — the HP filter is
   the problem, not the price gap.** Sweeping λ from 100 to 10⁶ traces a real tradeoff
   (smoother trends revise less but track less), and λ = 1600 is not on the efficient part
   of it — but no HP variant gets close. The **Hamilton (2018) regression filter dominates
   every HP variant on both axes at once**: noise-to-signal 0.24 against 1.09, real-time
   sign errors 11% against 33%, and *more* predictive power, not less (standardised effect
   0.344 against 0.262, R² 0.243 against 0.169, out-of-sample gain 5.4% against 3.3%).
   That is not a tradeoff, it is a strict improvement, and it is what Hamilton argued:
   his filter is one-sided by construction, so it has no endpoint to revise.

**What survives all of this.** Money carries real information about inflation, it is not a
repackaged supply shock, and its grip is probably stronger than the paper's 0.10 suggests.
But the P-star *gap* is the wrong way to read it: use money growth against potential
nominal growth, which is near-noise-free and available the day M2 prints. On that measure
money is currently running 7.7–8.7% annualized against a 4.25–5.0% speed limit — a solid
observation, unlike the ±5pp band on the gap. Two caveats stand: the money–inflation
relationship is genuinely regime-dependent (~0 on 1990–2019, strong on 2020–2026,
significant at t = 3.15 even for a near-noise-free indicator), and no monetary indicator
beats a plain AR(4) significantly out of sample.

See **Findings on model structure** below for the detail.

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
| GDP | Divisia M2 | 0.077 | 0.08 | 3.63 | 3.94 | 0.171 | 0.18 |
| GDP | Divisia M4 | 0.083 | 0.09 | 3.72 | 3.91 | 0.174 | 0.18 |
| PCE | M2 | 0.125 | 0.12 | 3.81 | 3.88 | 0.193 | 0.19 |
| PCE | Divisia M2 | 0.100 | 0.11 | 3.62 | 3.91 | 0.187 | 0.19 |
| PCE | Divisia M4 | 0.100 | 0.10 | 3.43 | 3.63 | 0.183 | 0.19 |

Two of the paper's prose diagnostics also reproduce: one-sided HP potential growth over
the four quarters to 2026Q1 is 2.48% (paper: 2.45%) and CBO's is 2.27% (paper: 2.24%).

The 2026Q1 **gap levels** run about +0.2pp above the published values (e.g. Divisia
M4/GDP +1.15 here vs +0.79 in the paper). This is data vintage, not method — 2026Q1
real GDP was revised +0.115% after publication, and the CFS workbook revises monthly.
Filter start date, implicit vs chain-type deflator, and recursive vs Kalman one-sided
HP were all ruled out (see `diagnostics/spec_sensitivity.py`).

## Current reading (`current_reading.py`)

Read on the **Hamilton filter**, which `filters.py` shows dominates the paper's HP(1600)
on both real-time reliability and predictive power. Published data through 2026Q2, with a
90% band from the Hamilton revision distribution (sd 1.65pp, against 3.13pp for HP).

*An earlier version of this table reported 2026Q2 as a nowcast, and two specifications then
excluded zero. The Q2 national accounts landed with GDP deflator inflation at 6.09% against
an assumed 3.24%, which moved every gap down by up to 1.2pp and reversed that conclusion.
See PAPER.md §8.1 — the episode is the repo's own thesis operating in real time.*

| Spec | 2026Q1 | 2026Q2 | 90% band | excludes zero? |
|---|---|---|---|---|
| M2/GDP | −0.41 | +0.06 | [−2.05, +3.38] | no |
| Divisia M2/GDP | +1.33 | +1.80 | [−0.31, +5.12] | no |
| Divisia M4/GDP | −1.40 | −0.71 | [−2.81, +2.61] | no |
| M2/PCE | +0.34 | +1.01 | [−1.10, +4.33] | no |
| Divisia M2/PCE | +1.12 | +1.94 | [−0.17, +5.26] | no |
| Divisia M4/PCE | −1.62 | −0.64 | [−2.74, +2.69] | no |

**No specification excludes zero**, on this filter or on HP(1600). But the halved band comes with
a catch: **the six specifications disagree far more under Hamilton than under HP** (mean
cross-aggregate spread 4.6pp vs 1.8pp). The paper's claim that "the choice of monetary
aggregate hardly matters" is a property of HP's heavy smoothing, not a robust finding.

**Why they disagree, and why it qualifies the result.** The Hamilton velocity gap splits
into two pieces, exactly (verified to 1e-6):

> Hamilton velocity gap  =  expected 8-quarter velocity change (the filter's own
> extrapolation of that series' history)  +  8-quarter excess money growth

| aggregate | extrapolation | excess money growth | = gap |
|---|---|---|---|
| M2 | +1.93 | −1.07 | +0.86 |
| **Divisia M2** | **+4.08** | −0.97 | **+3.10** |
| **Divisia M4** | **+0.42** | +0.12 | **+0.54** |

Actual money growth barely differs across the three (spread 1.2pp). The filter's
extrapolation differs a lot (spread 3.7pp), and that is where essentially all the
disagreement comes from. The Hamilton regression is fitted on 1967–2026, over which the
three velocity series behaved very differently (mean 8-quarter change: M2 −0.71, Divisia M2
+1.39, Divisia M4 +1.56), while over the past decade all three have velocity *falling*.
So the conditional means being extrapolated are partly stale, and stale in a
series-specific way.

This materially qualifies the Divisia M2 reading. Its +1.80 is +3.78 of extrapolated
velocity rise *minus* 1.86 of actual excess money growth — what positive signal there is
comes from the filter's prior about velocity, not from what money did. That is the price of Hamilton's
real-time stability: it does not chase the endpoint, but it inherits whatever the estimated
long-run dynamics get wrong, as a level bias that differs by series. See `models.png`.

Implied effect on inflation, with γ re-estimated on the Hamilton gap: −3 to +11bp, every
90% band spanning zero.

The trend-free cross-check is unaffected by any of this — 4-quarter money growth to 2026Q2
is 5.28% (M2), 5.83% (Divisia M2), 6.55% (Divisia M4), i.e. **+0.3 to +2.3pp above a
4.25–5.0% speed limit**, measured with noise-to-signal 0.06.

**Validation on the case that matters.** At 2021Q4, with inflation about to peak, the HP
gap read **+2.2** in real time against a hindsight value of +9.2 — it decayed to neutral
and called the all-clear. The Hamilton gap read **+18.7** against a hindsight of +21.8, and
held an unmistakable warning through the entire episode. Across 2021 the Hamilton real-time
average was +20.4 against a hindsight of +22.8; HP's was +5.0 against +9.1.

See `uncertainty.png`, `models.png` and `price_gaps.png`.

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
| Divisia M2/GDP | [−0.088, +0.082] | yes | **no** | [+0.074, +0.264] | **no** |
| Divisia M4/GDP | [−0.148, +0.035] | yes | **no** | [+0.088, +0.224] | **no** |
| M2/PCE | [−0.048, +0.188] | yes | yes | [+0.103, +0.231] | **no** |
| Divisia M2/PCE | [−0.046, +0.192] | yes | yes | [+0.089, +0.209] | **no** |
| Divisia M4/PCE | [−0.121, +0.109] | yes | yes | [+0.091, +0.184] | **no** |

So: for the GDP-based specifications the 1990–2019 data reject γ = 0.10 outright. The
PCE-based ones are simply uninformative over that window — wide enough to contain both 0
and 0.10. All six are solidly positive over 2020–2026.

**And the regime dependence may not be regime dependence at all** (`diagnostics/attenuation.py`).
Once the measurement-error variance is known from the vintage reconstruction, classical
attenuation — γ_obs = γ_true × var(gap)/(var(gap) + var(noise)) — ties the two findings
together. The gap's own variance differs by a factor of ~4 across these windows, so a
*constant* γ_true would look regime-dependent purely through attenuation:

| Divisia M2/GDP | sd(gap) | signal share | γ observed | implied γ_true |
|---|---|---|---|---|
| 1967–1983 | 3.62 | 0.57 | 0.112 | **0.195** |
| 1990–2019 | 1.76 | 0.24 | −0.003 | −0.013 |
| 2020–2026 | 6.92 | 0.83 | 0.169 | **0.203** |

The 1970s and the 2020s imply almost the same structural coefficient from very different
observed ones, and 1990–2019 is consistent too (a signal share of 0.25 predicts γ_obs ≈
0.05, inside that window's HAC interval). This suggests the paper's headline 0.10
understates the structural coefficient by roughly half.

**But attenuation is not the whole story, and an earlier version of this README said it
was.** The falsification test: if measurement error were the explanation, an indicator
measured almost without error should show no regime dependence. Money growth is such an
indicator — noise-to-signal 0.06, signal shares of 0.985–0.999 — and it shows the *same*
pattern, with the 2020–2026 versus 1990–2019 difference significant at **t = 3.15**
(against t = 2.64 for the price gap). Cleaning up the measurement error makes the regime
dependence sharper, not weaker.

Both things are true: measurement error inflates how unstable the *price gap* coefficient
looks, and there is genuine regime dependence in the money–inflation relationship
underneath it. Caveats on the correction itself: it is the single-regressor formula applied
to a regression with four lags of the dependent variable, and it assumes noise uncorrelated
with the true gap, which is doubtful for a filter revision.

### Does a money-demand V* fix it? (`money_demand.py`, `diagnostics/velocity_comparison.py`)

**No.** The hypothesis was that the 1990–2019 collapse comes from the HP filter
mis-measuring equilibrium velocity — treating rate-driven shifts in money demand as cycle
rather than as movements in equilibrium — and that a structural V* would repair it. Eight
variants were tried, crossing two opportunity-cost measures (the CFS Divisia user-cost
aggregate; the 3-month T-bill less the CFS own-rate aggregate), current vs HP-trended
opportunity cost, and full-sample vs recursive DOLS estimation of the cointegrating vector.

- **Nothing is cointegrated.** Engle-Granger ADF on the residual ranges −1.76 to −2.27
  against a 5% critical value of −3.34. There is no stable long-run money-demand relation
  in these data to substitute for the filter.
- **No variant repairs 1990–2019.** γ over that window across all eight: −0.036 to +0.028,
  none significant.
- **The best-behaved variant just reproduces the baseline.** T-bill-less-own-rate with
  fixed β gives full-sample γ = 0.079 against the HP baseline's 0.077, and 2020–2026
  0.173 against 0.169. Adding money-demand structure changes essentially nothing.
- **The CFS user-cost variants are actively worse**, flipping γ negative over 2020–2026
  (−0.15 to −0.22). The user cost spikes during hiking cycles, dragging V* with it, so
  tightening registers as expansionary — backwards for a policy-stance indicator.
- A first attempt estimating the trend as a state-space local level with the
  signal-to-noise ratio chosen by MLE degenerated (q → 7, τ tracks v one-for-one, β → 0.04,
  all six specs collapse onto the output gap). Documented in `money_demand.py`.

The useful conclusion is a narrowing one: the 1990–2019 hole is **not** an artifact of how
V* is estimated. It is in the data.

### Is the gap identified in real time? (`vintages.py`, `diagnostics/uncertainty.py`)

**No, and this is the largest single problem with the framework.** The paper's case for the
one-sided HP filter is that it works in real time — but the published estimates are
computed on final, revised data. Rebuilding the gap from ALFRED vintages (M2/GDP,
1992–2026, 137 quarters, gap for quarter *t* dated to the vintage two months after *t*
closes):

| | vs final two-sided | vs 5-year hindsight |
|---|---|---|
| sd of revision | 3.13pp | 2.16pp |
| sd of the gap itself | 2.88pp | 2.34pp |
| **noise-to-signal** | **1.09** | **0.93** |
| correlation, real-time vs benchmark | 0.47 | 0.57 |
| sign disagreements | 33% | 33% |

The revision is essentially *all* filter endpoint, not data:

| component | sd |
|---|---|
| filter endpoint (final 2-sided − final 1-sided) | 3.13pp |
| data revision (final 1-sided − real-time) | 0.31pp |

This is the Orphanides–van Norden (2002) result carrying over, as expected — the P-star
gap contains an output gap as one of its two components.

**The 2020–21 test cuts both ways.** In real time the gap jumped to +10.6 in 2020Q2 and
stayed high through 2021, so the model *would* have flagged the money surge — a real win
for the paper's central claim. But by 2021Q4 the real-time gap had faded to +2.2 and by
2022Q1 to −0.1, calling the all-clear, while the hindsight estimate says the impulse was
still near its peak (+9.2, +8.4). A policymaker following it live would have stood down
at exactly the wrong moment.

**Consequence for the current reading.** Applying the revision distribution:

| Spec | 2026Q1 gap | 90% band | sign certain? |
|---|---|---|---|
| M2/GDP | −0.13 | [−4.70, +7.33] | no |
| Divisia M2/GDP* | +0.62 | [−4.78, +6.77] | no |
| Divisia M4/GDP* | +1.02 | [−3.05, +6.33] | no |
| M2/PCE | −0.22 | [−5.62, +8.37] | no |
| Divisia M2/PCE* | +0.53 | [−3.53, +7.63] | no |
| Divisia M4/PCE* | +0.92 | [−3.61, +6.24] | no |

\* ALFRED has no Divisia vintages; the revision distribution is borrowed from M2/GDP.

Two things this does **not** say. It does not say the gap has not risen — the *change*
over 2024–2026 is far better identified than the level, since revisions are persistent
and largely common across adjacent quarters. And it does not overturn the forecast
arithmetic: conditioning on the measured gap, γ̂ × gap is still the right point forecast
(+9bp for the Divisia specs, 90% CI [+2, +16]), because γ̂ is the projection onto the
*noisy* gap and its attenuation is what makes it correct. Set that against the
regression's own residual spread of ~108bp per quarter.

Separately, an attenuation diagnostic: adding one more revision's worth of noise to the
gap shrinks γ̂ by ~52%, so the *structural* coefficient is materially larger than 0.10.
That matters for reading γ as economics, not for forecasting with it.

See `uncertainty.png`.

### Is recent inflation really supply-driven? (`supply_shocks.py`)

The paper's policy recommendation rests on an attribution it never estimates: the price
gap is near zero, therefore recent inflation "is more likely to reflect a combination of
adverse supply shocks — for instance, energy shocks, deglobalization shocks... — and
measurement error." No supply variable appears in any regression; the residual is assigned
a name. This tests it with Hamilton (1996) net oil price increases and the change in the
effective tariff rate (BEA customs duties / imports).

**The money signal survives.** γ is stable or slightly higher once supply is controlled
for, in all six specifications, and the supply block is jointly significant:

| Spec | γ base | γ + supply | HAC t | R² base | R² + supply | F(supply) |
|---|---|---|---|---|---|---|
| M2/GDP | 0.100 | 0.110 | 2.78 | 0.180 | 0.263 | 2.83 |
| Divisia M2/GDP | 0.077 | 0.091 | 2.72 | 0.171 | 0.260 | 3.05 |
| Divisia M4/GDP | 0.083 | 0.099 | 2.81 | 0.174 | 0.264 | 3.13 |
| M2/PCE | 0.125 | 0.121 | 3.69 | 0.193 | 0.327 | 5.08 |
| Divisia M2/PCE | 0.100 | 0.104 | 3.45 | 0.187 | 0.328 | 5.32 |
| Divisia M4/PCE | 0.100 | 0.101 | 3.54 | 0.183 | 0.321 | 5.17 |

Robust to dropping the contemporaneous supply terms (γ = 0.090–0.115) and to adding
import prices and PPI, which push R² to 0.60 while γ holds at 0.067 (t = 3.08). This is a
genuine point in the paper's favour: the price gap is not a repackaged supply shock.

**But the attribution for 2025Q1–2026Q1 does not hold up.** Cumulated contributions to the
change in inflation over the five quarters:

| | GDP deflator | PCE |
|---|---|---|
| actual change | **+1.14** | **+2.03** |
| inertia | −0.92 | −0.56 |
| money (gap) | −1.13 | −1.34 |
| **oil** | **+0.00** | **+0.01** |
| **tariffs** | **−0.54** | **+1.17** |
| constant | −0.93 | −1.27 |
| **unexplained** | **+4.66** | **+4.00** |

Two things fall out. The **deglobalization half of the story has real support** — tariffs
account for over half the rise in PCE inflation, the measure the Fed targets — and the
GDP/PCE split is economically coherent, since the GDP deflator excludes imports. The
**energy half has none**: oil *fell* through 2025, from $71.84 in 2025Q1 to $59.64 in
2025Q4, so there was no energy shock during the window the paper invokes one to explain.
And a large residual survives: neither money nor measured supply explains most of the
recent rise.

**The energy shock is arriving now.** 2026Q2 NOPI is 28.5 — rank 3 of 321 quarters since
1946, behind only 1974 and 1979H2 — as WTI went $59.64 → $71.98 → $95.75. Applying the
estimated pass-through:

| | GDP deflator | PCE |
|---|---|---|
| cumulated effect on inflation by 2027Q1 | **+1.52pp** | **+2.09pp** |
| money signal (γ × 2026Q1 gap), for scale | +0.06pp | +0.06pp |

The paper hedged on exactly this — "if oil prices continue to climb in the second half of
2027, then policy ought to move from neutral to restrictive" — but it is happening about a
year earlier than that. NOPI is asymmetric, so a partial reversal in oil would not net
this off.

**Caveats.** The 2025Q2 tariff move (+4.30pp) is the largest quarterly change since the
series begins in 1959, against a next-largest of +1.50pp in 1971Q4, so the coefficient is
extrapolated far outside the range that identifies it — indicative, not measured. And the
+4.66pp residual is about one residual standard deviation per quarter with 4 of 5
quarters positive: persistent, but no single quarter is extraordinary.

### Can a better filter rescue the gap? (`filters.py`)

**Yes — and this is the one extension that improves the paper's own object rather than
replacing it.** Sweeping the HP smoothing parameter and adding the Hamilton (2018)
regression filter, scored on real-time reliability (ALFRED vintages, M2/GDP) and on
predicting the change in inflation (Divisia M2):

| variant | noise/signal | sign err | std effect | HAC t | R² | OOS gain | DM t |
|---|---|---|---|---|---|---|---|
| HP λ=100 | 1.32 | 36% | 0.185 | 1.63 | 0.144 | 0.1% | −0.02 |
| HP λ=400 | 1.16 | 38% | 0.237 | 2.25 | 0.160 | 2.7% | −1.03 |
| **HP λ=1,600** (paper) | 1.09 | 33% | 0.262 | 2.47 | 0.169 | 3.3% | −1.11 |
| HP λ=6,400 | 1.02 | 27% | 0.267 | 2.51 | 0.169 | 3.1% | −1.08 |
| HP λ=25,600 | 0.89 | 28% | 0.262 | 2.52 | 0.167 | 2.6% | −0.98 |
| HP λ=100,000 | 0.78 | 30% | 0.246 | 2.46 | 0.161 | 1.7% | −0.74 |
| HP λ=1,000,000 | 0.74 | 38% | 0.192 | 2.07 | 0.146 | −0.1% | +0.07 |
| Hamilton, full-sample coefs | 0.24 | 11% | 0.414 | 4.54 | 0.224 | 6.6% | −1.56 |
| **Hamilton, recursive coefs** | **0.24** | **11%** | **0.344** | **2.74** | **0.243** | **5.4%** | **−1.69** |
| money growth (no trend) | 0.06 | 0% | 0.262 | 2.65 | 0.167 | 3.6% | −1.22 |

Within the HP family there is a genuine frontier — noise-to-signal falls monotonically in
λ while predictive power peaks around λ = 6,400 — so the paper's λ = 1600 is dominated
even inside its own family. But the interesting result is Hamilton, which beats every HP
variant on *both* axes simultaneously. Its trend is a forecast made from data eight
quarters earlier, so unlike the HP filter it has no endpoint to revise; the only revision
comes from re-estimated coefficients and data.

The recursive row is the honest one — applying full-sample Hamilton coefficients to
historical dates is a look-ahead, and it inflates the standardised effect from 0.344 to
0.414. Even after that correction Hamilton dominates λ = 1600 on every column, and its
Diebold-Mariano statistic of −1.69 is the closest any indicator in this repo comes to
beating an AR(4) (still short of two-sided significance; borderline one-sided).

So the P-star *idea* is defensible and it is the HP filter that was letting it down. The
practical choice is now between Hamilton (most predictive, decent real-time behaviour) and
money growth (near-perfect real-time behaviour, less predictive) — not between the paper's
gap and nothing.

### Can the endpoint problem be avoided rather than solved? (`nominal_gdp.py`)

**Yes, almost entirely.** Every problem above traces to estimating two unobserved trends
(V\* and Y\*) at the sample endpoint. Trying to estimate V\* *better* failed. This instead
needs it less, using the identity that with n = p + x and n\* = m + v\*, the nominal-GDP
gap n\* − n collapses to the velocity gap v\* − v — dropping Y\* entirely. One rung further,
money growth relative to nominal GDP growth needs no trend at all.

Real-time reliability down that ladder, from ALFRED vintages:

| indicator | latent trends | sd(revision) | noise/signal | corr | sign errors |
|---|---|---|---|---|---|
| price gap | V\*, Y\* | 3.13 | 1.09 | 0.47 | 33% |
| velocity gap (= nominal gap) | V\* | 3.48 | 0.99 | 0.55 | 37% |
| **money growth, 4q** | **none** | **0.27** | **0.06** | **1.00** | **0%** |
| money growth less nominal GDP growth | none | 0.75 | 0.13 | 0.99 | 4% |

Dropping Y\* buys almost nothing — V\* was doing the damage. Dropping both is
transformative: an 18-fold improvement in noise-to-signal, and zero real-time sign errors.

And the filtering machinery buys nothing in exchange. In sample, predicting the change in
GDP inflation with Divisia M2, raw money growth matches the price gap almost exactly
(standardised effect 0.262 vs 0.262; R² 0.167 vs 0.169; HAC t 2.65 vs 2.47). Out of sample
from 1990 it is slightly *better* (RMSE improvement over an AR(4) of 3.57% vs 3.33%,
Diebold-Mariano t −1.22 vs −1.11; neither significant).

Two things this does not fix. All four indicators show the same regime pattern — ~0 on
1990–2019, strong on 2020–2026 — so that is in the monetary information itself, not in the
filter. And no indicator beats an AR(4) significantly out of sample.

## Known caveats

**γ is not a constant.** See *Findings on model structure* above. The headline 0.10 is
rejected for 1990–2019 in the GDP-based specifications, and the model's out-of-sample
edge over an AR(4) since 1990 is not statistically significant.

**Standard errors still understate uncertainty.** `OLSResult` now supports Newey-West via
`hac_lags`, but nothing corrects for the price gap being a *generated* regressor — it is
built from filtered estimates of v* and x* and then treated as observed data. A bootstrap
through the whole pipeline (filter included) is the outstanding fix.

**Divisia real-time behaviour is assumed, not measured.** The CFS publishes no vintage
archive, so the revision distribution is measured on simple-sum M2/GDP and applied to the
Divisia specifications. The endpoint problem is a property of the filter rather than of
the aggregate, so this is plausible — but it is an assumption.

**Nothing here bands the *model*.** All the intervals condition on the P-star
specification being correct.

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

# real-time reconstruction from ALFRED vintages (~400 cached requests)
python vintages.py --fetch
python vintages.py

# supply-shock controls
python supply_shocks.py

# fewer-latent-trends comparison (needs the vintage cache)
python nominal_gdp.py

# filter frontier: HP lambda sweep vs the Hamilton (2018) filter
python filters.py

# current reading on the Hamilton gap, with bands
python current_reading.py
python plot_models.py

# charts
python plot_price_gaps.py --cfs data/Divisia.xlsx --out price_gaps.png
python plot_uncertainty.py
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
| `diagnostics/uncertainty.py` | Bands on the gap, on γ, and on the implied inflation effect. |
| `diagnostics/attenuation.py` | Does measurement error explain the regime dependence of γ? |

## Reproducibility and data vintages

The CFS revises its Divisia history monthly and **publishes only the current workbook — there
is no vintage archive**, and the Wayback Machine has never captured the file. An overwritten
workbook is therefore gone for good.

Date-stamped vintages are versioned in `data/` for exactly this reason:

| vintage | Divisia data through | used for |
|---|---|---|
| `data/Divisia_2026-08-04.xlsx` | June 2026 | current results, SSRN v2 (4 Aug 2026) |

`data/Divisia.xlsx` is a working copy of the newest vintage and is gitignored;
`download_cfs()` writes to a date-stamped file and will not silently overwrite one.

**Known gap.** The workbook underlying SSRN v1 (30 July 2026, Divisia through May 2026) was
overwritten in place before this policy existed and could not be recovered. The v1 *results*
are preserved in git history — `git show 1a2f7e3:PAPER.md` — but v1 cannot be re-run from a
clone. Everything from v2 onward can.

The ALFRED cache in `data/vintages/` is vintage-pinned by construction and unaffected.

## Data

| Source | Series |
|---|---|
| FRED | `GDP`, `GDPC1`, `PCECC96`, `PCECTPI`, `M2SL`, `GDPPOT`, `GDPNOW`, `PCEPI`, `PCEC96`, `USREC` |
| FRED (H.8 / H.4.1) | `TOTBKCR`, `BUSLOANS`, `REALLN`, `CONSUMER`, `TOTLL`, `WALCL`, `WRESBAL` |
| FRED (supply shocks) | `WTISPLC`, `B235RC1Q027SBEA`, `IMPGS`, `IR`, `PPIACO` |
| ALFRED | quarterly vintages of `GDP`, `GDPC1`, `M2SL`, 1992–2026, cached in `data/vintages/` |
| [CFS](https://centerforfinancialstability.org/amfm_data.php) | Divisia M2, M3, M4-, M4 (`Divisia.xlsx`) |

No API key required — everything comes through public CSV endpoints.

## Implementation notes

- `hp_one_sided_recursive` (expanding-window HP endpoint) and `hp_one_sided_kalman`
  (Stock-Watson 1999 filtered local-linear trend) agree to ~1e-8, as they must.
- The price gap is **exactly invariant to the level of real GDP/PCE**: the one-sided
  filter gains on `v*` and `x*` cancel, so `d(gap)/dx = (k-1) + (1-k) = 0`. Only the
  price index and the money stock move it. This is why the paper needs Table 2 —
  imposing constant potential growth is the only channel through which output re-enters.
