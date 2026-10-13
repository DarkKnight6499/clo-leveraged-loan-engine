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

## Calibration provenance

The supplied economic calibration is an illustrative choice of inputs, not verified market data. It changes tranche shares and spreads, the management fee split, initial collateral spreads and prices, rating default probabilities, first-lien recovery means, and replacement purchase prices and spreads. It does not change the verified definitions above or the model formulas. The 70% first-lien and 40% second-lien recovery means, rating probabilities, and all deal terms remain stylized/unverified. [Methodology](methodology.md#supplied-calibration-and-observed-results) records the assumptions and observed outputs; [run parameters](../examples/output/run_parameters.json) exports the configured terms. Return ranges used to select inputs are illustrative design targets, not externally verified performance expectations.

## Auto ABS prepayment convention

[CarMax Auto Owner Trust 2024-4 prospectus, Maturity and Prepayment Considerations, pages 65 and 66](https://www.sec.gov/Archives/edgar/data/2037519/000119312524248421/d901858d424b5.htm) was opened and the relevant original text read. Page 65 defines absolute prepayment speed relative to the original receivable count, with equal size and amortization assumptions. Page 66 describes level payments that fully amortize the hypothetical pools. These definitions support the implemented count-based prepayment convention and level-pay pool mechanics. Fractional defaults, severity curves, the pro rata switch, all enhancement amounts and the permanent deficit write-down rule are this engine's own stylized assumptions, not imported transaction provisions.

## ABS and CMBS assumption provenance

The new module inputs and reported numbers are model assumptions and actual example outputs. They are not regulations, rating agency criteria or observed market facts. CMBS refinance thresholds, extension eligibility and probability, workout lags, synthetic property labels and fixed severities are explicitly assumed. No external source is claimed for a universal conduit rule or threshold. [Structured parameters](../examples/output/structured_parameters.json) contains all supplied scenario terms; [structured results](../examples/output/structured_results.md) and the event and ledger CSVs contain the run evidence. Property-specific economics and legal servicing provisions are not modeled.
