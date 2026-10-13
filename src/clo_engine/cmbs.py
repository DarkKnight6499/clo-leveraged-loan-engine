"""Synthetic commercial mortgages, refinance tests and delayed workouts."""

from dataclasses import dataclass
from datetime import date
import math
import numpy as np
import pandas as pd
from .structure import Tranche
from .structured import CreditStructure, CreditResult, level_payment, allocate_credit, allocation_row
from .waterfall import WaterfallState, allocate_losses


@dataclass(frozen=True)
class Mortgage:
    """DSCR and LTV at closing imply initial NOI and property value."""
    loan_id: str
    property_type: str
    par: float
    coupon: float
    dscr: float
    ltv: float
    maturity_date: date
    io_months: int = 0
    amortization_months: int = 360

    def __post_init__(self) -> None:
        if not self.loan_id or not self.property_type or not isinstance(self.maturity_date, date):
            raise ValueError("Mortgage must have an identity, property type and maturity date")
        if not all(math.isfinite(x) for x in (self.par, self.coupon, self.dscr, self.ltv)):
            raise ValueError("Mortgage inputs must be finite")
        if min(self.par, self.coupon, self.dscr, self.ltv) <= 0:
            raise ValueError("Mortgage economics must be positive")
        if not isinstance(self.io_months, int) or self.io_months < 0:
            raise ValueError("IO months must be a nonnegative integer")
        level_payment(self.par, self.coupon, self.amortization_months)

    @property
    def noi(self) -> float:
        debt_service = self.par * self.coupon if self.io_months else 12 * level_payment(
            self.par, self.coupon, self.amortization_months)
        return self.dscr * debt_service

    @property
    def value(self) -> float:
        return self.par / self.ltv


@dataclass(frozen=True)
class CMBSScenario:
    """All rates, tests, extension and workout terms are illustrative assumptions."""
    name: str = "base"
    refinance_rate: float = 0.055
    noi_multiplier: float = 1.0
    value_multiplier: float = 1.0
    minimum_refi_dscr: float = 1.10
    maximum_refi_ltv: float = 0.80
    annual_default_rate: float = 0.003
    loss_severity: float = 0.35
    servicing_lag_months: int = 12
    extension_months: int = 12
    extension_probability: float = 0.60

    def __post_init__(self) -> None:
        values = (self.refinance_rate, self.noi_multiplier, self.value_multiplier,
                  self.minimum_refi_dscr, self.maximum_refi_ltv, self.annual_default_rate,
                  self.loss_severity, self.extension_probability)
        if not all(math.isfinite(x) for x in values) or self.refinance_rate < 0:
            raise ValueError("Scenario inputs must be finite and refinance rate nonnegative")
        if min(self.noi_multiplier, self.value_multiplier, self.maximum_refi_ltv) <= 0 or self.minimum_refi_dscr < 0:
            raise ValueError("Invalid refinance tests")
        if any(not 0 <= x <= 1 for x in
               (self.annual_default_rate, self.loss_severity, self.extension_probability)):
            raise ValueError("Default, severity and extension probabilities must lie in [0, 1]")
        if any(not isinstance(x, int) or x < 0 for x in
               (self.servicing_lag_months, self.extension_months)):
            raise ValueError("Timing lags must be nonnegative whole months")


def cmbs_scenarios() -> tuple[CMBSScenario, ...]:
    return (CMBSScenario(), CMBSScenario("stress_rates_up", 0.085, 0.85, 0.80,
                                        annual_default_rate=0.012, loss_severity=0.45),
            CMBSScenario("severe", 0.10, 0.70, 0.65,
                         annual_default_rate=0.03, loss_severity=0.60))


