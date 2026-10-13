# Synthetic CLO results

All inputs and outputs describe an illustrative synthetic deal.

## Base scenario

| metric | value |
| :-: | :-: |
| synthetic_loan_count | 150 |
| synthetic_industry_count | 25 |
| payment_periods | 40 |
| reinvestment_years | 4.000000 |
| equity_outlay | 47540494.456332 |
| base_equity_irr | 0.139500 |
| equity_share_of_funding | 0.095551 |
| equity_share_of_collateral_par | 0.095081 |
| base_equity_multiple | 2.049228 |
| base_oc_breach | False |
| base_ic_breach | False |
| base_interest_diversion_breach | False |
| max_cash_reconciliation_error | 7.450581e-09 |
| max_collateral_reconciliation_error | 5.960464e-08 |
| base_principal_loss | 0.000000 |
| maximum_stress_cash_error | 7.450581e-09 |
| portfolio_seed | 2026 |
| monte_carlo_seed | 90210 |
| paths_per_scenario | 200 |
| par | 500000000.000000 |
| purchase_cost | 497540494.456332 |
| par_build | 2459505.543668 |
| warf | 3008.000000 |
| warf_unrounded | 3007.576366 |
| was | 0.034454 |
| warr | 0.685367 |
| wal | 5.545246 |
| diversity_score | 67.399900 |
| industry_effective_count | 24.421985 |
| ccc_share | 0.075380 |
| ccc_haircut | 10325.505925 |
| oc_collateral | 499989674.494075 |

## Portfolio concentration

| metric | actual | limit | passes |
| :-: | :-: | :-: | :-: |
| largest_obligor | 0.018311 | 0.020000 | True |
| largest_industry | 0.053449 | 0.100000 | True |
| second_lien | 0.048776 | 0.100000 | True |
| cov_lite | 0.819909 | 0.900000 | True |

## Base tranche valuation

| class | rating_label | initial_notional | principal_paid | principal_loss | principal_loss_fraction | unpaid_interest | paid_principal_life | dcf_value | dcf_price_percent | discount_margin_from_par |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| A | AAA | 315000000.000000 | 315000000.000000 | 0.000000 | 0.000000 | 0.000000 | 5.226234 | 315000000.000000 | 100.000000 | 0.015000 |
| B | AA | 55000000.000000 | 55000000.000000 | 0.000000 | 0.000000 | 0.000000 | 6.466968 | 55000000.000000 | 100.000000 | 0.021000 |
| C | A | 35000000.000000 | 35000000.000000 | 0.000000 | 0.000000 | 0.000000 | 6.829906 | 35000000.000000 | 100.000000 | 0.028000 |
| D | BBB | 25000000.000000 | 25000000.000000 | 0.000000 | 0.000000 | 0.000000 | 7.039284 | 25000000.000000 | 100.000000 | 0.040000 |
| E | BB | 20000000.000000 | 20000000.000000 | 0.000000 | 0.000000 | 0.000000 | 7.467340 | 20000000.000000 | 100.000000 | 0.065000 |

## Monte Carlo equity

| scenario | paths | seed | correlation | default_multiplier | recovery_mode | recovery_override | irr_mean | irr_p05 | irr_median | irr_p95 | negative_irr_probability | multiple_mean | event_default_probability |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| flat | 200 | 90210 | 0.200000 | 1.000000 | beta | nan | 0.090309 | 0.055382 | 0.093533 | 0.117070 | 0.005000 | 1.600047 | 0.000000 |
| up | 200 | 90210 | 0.200000 | 1.000000 | beta | nan | 0.097957 | 0.062791 | 0.101219 | 0.125115 | 0.005000 | 1.657278 | 0.000000 |
| down | 200 | 90210 | 0.200000 | 1.000000 | beta | nan | 0.078564 | 0.044049 | 0.081725 | 0.104712 | 0.010000 | 1.514445 | 0.000000 |
| flat_severe | 200 | 90210 | 0.350000 | 3.000000 | fixed | 0.400000 | -0.493081 | -0.999900 | -0.482254 | -0.015014 | 0.955000 | 0.365437 | 0.040000 |

## Monte Carlo tranches

