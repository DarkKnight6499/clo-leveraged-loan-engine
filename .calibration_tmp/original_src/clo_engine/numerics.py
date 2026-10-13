"""Small numerical primitives without SciPy."""

from collections.abc import Callable
import math


def bisect_root(function: Callable[[float], float], lower: float, upper: float,
                tolerance: float = 1e-10, max_iterations: int = 200) -> float:
    """Find a bracketed root, with an absolute interval tolerance."""
    if not (math.isfinite(lower) and math.isfinite(upper) and lower < upper):
        raise ValueError("Root bracket must be finite and ordered")
    if not math.isfinite(tolerance) or tolerance <= 0 or max_iterations < 1:
        raise ValueError("Invalid solver controls")
    left, right = function(lower), function(upper)
    if not (math.isfinite(left) and math.isfinite(right)):
        raise ValueError("Function must be finite at bracket endpoints")
    if left == 0:
        return lower
    if right == 0:
        return upper
    if (left > 0) == (right > 0):
        raise ValueError("Root is not bracketed")
    for _ in range(max_iterations):
        middle = (lower + upper) / 2
        value = function(middle)
        if not math.isfinite(value):
            raise ValueError("Function must be finite inside bracket")
        if value == 0 or upper - lower <= tolerance:
            return middle
        if (value > 0) == (left > 0):
            lower, left = middle, value
        else:
            upper = middle
    raise RuntimeError("Bisection did not converge")


def normal_cdf(value: float) -> float:
    """Evaluate the standard normal CDF using erf."""
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def normal_quantile(probability: float) -> float:
    """Invert the normal CDF by bisection for copula thresholds."""
    if not 0 <= probability <= 1:
        raise ValueError("Probability must be between zero and one")
    if probability == 0:
        return -math.inf
    if probability == 1:
        return math.inf
    return bisect_root(lambda x: normal_cdf(x) - probability, -10, 10)


def period_probability(annual_rate: float, dt: float = 0.25) -> float:
    """Convert a constant annual repayment or default probability."""
    if not 0 <= annual_rate <= 1 or not math.isfinite(dt) or dt <= 0:
        raise ValueError("Invalid annual probability or period length")
    return 1 - (1 - annual_rate) ** dt