def synthetic_mortgages(count: int = 80, total_par: float = 200_000_000,
                         seed: int = 2026, closing_date: date = date(2026, 1, 1)) -> list[Mortgage]:
    if not isinstance(count, int) or count <= 0 or not math.isfinite(total_par) or total_par <= 0:
        raise ValueError("Count and total par must be positive")
    rng = np.random.default_rng(seed)
    weights = rng.uniform(0.5, 1.5, count)
    weights /= weights.sum()
    types = ("office", "retail", "multifamily", "industrial", "hotel")
    loans = []
    for index, weight in enumerate(weights):
        months = int(rng.integers(60, 121))
        io = months if rng.random() < 0.40 else int(rng.choice([0, 24, 36]))
        loans.append(Mortgage(f"M{index + 1:03d}", types[index % len(types)], total_par * weight,
                              float(rng.uniform(0.05, 0.065)), float(rng.uniform(1.25, 1.85)),
                              float(rng.uniform(0.55, 0.78)),
                              (pd.Timestamp(closing_date) + pd.DateOffset(months=months)).date(), io))
    return loans


def conduit_structure(par: float = 200_000_000) -> CreditStructure:
    terms = [("A", "AAA", 0.70, 0.035), ("B", "AA", 0.10, 0.040),
             ("C", "A", 0.07, 0.045), ("D", "BBB", 0.05, 0.050),
             ("E", "BB", 0.03, 0.060), ("F", "B-piece", 0.05, 0.080)]
    return CreditStructure(tuple(Tranche(n, r, s * par, c, 1, 1) for n, r, s, c in terms), par)


