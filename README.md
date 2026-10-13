# clo-leveraged-loan-engine

A standalone Python library for synthetic structured credit cash flows and illustrative CLO, auto ABS and conduit CMBS waterfalls. It connects collateral payments, defaults and recoveries to tranche interest, principal, credit enhancement and losses. It produces auditable CSV and Markdown tables without runtime network access.

The supplied CLO portfolio contains **150 synthetic loans across 25 synthetic industries**, generated with seed **2026**. Nothing in the project represents a real deal, assigned tranche rating, market forecast or observed investment return. Python, NumPy and pandas are the only runtime requirements beyond the standard library.

## Run

Run from the project root. Tests and examples import the local source tree, so package installation is optional if the dependencies are already available.

```powershell
python -m unittest discover -s tests -v
python examples/loan_mechanics.py
python examples/run_analysis.py
python examples/run_structured_credit.py
```

For library use, install the local package:

```powershell
python -m pip install .
```

```python
from clo_engine import (
    illustrative_structure, portfolio_metrics, run_deal, synthetic_portfolio,
)

loans = synthetic_portfolio()
metrics = portfolio_metrics(loans)
structure = illustrative_structure(metrics["par"], metrics["purchase_cost"])
result = run_deal(loans, structure)

print(result.tranche_analytics())
print(result.equity_irr, result.equity_multiple)
print(result.ledger)
```

`run_deal` uses deterministic constant defaults by default. Supply `annual_default_rate=None` and an explicit seeded NumPy generator for stochastic rating-based defaults. `monte_carlo`, `stress_table`, `break_even_default_rate`, `discounted_value` and `discount_margin` expose the scenario and valuation tools. Prices passed to the discount-margin solver are currency amounts, not percentages.

## Methodology

Loans pay SOFR subject to a benchmark floor, plus spread. Scheduled amortization uses original par. Constant annual default and repayment probabilities convert by preserving survival over quarterly periods. Purchases below par create par build; equity funds actual loan purchase cost less par-priced note issuance.

