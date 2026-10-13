"""Shared monthly structured credit accounting and paid-principal analytics."""

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from .structure import Tranche
from .waterfall import WaterfallState, pay_principal


def level_payment(balance: float, annual_rate: float, months: int) -> float:
    """Return the monthly payment for a fully amortizing fixed rate balance."""
    if not all(math.isfinite(x) for x in (balance, annual_rate)) or balance < 0 or annual_rate < 0:
        raise ValueError("Balance and rate must be finite and nonnegative")
    if not isinstance(months, int) or months <= 0:
        raise ValueError("Months must be a positive integer")
    rate = annual_rate / 12
    return balance / months if rate == 0 else balance * rate / (-math.expm1(-months * math.log1p(rate)))


@dataclass(frozen=True)
class CreditStructure:
    """Senior-to-junior classes. Tranche.spread stores the fixed annual coupon."""
    tranches: tuple[Tranche, ...]
    collateral_par: float
    servicing_fee: float = 0.005
    reserve_fraction: float = 0.0
    oc_target: float = 0.0
    oc_floor: float = 0.0
    loss_trigger: float = 1.0
    pro_rata: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.collateral_par) or self.collateral_par <= 0 or not self.tranches:
            raise ValueError("Provide positive collateral and at least one tranche")
        if len({x.name for x in self.tranches}) != len(self.tranches):
            raise ValueError("Class names must be unique")
        if sum(x.notional for x in self.tranches) > self.collateral_par * (1 + 1e-12):
            raise ValueError("Debt cannot exceed initial collateral")
        for value in (self.servicing_fee, self.reserve_fraction, self.oc_target,
                      self.oc_floor, self.loss_trigger):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Fees, enhancement and triggers must lie in [0, 1]")

    def subordination(self, index: int) -> float:
        """Initial collateral below a class, including OC but excluding reserve."""
        return 1 - sum(x.notional for x in self.tranches[:index + 1]) / self.collateral_par


@dataclass(frozen=True)
class CreditResult:
    """Monthly cash flows, realized write-downs, and remaining interest arrears."""
    ledger: pd.DataFrame
    interest: np.ndarray
    principal: np.ndarray
    losses: np.ndarray
    ending_balances: np.ndarray
    unpaid_interest: np.ndarray
    structure: CreditStructure
    events: pd.DataFrame

    def tranche_analytics(self) -> pd.DataFrame:
        times = self.ledger.time.to_numpy()
        rows = []
        for index, tranche in enumerate(self.structure.tranches):
            paid = float(self.principal[:, index].sum())
            loss = float(self.losses[:, index].sum() + self.ending_balances[index])
            rows.append(dict(
                **{"class": tranche.name}, rating_label=tranche.rating,
                initial_notional=tranche.notional,
                subordination=self.structure.subordination(index), principal_paid=paid,
                principal_loss=loss, principal_loss_fraction=loss / tranche.notional,
                unpaid_interest=float(self.unpaid_interest[index]),
                paid_principal_life=float(times @ self.principal[:, index] / paid) if paid > 0 else math.nan,
            ))
        return pd.DataFrame(rows)


@dataclass(frozen=True)
class CreditAllocation:
    interest: np.ndarray
    principal: np.ndarray
    fee_paid: float
    fee_arrears: float
    reserve: float
    reserve_draw: float
    reserve_deposit: float
    reserve_release: float
    excess_spread: float
    turbo: float
    residual: float
    reconciliation_error: float


