"""Par weighted collateral metrics and illustrative concentration limits."""

import math
import numpy as np
import pandas as pd
from .loans import Loan, RATING_FACTORS, loan_schedule


def industry_diversity_units(equivalent_units: float) -> float:
    """Look up the lower row of the published industry unit table."""
    if not math.isfinite(equivalent_units) or equivalent_units < 0:
        raise ValueError("Equivalent units must be nonnegative and finite")
    if equivalent_units < 0.05:
        return 0.0
    # Integer ticks avoid rounding a boundary into the wrong table row.
    tick = min(200, int(math.floor((equivalent_units - 0.05) * 10 + 1e-9)) + 1)
    if tick <= 10:
        score = tick / 10
    elif tick <= 30:
        score = 1 + (tick - 10) / 20
    elif tick <= 60:
        score = 2 + (tick - 30) / 30
    elif tick <= 100:
        score = 3 + (tick - 60) / 40
    else:
        score = 4 + (tick - 100) / 100
    # The verified table ends at 19.95; the cap above that is a stylized extension.
    return round(score, 4)


def diversity_score(loans: list[Loan]) -> float:
    """Sum industry scores after aggregating loans by borrower identity."""
    if not loans:
        return 0.0
    borrowers: dict[str, tuple[str, float]] = {}
    for loan in loans:
        industry, amount = borrowers.get(loan.borrower, (loan.industry, 0.0))
        if industry != loan.industry:
            raise ValueError("One borrower must have one industry")
        borrowers[loan.borrower] = (industry, amount + loan.par)
    average = sum(par for _, par in borrowers.values()) / len(borrowers)
    industries: dict[str, float] = {}
    for industry, par in borrowers.values():
        industries[industry] = industries.get(industry, 0.0) + min(1.0, par / average)
    return sum(industry_diversity_units(score) for score in industries.values())


def ccc_adjustment(balances: np.ndarray, prices: np.ndarray, ccc: np.ndarray,
                   bucket_limit: float = 0.075) -> tuple[float, float]:
    """Return CCC share and par haircut on the lowest priced excess slice."""
    balances, prices, ccc = (np.asarray(balances, dtype=float),
                             np.asarray(prices, dtype=float), np.asarray(ccc, dtype=bool))
    if balances.ndim != 1 or not (balances.shape == prices.shape == ccc.shape):
        raise ValueError("CCC arrays must have matching vector shapes")
    if not (np.isfinite(balances).all() and np.isfinite(prices).all()):
        raise ValueError("CCC arrays must be finite")
    if (balances < 0).any() or (prices < 0).any() or not 0 <= bucket_limit <= 1:
        raise ValueError("Invalid CCC inputs")
    total = float(balances.sum())
    if total == 0:
        return 0.0, 0.0
    ccc_par = float(balances[ccc].sum())
    excess = max(0, ccc_par - bucket_limit * total)
    haircut = 0.0
    indices = np.flatnonzero(ccc)
    for index in indices[np.argsort(prices[indices], kind="stable")]:
        selected = min(excess, balances[index])
        haircut += selected * max(0, 1 - prices[index])
        excess -= selected
        if excess <= 1e-12:
            break
    return ccc_par / total, haircut


def portfolio_metrics(loans: list[Loan], sofr: float = 0.035,
                       bucket_limit: float = 0.075) -> dict[str, float]:
    """Calculate funded performing loan metrics, excluding no hidden assets."""
    if not loans:
        raise ValueError("Portfolio must not be empty")
    par = np.array([x.par for x in loans])
    weights = par / par.sum()
    share, haircut = ccc_adjustment(par, np.array([x.price for x in loans]),
                                    np.array([x.rating.startswith("Caa") for x in loans]), bucket_limit)
    lives = []
    for loan in loans:
        curve = np.full(math.ceil(loan.maturity / 0.25), sofr)
        schedule = loan_schedule(loan, curve)
        lives.append(float((schedule.time * schedule.principal).sum() / loan.par))
    industries: dict[str, float] = {}
    for loan in loans:
        industries[loan.industry] = industries.get(loan.industry, 0) + loan.par
    raw_warf = float(weights @ np.array([RATING_FACTORS[x.rating] for x in loans]))
    return {
        "par": float(par.sum()), "purchase_cost": sum(x.purchase_cost for x in loans),
        "par_build": sum(x.par - x.purchase_cost for x in loans),
        "warf": float(math.ceil(raw_warf)), "warf_unrounded": raw_warf,
        "was": float(weights @ np.array([x.coupon(sofr) - sofr for x in loans])),
        "warr": float(weights @ np.array([x.recovery for x in loans])),
        "wal": float(weights @ np.array(lives)), "diversity_score": diversity_score(loans),
        "industry_effective_count": 1 / sum((p / par.sum()) ** 2 for p in industries.values()),
        "ccc_share": share, "ccc_haircut": haircut, "oc_collateral": float(par.sum()) - haircut,
    }


def concentration_tests(loans: list[Loan], limits: dict[str, float] | None = None) -> pd.DataFrame:
    """Evaluate stylized limits, not the requirements of a particular deal."""
    if not loans:
        raise ValueError("Portfolio must not be empty")
    if limits is None:
        limits = {"largest_obligor": 0.02, "largest_industry": 0.10,
                  "second_lien": 0.10, "cov_lite": 0.90}
    total = sum(x.par for x in loans)
    borrowers: dict[str, float] = {}
    industries: dict[str, float] = {}
    for loan in loans:
        borrowers[loan.borrower] = borrowers.get(loan.borrower, 0) + loan.par
        industries[loan.industry] = industries.get(loan.industry, 0) + loan.par
    values = {"largest_obligor": max(borrowers.values()) / total,
              "largest_industry": max(industries.values()) / total,
              "second_lien": sum(x.par for x in loans if x.second_lien) / total,
              "cov_lite": sum(x.par for x in loans if x.cov_lite) / total}
    if set(limits) != set(values) or any(not 0 <= x <= 1 for x in limits.values()):
        raise ValueError("Provide all four valid concentration limits")
    return pd.DataFrame([{"metric": key, "actual": value, "limit": limits[key],
                          "passes": value <= limits[key]} for key, value in values.items()])
