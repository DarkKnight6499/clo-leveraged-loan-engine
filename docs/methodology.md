# Methodology and model boundaries

## Scope and units

The package models fully funded synthetic floating rate loans and an illustrative cash CLO, plus monthly auto ABS and commercial mortgage CMBS. Monetary amounts are currency units, rates and prices are decimal fractions, and time is years. CLO payments occur quarterly; ABS and CMBS payments occur monthly. AAA through the B-piece are synthetic labels for payment priority, not assigned ratings. The existing CLO methodology below is unchanged; the monthly model sections define the additional conventions. There is no network access at runtime. Public definition checks are recorded in [sources.md](sources.md).

The synthetic generator uses `numpy.random.default_rng` with an explicit seed. Borrower identity, industry, rating, par, spread, benchmark floor, maturity, amortization, purchase price, lien and covenant flags, and recovery mean are immutable loan inputs. Industries are simplified synthetic labels, not a complete agency classification map. Reinvestment loan balances remain separate from original loans.

## Supplied calibration and observed results

The calibration changes only illustrative inputs. Coupon, default, recovery, valuation and waterfall formulas and timing conventions are unchanged. The terms are chosen to produce moderate synthetic equity returns, not fitted to observed deals or an agency model. The base case retains zero defaults, so its return is a no-credit-loss illustration; Monte Carlo supplies credit risk.

On $500,000,000 collateral par, note shares A/B/C/D/E are 63%/11%/7%/5%/4%, with SOFR spreads of 150/210/280/400/650 bp. OC triggers are 125%/125%/116%/110%/104%, and IC triggers are 120%/120%/110%/105%/100%. A and B share tests. The D-level reinvestment diversion trigger is 108%, with a 50% diversion fraction. Senior and subordinated management fees are 10 and 40 bp annually. Administration costs are $200,000 annually, capped at $250,000; assumed taxes are zero.

The seeded portfolio keeps its rating mix, loan amounts, maturities, floors and industry assignments. Loan spreads are 250 bp plus 40 bp per rating step from B1 through Caa3, a uniform 0 to 80 bp component, and an additional 100 bp for second liens. B-rated purchase prices are uniform from 99% to 100.5%; Caa prices are uniform from 94% to 98%. Recovery means are 70% for first liens and 40% for second liens, with independent beta concentration 20.

| Rating | Assumed annual default probability |
| :-: | :-: |
| B1 | 0.75% |
| B2 | 1.25% |
| B3 | 2.5% |
| Caa1 | 6% |
| Caa2 | 12% |
| Caa3 | 20% |

Reinvestment remains four years over a ten-year horizon. Replacement loans buy at 99.75% of par, earn SOFR plus 360 bp, use B2 default risk, mature five years after purchase, and amortize 1% of original par annually. Their benchmark floor remains 1%. Their recovery mean is initial portfolio WARR. Annual prepayment remains 10%. Near-par reinvestment reduces the mechanical par build that previously amplified equity returns. Recovery and default assumptions also change the amount of simulated credit loss.

The actual seed-2026 portfolio costs $497,540,494.46; par build is $2,459,505.54. Equity outlay is $47,540,494.46, or 9.555101% of funded capital and 9.508099% of collateral par. WAS is 3.445373%, and model WARR is 68.536722%.

The no-default base returns 13.949956% equity IRR and 2.049228x cash multiple. It has no note principal loss and no OC, IC or interest diversion breach. With 200 flat-SOFR paths and seed 90210, mean equity IRR is 9.0309%, the fifth percentile is 5.5382%, and mean cash multiple is 1.600047x. Negative equity IRR occurs in 0.5% of flat paths. No note principal loss is observed in that sample; credit losses reduce equity distributions first. Zero observed losses are not a population guarantee.

At 10% constant annual defaults and 30% fixed recovery, all classes breach OC and IC, and reinvestment interest diversion triggers. First-principal-loss annual default boundaries at 40% recovery are A: 14.7462%, B: 11.4404%, C: 8.6845%, D: 6.5057%, E: 4.3598%. Their descending order confirms seniority protection in this illustration.

