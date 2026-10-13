"""Reproduce synthetic tables and the README results without network access."""

from dataclasses import asdict
from pathlib import Path
import json
import math
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clo_engine import (
    break_even_default_rate, concentration_tests, discount_margin,
    illustrative_structure, monte_carlo, portfolio_metrics, run_deal,
    sofr_curve, stress_table, synthetic_portfolio,
)
from clo_engine.loans import portfolio_frame
from clo_engine.loans import DEFAULT_PROBABILITIES, RATING_FACTORS


def markdown_table(frame: pd.DataFrame, decimals: int = 6) -> str:
    """Render portable Markdown without the optional tabulate package."""
    def format_value(value: object) -> str:
        if isinstance(value, (float, np.floating)):
            if 0 < abs(value) < 10 ** (-decimals):
                return f"{value:.{decimals}e}"
            return f"{value:.{decimals}f}" if math.isfinite(value) else str(value)
        return str(value).replace("|", "/")
    columns = [str(x) for x in frame.columns]
    lines = ["| " + " | ".join(columns) + " |",
             "| " + " | ".join(":-:" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(format_value(x) for x in row) + " |"
                 for row in frame.itertuples(index=False, name=None))
    return "\n".join(lines) + "\n"


def main() -> None:
    output = ROOT / "examples" / "output"
    output.mkdir(parents=True, exist_ok=True)
    loans = synthetic_portfolio()
    metrics = portfolio_metrics(loans)
    structure = illustrative_structure(metrics["par"], metrics["purchase_cost"])
    base = run_deal(loans, structure)
    analytics = base.tranche_analytics()
    analytics["discount_margin_from_par"] = [
        discount_margin(base.interest[:, i] + base.principal[:, i], base.curve, tranche.notional)
        for i, tranche in enumerate(structure.tranches)
    ]
    break_even = pd.DataFrame([
        {"class": tranche.name, "rating_label": tranche.rating, "recovery": 0.40,
         "break_even_annual_cdr": break_even_default_rate(loans, structure, tranche.name)}
        for tranche in structure.tranches
    ])
    simulations = [monte_carlo(loans, structure, paths=200, scenario=scenario)
                   for scenario in ("flat", "up", "down")]
    severe = monte_carlo(loans, structure, paths=200, correlation=0.35,
                        default_multiplier=3, recovery=0.40)
    for frame in (severe.paths, severe.tranches, severe.equity):
        frame["scenario"] = "flat_severe"
    simulations.append(severe)
    frames = {
        "synthetic_loans": portfolio_frame(loans),
        "synthetic_sofr_curves": pd.DataFrame({key: sofr_curve(structure.periods, key)
                                               for key in ("flat", "up", "down")}),
        "portfolio_metrics": pd.DataFrame([metrics]),
        "concentration_tests": concentration_tests(loans),
        "structure": pd.DataFrame([asdict(x) for x in structure.tranches]),
        "base_ledger": base.ledger,
        "base_tranches": analytics,
        "stress": stress_table(loans, structure),
        "break_even": break_even,
        "monte_carlo_paths": pd.concat([x.paths for x in simulations], ignore_index=True),
        "monte_carlo_tranches": pd.concat([x.tranches for x in simulations], ignore_index=True),
        "monte_carlo_equity": pd.concat([x.equity for x in simulations], ignore_index=True),
    }
    for name, frame in frames.items():
        frame.to_csv(output / f"{name}.csv", index=False, float_format="%.10g")
    parameters = {"data_type": "synthetic", "structure": asdict(structure),
                  "default_probabilities_stylized_unverified": DEFAULT_PROBABILITIES,
                  "rating_factors_verified": RATING_FACTORS,
                  "baseline_recovery_concentration": 20.0,
                  "annual_prepayment": 0.10, "baseline_latent_correlation": 0.20}
    (output / "run_parameters.json").write_text(
        json.dumps(parameters, indent=2, default=str) + "\n", encoding="utf-8")
    environment = {"python": sys.version, "numpy": np.__version__, "pandas": pd.__version__}
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    summary = {
        "synthetic_loan_count": len(loans), "synthetic_industry_count": len({x.industry for x in loans}),
        "payment_periods": structure.periods, "reinvestment_years": structure.reinvestment_years,
        "equity_outlay": structure.equity, "base_equity_irr": base.equity_irr,
        "equity_share_of_funding": structure.equity / metrics["purchase_cost"],
        "equity_share_of_collateral_par": structure.equity / metrics["par"],
        "base_equity_multiple": base.equity_multiple,
        "base_oc_breach": bool(base.ledger.filter(regex="_oc_breach$").to_numpy().any()),
        "base_ic_breach": bool(base.ledger.filter(regex="_ic_breach$").to_numpy().any()),
        "base_interest_diversion_breach": bool(base.ledger.interest_diversion_breach.any()),
        "max_cash_reconciliation_error": float(base.ledger.reconciliation_error.abs().max()),
        "max_collateral_reconciliation_error": float(base.ledger.collateral_reconciliation.abs().max()),
        "base_principal_loss": float(base.ending_balances.sum()),
        "maximum_stress_cash_error": float(frames["stress"].cash_reconciliation_max.max()),
        "portfolio_seed": 2026, "monte_carlo_seed": 90210,
        "paths_per_scenario": 200, **metrics,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    sections = ["# Synthetic CLO results\n", "All inputs and outputs describe an illustrative synthetic deal.\n",
                "## Base scenario\n", markdown_table(pd.DataFrame(
                    [{"metric": key, "value": value} for key, value in summary.items()])),
                "## Portfolio concentration\n", markdown_table(frames["concentration_tests"]),
                "## Base tranche valuation\n", markdown_table(analytics),
                "## Monte Carlo equity\n", markdown_table(frames["monte_carlo_equity"]),
                "## Monte Carlo tranches\n", markdown_table(frames["monte_carlo_tranches"]),
                "## Deterministic stress\n", markdown_table(frames["stress"]),
                "## First principal loss boundary\n", markdown_table(break_even),
                "Zero observed losses do not establish zero population risk.\n"]
    (output / "results.md").write_text("\n".join(sections), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(frames["monte_carlo_equity"].to_string(index=False))
    print(break_even.to_string(index=False))


if __name__ == "__main__":
    main()
