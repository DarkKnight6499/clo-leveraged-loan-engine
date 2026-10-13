"""Monte Carlo summaries and deterministic constant default stress searches."""

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from .engine import run_deal
from .loans import Loan, sofr_curve
from .structure import CLOStructure


@dataclass(frozen=True)
class MonteCarloResult:
    """Path observations and estimates, including sampling uncertainty."""
    paths: pd.DataFrame
    tranches: pd.DataFrame
    equity: pd.DataFrame


def monte_carlo(loans: list[Loan], structure: CLOStructure, paths: int = 200,
                seed: int = 90210, scenario: str = "flat", correlation: float = 0.20,
                default_multiplier: float = 1.0, recovery: float | None = None,
                prepayment: float = 0.10) -> MonteCarloResult:
    """Estimate physical scenario outcomes, not risk neutral prices or ratings."""
    if paths < 1:
        raise ValueError("Path count must be positive")
    seeds = np.random.SeedSequence(seed).spawn(paths)
    rows = []
    curve = sofr_curve(structure.periods, scenario)
    for index, child in enumerate(seeds):
        result = run_deal(loans, structure, curve, annual_default_rate=None,
                          rng=np.random.default_rng(child), correlation=correlation,
                          default_multiplier=default_multiplier, recovery=recovery,
                          prepayment=prepayment)
        analytics = result.tranche_analytics()
        row = {"path": index, "scenario": scenario, "equity_irr": result.equity_irr,
               "equity_multiple": result.equity_multiple,
               "event_default": bool(result.ledger.event_default.any()),
               "credit_loss": float(result.ledger.credit_loss.sum())}
        for slot, tranche in enumerate(structure.tranches):
            row[f"{tranche.name}_loss"] = result.ending_balances[slot] / tranche.notional
            row[f"{tranche.name}_unpaid_interest"] = result.unpaid_interest[slot] / tranche.notional
            row[f"{tranche.name}_oc_breach"] = bool(result.ledger[f"{tranche.name}_oc_breach"].any())
            row[f"{tranche.name}_ic_breach"] = bool(result.ledger[f"{tranche.name}_ic_breach"].any())
            row[f"{tranche.name}_life"] = analytics.iloc[slot].paid_principal_life
        rows.append(row)
    frame = pd.DataFrame(rows)
    summary = []
    for tranche in structure.tranches:
        losses = frame[f"{tranche.name}_loss"].to_numpy()
        probability = float(np.mean(losses > 1e-8))
        summary.append({
            "scenario": scenario, "class": tranche.name, "rating_label": tranche.rating,
            "loss_probability": probability,
            "loss_probability_standard_error": math.sqrt(probability * (1 - probability) / paths),
            "expected_principal_loss": float(losses.mean()),
            "expected_unpaid_interest": float(frame[f"{tranche.name}_unpaid_interest"].mean()),
            "oc_breach_probability": float(frame[f"{tranche.name}_oc_breach"].mean()),
            "ic_breach_probability": float(frame[f"{tranche.name}_ic_breach"].mean()),
            "expected_paid_principal_life": float(frame[f"{tranche.name}_life"].mean()),
            "paths_without_principal_payment": int(frame[f"{tranche.name}_life"].isna().sum()),
        })
    irrs = frame.equity_irr.to_numpy()
    equity = pd.DataFrame([{
        "scenario": scenario, "paths": paths, "seed": seed, "correlation": correlation,
        "default_multiplier": default_multiplier,
        "recovery_mode": "beta" if recovery is None else "fixed",
        "recovery_override": math.nan if recovery is None else recovery,
        "irr_mean": float(irrs.mean()), "irr_p05": float(np.quantile(irrs, 0.05)),
        "irr_median": float(np.median(irrs)), "irr_p95": float(np.quantile(irrs, 0.95)),
        "negative_irr_probability": float(np.mean(irrs < 0)),
        "multiple_mean": float(frame.equity_multiple.mean()),
        "event_default_probability": float(frame.event_default.mean()),
    }])
    return MonteCarloResult(frame, pd.DataFrame(summary), equity)


def break_even_default_rate(loans: list[Loan], structure: CLOStructure,
                            class_name: str, recovery: float = 0.40,
                            prepayment: float = 0.10, rate_tolerance: float = 1e-6,
                            loss_tolerance: float = 1e-8) -> float:
    """Bisect the first material principal loss boundary on the CDR interval."""
    names = [x.name for x in structure.tranches]
    if class_name not in names or not 0 <= recovery <= 1:
        raise ValueError("Unknown class or invalid recovery")
    if not math.isfinite(rate_tolerance) or not 0 < rate_tolerance < 1:
        raise ValueError("Invalid rate tolerance")
    if not math.isfinite(loss_tolerance) or not 0 < loss_tolerance < 1:
        raise ValueError("Invalid loss tolerance")
    slot = names.index(class_name)
    def impaired(rate: float) -> bool:
        result = run_deal(loans, structure, annual_default_rate=rate,
                          recovery=recovery, prepayment=prepayment)
        return bool(result.ending_balances[slot] / structure.tranches[slot].notional > loss_tolerance)
    if impaired(0.0):
        return 0.0
    if not impaired(1.0):
        return math.nan
    lower, upper = 0.0, 1.0
    while upper - lower > rate_tolerance:
        middle = (lower + upper) / 2
        if impaired(middle):
            upper = middle
        else:
            lower = middle
    return upper


def stress_table(loans: list[Loan], structure: CLOStructure,
                 default_rates: tuple[float, ...] = (0.0, 0.02, 0.05, 0.10, 0.20),
                 recoveries: tuple[float, ...] = (0.30, 0.50, 0.70)) -> pd.DataFrame:
    """Run deterministic fractional CDR and fixed recovery combinations."""
    rows = []
    for recovery in recoveries:
        for rate in default_rates:
            result = run_deal(loans, structure, annual_default_rate=rate, recovery=recovery)
            row = {"annual_cdr": rate, "recovery": recovery, "equity_irr": result.equity_irr,
                   "equity_multiple": result.equity_multiple,
                   "cash_reconciliation_max": float(result.ledger.reconciliation_error.abs().max())}
            for slot, tranche in enumerate(structure.tranches):
                row[f"{tranche.name}_principal_loss"] = result.ending_balances[slot] / tranche.notional
                row[f"{tranche.name}_oc_breach"] = bool(result.ledger[f"{tranche.name}_oc_breach"].any())
                row[f"{tranche.name}_ic_breach"] = bool(result.ledger[f"{tranche.name}_ic_breach"].any())
            rows.append(row)
    return pd.DataFrame(rows)