Full scenario results, cash reconciliation errors and parameters are reproduced by the example scripts in [the output tables](../examples/output/results.md). [README](../README.md) reports the rising, falling and severe scenarios. All economics in this section are stylized/unverified assumptions or model outputs, not current market observations.

## Loan proceeds and purchase economics

For surviving opening par B, coupon interest is:

`interest = B * (max(SOFR, floor) + spread) * 0.25`.

Scheduled amortization is one quarter of the annual rate times original par. Payments cannot exceed outstanding par. The engine scales the amortization base when deterministic fractional defaults remove part of a loan. Prepayments occur after amortization. Constant annual repayment and default probabilities convert to quarterly probabilities with `q = 1 - (1 - annual_rate)^0.25`, preserving annual survival.

Default happens at the start of a period. Defaulted principal earns no coupon. Recovery arrives immediately as principal proceeds. After interest accrual, amortization and prepayment, loans maturing on the payment date pay the remaining balloon. Off-grid maturity dates pay at the next quarter. The last deal date liquidates any remaining performing loans at par. The public loan schedule requires a curve through maturity and does not silently force early redemption.

Purchase cost is `par * price`. Par build is par minus that cost. The generator has near-par B-rated loans, including premium purchases, and lower-priced Caa loans. Its purchase price also acts as a static market-value proxy for CCC excess selection. Equity funds purchase cost less par-priced note issuance. A discount purchase can materially increase modeled equity returns. There is no issuance cost, accrued purchase interest or ramp-up period.

## Portfolio metrics

Metric formulas apply to the supplied performing, fully funded collateral. Cash is excluded from quality weights. Defaults are removed in the cash flow engine. There are no unfunded commitments, fixed rate loans, deferring assets or hidden adjustments.

- WARF: par weighted rating factors, rounded up to an integer. The unrounded value is also exposed.
- WAS: par weighted `spread + max(floor - SOFR, 0)`. This is a floor-aware effective spread over the current benchmark, not the all-in coupon.
- WARR: par weighted model recovery means, unrounded. First-lien and second-lien assumptions are stylized.
- WAL: principal-payment-weighted scheduled life, then weighted by loan par. It includes amortization and maturity, with no assumed default or optional prepayment for this quality metric.
- CCC share: Caa loan par divided by performing par. This is a Moody's-style rating proxy, not a reproduced S&P rating classification.
- CCC excess haircut: excess par above the configured bucket allowance, selected in ascending price order, valued at the static price proxy. A fractional slice of the boundary loan is allowed. The haircut is selected par times `max(1 - price, 0)`. No premium increases the numerator.
- OC collateral: surviving performing par minus that haircut, plus remaining principal cash when tests are run. Other indenture adjustments, including separate discount-obligation haircuts, are omitted.
- Concentrations: aggregate facilities by borrower and industry before measuring the largest share. Second-lien and cov-lite shares use total performing par. Limits are illustrative.

These choices follow selected filed definitions, with adaptations and omissions identified in [sources.md](sources.md). They do not define a universal indenture convention. Portfolio WARR intentionally omits contractual agency rounding.

## Published diversity method

Facilities aggregate by borrower. Equivalent units are borrower par divided by average borrower par, capped at one. Industry totals map to the lower published table row; scores then sum. `industry_diversity_units` encodes the verified table segments at the same row precision. Scores above the final equivalent-unit row are capped at its final score, a stylized extension.

One borrower produces one unit. Equal borrowers in separate industries produce the borrower count. Multiple borrowers in the same industry can produce more than one unit under the published method. For example, three equal borrowers in one industry produce two diversity units. Treating every industry as exactly one unit would contradict the table. The additional `industry_effective_count` metric is inverse industry Herfindahl concentration; all borrowers in one industry give one under that different measure. These distinctions are tested independently. Affiliated legal entities must be assigned the same borrower identity by the caller; no affiliate inference is attempted.

## Illustrative waterfall

