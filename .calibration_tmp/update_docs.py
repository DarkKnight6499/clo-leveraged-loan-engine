from pathlib import Path
import json
import pandas as pd
out = Path('examples/output')
s = json.loads((out/'summary.json').read_text())
p = json.loads((out/'run_parameters.json').read_text())
mc = pd.read_csv(out/'monte_carlo_equity.csv')
t = pd.read_csv(out/'monte_carlo_tranches.csv')
b = pd.read_csv(out/'break_even.csv')
readme = Path('README.md').read_text()
replacements = {
'**119 unittest tests pass.**': '**124 unittest tests pass.**',
'$477,135,268.53': f"${s['purchase_cost']:,.2f}",
'$22,864,731.47': f"${s['par_build']:,.2f}",
'$42,135,268.53': f"${s['equity_outlay']:,.2f}",
'4.603427%': f"{100*s['was']:.6f}%",
'63.780602%': f"{100*s['warr']:.6f}%",
'$77,441.29': f"${s['ccc_haircut']:,.2f}",
'33.634863%': f"{100*s['base_equity_irr']:.6f}%",
'3.579376x': f"{s['base_equity_multiple']:.6f}x",
'**$1.192093e-7**': f"**${s['max_collateral_reconciliation_error']:.6e}**",
'Discount purchase economics, par redemption and frictionless reinvestment contribute to the high synthetic base return.': 'No base OC, IC or interest diversion tests breach. Near-par purchases and reinvestment limit synthetic par build; par redemption and frictionless reinvestment still benefit equity.',
}
for old,new in replacements.items():
 assert old in readme, old
 readme=readme.replace(old,new)
start=readme.index('| Flat |')
end=readme.index('\n\nLower and upper tails',start)
labels={'flat':'Flat','up':'Rising','down':'Falling','flat_severe':'Severe'}
readme=readme[:start]+'\n'.join(f"| {labels[r.scenario]} | {100*r.irr_mean:.4f}% | {100*r.irr_p05:.4f}% | {100*r.irr_median:.4f}% | {100*r.irr_p95:.4f}% |" for r in mc.itertuples())+readme[end:]
start=readme.index('| A | AAA |')
end=readme.index('\n\nExpected loss',start)
readme=readme[:start]+'\n'.join(f"| {r._2} | {r.rating_label} | {100*r.loss_probability:.1f}% | {100*r.expected_principal_loss:.6f}% | {100*r.oc_breach_probability:.1f}% |" for r in t[t.scenario=='flat_severe'].itertuples())+readme[end:]
start=readme.index('The constant annual default boundaries')
end=readme.index('These are modeled',start)
bounds=', '.join(f"**{100*r.break_even_annual_cdr:.4f}%** for {r._1}" for r in b.itertuples())
readme=readme[:start]+f'The constant annual default boundaries at **40% recovery** are {bounds}. '+readme[end:]
flat=mc[mc.scenario=='flat'].iloc[0]
readme=readme.replace('The severe sample demonstrates the tranche protection hierarchy:',f"The flat sample has mean equity cash multiple **{flat.multiple_mean:.6f}x** and **{100*flat.negative_irr_probability:.1f}%** probability of negative equity IRR. The severe sample demonstrates the tranche protection hierarchy:")
intro=f'''## Illustrative calibration

Notes total $450,000,000, or 90% of collateral par. Equity funds the residual purchase cost: **${s['equity_outlay']:,.2f}**, **{100*s['equity_share_of_funding']:.6f}%** of total funded capital and **{100*s['equity_share_of_collateral_par']:.6f}%** of collateral par.

| Class | Share of collateral par | Spread over SOFR | OC trigger | IC trigger |
| :-: | :-: | :-: | :-: | :-: |
'''
for r in p['structure']['tranches']:
 intro+=f"| {r['name']} ({r['rating']}) | {100*r['notional']/s['par']:.0f}% | {r['spread']*10000:.0f} bp | {r['oc_trigger']*100:.0f}% | {r['ic_trigger']*100:.0f}% |\n"
