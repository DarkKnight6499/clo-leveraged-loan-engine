"""Compare synthetic loan amortization and prepayment cash flows."""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clo_engine import Loan, loan_schedule
from run_analysis import markdown_table


def main() -> None:
    output = ROOT / "examples" / "output"
    output.mkdir(parents=True, exist_ok=True)
    loan = Loan("Synthetic demonstration borrower", "Software", "B2", 1_000_000,
                spread=0.04, floor=0.01, maturity=5, price=0.95)
    rows = []
    for repayment in (0.0, 0.20):
        schedule = loan_schedule(loan, np.full(20, 0.005), prepayment=repayment)
        schedule.to_csv(output / f"loan_schedule_{int(repayment * 100)}.csv", index=False)
        rows.append({"annual_prepayment": repayment, "purchase_cost": loan.purchase_cost,
                     "first_interest": schedule.interest.iloc[0],
                     "total_interest": schedule.interest.sum(), "total_principal": schedule.principal.sum(),
                     "principal_life": float((schedule.time * schedule.principal).sum() / loan.par)})
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "loan_comparison.csv", index=False)
    (output / "loan_comparison.md").write_text(
        "# Synthetic loan mechanics\n\n" + markdown_table(frame), encoding="utf-8")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