The initial capital structure has five sequential note classes and residual equity. All note coupons use nonnegative SOFR plus stated spreads, accrued on opening note balances. Reinvestment lasts four years in the supplied example, followed by sequential amortization. The horizon is ten years. The first payment is a quarter after the synthetic closing date. No business-day roll or legal determination-date lag is modeled.

Separate cash buckets follow this order:

1. Taxes, capped newly accrued trustee and administration expenses, and the senior management fee. Interest pays first, with principal supporting any shortfall.
2. Class A interest, then Class B interest. Principal can support unpaid current or prior A/B interest.
3. Shared A/B OC and IC tests. Available interest pays senior note principal until both pro forma tests pass or interest is exhausted.
4. Class C interest and its tests, then Class D interest and its tests, then Class E interest and an extra illustrative E test.
5. During reinvestment, a stricter D-level OC diversion test redirects the configured fraction of remaining interest to loan purchases, capped at the modeled par cure need.
6. The subordinated fee and residual equity interest.
7. Remaining principal buys new collateral during reinvestment. After reinvestment, it pays senior notes sequentially. At final liquidation, each class receives unpaid interest before its principal in seniority order. Principal remaining after all notes, interest arrears and subordinated fees pays equity.

Unpaid interest and fees carry as separate arrears, without interest on interest or automatic principal capitalization. The expense cap applies to newly billed administration costs; previous unpaid amounts can be caught up above the new-period cap. Costs above the cap are not separately accrued. Fees use opening collateral par. Unpaid fees are not reported as tranche principal losses.

OC is adjusted collateral plus unused principal cash divided by cumulative live note balances through the tested class. IC is current collateral interest less due senior expenses, floored at zero, divided by quarterly coupon on cumulative live debt. Ratios and breach flags record the point before each cure. A/B share one test. C, D and E tests see prior senior cures. Sequential paydown reduces the IC denominator using the actual senior coupon rates. Cure amounts use the maximum of the required OC and IC paydown. This is a pro forma coupon test, rather than a trustee reconstruction of collection-period interest.

Principal does not independently run a legal coverage cure waterfall during reinvestment. Existing OC tests use principal cash at par before purchases; buying at a premium can lower next-period collateral par. The simplified reinvestment mandate does not enforce all collateral-quality or concentration tests on every purchase. Portfolio quality results and concentration tests describe initial collateral. Dynamic OC includes reinvestment balances and cash.

`event_default` is a post-allocation diagnostic: unpaid A/B interest or A/B OC below the configured floor. It is neither a legal default determination nor an acceleration instruction. A flagged deal continues through the ordinary waterfall. There is no enforcement liquidation waterfall, grace period or voting process.

## Reinvestment

Each quarter's purchase cash buys par at the configured constant purchase price. Each purchase creates equal new synthetic obligors across the industry labels. New loans use B2 default risk, the configured spread and remaining maturity, a benchmark floor, and annual original-par amortization. Their recovery mean equals initial portfolio WARR. These are pooled synthetic assumptions; new loans have no manager-selected legal or covenant characteristics. Purchases occur at period end and first earn coupon next period. Performing loans default only once; unused historical slots remain at zero balance.

## Default and recovery simulation

Each quarter draws a fresh common Gaussian factor and one independent Gaussian shock per borrower:

`latent_i = sqrt(rho) * common + sqrt(1 - rho) * individual_i`.

Default occurs when latent is below the inverse standard normal quarterly default threshold. The inverse CDF uses bisection and the CDF uses `math.erf`. Multiple facilities of the same borrower share the shock and must share a default probability rating. Distinct borrowers have latent correlation rho. This is not default-indicator correlation. Common factors are independent across quarters, making the model a sequence of conditional-survival period copulas, not a persistent lifetime copula.

The annual rating default table is stylized/unverified. Multipliers apply to annual probabilities before converting periods and are capped at one. Defaults are absorbing. Rating migrations, systematic rating changes and time-varying hazard calibration are absent.