intro+='''
Senior and subordinated management fees are 10 bp and 40 bp annually on opening collateral par. Administration expenses are $200,000 annually with a $250,000 cap. Initial B-rated loans cost 99% to 100.5% of par; Caa loans cost 94% to 98%. First-lien and second-lien recovery means are 70% and 40%. Reinvestment buys at 99.75% of par with a 360 bp spread, five-year maturity and B2 default risk. The four-year reinvestment period and ten-year horizon remain unchanged.

These inputs target illustrative return ranges, without empirical market calibration. The deterministic base remains a no-default cash flow case. Rating default assumptions and all other terms are detailed in [methodology](docs/methodology.md) and exported in [run parameters](examples/output/run_parameters.json).

'''
readme=readme.replace('## Validation and actual results\n',intro+'## Validation and actual results\n')
readme=readme.replace('Both example scripts complete successfully.', 'Five calibration checks additionally enforce equity funding and return ranges, a visible Monte Carlo left tail, senior protection, and base-versus-stress coverage behavior. Existing assertions and tolerances remain intact. Both example scripts complete successfully.')
readme=readme.replace('The [deterministic stress table]', 'At 10% annual defaults and 30% recovery, all classes breach both OC and IC tests and interest diversion is triggered. The [deterministic stress table]')
Path('README.md').write_text(readme,encoding='utf-8')
method=Path('docs/methodology.md').read_text()
section='''## Supplied calibration and observed results

The calibration changes only illustrative inputs. Coupon, default, recovery, valuation and waterfall formulas and timing conventions are unchanged. The terms are chosen to produce moderate synthetic equity returns, not fitted to observed deals or an agency model. The base case retains zero defaults, so its return is a no-credit-loss illustration; Monte Carlo supplies credit risk.

On $500,000,000 collateral par, note shares A/B/C/D/E are 63%/11%/7%/5%/4%, with SOFR spreads of 150/210/280/400/650 bp. OC triggers are 125%/125%/116%/110%/104%, and IC triggers are 120%/120%/110%/105%/100%. A and B share tests. The D-level reinvestment diversion trigger is 108%, with a 50% diversion fraction. Senior and subordinated management fees are 10 and 40 bp annually. Administration costs are $200,000 annually, capped at $250,000; assumed taxes are zero.

The seeded portfolio keeps its rating mix, loan amounts, maturities, floors and industry assignments. Loan spreads are 250 bp plus 40 bp per rating step from B1 through Caa3, a uniform 0 to 80 bp component, and an additional 100 bp for second liens. B-rated purchase prices are uniform from 99% to 100.5%; Caa prices are uniform from 94% to 98%. Recovery means are 70% for first liens and 40% for second liens, with independent beta concentration 20.

| Rating | Assumed annual default probability |
| :-: | :-: |
'''
for rating,prob in p['default_probabilities_stylized_unverified'].items():
 section+=f'| {rating} | {100*prob:g}% |\n'
section+='''
Reinvestment remains four years over a ten-year horizon. Replacement loans buy at 99.75% of par, earn SOFR plus 360 bp, use B2 default risk, mature five years after purchase, and amortize 1% of original par annually. Their benchmark floor remains 0.5%. Their recovery mean is initial portfolio WARR. Annual prepayment remains 10%. Near-par reinvestment reduces the mechanical par build that previously amplified equity returns. Recovery and default assumptions also change the amount of simulated credit loss.

'''
section+=f"The actual seed-2026 portfolio costs ${s['purchase_cost']:,.2f}; par build is ${s['par_build']:,.2f}. Equity outlay is ${s['equity_outlay']:,.2f}, or {100*s['equity_share_of_funding']:.6f}% of funded capital and {100*s['equity_share_of_collateral_par']:.6f}% of collateral par. WAS is {100*s['was']:.6f}%, and model WARR is {100*s['warr']:.6f}%.\n\n"
section+=f"The no-default base returns {100*s['base_equity_irr']:.6f}% equity IRR and {s['base_equity_multiple']:.6f}x cash multiple. It has no note principal loss and no OC, IC or interest diversion breach. With 200 flat-SOFR paths and seed 90210, mean equity IRR is {100*flat.irr_mean:.4f}%, the fifth percentile is {100*flat.irr_p05:.4f}%, and mean cash multiple is {flat.multiple_mean:.6f}x. Negative equity IRR occurs in {100*flat.negative_irr_probability:.1f}% of flat paths. No note principal loss is observed in that sample; credit losses reduce equity distributions first. Zero observed losses are not a population guarantee.\n\n"
section+='At 10% constant annual defaults and 30% fixed recovery, all classes breach OC and IC, and reinvestment interest diversion triggers. First-principal-loss annual default boundaries at 40% recovery are '+', '.join(f"{r._1}: {100*r.break_even_annual_cdr:.4f}%" for r in b.itertuples())+'. Their descending order confirms seniority protection in this illustration.\n\nFull scenario results, cash reconciliation errors and parameters are reproduced by the example scripts in [the output tables](../examples/output/results.md). [README](../README.md) reports the rising, falling and severe scenarios. All economics in this section are stylized/unverified assumptions or model outputs, not current market observations.\n\n'
method=method.replace('## Loan proceeds and purchase economics\n',section+'## Loan proceeds and purchase economics\n')
Path('docs/methodology.md').write_text(method,encoding='utf-8')
source=Path('docs/sources.md').read_text()
source+='\n## Calibration provenance\n\nThe supplied economic calibration is an illustrative choice of inputs, not verified market data. It changes tranche shares and spreads, the management fee split, initial collateral spreads and prices, rating default probabilities, first-lien recovery means, and replacement purchase prices and spreads. It does not change the verified definitions above or the model formulas. The 70% first-lien and 40% second-lien recovery means, rating probabilities, and all deal terms remain stylized/unverified. [Methodology](methodology.md#supplied-calibration-and-observed-results) records the assumptions and observed outputs; [run parameters](../examples/output/run_parameters.json) exports the configured terms. Return ranges used to select inputs are illustrative design targets, not externally verified performance expectations.\n'
Path('docs/sources.md').write_text(source,encoding='utf-8')
