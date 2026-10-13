from dataclasses import replace
import unittest
import _support
from clo_engine import (AutoPool, run_abs, auto_structure, run_cmbs, synthetic_mortgages,
                        illustrative_structure, synthetic_portfolio, run_deal, comparison_table)


class ComparisonTests(unittest.TestCase):
    def test_common_columns_and_subordination(self):
        pool = AutoPool(par=100_000)
        abs_result = run_abs(pool)
        loans = synthetic_mortgages(count=5, total_par=100_000)
        cmbs_result = run_cmbs(loans)
        clo_result = run_deal(synthetic_portfolio(), illustrative_structure())
        table = comparison_table({"CLO": (clo_result, clo_result),
                                  "ABS": (abs_result, abs_result), "CMBS": (cmbs_result, cmbs_result)},
                                 {"CLO": 500_000_000, "ABS": pool.par, "CMBS": 100_000})
        self.assertEqual(list(table.asset_type), ["CLO", "ABS", "CMBS"])
        for row, expected in zip(table.itertuples(), [.14, .08, .08]):
            self.assertAlmostEqual(row.subordination, expected)
            self.assertAlmostEqual(row.base_loss_fraction, row.stress_loss_fraction)
            self.assertGreaterEqual(row.base_loss_fraction, 0)

    def test_different_structures_rejected(self):
        pool = AutoPool(par=100_000)
        base = run_abs(pool)
        stress = run_abs(pool, replace(auto_structure(pool.par), pro_rata=False))
        with self.assertRaises(ValueError):
            comparison_table({"ABS": (base, stress)}, {"ABS": pool.par})
