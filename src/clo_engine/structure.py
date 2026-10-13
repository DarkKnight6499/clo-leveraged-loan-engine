"""Illustrative liabilities and payment dates, not a rated transaction."""

from dataclasses import dataclass
from datetime import date
import math
import pandas as pd


@dataclass(frozen=True)
class Tranche:
    """A synthetic class, in descending order of payment priority."""
    name: str
    rating: str
    notional: float
    spread: float
    oc_trigger: float
    ic_trigger: float

    def __post_init__(self) -> None:
        values = (self.notional, self.spread, self.oc_trigger, self.ic_trigger)
        if not self.name or not self.rating or not all(math.isfinite(x) for x in values):
            raise ValueError("Tranche inputs must be finite and named")
        if self.notional <= 0 or self.spread < 0 or self.oc_trigger < 1 or self.ic_trigger < 1:
            raise ValueError("Invalid tranche economics")


@dataclass(frozen=True)
class CLOStructure:
    """All fees and trigger levels are stylized/unverified assumptions."""
    tranches: tuple[Tranche, ...]
    equity: float
    reinvestment_years: float = 4.0
    horizon_years: float = 10.0
    senior_fee: float = 0.0010
    subordinated_fee: float = 0.0040
    admin_expense: float = 200_000
    admin_cap: float = 250_000
    annual_tax: float = 0.0
    ccc_limit: float = 0.075
    diversion_trigger: float = 1.08
    diversion_fraction: float = 0.5
    default_oc_trigger: float = 1.0
    reinvestment_price: float = 0.9975
    reinvestment_spread: float = 0.036
    reinvestment_maturity: float = 5.0
    closing_date: date = date(2026, 1, 1)

    def __post_init__(self) -> None:
        values = (self.equity, self.reinvestment_years, self.horizon_years, self.senior_fee,
                  self.subordinated_fee, self.admin_expense, self.admin_cap, self.annual_tax,
                  self.ccc_limit, self.diversion_trigger, self.diversion_fraction,
                  self.default_oc_trigger, self.reinvestment_price, self.reinvestment_spread,
                  self.reinvestment_maturity)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("Structure inputs must be finite")
        if len(self.tranches) != 5 or len({x.name for x in self.tranches}) != 5:
            raise ValueError("Provide five uniquely named classes in seniority order")
        if self.equity <= 0 or not 0 <= self.reinvestment_years < self.horizon_years:
            raise ValueError("Invalid equity or reinvestment horizon")
        if any(abs(x * 4 - round(x * 4)) > 1e-9 for x in
               (self.reinvestment_years, self.horizon_years)):
            raise ValueError("Deal horizons must be whole quarters")
        if min(self.senior_fee, self.subordinated_fee, self.admin_expense,
               self.admin_cap, self.annual_tax, self.reinvestment_spread) < 0:
            raise ValueError("Fees, taxes and spread cannot be negative")
        if not 0 <= self.ccc_limit <= 1 or not 0 <= self.diversion_fraction <= 1:
            raise ValueError("Invalid bucket or diversion fraction")
        if min(self.diversion_trigger, self.default_oc_trigger) < 1:
            raise ValueError("Invalid OC trigger")
        if min(self.reinvestment_price, self.reinvestment_maturity) <= 0:
            raise ValueError("Invalid reinvestment terms")

    @property
    def periods(self) -> int:
        return round(self.horizon_years * 4)

    def payment_dates(self) -> list[date]:
        return [(pd.Timestamp(self.closing_date) + pd.DateOffset(months=3 * (i + 1))).date()
                for i in range(self.periods)]


def illustrative_structure(total_par: float = 500_000_000,
                           purchase_cost: float | None = None) -> CLOStructure:
    """Fund actual purchase cost with par priced notes and residual equity."""
    if not math.isfinite(total_par) or total_par <= 0:
        raise ValueError("Total par must be positive")
    terms = [
        ("A", "AAA", 0.63, 0.015, 1.25, 1.20),
        ("B", "AA", 0.11, 0.021, 1.25, 1.20),
        ("C", "A", 0.07, 0.028, 1.16, 1.10),
        ("D", "BBB", 0.05, 0.040, 1.10, 1.05),
        ("E", "BB", 0.04, 0.065, 1.04, 1.00),
    ]
    tranches = tuple(Tranche(name, rating, share * total_par, spread, oc, ic)
                     for name, rating, share, spread, oc, ic in terms)
    funding = total_par if purchase_cost is None else purchase_cost
    return CLOStructure(tranches=tranches, equity=funding - sum(x.notional for x in tranches))
