"""Synthetic level-pay auto ABS with absolute prepayments and loss triggers."""

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from .structure import Tranche
from .structured import CreditStructure, CreditResult, level_payment, allocate_credit, allocation_row
from .waterfall import WaterfallState, allocate_losses


@dataclass(frozen=True)
class AutoPool:
    """Homogeneous new loans represented by fractional surviving loan counts."""
    par: float = 100_000_000
    annual_rate: float = 0.09
    months: int = 60
    loan_count: int = 10_000

    def __post_init__(self) -> None:
        level_payment(self.par, self.annual_rate, self.months)
        if self.par <= 0 or not isinstance(self.loan_count, int) or self.loan_count <= 0:
            raise ValueError("Pool par and loan count must be positive")


@dataclass(frozen=True)
class ABSScenario:
    """Annual conditional default curve and monthly absolute prepayment speed.

    Scalars or one value per month are accepted. Severity is loss/defaulted par.
    Default removes fractional loan counts before accrual, then surviving loans
    pay the original level payment. Prepayment removes original-count units.
    """
    name: str = "base"
    annual_default_curve: float | tuple[float, ...] = 0.025
    severity_curve: float | tuple[float, ...] = 0.50
    abs_speed: float | tuple[float, ...] = 0.01


def abs_scenarios(months: int = 60) -> tuple[ABSScenario, ...]:
    """Seasoning curves are illustrative inputs, not empirical calibrations."""
    if not isinstance(months, int) or months <= 0:
        raise ValueError("Months must be positive")
    shape = np.interp(np.arange(1, months + 1) / months,
                      [0, 0.25, 0.5, 1], [0.5, 1.5, 1.0, 0.4])
    return tuple(ABSScenario(name, tuple(rate * shape), severity, speed)
                 for name, rate, severity, speed in
                 [("base", 0.025, 0.50, 0.01), ("stress", 0.15, 0.65, 0.005),
                  ("severe", 0.35, 0.80, 0.002)])


def auto_structure(par: float = 100_000_000, pro_rata: bool = True) -> CreditStructure:
    terms = [("A", "AAA", 0.70, 0.040), ("B", "AA", 0.10, 0.045),
             ("C", "A", 0.08, 0.050), ("D", "BBB", 0.04, 0.060),
             ("E", "BB", 0.02, 0.075)]
    return CreditStructure(tuple(Tranche(n, r, s * par, c, 1, 1) for n, r, s, c in terms),
                           par, servicing_fee=0.01, reserve_fraction=0.01, oc_target=0.08,
                           oc_floor=0.01, loss_trigger=0.04, pro_rata=pro_rata)


def _curve(value: float | tuple[float, ...], months: int, label: str) -> np.ndarray:
    curve = np.asarray(value, dtype=float)
    if curve.ndim == 0:
        curve = np.full(months, float(curve))
    if curve.shape != (months,) or not np.isfinite(curve).all() or ((curve < 0) | (curve > 1)).any():
        raise ValueError(f"{label} must contain one probability per month or a scalar in [0, 1]")
    return curve


def auto_schedule(pool: AutoPool, scenario: ABSScenario = ABSScenario()) -> pd.DataFrame:
    """Amortize per-loan balances; ABS speed is not CPR or a par fraction."""
    defaults = _curve(scenario.annual_default_curve, pool.months, "Default curve")
    severities = _curve(scenario.severity_curve, pool.months, "Severity curve")
    speeds = _curve(scenario.abs_speed, pool.months, "ABS speed")
    count = float(pool.loan_count)
    unit_balance = pool.par / pool.loan_count
    payment = level_payment(unit_balance, pool.annual_rate, pool.months)
    rows = []
    for index in range(pool.months):
        opening = count * unit_balance
        default_count = count * (1 - (1 - defaults[index]) ** (1 / 12))
        defaulted = default_count * unit_balance
        count -= default_count
        interest = count * unit_balance * pool.annual_rate / 12
        scheduled_unit = min(unit_balance, max(0, payment - unit_balance * pool.annual_rate / 12))
        if index == pool.months - 1:
            scheduled_unit = unit_balance
        scheduled = count * scheduled_unit
        unit_balance -= scheduled_unit
        prepaid_count = min(count, speeds[index] * pool.loan_count) if unit_balance > 0 else 0.0
        prepaid = prepaid_count * unit_balance
        count -= prepaid_count
        recovery = defaulted * (1 - severities[index])
        closing = count * unit_balance
        rows.append(dict(month=index + 1, time=(index + 1) / 12, opening_par=opening,
                         surviving_count=count, default_count=default_count, prepaid_count=prepaid_count,
                         defaulted_par=defaulted, recovery=recovery, credit_loss=defaulted - recovery,
                         amortization=scheduled, prepayment=prepaid, collateral_interest=interest,
                         collateral_principal=scheduled + prepaid + recovery, closing_par=closing,
                         collateral_reconciliation=opening - defaulted - scheduled - prepaid - closing))
    return pd.DataFrame(rows)


