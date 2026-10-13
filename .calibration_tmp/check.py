import sys
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0, str(Path.cwd()/'src'))
from clo_engine import *
loans=synthetic_portfolio(count=30,total_par=10_000_000)
s=replace(illustrative_structure(10_000_000,sum(x.purchase_cost for x in loans)),admin_expense=4000,admin_cap=5000,reinvestment_years=0)
first=replace(loans[0],par=5_000_000,rating='Caa3',borrower='same')
second=replace(first,spread=.08)
for seed in range(10):
 r=run_deal([first,second],s,prepayment=0,annual_default_rate=None,rng=np.random.default_rng(seed))
 print(seed,int((r.ledger.defaulted_par>0).sum()))
loans=synthetic_portfolio();m=portfolio_metrics(loans);s=illustrative_structure(m['par'],m['purchase_cost'])
for rate,recovery in [(.02,.70),(.10,.30),(.20,.30)]:
 r=run_deal(loans,s,annual_default_rate=rate,recovery=recovery)
 print(rate,recovery,r.equity_irr,r.ending_balances,r.ledger.filter(regex='breach').any().to_dict())