Recovery is independent beta noise with `alpha = mean * concentration` and `beta = (1 - mean) * concentration`. Its expected value is the lien-based model mean. Endpoint means give deterministic zero or full recovery. Default-weighted realized recovery need not equal initial par-weighted WARR. A supplied recovery override is fixed, as used in deterministic stresses and the severe Monte Carlo illustration. There is no common recovery factor, recovery lag or negative default-recovery dependence.

Each Monte Carlo path has its own `SeedSequence` child generator. SOFR curves are deterministic flat, rising or falling scenarios. Matching scenario seeds give comparable credit randomness where reinvestment cohort creation remains identical. Equity percentiles are empirical, not fitted to a parametric distribution. The severe case changes credit assumptions; it is not a forecast.

## Valuation and tranche risk

DCF uses successive discount factors `1 + (SOFR_t + margin) * 0.25`. Coupon accrual and discounting therefore reconcile a fully repaid floater to par when margin equals its stated spread. Negative margins are allowed if all discount factors remain positive. Discount margin solves the currency-price equation by an independently implemented bisection with an expanding upper bracket. It requires nonnegative future cash flows. A price percent must first be converted to a currency amount.

Equity IRR solves for log annual growth. A single initial outlay and nonnegative distributions produce a unique root. Returned IRR is an effective annual rate; discount margin is a nominal annual quarterly-compounded spread. Total loss returns minus one. The cash multiple is distributions divided by the actual equity outlay.

Tranche principal loss is remaining principal at the terminal date divided by initial notional. Unpaid terminal interest is reported separately and is not included in principal loss probabilities. Paid principal life is time-weighted principal receipts divided by principal actually received. Monte Carlo life averages exclude paths with no principal receipt and report their count. It is conditional receipt timing, not an unconditional promise to repay. DCF values from simulated physical credit scenarios are scenario valuations, not arbitrage-free market prices.

Break-even default rate is the constant annual fractional default probability where a tranche first has principal loss above the documented numerical threshold. Recovery, prepayment, SOFR and reinvestment terms are held fixed. Bisection operates on the loss indicator, returning the impaired side of the rate bracket. It assumes monotone impairment under the specified structure; tests check a grid and each returned boundary for the supplied cases. Arbitrary custom waterfalls need their own monotonicity audit. If no loss occurs even at full annual default, the result is NaN. This annual probability is different from cumulative lifetime default or an agency break-even default metric.

## Reconciliation and validation

The cash ledger reconciles interest plus principal input against expenses, note interest, note principal, fees, equity and purchase cash. Coverage diversion is a subset of note principal; interest diversion is a subset of purchase cash. Neither is counted twice. Collateral reconciles opening par less defaults and repayments, plus newly purchased par, to closing par. Terminal note balances reconcile to issued par less principal paid.

The unittest suite covers analytic coupon and floater benchmarks, hand metric cases, loan splitting, monotone prices and defaults, cash additivity and conservation, OC cures, sequential seniority, arrears, extreme defaults and recoveries, root round trips, seeded reproducibility, and sampling checks against normal and beta moments. Floating-point currency errors are measured explicitly, rather than rounded away in the ledger. The tables in `examples/output` retain the empirical observations behind summaries.

## CLO omitted features

No trustee-level day count nuances, loan-level legal modeling, manager trading, price evolution, agency rating assignment, recovery workouts, maturity extensions, credit facilities, warehouse or ramp-up financing, unfunded revolvers, hedges, FX, fixed-rate assets, refinancing, resets, optional calls, investor taxes, incentive fees, transaction costs, liquidity premiums, legal discount-obligation OC rules, rating migration or real data calibration is included. No optimizer, external scientific library, chart renderer or spreadsheet deliverable is needed. The engine is a reproducible synthetic research model with explicit assumptions.

## Shared monthly structured credit machinery

`structured.py` introduces `CreditStructure`, `CreditResult` and the monthly `allocate_credit` waterfall. The existing `Tranche` input and `WaterfallState` balances are reused. `waterfall.py` now exposes `pay_principal` for sequential or live-balance pro rata payments and `allocate_losses` for bottom-up write-downs. The original CLO uses the same sequential principal primitive while retaining its quarterly waterfall, coverage tests, fees and terminal loss convention.