Quality metrics include WARF, floor-aware WAS, model WARR, scheduled WAL, diversity, Caa share as a CCC proxy, lowest-price CCC excess haircuts, and borrower, industry, second-lien and cov-lite concentration tests. The rating factor table was checked against a [filed rating-factor definition](https://www.sec.gov/Archives/edgar/data/1253986/000110465917065845/a17-20585_1ex10d1.htm). Selected quality definitions and the industry equivalent-unit method were checked against [filed collateral metric definitions and the diversity schedule](https://www.sec.gov/Archives/edgar/data/1373561/000119312512507388/d455464dex41.htm).

Interest and principal proceeds remain separate. Taxes and senior expenses precede management fees and note interest. Shared A/B coverage tests and subsequent class tests divert interest to senior principal when needed. A reinvestment diversion test redirects interest to purchases. Principal buys synthetic replacement loans during the **4-year** reinvestment period, then amortizes notes sequentially. The example has **40 quarterly payments**. The structure adapts selected [filed CCC and coverage provisions and payment priorities](https://www.sec.gov/Archives/edgar/data/1702510/000170251024000079/indenture-clo2024x1.htm), with its own illustrative terms and an extra junior test.

Monte Carlo uses a quarterly one-factor Gaussian copula, fresh common shocks each quarter, absorbing borrower defaults, and independent beta recoveries. SOFR scenarios are flat, rising and falling. DCF applies successive benchmark-plus-margin discount factors. Own bisection solves normal thresholds, discount margins and constant-default loss boundaries. Equity IRR is an effective annual return from actual invested equity and distributions.

[Methodology](docs/methodology.md) defines every metric, payment priority, timing convention and simplification. [Primary source audit](docs/sources.md) distinguishes verified definitions from assumptions. All default probabilities, recovery means, correlations, trigger levels, fees, concentration limits, prices and reinvestment terms are **stylized/unverified assumptions**. There are no implemented regulatory parameters.

## Illustrative calibration

Notes total $450,000,000, or 90% of collateral par. Equity funds the residual purchase cost: **$47,540,494.46**, **9.555101%** of total funded capital and **9.508099%** of collateral par.

| Class | Share of collateral par | Spread over SOFR | OC trigger | IC trigger |
| :-: | :-: | :-: | :-: | :-: |
| A (AAA) | 63% | 150 bp | 125% | 120% |
| B (AA) | 11% | 210 bp | 125% | 120% |
| C (A) | 7% | 280 bp | 116% | 110% |
| D (BBB) | 5% | 400 bp | 110% | 105% |
| E (BB) | 4% | 650 bp | 104% | 100% |

Senior and subordinated management fees are 10 bp and 40 bp annually on opening collateral par. Administration expenses are $200,000 annually with a $250,000 cap. Initial B-rated loans cost 99% to 100.5% of par; Caa loans cost 94% to 98%. First-lien and second-lien recovery means are 70% and 40%. Reinvestment buys at 99.75% of par with a 360 bp spread, five-year maturity and B2 default risk. The four-year reinvestment period and ten-year horizon remain unchanged.

These inputs target illustrative return ranges, without empirical market calibration. The deterministic base remains a no-default cash flow case. Rating default assumptions and all other terms are detailed in [methodology](docs/methodology.md) and exported in [run parameters](examples/output/run_parameters.json).

## Validation and actual results

**169 unittest tests pass.** They cover hand-calculated coupons and portfolio metrics, analytic floater valuation, diversity table boundaries, default and recovery moments, arrears, coverage cures, cash conservation, principal reconciliation, monotone seniority loss boundaries, edge cases and solver round trips. Five calibration checks additionally enforce equity funding and return ranges, a visible Monte Carlo left tail, senior protection, and base-versus-stress coverage behavior. The structured credit tests add closed-form level-pay balances, absolute prepayments, reserve movements, OC turbo, latched loss triggers, bottom-up write-downs, refinance tests, extensions, delayed workouts, seeded determinism and stress monotonicity. All original tests and tolerances are retained. All three example scripts complete successfully. CI runs the suite and examples on the configured Python versions.

The following values come from the executed examples and committed [result tables](examples/output/results.md). Currency values are in dollars. The deterministic base uses no defaults; Monte Carlo introduces credit risk.

| Initial synthetic collateral metric | Result |
| :-: | :-: |
| Loan par | $500,000,000.00 |
| Purchase cost | $497,540,494.46 |
| Par build | $2,459,505.54 |
| Equity outlay | $47,540,494.46 |
| WARF, rounded up | 3008 |
| WAS | 3.445373% |
| Model WARR | 68.536722% |
| Scheduled WAL | 5.545246 years |
| Published-method diversity score | 67.3999 |
| Caa share | 7.538031% |
| CCC excess haircut | $10,325.51 |

All initial concentration tests pass. The published diversity method permits multiple diversity units within one industry. The separate industry effective count is **24.421985**. A single-industry effective count and published diversity score are different measures.

The no-default base produces equity IRR **13.949956%**, cash multiple **2.049228x**, and no note principal loss. All base note DCF prices equal **100.000000%** at their stated margins. Maximum absolute cash reconciliation error is **$7.450581e-9**; maximum collateral reconciliation error is **$5.960464e-08**. No base OC, IC or interest diversion tests breach. Near-par purchases and reinvestment limit synthetic par build; par redemption and frictionless reinvestment still benefit equity.

Monte Carlo uses **200 paths per scenario**, seed **90210**. Baseline latent correlation is **0.20** with beta recoveries. The severe case uses flat SOFR, default probabilities multiplied by **3**, latent correlation **0.35**, and fixed recovery **40%**.

| Scenario | Mean equity IRR | Lower-tail equity IRR | Median equity IRR | Upper-tail equity IRR |
| :-: | :-: | :-: | :-: | :-: |
| Flat | 9.0309% | 5.5382% | 9.3533% | 11.7070% |
| Rising | 9.7957% | 6.2791% | 10.1219% | 12.5115% |
| Falling | 7.8564% | 4.4049% | 8.1725% | 10.4712% |
| Severe | -49.3081% | -99.9900% | -48.2254% | -1.5014% |

Lower and upper tails are the empirical fifth and ninety-fifth percentiles. No note principal losses occur in the baseline samples, although coverage breaches occur. Zero observed losses do not establish zero population risk. The flat sample has mean equity cash multiple **1.600047x** and **0.5%** probability of negative equity IRR. The severe sample demonstrates the tranche protection hierarchy:

| Class | Synthetic label | Principal loss probability | Expected principal loss | OC breach probability |
| :-: | :-: | :-: | :-: | :-: |
| A | AAA | 0.5% | 0.011753% | 66.0% |
| B | AA | 1.5% | 0.794526% | 66.0% |
| C | A | 8.5% | 3.683905% | 89.0% |
| D | BBB | 21.0% | 13.079385% | 95.0% |
| E | BB | 49.5% | 33.186306% | 89.0% |

Expected loss is relative to initial tranche principal. Unpaid interest and sampling standard errors are reported separately in CSV. Breaches are recorded before each class's cure, so breach probabilities need not be monotone across classes.

The constant annual default boundaries at **40% recovery** are **14.7462%** for A, **11.4404%** for B, **8.6845%** for C, **6.5057%** for D, **4.3598%** for E. These are modeled first-principal-loss thresholds, not agency break-even metrics. At 10% annual defaults and 30% recovery, all classes breach both OC and IC tests and interest diversion is triggered. The [deterministic stress table](examples/output/stress.csv) and [raw Monte Carlo paths](examples/output/monte_carlo_paths.csv) expose the underlying results.

## ABS and CMBS

The auto ABS has $100,000,000 of synthetic collateral, 10,000 equal new loans, a 9% fixed coupon and 60 monthly level payments. Notes fund 94% of collateral; residual funding covers 6% initial OC plus a separately funded 1% reserve. Initial principal pays pro rata. Cumulative net loss at or above 4% permanently switches principal to sequential pay and traps all available excess spread as senior principal. Before the trigger, excess spread builds OC toward 8% of closing collateral with a 1% initial-par floor. Reserve cash supports fees and coupons, replenishes from excess spread, and releases at final maturity. The sequential option is also available independently of the trigger.

Absolute prepayment speed is a monthly fraction of the original loan count, capped at surviving loans, not annual CPR or a fraction of original principal. This convention was checked against [CarMax Auto Owner Trust 2024-4, Maturity and Prepayment Considerations, page 65](https://www.sec.gov/Archives/edgar/data/2037519/000119312524248421/d901858d424b5.htm). Default and severity curves are explicit synthetic assumptions. ABS defaults are deterministic fractional loan counts, so no simulation seed is required.

The CMBS pool has 80 synthetic commercial mortgages totaling $200,000,000, generated with seed 2026. Property labels cover office, retail, multifamily, industrial and hotel. Loans include full-term IO, partial IO and amortizing balloons. Closing DSCR and LTV imply NOI and property value. Monthly term defaults use path seed 90210. Balloon repayment requires refinance DSCR of at least 1.10 and LTV no greater than 80%. An eligible failed refinance can extend once for 12 months. Defaults enter special servicing, stop paying, and resolve after a 12-month lag. Principal pays sequentially; realized losses write down classes bottom-up. AAA through the B-piece fund the entire pool, with no OC or reserve. All coupons, tests, severities, extensions and servicing terms are illustrative assumptions.

```python
from clo_engine import (
    AutoPool, abs_scenarios, run_abs, synthetic_mortgages, cmbs_scenarios, run_cmbs,
)

abs_result = run_abs(AutoPool(), scenario=abs_scenarios()[1])
cmbs_result = run_cmbs(synthetic_mortgages(), scenario=cmbs_scenarios()[1], seed=90210)
print(abs_result.tranche_analytics())
print(cmbs_result.tranche_analytics())
```

These values come from `python examples/run_structured_credit.py` and [its result tables](examples/output/structured_results.md). Loss percentages use initial pool or class principal as indicated. Class WAL weights principal actually paid.

| Sector and scenario | Pool cumulative net loss | Total note principal loss | BBB-like principal loss |
| :-: | :-: | :-: | :-: |
| ABS base | 2.726734% | $0.00 | 0.000000% |
| ABS stress | 20.406592% | $6,912,478.95 | 86.541803% |
| ABS severe | 49.275693% | $37,580,831.80 | 96.001268% |
| CMBS base | 2.130883% | $4,261,766.37 | 0.000000% |
| CMBS stress, rates up | 38.855390% | $77,710,779.99 | 100.000000% |
| CMBS severe | 57.970014% | $115,940,027.53 | 100.000000% |
| CMBS refinance rates up only | 19.613815% | $39,227,629.59 | 100.000000% |

ABS stress and severe switch at months 7 and 3. The ABS BBB-like class has first-loss CNL boundaries of 14.098793% in the base parameter family, 15.650057% in stress, and 16.639943% in severe. Each search scales that scenario's default curve while fixing severity and prepayment speed. These are modeled first-loss boundaries, not rating agency breakeven criteria. All classes' boundaries are exported in [abs_break_even_cnl.csv](examples/output/abs_break_even_cnl.csv).

CMBS base losses affect only the B-piece, which loses 42.617664% of initial principal. Combined stress raises refinance rates from 5.5% to 8.5%, reduces NOI to 85% and property value to 80%, and increases defaults and severity. The separate rate-only scenario changes only the refinance rate to 8.5%. Extensions number 4 in base, 42 in combined stress, and 33 in the rate-only scenario. Combined stress also produces $1,852,639.63 of unpaid note interest; interest shortfalls remain separate from principal loss.

## Cross-sector comparison

The comparison uses each sector's own base and stress assumptions. It is descriptive, not a common calibrated shock or a comparison of assigned ratings. Initial subordination includes collateral below class D and ABS OC, but excludes the separately funded ABS reserve. CLO stress uses 10% annual defaults and 30% recovery. ABS uses its stress seasoning curve; CMBS uses the combined rates-up stress above.

| BBB-like class D | Initial subordination | Base WAL, years | Stress WAL, years | Base principal loss | Stress principal loss |
| :-: | :-: | :-: | :-: | :-: | :-: |
| CLO | 14% | 7.039284 | Undefined | 0% | 100% |
| ABS | 8% | 1.952092 | 0.293003 | 0% | 86.541803% |
| CMBS | 8% | 9.652708 | Undefined | 0% | 100% |

Undefined WAL means no principal was received. ABS stress WAL describes the small payments received before the trigger and later write-downs, not the time until full repayment. CLO reinvests and uses coverage diversions; ABS amortizes monthly and uses reserve, OC and CNL switching; CMBS concentrates principal at balloons and delays loss realization through servicing. Shared tranche inputs, principal allocation and reporting conventions keep the comparison auditable. Full ledgers and class loss allocations appear in `examples/output`.

All pools are synthetic, servicing is simplified, and no rating agency criteria are implemented. Property types are descriptive labels; CMBS has no rent roll, property valuation model, advances, appraisal reductions or workout negotiation. ABS has homogeneous unseasoned loans, immediate fixed-severity recoveries, permanent write-downs with no reinstatement, and no revolving credit-card mechanics. The deliberately harsh stresses can impair even the AAA-like classes. These models are not trustee models, ratings or forecasts.

## Files and outputs

- `src/clo_engine/`: loan mechanics, metrics, numerical primitives, structure, waterfall, cash flow engine, simulation, valuation, ABS, CMBS, monthly structured accounting and comparison.
- `tests/`: standard-library unittest suite; no pytest or external scientific toolkit.
- `docs/`: methodology and primary source audit.
- `examples/loan_mechanics.py`: standalone floor, amortization and prepayment demonstration.
- `examples/run_analysis.py`: complete portfolio, valuation, Monte Carlo and stress workflow.
- `examples/run_structured_credit.py`: ABS and CMBS scenario ledgers, tranche losses and WAL, ABS CNL boundaries, mortgage events and the common BBB-like comparison.
- `examples/output/`: synthetic input CSVs, payment ledger, concentration checks, tranche analytics, stress results, loss boundaries, raw paths, summaries and Markdown tables.
- `.github/workflows/ci.yml`: reproducible validation workflow.

## Limitations

This is a synthetic research engine, not a trustee model or a rating tool. The CLO module omits trustee-level day count nuances, loan-level legal modeling, manager trading, recovery delays, migrations, credit calibration, dynamic market prices, legal discount-obligation haircuts, transaction costs, hedges, refinancing, optional calls and legal enforcement waterfalls. CLO recoveries arrive immediately, surviving terminal collateral redeems at par, and replacement loans use fixed synthetic terms. Concentration and full quality tests describe initial CLO collateral; reinvestment does not reproduce indenture eligibility enforcement. The CMBS module adds simplified refinancing, extensions and recovery delays as described above.

Model WARR uses assumed recoveries. The diversity table cap above its published endpoint is stylized; synthetic industry labels are not the full agency map. Note life reports timing of principal actually paid and excludes paths with no principal receipt from its average. Event-of-default flags are diagnostics and do not accelerate the deal. Scenario valuations use physical simulated cash flows, not risk-neutral calibration. All these choices can materially change tranche risk and equity returns.

MIT licensed. No external data or runtime services are required.
