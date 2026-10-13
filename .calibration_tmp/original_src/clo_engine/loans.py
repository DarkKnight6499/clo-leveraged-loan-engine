"""Synthetic loan data and floating rate payment mechanics."""

from dataclasses import asdict, dataclass
import math
import numpy as np
import pandas as pd
from .numerics import period_probability

# Verified in the filed indenture rating factor definition, see docs/sources.md.
RATING_FACTORS = {"B1": 2220, "B2": 2720, "B3": 3490,
                  "Caa1": 4770, "Caa2": 6500, "Caa3": 8070}
# Stylized/unverified annual default probabilities, not agency calibration.
DEFAULT_PROBABILITIES = {"B1": 0.015, "B2": 0.025, "B3": 0.045,
                         "Caa1": 0.10, "Caa2": 0.16, "Caa3": 0.25}
INDUSTRIES = (
    "Aerospace", "Automotive", "Banking", "Beverage", "Broadcasting",
    "Business services", "Chemicals", "Construction", "Consumer products", "Containers",
    "Energy", "Environmental", "Food", "Healthcare", "Hotels",
    "Insurance", "Leisure", "Machinery", "Metals", "Packaging",
    "Retail", "Software", "Telecom", "Transport", "Utilities",
)


@dataclass(frozen=True)
class Loan:
    """A fully funded synthetic loan; rates and prices are decimal fractions."""
    borrower: str
    industry: str
    rating: str
    par: float
    spread: float = 0.04
    floor: float = 0.01
    maturity: float = 6.0
    amortization: float = 0.01
    price: float = 1.0
    second_lien: bool = False
    cov_lite: bool = True
    recovery: float = 0.65

    def __post_init__(self) -> None:
        if not self.borrower or not self.industry or self.rating not in RATING_FACTORS:
            raise ValueError("Missing identity or unsupported rating")
        values = (self.par, self.spread, self.floor, self.maturity,
                  self.amortization, self.price, self.recovery)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("Loan inputs must be finite")
        if self.par <= 0 or self.maturity <= 0 or self.price <= 0:
            raise ValueError("Par, maturity and price must be positive")
        if self.spread < 0 or self.floor < 0 or not 0 <= self.amortization <= 1:
            raise ValueError("Invalid spread, floor or amortization")
        if not 0 <= self.recovery <= 1:
            raise ValueError("Recovery must be between zero and one")

    def coupon(self, sofr: float) -> float:
        """Annual cash coupon after the benchmark floor."""
        if not math.isfinite(sofr):
            raise ValueError("SOFR must be finite")
        return max(sofr, self.floor) + self.spread

    @property
    def purchase_cost(self) -> float:
        return self.par * self.price


def synthetic_portfolio(count: int = 150, total_par: float = 500_000_000,
                        seed: int = 2026) -> list[Loan]:
    """Create seeded synthetic collateral, with no external data."""
    if count < 1 or not math.isfinite(total_par) or total_par <= 0:
        raise ValueError("Invalid portfolio size")
    rng = np.random.default_rng(seed)
    weights = rng.lognormal(0, 0.35, count)
    amounts = total_par * weights / weights.sum()
    ratings = rng.choice(list(RATING_FACTORS), count, p=[0.30, 0.40, 0.23, 0.04, 0.02, 0.01])
    result = []
    for i in range(count):
        rating = str(ratings[i])
        second = bool(rng.random() < 0.06)
        severity = list(RATING_FACTORS).index(rating)
        result.append(Loan(
            borrower=f"Synthetic borrower {i + 1:03d}", industry=INDUSTRIES[i % len(INDUSTRIES)],
            rating=rating, par=float(amounts[i]),
            spread=float(0.032 + 0.006 * severity + rng.uniform(0, 0.012) + 0.012 * second),
            floor=float(rng.choice([0.0, 0.005, 0.01])),
            maturity=float(rng.choice(np.arange(4.5, 7.25, 0.25))),
            price=float(rng.uniform(0.93, 1.015) if severity < 3 else rng.uniform(0.55, 0.85)),
            second_lien=second, cov_lite=bool(rng.random() < 0.85),
            recovery=0.40 if second else 0.65,
        ))
    return result


def portfolio_frame(loans: list[Loan]) -> pd.DataFrame:
    """Export synthetic loan inputs with purchase costs."""
    frame = pd.DataFrame([asdict(loan) for loan in loans])
    frame["purchase_cost"] = [loan.purchase_cost for loan in loans]
    frame["data_type"] = "synthetic"
    return frame


def sofr_curve(periods: int = 40, scenario: str = "flat", initial: float = 0.035) -> np.ndarray:
    """Produce a synthetic forward benchmark curve, never a market forecast."""
    if periods < 1 or not math.isfinite(initial) or initial < 0:
        raise ValueError("Invalid curve inputs")
    shifts = {"flat": 0.0, "up": 0.02, "down": -0.03}
    if scenario not in shifts:
        raise ValueError("Scenario must be flat, up or down")
    return np.maximum(0, initial + np.linspace(0, shifts[scenario], periods))


def loan_schedule(loan: Loan, curve: np.ndarray, prepayment: float = 0,
                  dt: float = 0.25) -> pd.DataFrame:
    """Pay opening balance interest, original par amortization, then prepayment."""
    curve = np.asarray(curve, dtype=float)
    if curve.ndim != 1 or not np.isfinite(curve).all():
        raise ValueError("Curve must be a finite vector")
    q = period_probability(prepayment, dt)
    if len(curve) * dt + 1e-12 < loan.maturity:
        raise ValueError("Curve must reach loan maturity")
    balance = loan.par
    rows = []
    for index, rate in enumerate(curve):
        time = (index + 1) * dt
        opening = balance
        interest = opening * loan.coupon(float(rate)) * dt
        amortization = min(balance, loan.par * loan.amortization * dt)
        balance -= amortization
        prepaid = balance * q if time + 1e-12 < loan.maturity else 0
        balance -= prepaid
        balloon = balance if time + 1e-12 >= loan.maturity else 0
        balance -= balloon
        rows.append(dict(time=time, opening=opening, interest=interest,
                         amortization=amortization, prepayment=prepaid, balloon=balloon,
                         principal=amortization + prepaid + balloon, closing=balance))
        if balance <= 1e-12:
            break
    return pd.DataFrame(rows)
