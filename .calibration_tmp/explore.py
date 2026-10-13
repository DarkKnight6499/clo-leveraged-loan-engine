import sys
from pathlib import Path
from dataclasses import replace
sys.path.insert(0, str(Path.cwd() / 'src'))
from clo_engine import *
from clo_engine.structure import Tranche
loans = synthetic_portfolio()
loans = [replace(x, price=(.99 + (x.price-.93)/.085*.015) if not x.rating.startswith('Caa') else (.94+(x.price-.55)/.30*.04), recovery=.35 if x.second_lien else .60, spread=.025+.004*list(['B1','B2','B3','Caa1','Caa2','Caa3']).index(x.rating)+(x.spread-.032-.006*list(['B1','B2','B3','Caa1','Caa2','Caa3']).index(x.rating)-.012*x.second_lien)/.012*.008+.010*x.second_lien) for x in loans]
metrics=portfolio_metrics(loans)
terms=[('A','AAA',.63,.015,1.25,1.20),('B','AA',.11,.021,1.25,1.20),('C','A',.07,.028,1.16,1.10),('D','BBB',.05,.04,1.10,1.05),('E','BB',.04,.065,1.04,1.00)]
s=illustrative_structure(metrics['par'],metrics['purchase_cost'])
s=replace(s,tranches=tuple(Tranche(n,r,f*metrics['par'],z,oc,ic) for n,r,f,z,oc,ic in terms),equity=metrics['purchase_cost']-.9*metrics['par'],senior_fee=.001,subordinated_fee=.004,reinvestment_price=.9975)
print('metrics',metrics)
for spread in [.028,.030,.032,.034,.036]:
    structure=replace(s,reinvestment_spread=spread)
    b=run_deal(loans,structure)
    mc=monte_carlo(loans,structure,paths=100)
    print(spread,b.equity_irr,b.equity_multiple,mc.equity[['irr_mean','irr_p05','irr_median','irr_p95']].to_dict('records'),b.ledger.filter(regex='breach').any().to_dict())
