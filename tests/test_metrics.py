from dataclasses import replace
import unittest
import numpy as np
import _support
from clo_engine.loans import Loan
from clo_engine.metrics import (
    portfolio_metrics, concentration_tests, diversity_score,
    industry_diversity_units, ccc_adjustment,
)


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.loans = [Loan("a", "Food", "B1", 100, spread=0.03, floor=0.02, recovery=0.6),
                      Loan("b", "Software", "B2", 200, spread=0.04, floor=0.01, recovery=0.7),
                      Loan("c", "Retail", "Caa1", 100, spread=0.06, floor=0, recovery=0.4, price=0.6)]

    def test_warf_three_loan_hand_case(self):
        metrics = portfolio_metrics(self.loans)
        self.assertEqual(metrics["warf_unrounded"], (2220 + 2 * 2720 + 4770) / 4)
        self.assertEqual(metrics["warf"], 3108)

    def test_was_with_floor_hand_case(self):
        metrics = portfolio_metrics(self.loans, sofr=0.005)
        self.assertAlmostEqual(metrics["was"], (0.045 + 2 * 0.045 + 0.06) / 4)

    def test_was_no_floor_adjustment(self):
        self.assertAlmostEqual(portfolio_metrics(self.loans, sofr=0.04)["was"], 0.0425)

    def test_warr_hand_case(self):
        self.assertAlmostEqual(portfolio_metrics(self.loans)["warr"], (0.6 + 1.4 + 0.4) / 4)

    def test_wal_bullet(self):
        loans = [replace(x, amortization=0, maturity=m) for x, m in zip(self.loans, [2, 4, 6])]
        self.assertAlmostEqual(portfolio_metrics(loans)["wal"], 4)

    def test_ccc_excess_haircut_hand_case(self):
        share, haircut = ccc_adjustment(np.array([80, 10, 10]), np.array([1, 0.4, 0.8]),
                                       np.array([False, True, True]), 0.075)
        self.assertAlmostEqual(share, 0.2)
        self.assertAlmostEqual(haircut, 10 * 0.6 + 2.5 * 0.2)

    def test_ccc_below_limit(self):
        self.assertEqual(ccc_adjustment(np.array([95, 5]), np.array([1, 0.5]),
                                        np.array([False, True]))[1], 0)

    def test_ccc_haircut_monotone_price(self):
        amounts, flags = np.array([80, 20]), np.array([False, True])
        low = ccc_adjustment(amounts, np.array([1, 0.3]), flags)[1]
        high = ccc_adjustment(amounts, np.array([1, 0.8]), flags)[1]
        self.assertGreater(low, high)

    def test_ccc_no_negative_haircut(self):
        self.assertEqual(ccc_adjustment(np.array([100]), np.array([1.1]), np.array([True]))[1], 0)

    def test_ccc_zero_balance(self):
        self.assertEqual(ccc_adjustment(np.zeros(2), np.ones(2), np.ones(2, bool)), (0, 0))

    def test_ccc_invalid_shape(self):
        with self.assertRaises(ValueError):
            ccc_adjustment(np.ones(2), np.ones(1), np.ones(2, bool))

    def test_diversity_single_borrower_is_one(self):
        loans = [replace(x, borrower="same", industry="Food") for x in self.loans]
        self.assertAlmostEqual(diversity_score(loans), 1)

    def test_diversity_even_distinct_industries_count(self):
        self.assertEqual(diversity_score([replace(x, par=100) for x in self.loans]), 3)

    def test_diversity_same_industry_published_result(self):
        loans = [replace(x, par=100, industry="Food") for x in self.loans]
        self.assertEqual(diversity_score(loans), 2)
        self.assertEqual(portfolio_metrics(loans)["industry_effective_count"], 1)

    def test_diversity_lower_row_no_interpolation(self):
        self.assertEqual(industry_diversity_units(1.04), 1)
        self.assertEqual(industry_diversity_units(1.05), 1.05)
        self.assertEqual(industry_diversity_units(3.05), 2.0333)

    def test_diversity_table_segments(self):
        for units, expected in [(5.95, 3), (6.05, 3.025), (9.95, 4), (10.05, 4.01), (19.95, 5)]:
            with self.subTest(units=units):
                self.assertEqual(industry_diversity_units(units), expected)

    def test_diversity_loan_split_invariant(self):
        split = [replace(self.loans[0], par=50), replace(self.loans[0], par=50), *self.loans[1:]]
        self.assertEqual(diversity_score(split), diversity_score(self.loans))

    def test_diversity_inconsistent_industry_rejected(self):
        with self.assertRaises(ValueError):
            diversity_score([self.loans[0], replace(self.loans[1], borrower="a")])

    def test_metrics_scale_invariant(self):
        first = portfolio_metrics(self.loans)
        second = portfolio_metrics([replace(x, par=x.par * 10) for x in self.loans])
        for key in ["warf", "was", "warr", "wal", "ccc_share", "diversity_score"]:
            self.assertAlmostEqual(first[key], second[key])

    def test_purchase_par_build(self):
        metrics = portfolio_metrics(self.loans)
        self.assertAlmostEqual(metrics["par_build"], 40)
        self.assertAlmostEqual(metrics["purchase_cost"] + metrics["par_build"], metrics["par"])

    def test_concentration_aggregates_borrowers(self):
        loans = [replace(x, borrower="same") for x in self.loans]
        table = concentration_tests(loans).set_index("metric")
        self.assertEqual(table.loc["largest_obligor", "actual"], 1)
        self.assertFalse(table.loc["largest_obligor", "passes"])

    def test_concentration_second_lien_and_covlite(self):
        loans = [replace(self.loans[0], second_lien=True), *self.loans[1:]]
        table = concentration_tests(loans).set_index("metric")
        self.assertEqual(table.loc["second_lien", "actual"], 0.25)
        self.assertEqual(table.loc["cov_lite", "actual"], 1)

    def test_empty_portfolio_rejected(self):
        with self.assertRaises(ValueError):
            portfolio_metrics([])
