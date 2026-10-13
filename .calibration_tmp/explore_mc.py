exec(open('.calibration_tmp/explore.py').read().split("print('metrics'")[0])
from clo_engine.loans import DEFAULT_PROBABILITIES
for recovery in [.65,.70]:
    pool=[replace(x,recovery=.40 if x.second_lien else recovery) for x in loans]
    for probs in [(.004,.008,.015,.035,.07,.12),(.005,.01,.02,.05,.10,.18),(.0075,.0125,.025,.06,.12,.20)]:
        DEFAULT_PROBABILITIES.update(zip(DEFAULT_PROBABILITIES,probs))
        structure=replace(s,reinvestment_spread=.036)
        mc=monte_carlo(pool,structure,paths=200)
        print(recovery,probs,mc.equity[['irr_mean','irr_p05','irr_median','irr_p95','negative_irr_probability']].to_dict('records'),mc.tranches[['class','loss_probability','oc_breach_probability','ic_breach_probability']].to_dict('records'))
