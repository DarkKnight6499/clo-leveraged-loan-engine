# Primary source audit

The public documents below were opened and their relevant text read through the web tool. These references support selected definitions, not a claim that this engine reproduces any transaction. No regulatory capital or regulatory threshold is implemented.

## Rating factors

[Arbor Realty Commercial Real Estate Notes indenture, Article 1, Section 1.1, definition of Moody's Rating Factor](https://www.sec.gov/Archives/edgar/data/1253986/000110465917065845/a17-20585_1ex10d1.htm) verifies the implemented factors: B1 2220, B2 2720, B3 3490, Caa1 4770, Caa2 6500, Caa3 8070. The definition of Moody's Weighted Average Rating Factor also confirms par weighting and rounding up. This is a filed real estate transaction, used only to corroborate the numerical factor table, not loan recovery assumptions.

## Collateral quality definitions and diversity

[NewStar Commercial Loan Funding indenture, Section 1.1 and Schedule 4](https://www.sec.gov/Archives/edgar/data/1373561/000119312512507388/d455464dex41.htm) verifies par weighting for floating spread and average life. The Aggregate Funded Spread definition includes benchmark floor uplift. Applying that logic to SOFR is an explicit adaptation of the older benchmark provision. Schedule 4 verifies borrower aggregation, equivalent units capped at one, industry grouping, lower-row lookup, and summation of industry scores.

[Filed financing agreement, Schedule C](https://www.sec.gov/Archives/edgar/data/1812554/000119312524059517/d759694dex101.htm) independently corroborates the same numerical industry score table. Its industry classification differs from the older Moody's schedule. The implemented numerical table is therefore distinct from the synthetic industry labels. Above its final row, the implementation uses a stylized cap, not a verified extrapolation.

## CCC and payment priorities

[Carlyle Direct Lending CLO indenture, Section 1.1 and Section 11.1(a)](https://www.sec.gov/Archives/edgar/data/1702510/000170251024000079/indenture-clo2024x1.htm) verifies lowest-market-value selection for CCC Excess, the par-versus-market-value excess adjustment, cumulative senior debt in OC, shared A/B tests, C and D tests, and reinvestment interest diversion. Its actual contractual percentages are not imported into this project. The engine uses its own illustrative thresholds and a Caa proxy for CCC.

## Explicitly stylized/unverified

Annual default probabilities, lien recovery means, beta concentration, latent correlation, all deal spreads and trigger levels, fees and expense caps, concentration limits, synthetic prices, SOFR scenarios, reinvestment terms, and event-of-default flags are model assumptions. None is presented as agency calibration, current market data, a regulatory requirement, or a real deal term. WARR is the unrounded par weighted model recovery mean, not an agency recovery schedule. There are no unverified regulatory assertions.