For monthly fixed-rate notes, `Tranche.spread` stores the entire annual coupon, with no benchmark added. Its OC and IC fields are set to one and are not used by the monthly models. These conventions are different from floating-rate CLO spreads. Structures may have any number of uniquely named classes in seniority order. There is no rating assignment or agency criterion.

Monthly cash priority is servicing fee and previous fee arrears, note coupons and previous interest arrears in seniority order, reserve replenishment, any ABS OC turbo, ordinary principal, then residual cash. Reserve supports fees and coupons in that same order. Note interest accrues on opening live note balances, before current-month principal payments and write-downs. Arrears carry without compounding, even after a class is written down. Principal supports unpaid fees and coupons only after all live principal is paid. Remaining reserve releases into principal at the final date. CMBS disables turbo and has no reserve.

Cash reconciliation includes the reserve: opening reserve plus collateral interest and principal equals fees, note interest, note principal, residual cash and closing reserve. Reserve deposits, draws and releases are transfers inside that identity. Turbo is part of note principal, not an additional use. Write-downs are noncash and are never reported as principal payments. Per class, initial principal equals principal paid plus cumulative write-downs plus ending live balance. `CreditResult.tranche_analytics()` uses cumulative write-downs plus any ending balance as principal loss, with unpaid interest reported separately.

Paid-principal WAL is `sum(time * principal_paid) / sum(principal_paid)`, consistent with the CLO result. No principal receipt gives NaN, displayed as undefined in the README. A short WAL on an impaired class can reflect a few early payments followed by loss. It does not imply rapid full repayment. Monthly result objects provide the same core analytics columns used by the comparison table; they do not add monthly DCF or equity IRR calculations.

## Auto ABS pool mechanics

`AutoPool` describes equal, unseasoned fixed-rate auto loans. The supplied pool has $100,000,000 par, 10,000 loans, a 9% annual coupon and 60 months. For each original loan balance P, monthly rate r and term N, the level payment is `P * r / (1 - (1 + r) ** (-N))`. At zero rate it is `P / N`. `level_payment` uses `log1p` and `expm1` to avoid cancellation at small positive rates. The no-default, no-prepayment balance after t payments is `P * (1 + r) ** t - payment * ((1 + r) ** t - 1) / r`. Tests compare every payment date to that closed form.

Default happens at the beginning of the month. The annual conditional default curve converts to a monthly fraction using `1 - (1 - annual_default) ** (1 / 12)`. It removes fractional surviving loan counts, not complete stochastic loans. Defaulted balances receive immediate principal recovery equal to defaulted par times one minus loss severity. They pay no current interest. Surviving loans accrue interest and pay the original per-loan level payment. Scheduled principal is capped at the remaining balance; the final month clears numerical residue.

