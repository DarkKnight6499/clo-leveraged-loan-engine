"""Synthetic structured credit mechanics and illustrative CLO, ABS and CMBS."""

from .loans import Loan, loan_schedule, synthetic_portfolio, sofr_curve
from .metrics import portfolio_metrics, concentration_tests, diversity_score
from .structure import CLOStructure, Tranche, illustrative_structure
from .engine import DealResult, run_deal
from .simulation import monte_carlo, break_even_default_rate, stress_table
from .valuation import discounted_value, discount_margin, equity_irr, cash_multiple
from .abs import AutoPool, ABSScenario, abs_scenarios, auto_structure, auto_schedule, run_abs, abs_break_even_cnl
from .cmbs import Mortgage, CMBSScenario, synthetic_mortgages, conduit_structure, cmbs_scenarios, run_cmbs
from .structured import CreditStructure, CreditResult, level_payment
from .comparison import comparison_table

__all__ = [
    "Loan", "loan_schedule", "synthetic_portfolio", "sofr_curve",
    "portfolio_metrics", "concentration_tests", "diversity_score",
    "CLOStructure", "Tranche", "illustrative_structure", "DealResult", "run_deal",
    "monte_carlo", "break_even_default_rate", "stress_table",
    "discounted_value", "discount_margin", "equity_irr", "cash_multiple",
    "AutoPool", "ABSScenario", "abs_scenarios", "auto_structure", "auto_schedule", "run_abs",
    "abs_break_even_cnl", "Mortgage", "CMBSScenario", "synthetic_mortgages", "conduit_structure",
    "cmbs_scenarios", "run_cmbs", "CreditStructure", "CreditResult", "level_payment", "comparison_table",
]