def run_abs(pool: AutoPool = AutoPool(), structure: CreditStructure | None = None,
            scenario: ABSScenario = ABSScenario()) -> CreditResult:
    structure = auto_structure(pool.par) if structure is None else structure
    if not math.isclose(structure.collateral_par, pool.par, rel_tol=1e-12):
        raise ValueError("Structure collateral must match pool par")
    schedule = auto_schedule(pool, scenario)
    state = WaterfallState.initial(structure)
    reserve = structure.reserve_fraction * pool.par
    fee_arrears = cumulative_loss = 0.0
    triggered = False
    rows, interest, principal, losses = [], [], [], []
    for index, cash in enumerate(schedule.to_dict("records")):
        cumulative_loss += cash["credit_loss"]
        triggered = triggered or cumulative_loss / pool.par >= structure.loss_trigger
        sequential = not structure.pro_rata or triggered
        allocation = allocate_credit(structure, state, cash["collateral_interest"],
                                     cash["collateral_principal"], cash["opening_par"],
                                     cash["closing_par"], reserve, sequential, turbo_all=triggered,
                                     final=index == pool.months - 1, fee_arrears=fee_arrears)
        reserve, fee_arrears = allocation.reserve, allocation.fee_arrears
        # OC absorbs losses first; reserve and retained excess spread support assets.
        deficit = max(0, float(state.balances.sum()) - cash["closing_par"] - reserve)
        written = allocate_losses(state.balances, deficit)
        row = dict(cash, cumulative_net_loss=cumulative_loss / pool.par,
                   trigger_breach=triggered, principal_mode="sequential" if sequential else "pro_rata",
                   **allocation_row(allocation, state, structure, written))
        rows.append(row)
        interest.append(allocation.interest)
        principal.append(allocation.principal)
        losses.append(written)
    return CreditResult(pd.DataFrame(rows), np.array(interest), np.array(principal), np.array(losses),
                        state.balances.copy(), state.interest_arrears.copy(), structure, pd.DataFrame())


def abs_break_even_cnl(pool: AutoPool, structure: CreditStructure,
                       template: ABSScenario | None = None) -> pd.DataFrame:
    """First-loss CNL along a fixed default shape, severity and speed family.

    Scale the annual default curve up to one at every date. Return the impaired
    side of bisection. Boundaries depend on loss timing, not only aggregate CNL.
    NaN means no loss in the searched family, including its all-default endpoint.
    """
    template = ABSScenario(annual_default_curve=0.025) if template is None else template
    shape = _curve(template.annual_default_curve, pool.months, "Default curve")
    if (shape <= 0).any():
        raise ValueError("Boundary search needs a strictly positive default shape")
    upper = 1 / float(shape.min())
    tolerance = pool.par * 1e-10

    def evaluate(scale: float) -> CreditResult:
        return run_abs(pool, structure, ABSScenario("boundary", tuple(np.minimum(1, shape * scale)),
                                                   template.severity_curve, template.abs_speed))

    endpoint = evaluate(upper)
    rows = []
    for index, tranche in enumerate(structure.tranches):
        low, high = 0.0, upper
        reachable = endpoint.losses[:, index].sum() > tolerance
        if reachable:
            for _ in range(40):
                middle = (low + high) / 2
                result = evaluate(middle)
                if result.losses[:, index].sum() > tolerance:
                    high = middle
                else:
                    low = middle
            boundary = evaluate(high)
            cnl = float(boundary.ledger.cumulative_net_loss.iloc[-1])
        else:
            cnl = math.nan
        rows.append({"class": tranche.name, "rating_label": tranche.rating,
                     "break_even_cumulative_net_loss": cnl,
                     "default_curve_multiplier": high if reachable else math.nan,
                     "reachable": reachable, "loss_tolerance": tolerance})
    return pd.DataFrame(rows)