After scheduled principal, prepayment removes `min(surviving_count, ABS_speed * original_count)` loans at their then-remaining per-loan balance. Absolute speed is a monthly fraction of the original number of loans, not annual CPR, monthly SMM or original principal. The convention and equal-loan assumption were verified in [CarMax Auto Owner Trust 2024-4, Maturity and Prepayment Considerations, page 65](https://www.sec.gov/Archives/edgar/data/2037519/000119312524248421/d901858d424b5.htm). The engine adds fractional defaults and treats voluntary prepayments separately from default liquidations, a stylized adaptation. A large speed cannot remove more than the surviving count. ABS is deterministic and requires no seed.

`ABSScenario` accepts either scalars or one value per month for the annual default curve, severity curve and absolute prepayment speed. The supplied seasoning shape interpolates monthly fractional age through points `(0, 0.5)`, `(0.25, 1.5)`, `(0.5, 1.0)` and `(1, 0.4)`. Default curves equal the following scale times that shape. Severities and speeds are constant in the supplied cases.

| ABS scenario | Annual default scale | Loss severity | Monthly ABS speed |
| :-: | :-: | :-: | :-: |
| Base | 2.5% | 50% | 1.0% |
| Stress | 15% | 65% | 0.5% |
| Severe | 35% | 80% | 0.2% |

Every value in this table is an explicit synthetic assumption. No empirical or agency calibration is claimed. `structured_parameters.json` exports all monthly curve values.

## Auto ABS enhancement, triggers and losses

Class shares A/B/C/D/E are 70%/10%/8%/4%/2% of initial par; fixed coupons are 4%/4.5%/5%/6%/7.5%. Notes total 94% of par. The 6% residual collateral is initial OC. The reserve is separately funded at 1% of initial par, so initial residual funding is 7% of par, including reserve. Reserve replenishment targets that same fixed amount until final maturity. Servicing costs 1% annually on opening performing par. There is no modeled yield on reserve cash.

Ordinary principal starts pro rata across live balances, unless `pro_rata=False`. CNL is cumulative defaulted par less immediate recoveries divided by initial collateral par. At or above 4% CNL, the trigger permanently switches ordinary principal to sequential payment and applies all excess interest after fees, coupons and reserve replenishment as senior principal. The current month's losses can switch the current month's waterfall. The trigger never cures back to pro rata.

Before the trigger, excess spread pays senior principal only to build the OC target. The required OC amount is the larger of 8% of closing performing collateral and 1% of initial par, capped at closing collateral. Turbo need is live debt minus this month's ordinary principal cash minus closing collateral plus target OC, floored at zero. Turbo is capped by available excess spread and live debt, and always pays sequentially even when ordinary principal is pro rata. Target OC is a cash retention rule, not a promise that enough cash exists to reach it.

After interest and principal allocation, any excess of live notes over performing collateral plus reserve is written down bottom-up. Initial OC, reserve and principal paid from excess spread therefore support notes before write-downs. Written principal is never reinstated, even if future excess spread later improves coverage. This permanent monthly deficit rule is a simplifying, potentially conservative assumption. Pro rata payments before trigger mean a junior class can receive principal before its later loss.

The actual run produces pool CNL of 2.726734%, 20.406592% and 49.275693% in base, stress and severe. Note losses are $0.00, $6,912,478.95 and $37,580,831.80. Stress switches at month 7 and severe at month 3; base never switches. Class D principal losses are 0%, 86.541803% and 96.001268%. No terminal unpaid note interest occurs in these ABS cases. Detailed results are in [structured_results.md](../examples/output/structured_results.md).

## ABS modeled first-loss CNL boundaries

`abs_break_even_cnl` fixes a scenario's severity and ABS speed, scales its positive annual default curve, and clips annual probabilities at one. The upper search point makes every date's annual default probability one. For each class, bisection returns the impaired side of the first-loss threshold, defined as cumulative class write-down above `initial_pool_par * 1e-10`, or $0.01 in the supplied pool. The search uses 40 iterations. Reported CNL is total lifetime pool net loss from that boundary run, not the CNL in the first month of impairment. NaN means no loss even at the searched endpoint.

| Class | Base-family first-loss CNL | Stress-family first-loss CNL | Severe-family first-loss CNL |
| :-: | :-: | :-: | :-: |
| A | 31.670799% | 33.968192% | 35.521314% |
| B | 23.177856% | 25.301507% | 26.853822% |
| C | 17.008532% | 18.753499% | 19.943304% |
| D | 14.098793% | 15.650057% | 16.639943% |
| E | 12.826342% | 14.218309% | 15.105362% |

These run outputs differ across parameter families because loss timing, severity, prepayments and retained spread differ. They are not static subordination percentages or rating agency breakeven metrics. Bisection assumes a monotone first-impairment indicator along the fixed search family. Tests audit grids and both sides of the returned boundaries in the supplied families. With pro rata switching, the dollar loss of a junior class need not rise at every fine increment in default rate: earlier triggers can preserve more senior cash while changing how much junior principal pays before switching. The standard base, stress and severe tranche loss vectors are monotone. Custom curves and structures need their own monotonicity audit.

## CMBS mortgage pool and refinance model

`Mortgage` stores loan ID, property type, original par, fixed coupon, closing DSCR, closing LTV, maturity date, IO months and amortization months. The supplied seed-2026 generator creates 80 loans totaling $200,000,000. Amounts are proportional to independent uniform weights between 0.5 and 1.5. Coupons are uniform between 5% and 6.5%, DSCR between 1.25 and 1.85, and LTV between 55% and 78%. Maturities range from 60 to 120 months after January 1, 2026. Full-term IO is selected with probability 40%; other loans have zero, 24 or 36 IO months. Amortization uses a 360-month level-payment schedule. All these choices are unverified illustrative inputs.

Initial property value is `original_par / LTV`. Initial annual debt service is original par times coupon for an initially IO loan, or twelve monthly level payments for an amortizing loan. Initial NOI equals closing DSCR times that debt service. Scenario multipliers apply to NOI and value throughout the path. Property labels do not independently change hazard, severity or valuation. After IO ends, the original level payment resumes without a recast; loans pay the remaining balloon at maturity if refinance succeeds.

At each month's start, an independent uniform loan draw is compared to `1 - (1 - annual_default_rate) ** (1 / 12)`. A term default is absorbing. At maturity, surviving loans test opening principal against a new 360-month amortizing refinance loan. Refinance DSCR equals stressed NOI divided by twelve level payments at the scenario refinance rate; refinance LTV equals opening balance divided by stressed property value. Both DSCR at least 1.10 and LTV no greater than 80% are required. Off-grid maturity dates test at the next monthly payment date. A successful refinance pays the coupon, scheduled principal and remaining balloon that month.

If either test fails, an unextended loan can extend once if stressed NOI covers its existing annual interest, the seeded extension draw passes the 60% probability, and extension duration is positive. Its original coupon continues for the 12-month extension. Existing IO ends on its original IO date, including during extension. The extended maturity reruns the same refinance tests; another failure defaults rather than extending again. There is no rate recast or endogenous refinancing market.

NOI also caps each performing loan's monthly interest and scheduled principal cash. Missing loan interest is not advanced or capitalized. Defaulted loans immediately stop paying and enter a pending special-servicing balance. Twelve months later, the defaulted principal resolves into recovery and realized loss at the scenario's fixed severity. The entire defaulted principal remains in the pending ledger until resolution; it is not treated as cash or performing collateral. Zero-lag cases resolve on the default date. The horizon includes the latest maturity, one extension and the servicing lag, so no defaulted balance is silently liquidated early at par.

Defaults use seed 90210 in examples. Default draws for all months and loans and one extension draw per loan are generated before any branching. Matching seeds share shocks across the supplied scenarios, which have identical horizons. Different seeds change loan defaults. There is no common-factor copula, stochastic severity, interest on workout balances or stochastic property process.

## CMBS structure and observed scenarios

Classes A/B/C/D/E/F have synthetic labels AAA/AA/A/BBB/BB/B-piece, shares 70%/10%/7%/5%/3%/5%, and fixed coupons 3.5%/4%/4.5%/5%/6%/8%. Initial subordination below those classes is 30%/20%/13%/8%/5%/0%. All collateral is financed by these classes; the B-piece is a junior debt class, not an unfunded residual. Servicing is 0.5% annually on opening performing par, including loans that default that month. There is no separate special-servicer fee.

After coupons, ordinary principal pays sequentially. There is no OC turbo or reinvestment. At resolution, realized principal loss writes down surviving debt bottom-up after that month's cash waterfall. Note coupons for the resolution month still use opening note balances. Prior unpaid interest remains separately owed after a write-down. The illustrative conduit requires full debt funding and does not accept pro rata, reserve or OC enhancement terms.

| CMBS scenario | Refinance rate | NOI multiplier | Value multiplier | Annual term defaults | Loss severity |
| :-: | :-: | :-: | :-: | :-: | :-: |
| Base | 5.5% | 1.00 | 1.00 | 0.3% | 35% |
| Combined stress | 8.5% | 0.85 | 0.80 | 1.2% | 45% |
| Severe | 10.0% | 0.70 | 0.65 | 3.0% | 60% |
| Refinance rates up only | 8.5% | 1.00 | 1.00 | 0.3% | 35% |

The rate-only scenario isolates the refinance rate change while keeping loan coupons and other assumptions fixed. It is exported separately from the combined comparison stress. The scenarios are synthetic stresses, not market estimates or agency tests.

The base realizes $4,261,766.37 loss, or 2.130883% of initial pool par, entirely in class F. F loses 42.617664% of initial principal and carries $323,357.78 unpaid interest. Class D has no principal loss and paid-principal WAL of 9.652708 years. Four loans extend. Combined stress produces $77,710,779.99 loss, or 38.855390% of pool par, 42 extensions and $1,852,639.63 unpaid note interest. Losses exhaust F, E, D, C and B and impair A by 12.650557% of its initial principal. Severe pool loss is 57.970014%, with A losing 39.957163% and every junior class losing all principal. The rate-only scenario has 33 extensions and 19.613815% pool loss; class D receives no principal and loses 100%. Per-loan default reasons, refinance tests, extension dates and resolution amounts appear in the scenario event CSVs.

## Common comparison and monthly validation

`comparison_table` selects the uniquely BBB-labeled class from each unchanged base/stress structure. Subordination is one minus initial debt through that class divided by initial collateral. It includes CLO residual collateral and ABS OC, excludes ABS reserve, and includes junior CMBS classes. All losses divide by original class principal. CLO losses use its terminal unpaid principal convention; ABS and CMBS use explicit write-downs. With all collateral resolved at the horizon, these are comparable principal deficits, though recognition timing differs.

The run compares CLO D at 14% subordination, ABS D at 8%, and CMBS D at 8%. Their base paid-principal WALs are 7.039284, 1.952092 and 9.652708 years. Base principal loss is zero for all three. Stress principal loss is 100%, 86.541803% and 100%, respectively. ABS stress paid-principal WAL is 0.293003 years; CLO and CMBS stress WALs are undefined because those classes receive no principal. CLO stress fixes 10% annual defaults and 30% recovery, ABS uses its stress curve, and CMBS uses combined stress. Scenario names do not imply equivalent shock severity, expected loss or credit ratings.

The project has 169 unittest tests, retaining every original test. Monthly checks cover level-pay closed forms, zero-rate payments, count-based prepayments, default survival and severity, cash and collateral conservation, principal plus write-down conservation, reserve support and replenishment, OC turbo, trigger switching and latch behavior, bottom-up losses, seeded mortgage generation and defaults, refinance DSCR and LTV failures, rate-only stress, maturity rounding, one-time extension and delayed or immediate resolution. Stress vectors and first-loss indicators receive separate monotonicity checks. Maximum monthly example cash error is $9.313226e-10; maximum collateral error is $7.078052e-08. All examples reproduce their committed outputs without runtime network access.

## Monthly model stylization

All ABS and CMBS pools are synthetic. Defaults, severities, fees, coupons, extension terms, test thresholds and value/NOI shocks are assumed. There are no rating agency criteria. Neither model is a trustee waterfall, a legal deal reconstruction or a forecast.

ABS is a homogeneous level-pay auto pool, not a revolving credit-card pool. It omits delinquency states, servicing advances, seasoning heterogeneity, borrower correlation, recovery delays, repossession expenses, optional calls and legal note reinstatement. Reserve is funded externally at closing; its funding is disclosed but residual IRR is not computed. Monthly permanent deficit write-downs may differ materially from transaction accounting.

CMBS omits rent rolls, leases, vacancies, capitalization-rate valuation, property-specific hazard, sponsor support, appraisal reductions, servicing advances, workout negotiation, recovery distributions, intercreditor rights, prepayment penalties, defeasance and full legal interest-shortfall allocation rules. All classes share ordinary coupon seniority and carry uncompounded arrears; losses apply to principal only. Rate stress affects hypothetical refinance debt service, not existing fixed-rate coupons. A pending loan earns no interest and pays no additional workout fee. These simplifications can materially alter loss amounts, recognition timing and WAL.
