"""An auditable interest and principal waterfall for an illustrative deal."""

from dataclasses import dataclass
import math
import numpy as np
from .structure import CLOStructure


@dataclass
class WaterfallState:
    """Mutable balances and unpaid obligations, owned by one simulation path."""
    balances: np.ndarray
    interest_arrears: np.ndarray
    expense_arrears: np.ndarray
    subordinated_arrears: float = 0.0

    @classmethod
    def initial(cls, structure: CLOStructure) -> "WaterfallState":
        return cls(np.array([x.notional for x in structure.tranches], dtype=float), np.zeros(5), np.zeros(3))


@dataclass(frozen=True)
class PeriodAllocation:
    """Every currency use of proceeds, plus diagnostic ratios before cures."""
    interest_paid: np.ndarray
    principal_paid: np.ndarray
    oc_ratios: np.ndarray
    ic_ratios: np.ndarray
    oc_breaches: np.ndarray
    ic_breaches: np.ndarray
    expenses_paid: float
    subordinated_paid: float
    equity_interest: float
    equity_principal: float
    reinvestment_cash: float
    coverage_diversion: float
    interest_diversion: float
    diversion_breach: bool
    event_default: bool
    interest_in: float
    principal_in: float
    reconciliation_error: float

    @property
    def equity(self) -> float:
        return self.equity_interest + self.equity_principal


