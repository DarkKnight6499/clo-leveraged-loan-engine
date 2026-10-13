"""Cash flow valuation with explicit quarterly compounding conventions."""

import math
import numpy as np
from .numerics import bisect_root


def discounted_value(cashflows: np.ndarray, curve: np.ndarray, margin: float,
                     dt: float = 0.25) -> float:
    """Discount period end cash using successive benchmark plus margin factors."""
    cashflows, curve = np.asarray(cashflows, dtype=float), np.asarray(curve, dtype=float)
    if cashflows.ndim != 1 or cashflows.shape != curve.shape or cashflows.size == 0:
        raise ValueError("Provide matching nonempty cash flow and curve vectors")
    if not np.isfinite(cashflows).all() or not np.isfinite(curve).all():
        raise ValueError("Cash flows and curve must be finite")
    if not math.isfinite(margin) or not math.isfinite(dt) or dt <= 0:
        raise ValueError("Invalid margin or period length")
    factors = 1 + (curve + margin) * dt
    if (factors <= 0).any():
        raise ValueError("Discount factors must be positive")
    return float(np.sum(cashflows / np.cumprod(factors)))


def discount_margin(cashflows: np.ndarray, curve: np.ndarray, price: float,
                    dt: float = 0.25) -> float:
    """Solve a monotone DCF margin for a currency price, allowing negative margins."""
    cashflows, curve = np.asarray(cashflows, dtype=float), np.asarray(curve, dtype=float)
    if cashflows.ndim != 1 or cashflows.size == 0 or (cashflows < 0).any():
        raise ValueError("Discount margin requires nonnegative future cash flows")
    if not math.isfinite(price) or price <= 0 or cashflows.sum() <= 0:
        raise ValueError("Price and total cash must be positive")
    discounted_value(cashflows, curve, 0, dt)
    lower = -1 / dt - float(curve.min()) + 1e-10
    active = cashflows > 0
    def objective(margin: float) -> float:
        cumulative_logs = np.cumsum(np.log1p((curve + margin) * dt))
        terms = np.log(cashflows[active]) - cumulative_logs[active]
        largest = float(terms.max())
        return largest + math.log(float(np.exp(terms - largest).sum())) - math.log(price)
    upper = 1.0
    while objective(upper) > 0 and upper < 1e6:
        upper *= 2
    return bisect_root(objective, lower, upper)


def equity_irr(initial: float, distributions: np.ndarray, dt: float = 0.25) -> float:
    """Return effective annual IRR for one outlay and nonnegative distributions."""
    distributions = np.asarray(distributions, dtype=float)
    if (not math.isfinite(initial) or initial <= 0 or distributions.ndim != 1
            or distributions.size == 0 or not np.isfinite(distributions).all()
            or (distributions < 0).any() or not math.isfinite(dt) or dt <= 0):
        raise ValueError("Invalid equity cash flows")
    if distributions.sum() == 0:
        return -1.0
    times = np.arange(1, len(distributions) + 1) * dt
    # Solve log annual growth to handle IRRs arbitrarily close to total loss.
    active = distributions > 0
    logs = np.log(distributions[active]) - math.log(initial)
    def objective(log_growth: float) -> float:
        terms = logs - times[active] * log_growth
        largest = float(terms.max())
        return largest + math.log(float(np.exp(terms - largest).sum()))
    root = bisect_root(objective, -100 / dt, 100 / dt)
    return math.expm1(root)


def cash_multiple(initial: float, distributions: np.ndarray) -> float:
    """Return total distributions divided by initial invested capital."""
    values = np.asarray(distributions, dtype=float)
    if initial <= 0 or not math.isfinite(initial) or values.ndim != 1:
        raise ValueError("Invalid capital or distribution shape")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Distributions must be finite and nonnegative")
    return float(values.sum() / initial)
