"""Reproduce monthly ABS, CMBS and cross-sector synthetic result tables."""

from dataclasses import asdict, replace
from pathlib import Path
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clo_engine import (
    AutoPool, abs_scenarios, auto_structure, run_abs, abs_break_even_cnl,
    synthetic_mortgages, cmbs_scenarios, conduit_structure, run_cmbs,
    synthetic_portfolio, portfolio_metrics, illustrative_structure, run_deal,
    comparison_table,
)
from run_analysis import markdown_table


def main() -> None:
    output = ROOT / "examples" / "output"
    output.mkdir(parents=True, exist_ok=True)
    pool = AutoPool()
    abs_structure = auto_structure(pool.par)
    abs_inputs = abs_scenarios(pool.months)
    abs_results = [run_abs(pool, abs_structure, s) for s in abs_inputs]
    boundaries = pd.concat([
        abs_break_even_cnl(pool, abs_structure, scenario).assign(scenario=scenario.name)
        for scenario in abs_inputs], ignore_index=True)
    mortgages = synthetic_mortgages()
    cmbs_structure = conduit_structure(sum(x.par for x in mortgages))
    cmbs_inputs = (*cmbs_scenarios(), replace(cmbs_scenarios()[0], name="refinance_rates_up",
                                             refinance_rate=0.085))
    cmbs_results = [run_cmbs(mortgages, cmbs_structure, s, seed=90210) for s in cmbs_inputs]
    loans = synthetic_portfolio()
    metrics = portfolio_metrics(loans)
    clo_structure = illustrative_structure(metrics["par"], metrics["purchase_cost"])
    clo_base = run_deal(loans, clo_structure)
    clo_stress = run_deal(loans, clo_structure, annual_default_rate=.10, recovery=.30)
    comparison = comparison_table(
        {"CLO": (clo_base, clo_stress), "ABS": tuple(abs_results[:2]), "CMBS": tuple(cmbs_results[:2])},
        {"CLO": metrics["par"], "ABS": pool.par, "CMBS": cmbs_structure.collateral_par})
    frames = {"structured_comparison": comparison, "abs_break_even_cnl": boundaries,
              "synthetic_mortgages": pd.DataFrame([asdict(x) for x in mortgages])}
    summaries = []
    for sector, inputs, results in [("abs", abs_inputs, abs_results), ("cmbs", cmbs_inputs, cmbs_results)]:
        analytics = []
        for scenario, result in zip(inputs, results):
            table = result.tranche_analytics()
            table.insert(0, "scenario", scenario.name)
            analytics.append(table)
            frames[f"{sector}_{scenario.name}_ledger"] = result.ledger
            if sector == "cmbs":
                frames[f"{sector}_{scenario.name}_events"] = result.events
            summaries.append(dict(
                sector=sector.upper(), scenario=scenario.name,
                cumulative_net_loss=float(result.ledger.credit_loss.sum() / result.structure.collateral_par),
                note_principal_loss=float(result.losses.sum()),
                unpaid_note_interest=float(result.unpaid_interest.sum()),
                max_cash_error=float(result.ledger.reconciliation_error.abs().max()),
                max_collateral_error=float(result.ledger.collateral_reconciliation.abs().max()),
                first_trigger_month=int(result.ledger.loc[result.ledger.trigger_breach, "month"].iloc[0])
                if sector == "abs" and result.ledger.trigger_breach.any() else None,
                extensions=int((result.events.event == "extension").sum())
                if sector == "cmbs" and not result.events.empty else 0,
            ))
        frames[f"{sector}_tranches"] = pd.concat(analytics, ignore_index=True)
    summary = pd.DataFrame(summaries)
    frames["structured_summary"] = summary
    for name, frame in frames.items():
        frame.to_csv(output / f"{name}.csv", index=False, float_format="%.12g")
    parameters = dict(
        auto_pool=asdict(pool), abs_structure=asdict(abs_structure),
        abs_scenarios=[asdict(x) for x in abs_inputs],
        cmbs_structure=asdict(cmbs_structure), cmbs_scenarios=[asdict(x) for x in cmbs_inputs],
        mortgage_pool_seed=2026, cmbs_path_seed=90210, mortgage_count=len(mortgages),
        clo_comparison_annual_default_rate=.10, clo_comparison_recovery=.30,
    )
    (output / "structured_parameters.json").write_text(json.dumps(parameters, indent=2) + "\n", encoding="utf-8")
    sections = ["# Synthetic structured credit results\n",
                "Synthetic pools, simplified servicing and no rating agency criteria.\n",
                "## BBB-like class comparison\n", markdown_table(comparison),
                "Scenario severity is sector-specific; these labels do not equate credit risk.\n",
                "## Scenario accounting\n", markdown_table(summary),
                "## ABS tranche analytics\n", markdown_table(frames["abs_tranches"]),
                "## ABS first-loss CNL boundaries\n", markdown_table(boundaries),
                "Each boundary scales its scenario seasoning curve at fixed severity and absolute speed.\n",
                "## CMBS tranche analytics\n", markdown_table(frames["cmbs_tranches"])]
    (output / "structured_results.md").write_text("\n".join(sections), encoding="utf-8")
    print(comparison.to_string(index=False))
    print(summary.to_string(index=False))
    print(boundaries.to_string(index=False))


if __name__ == "__main__":
    main()