| scenario | class | rating_label | loss_probability | loss_probability_standard_error | expected_principal_loss | expected_unpaid_interest | oc_breach_probability | ic_breach_probability | expected_paid_principal_life | paths_without_principal_payment |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| flat | A | AAA | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.272468 | 0 |
| flat | B | AA | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.582119 | 0 |
| flat | C | A | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.005000 | 0.000000 | 6.948477 | 0 |
| flat | D | BBB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.015000 | 0.000000 | 7.325215 | 0 |
| flat | E | BB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.005000 | 0.000000 | 7.869220 | 0 |
| up | A | AAA | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.272464 | 0 |
| up | B | AA | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.582119 | 0 |
| up | C | A | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.005000 | 0.000000 | 6.948477 | 0 |
| up | D | BBB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.015000 | 0.000000 | 7.325215 | 0 |
| up | E | BB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.005000 | 0.000000 | 7.869220 | 0 |
| down | A | AAA | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 5.272474 | 0 |
| down | B | AA | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 6.582119 | 0 |
| down | C | A | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.005000 | 0.000000 | 6.948477 | 0 |
| down | D | BBB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.015000 | 0.000000 | 7.325215 | 0 |
| down | E | BB | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.005000 | 0.015000 | 7.869220 | 0 |
| flat_severe | A | AAA | 0.005000 | 0.004987 | 0.000118 | 0.000006 | 0.660000 | 0.020000 | 5.204674 | 0 |
| flat_severe | B | AA | 0.015000 | 0.008595 | 0.007945 | 0.000445 | 0.660000 | 0.020000 | 6.813500 | 1 |
| flat_severe | C | A | 0.085000 | 0.019720 | 0.036839 | 0.022556 | 0.890000 | 0.090000 | 7.435787 | 3 |
| flat_severe | D | BBB | 0.210000 | 0.028801 | 0.130794 | 0.101524 | 0.950000 | 0.280000 | 8.106979 | 17 |
| flat_severe | E | BB | 0.495000 | 0.035354 | 0.331863 | 0.324306 | 0.890000 | 0.890000 | 8.645488 | 42 |

## Deterministic stress

| annual_cdr | recovery | equity_irr | equity_multiple | cash_reconciliation_max | A_principal_loss | A_oc_breach | A_ic_breach | B_principal_loss | B_oc_breach | B_ic_breach | C_principal_loss | C_oc_breach | C_ic_breach | D_principal_loss | D_oc_breach | D_ic_breach | E_principal_loss | E_oc_breach | E_ic_breach |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 0.000000 | 0.300000 | 0.139500 | 2.049228 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False |
| 0.020000 | 0.300000 | -0.024159 | 0.896474 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | True | False | 0.000000 | False | True |
| 0.050000 | 0.300000 | -0.812183 | 0.190496 | 7.450581e-09 | 0.000000 | True | False | 0.000000 | True | False | 0.000000 | True | False | 0.000000 | True | False | 0.653876 | True | True |
| 0.100000 | 0.300000 | -0.985748 | 0.089552 | 7.450581e-09 | 0.000000 | True | True | 0.040183 | True | True | 1.000000 | True | True | 1.000000 | True | True | 1.000000 | True | True |
| 0.200000 | 0.300000 | -0.999999 | 0.027517 | 3.725290e-09 | 0.389360 | True | True | 1.000000 | True | True | 1.000000 | True | True | 1.000000 | True | True | 1.000000 | True | True |
| 0.000000 | 0.500000 | 0.139500 | 2.049228 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False |
| 0.020000 | 0.500000 | 0.039313 | 1.211027 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False |
| 0.050000 | 0.500000 | -0.622212 | 0.271298 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | True | False | 0.000000 | True | False | 0.000000 | True | True |
| 0.100000 | 0.500000 | -0.949054 | 0.119003 | 3.725290e-09 | 0.000000 | True | False | 0.000000 | True | False | 0.000000 | True | True | 0.883746 | True | True | 1.000000 | True | True |
| 0.200000 | 0.500000 | -0.999215 | 0.050935 | 3.725290e-09 | 0.117768 | True | True | 1.000000 | True | True | 1.000000 | True | True | 1.000000 | True | True | 1.000000 | True | True |
| 0.000000 | 0.700000 | 0.139500 | 2.049228 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False |
| 0.020000 | 0.700000 | 0.084596 | 1.537853 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False |
| 0.050000 | 0.700000 | -0.051718 | 0.787077 | 7.450581e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | True | False | 0.000000 | False | True |
| 0.100000 | 0.700000 | -0.752372 | 0.205967 | 3.725290e-09 | 0.000000 | False | False | 0.000000 | False | False | 0.000000 | True | False | 0.000000 | True | False | 0.340611 | True | True |
| 0.200000 | 0.700000 | -0.989014 | 0.075604 | 7.450581e-09 | 0.000000 | True | False | 0.000000 | True | False | 0.622394 | True | True | 1.000000 | True | True | 1.000000 | True | True |

## First principal loss boundary

| class | rating_label | recovery | break_even_annual_cdr |
| :-: | :-: | :-: | :-: |
| A | AAA | 0.400000 | 0.147462 |
| B | AA | 0.400000 | 0.114404 |
| C | A | 0.400000 | 0.086845 |
| D | BBB | 0.400000 | 0.065057 |
| E | BB | 0.400000 | 0.043598 |

Zero observed losses do not establish zero population risk.
