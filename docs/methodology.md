# Methodology and model boundaries

## Scope and units

The package models fully funded synthetic floating rate loans and an illustrative cash CLO. Monetary amounts are currency units, rates and prices are decimal fractions, time is years, and payments occur quarterly. AAA through BB are synthetic labels for payment priority, not assigned ratings. There is no network access at runtime. Public definition checks are recorded in [sources.md](sources.md).

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

## Omitted features

No trustee-level day count nuances, loan-level legal modeling, manager trading, price evolution, agency rating assignment, recovery workouts, maturity extensions, credit facilities, warehouse or ramp-up financing, unfunded revolvers, hedges, FX, fixed-rate assets, refinancing, resets, optional calls, investor taxes, incentive fees, transaction costs, liquidity premiums, legal discount-obligation OC rules, rating migration or real data calibration is included. No optimizer, external scientific library, chart renderer or spreadsheet deliverable is needed. The engine is a reproducible synthetic research model with explicit assumptions.