def allocate_credit(structure: CreditStructure, state: WaterfallState,
                    interest: float, principal: float, opening_par: float,
                    closing_par: float, reserve: float, sequential: bool,
                    turbo_all: bool = False, final: bool = False,
                    fee_arrears: float = 0.0, enable_turbo: bool = True) -> CreditAllocation:
    """Pay fees, coupons, reserve, OC turbo, principal, then residual cash.

    Reserve supports fees and coupons. Principal does not support coupons until
    all live principal is paid. Arrears carry without compounding. Final reserve
    releases into principal. Turbo always pays senior principal first.
    """
    if not all(math.isfinite(x) and x >= 0 for x in
               (interest, principal, opening_par, closing_par, reserve, fee_arrears)):
        raise ValueError("Cash, collateral and arrears must be finite and nonnegative")
    count = len(structure.tranches)
    for values in (state.balances, state.interest_arrears):
        if values.shape != (count,) or not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Waterfall state must match the classes and remain nonnegative")
    reserve_open = reserve
    interest_cash = interest
    draw = 0.0

    def pay(amount: float) -> float:
        nonlocal interest_cash, reserve, draw
        cash = min(amount, interest_cash)
        interest_cash -= cash
        support = min(amount - cash, reserve)
        reserve -= support
        draw += support
        return cash + support

    fee_due = opening_par * structure.servicing_fee / 12 + fee_arrears
    fee_paid = pay(fee_due)
    owed = state.balances * np.array([x.spread for x in structure.tranches]) / 12 + state.interest_arrears
    paid_interest = np.array([pay(float(x)) for x in owed])
    state.interest_arrears = np.maximum(owed - paid_interest, 0)
    excess = interest_cash
    reserve_target = structure.reserve_fraction * structure.collateral_par if not final else 0
    deposit = min(interest_cash, max(0, reserve_target - reserve))
    reserve += deposit
    interest_cash -= deposit
    release = reserve if final else 0.0
    reserve -= release
    principal_cash = principal + release
    oc_target = min(closing_par, max(structure.oc_target * closing_par,
                                    structure.oc_floor * structure.collateral_par))
    cure = max(0, float(state.balances.sum()) - principal_cash - closing_par + oc_target)
    turbo = min(interest_cash, float(state.balances.sum()),
                float(state.balances.sum()) if turbo_all else cure) if enable_turbo else 0.0
    paid_principal = pay_principal(state.balances, turbo)
    interest_cash = max(0, interest_cash - float(paid_principal.sum()))
    turbo = float(paid_principal.sum())
    payments = pay_principal(state.balances, principal_cash, sequential)
    paid_principal += payments
    principal_cash = max(0, principal_cash - float(payments.sum()))
    # Residual principal supports unpaid fees and coupons before equity.
    extra_fee = min(principal_cash, fee_due - fee_paid)
    principal_cash -= extra_fee
    fee_paid += extra_fee
    for index in range(len(state.balances)):
        extra = min(principal_cash, state.interest_arrears[index])
        paid_interest[index] += extra
        state.interest_arrears[index] -= extra
        principal_cash -= extra
    residual = interest_cash + principal_cash
    used = fee_paid + float(paid_interest.sum() + paid_principal.sum()) + residual + reserve
    error = interest + principal + reserve_open - used
    return CreditAllocation(paid_interest, paid_principal, fee_paid, fee_due - fee_paid,
                            reserve, draw, deposit, release, excess, turbo, residual, error)


def allocation_row(allocation: CreditAllocation, state: WaterfallState,
                   structure: CreditStructure, losses: np.ndarray) -> dict:
    row = dict(fee_paid=allocation.fee_paid, fee_arrears=allocation.fee_arrears,
               reserve=allocation.reserve, reserve_draw=allocation.reserve_draw,
               reserve_deposit=allocation.reserve_deposit, reserve_release=allocation.reserve_release,
               excess_spread=allocation.excess_spread, turbo=allocation.turbo,
               residual=allocation.residual, reconciliation_error=allocation.reconciliation_error)
    for index, tranche in enumerate(structure.tranches):
        row.update({f"{tranche.name}_interest": allocation.interest[index],
                    f"{tranche.name}_principal": allocation.principal[index],
                    f"{tranche.name}_loss": losses[index],
                    f"{tranche.name}_balance": state.balances[index],
                    f"{tranche.name}_interest_shortfall": state.interest_arrears[index]})
    return row
