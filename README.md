# clo-leveraged-loan-engine

A standalone Python library for synthetic leveraged loan cash flows and an illustrative CLO waterfall. It connects loan coupons, amortization, prepayments, defaults and recoveries to collateral quality tests, reinvestment, sequential note payments and equity distributions. It produces auditable CSV and Markdown tables without runtime network access.

The supplied portfolio contains **150 synthetic loans across 25 synthetic industries**, generated with seed **2026**. Nothing in the project represents a real deal, assigned tranche rating, market forecast or observed investment return. Python, NumPy and pandas are the only runtime requirements beyond the standard library.

## Run

Run from the project root. Tests and examples import the local source tree, so package installation is optional if the dependencies are already available.

```powershell
python -m unittest discover -s tests -v
python examples/loan_mechanics.py
python examples/run_analysis.py
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

**124 unittest tests pass.** They cover hand-calculated coupons and portfolio metrics, analytic floater valuation, diversity table boundaries, default and recovery moments, arrears, coverage cures, cash conservation, principal reconciliation, monotone seniority loss boundaries, edge cases and solver round trips. Five calibration checks additionally enforce equity funding and return ranges, a visible Monte Carlo left tail, senior protection, and base-versus-stress coverage behavior. Existing test conditions and tolerances are retained; calibration-dependent fixtures and expected numbers are updated. Both example scripts complete successfully. CI runs the suite and both examples on the configured Python versions.

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

## Files and outputs

- `src/clo_engine/`: loan mechanics, metrics, numerical primitives, structure, waterfall, cash flow engine, simulation and valuation.
- `tests/`: standard-library unittest suite; no pytest or external scientific toolkit.
- `docs/`: methodology and primary source audit.
- `examples/loan_mechanics.py`: standalone floor, amortization and prepayment demonstration.
- `examples/run_analysis.py`: complete portfolio, valuation, Monte Carlo and stress workflow.
- `examples/output/`: synthetic input CSVs, payment ledger, concentration checks, tranche analytics, stress results, loss boundaries, raw paths, summaries and Markdown tables.
- `.github/workflows/ci.yml`: reproducible validation workflow.

## Limitations

This is a synthetic research engine, not a trustee model or a rating tool. It omits trustee-level day count nuances, loan-level legal modeling, manager trading, recovery delays, migrations, credit calibration, dynamic market prices, legal discount-obligation haircuts, transaction costs, hedges, refinancing, optional calls and legal enforcement waterfalls. Recoveries arrive immediately, surviving terminal collateral redeems at par, and replacement loans use fixed synthetic terms. Concentration and full quality tests describe initial collateral; reinvestment does not reproduce indenture eligibility enforcement.

Model WARR uses assumed recoveries. The diversity table cap above its published endpoint is stylized; synthetic industry labels are not the full agency map. Note life reports timing of principal actually paid and excludes paths with no principal receipt from its average. Event-of-default flags are diagnostics and do not accelerate the deal. Scenario valuations use physical simulated cash flows, not risk-neutral calibration. All these choices can materially change tranche risk and equity returns.

MIT licensed. No external data or runtime services are required.