def run_cmbs(loans: list[Mortgage], structure: CreditStructure | None = None,
             scenario: CMBSScenario = CMBSScenario(), seed: int = 90210,
             closing_date: date = date(2026, 1, 1)) -> CreditResult:
    """Run absorbing defaults and at most one maturity extension per loan.

    Failed balloon tests extend only if NOI covers existing interest and the
    seeded extension draw passes. Failed extension tests default. No advances
    accrue on specially serviced loans; recovery and realized loss arrive after
    the lag. Simulation continues through every extension and workout.
    """
    if not loans or len({x.loan_id for x in loans}) != len(loans):
        raise ValueError("Provide uniquely named mortgages")
    par = sum(x.par for x in loans)
    structure = conduit_structure(par) if structure is None else structure
    if not math.isclose(par, structure.collateral_par, rel_tol=1e-12):
        raise ValueError("Structure collateral must match mortgage par")
    if not math.isclose(sum(x.notional for x in structure.tranches), par, rel_tol=1e-12):
        raise ValueError("This conduit requires fully funded debt including its B-piece")
    if structure.reserve_fraction or structure.oc_target or structure.oc_floor or structure.pro_rata:
        raise ValueError("This conduit uses sequential pay without reserve or OC enhancement")
    dates = [pd.Timestamp(x.maturity_date) for x in loans]
    if min(dates) <= pd.Timestamp(closing_date):
        raise ValueError("Maturities must follow closing")
    max_date = max(dates)
    months = (max_date.year - closing_date.year) * 12 + max_date.month - closing_date.month
    if max_date.day > closing_date.day:
        months += 1
    horizon = months + scenario.extension_months + scenario.servicing_lag_months
    rng = np.random.default_rng(seed)
    # Draw entire arrays before branching so matching seeds share loan shocks.
    default_draws = rng.random((horizon, len(loans)))
    extension_draws = rng.random(len(loans))
    balances = np.array([x.par for x in loans], dtype=float)
    extended = np.zeros(len(loans), dtype=bool)
    payments = np.array([level_payment(x.par, x.coupon, x.amortization_months) for x in loans])
    state = WaterfallState.initial(structure)
    pending: list[tuple[int, int, float]] = []
    rows, events, interest, principal, losses = [], [], [], [], []
    fee_arrears = 0.0
    q_default = 1 - (1 - scenario.annual_default_rate) ** (1 / 12)
    for index in range(horizon):
        month = index + 1
        payment_date = pd.Timestamp(closing_date) + pd.DateOffset(months=month)
        opening = float(balances.sum())
        pending_open = sum(amount for _, _, amount in pending)
        defaulted = amortization = balloon = interest_cash = 0.0
        for loan_index, loan in enumerate(loans):
            balance = balances[loan_index]
            if balance <= 0:
                continue
            reason = None
            noi = loan.noi * scenario.noi_multiplier
            refi_dscr = noi / (12 * level_payment(balance, scenario.refinance_rate, 360))
            refi_ltv = balance / (loan.value * scenario.value_multiplier)
            if default_draws[index, loan_index] < q_default:
                reason = "term_default"
            elif payment_date >= dates[loan_index]:
                passes = refi_dscr >= scenario.minimum_refi_dscr and refi_ltv <= scenario.maximum_refi_ltv
                if passes:
                    # Successful refinance pays coupon and scheduled principal first.
                    pass
                elif (not extended[loan_index] and scenario.extension_months > 0
                      and noi >= balance * loan.coupon
                      and extension_draws[loan_index] < scenario.extension_probability):
                    extended[loan_index] = True
                    dates[loan_index] = payment_date + pd.DateOffset(months=scenario.extension_months)
                    events.append(dict(loan_id=loan.loan_id, property_type=loan.property_type,
                                       month=month, date=str(payment_date.date()), event="extension",
                                       balance=balance, refi_dscr=refi_dscr, refi_ltv=refi_ltv))
                else:
                    reason = "extension_default" if extended[loan_index] else "balloon_default"
            if reason:
                pending.append((month + scenario.servicing_lag_months, loan_index, balance))
                defaulted += balance
                balances[loan_index] = 0
                events.append(dict(loan_id=loan.loan_id, property_type=loan.property_type,
                                   month=month, date=str(payment_date.date()), event=reason,
                                   balance=balance, refi_dscr=refi_dscr, refi_ltv=refi_ltv))
                continue
            coupon = balance * loan.coupon / 12
            # NOI caps debt service; a payment deficit becomes interest shortfall.
            paid_interest = min(coupon, noi / 12)
            scheduled = 0.0 if month <= loan.io_months else min(
                balance, max(0, min(payments[loan_index], noi / 12) - coupon))
            interest_cash += paid_interest
            amortization += scheduled
            balance -= scheduled
            if payment_date >= dates[loan_index]:
                balloon += balance
                balance = 0.0
            balances[loan_index] = balance
        recovered = realized = resolved = 0.0
        remaining = []
        for resolution, loan_index, amount in pending:
            if resolution <= month:
                recovery = amount * (1 - scenario.loss_severity)
                recovered += recovery
                realized += amount - recovery
                resolved += amount
                events.append(dict(loan_id=loans[loan_index].loan_id,
                                   property_type=loans[loan_index].property_type, month=month,
                                   date=str(payment_date.date()), event="resolution", balance=amount,
                                   recovery=recovery, credit_loss=amount - recovery))
            else:
                remaining.append((resolution, loan_index, amount))
        pending = remaining
        closing = float(balances.sum())
        pending_close = sum(amount for _, _, amount in pending)
        principal_cash = recovered + amortization + balloon
        allocation = allocate_credit(structure, state, interest_cash, principal_cash, opening,
                                     closing + pending_close, 0, True, final=month == horizon,
                                     fee_arrears=fee_arrears, enable_turbo=False)
        fee_arrears = allocation.fee_arrears
        written = allocate_losses(state.balances, realized)
        rows.append(dict(month=month, date=str(payment_date.date()), time=month / 12,
                         opening_par=opening, closing_par=closing, pending_open=pending_open,
                         special_servicing_par=pending_close, defaulted_par=defaulted,
                         resolved_par=resolved, recovery=recovered, credit_loss=realized,
                         amortization=amortization, balloon=balloon,
                         collateral_interest=interest_cash, collateral_principal=principal_cash,
                         collateral_reconciliation=opening + pending_open - amortization - balloon
                         - recovered - realized - closing - pending_close,
                         **allocation_row(allocation, state, structure, written)))
        interest.append(allocation.interest)
        principal.append(allocation.principal)
        losses.append(written)
    return CreditResult(pd.DataFrame(rows), np.array(interest), np.array(principal), np.array(losses),
                        state.balances.copy(), state.interest_arrears.copy(), structure, pd.DataFrame(events))