def allocate_period(structure: CLOStructure, state: WaterfallState,
                     interest: float, principal: float, collateral_oc: float,
                     fee_base: float, sofr: float, reinvest: bool,
                     final: bool = False) -> PeriodAllocation:
    """Apply shared A/B tests, then C, D and an illustrative E test."""
    inputs = (interest, principal, collateral_oc, fee_base, sofr)
    if not all(math.isfinite(x) for x in inputs) or min(inputs[:4]) < 0:
        raise ValueError("Proceeds and collateral must be finite and nonnegative")
    if final and reinvest:
        raise ValueError("Final proceeds cannot be reinvested")
    arrays = (state.balances, state.interest_arrears, state.expense_arrears)
    if tuple(x.shape for x in arrays) != ((5,), (5,), (3,)):
        raise ValueError("Invalid waterfall state shapes")
    if any(not np.isfinite(x).all() or (x < 0).any() for x in arrays):
        raise ValueError("Invalid waterfall balances or arrears")
    if not math.isfinite(state.subordinated_arrears) or state.subordinated_arrears < 0:
        raise ValueError("Invalid subordinated fee arrears")
    dt = 0.25
    opening = state.balances.copy()
    rates = np.array([max(sofr, 0) + x.spread for x in structure.tranches])
    current_interest = opening * rates * dt
    owed = current_interest + state.interest_arrears
    billed_expenses = np.array([structure.annual_tax * dt,
                                min(structure.admin_expense, structure.admin_cap) * dt,
                                fee_base * structure.senior_fee * dt])
    expense_due = billed_expenses + state.expense_arrears
    sub_due = fee_base * structure.subordinated_fee * dt + state.subordinated_arrears
    interest_cash, principal_cash = interest, principal
    paid_interest, paid_principal = np.zeros(5), np.zeros(5)
    oc_ratios, ic_ratios = np.full(5, math.inf), np.full(5, math.inf)
    oc_breaches, ic_breaches = np.zeros(5, bool), np.zeros(5, bool)
    expense_paid = np.zeros(3)
    net_interest = max(0, interest - float(expense_due.sum()))

    def priority_cash(amount: float, use_principal: bool) -> float:
        nonlocal interest_cash, principal_cash
        from_interest = min(interest_cash, amount)
        interest_cash -= from_interest
        from_principal = min(principal_cash, amount - from_interest) if use_principal else 0.0
        principal_cash -= from_principal
        return from_interest + from_principal

    def principal_sequence(amount: float) -> float:
        remaining = amount
        for index in range(5):
            payment = min(remaining, state.balances[index])
            state.balances[index] -= payment
            paid_principal[index] += payment
            remaining -= payment
        return amount - remaining

    for index in range(3):
        expense_paid[index] = priority_cash(float(expense_due[index]), True)
    state.expense_arrears = np.maximum(0, expense_due - expense_paid)

    def pay_interest(index: int) -> None:
        paid_interest[index] += priority_cash(float(owed[index]), index <= 1)

    coverage_diversion = 0.0

    def coverage_test(index: int, shared: bool = False) -> None:
        nonlocal interest_cash, coverage_diversion
        debt = float(state.balances[:index + 1].sum())
        numerator = collateral_oc + principal_cash
        denominator = float((state.balances[:index + 1] * rates[:index + 1] * dt).sum())
        oc = numerator / debt if debt > 1e-10 else math.inf
        ic = net_interest / denominator if denominator > 1e-10 else math.inf
        tranche = structure.tranches[index]
        slots = [0, 1] if shared else [index]
        for slot in slots:
            oc_ratios[slot], ic_ratios[slot] = oc, ic
            oc_breaches[slot] = oc + 1e-12 < tranche.oc_trigger
            ic_breaches[slot] = ic + 1e-12 < tranche.ic_trigger
        oc_need = max(0, debt - numerator / tranche.oc_trigger)
        target_coupon = net_interest / tranche.ic_trigger
        excess_coupon = max(0, denominator - target_coupon)
        ic_need = 0.0
        for slot in range(index + 1):
            payment = min(state.balances[slot], excess_coupon / (rates[slot] * dt)) if rates[slot] > 0 else 0
            ic_need += payment
            excess_coupon = max(0, excess_coupon - payment * rates[slot] * dt)
        diverted = principal_sequence(min(interest_cash, max(oc_need, ic_need)))
        interest_cash -= diverted
        coverage_diversion += diverted

    pay_interest(0)
    pay_interest(1)
    coverage_test(1, shared=True)
    for index in (2, 3, 4):
        pay_interest(index)
        coverage_test(index)

    debt_d = float(state.balances[:4].sum())
    diversion_ratio = (collateral_oc + principal_cash) / debt_d if debt_d > 1e-10 else math.inf
    diversion_breach = reinvest and diversion_ratio + 1e-12 < structure.diversion_trigger
    interest_diversion = 0.0
    if diversion_breach:
        par_needed = max(0, structure.diversion_trigger * debt_d - collateral_oc - principal_cash)
        interest_diversion = min(interest_cash * structure.diversion_fraction,
                                  par_needed * structure.reinvestment_price)
        interest_cash -= interest_diversion

    sub_paid = priority_cash(sub_due, False)
    state.subordinated_arrears = max(0, sub_due - sub_paid)
    state.interest_arrears = np.maximum(0, owed - paid_interest)
    reinvestment_cash = 0.0
    if reinvest:
        reinvestment_cash = principal_cash + interest_diversion
        principal_cash = 0.0
    else:
        if final:
            # At liquidation, each senior class recovers arrears before its principal.
            for index in range(5):
                extra_interest = min(principal_cash, state.interest_arrears[index])
                principal_cash -= extra_interest
                paid_interest[index] += extra_interest
                state.interest_arrears[index] -= extra_interest
                payment = min(principal_cash, state.balances[index])
                state.balances[index] -= payment
                paid_principal[index] += payment
                principal_cash -= payment
        else:
            principal_cash -= principal_sequence(principal_cash)
        if state.balances.sum() <= 1e-8:
            for index in range(5):
                extra_interest = min(principal_cash, state.interest_arrears[index])
                paid_interest[index] += extra_interest
                state.interest_arrears[index] -= extra_interest
                principal_cash -= extra_interest
            extra_sub = min(principal_cash, state.subordinated_arrears)
            sub_paid += extra_sub
            state.subordinated_arrears -= extra_sub
            principal_cash -= extra_sub
    # Equity cannot receive interest while a higher priority obligation is unpaid.
    if (state.interest_arrears.sum() + state.expense_arrears.sum()
            + state.subordinated_arrears > 1e-8 and interest_cash > 0):
        diverted = principal_sequence(interest_cash)
        coverage_diversion += diverted
        interest_cash -= diverted
    senior_unpaid = bool(np.any(state.interest_arrears[:2] > 1e-8))
    senior_debt = float(state.balances[:2].sum())
    default_oc = (collateral_oc + principal_cash) / senior_debt if senior_debt > 1e-10 else math.inf
    event_default = senior_unpaid or default_oc < structure.default_oc_trigger
    used = (float(paid_interest.sum() + paid_principal.sum() + expense_paid.sum())
            + sub_paid + interest_cash + principal_cash + reinvestment_cash)
    return PeriodAllocation(
        paid_interest, paid_principal, oc_ratios, ic_ratios, oc_breaches, ic_breaches,
        float(expense_paid.sum()), sub_paid, interest_cash, principal_cash,
        reinvestment_cash, coverage_diversion, interest_diversion, diversion_breach,
        event_default, interest, principal, interest + principal - used,
    )
