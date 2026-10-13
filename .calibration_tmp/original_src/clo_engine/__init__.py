"""Leveraged loan mechanics and an illustrative CLO engine."""

from .loans import Loan, loan_schedule, synthetic_portfolio, sofr_curve
from .metrics import portfolio_metrics, concentration_tests, diversity_score
from .structure import CLOStructure, Tranche, illustrative_structure
from .engine import DealResult, run_deal
from .simulation import monte_carlo, break_even_default_rate, stress_table
from .valuation import discounted_value, discount_margin, equity_irr, cash_multiple

__all__ = [
    "Loan", "loan_schedule", "synthetic_portfolio", "sofr_curve",
    "portfolio_metrics", "concentration_tests", "diversity_score",
    "CLOStructure", "Tranche", "illustrative_structure", "DealResult", "run_deal",
    "monte_carlo", "break_even_default_rate", "stress_table",
    "discounted_value", "discount_margin", "equity_irr", "cash_multiple",
]
