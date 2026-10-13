import math
import unittest
import numpy as np
import _support
from clo_engine.numerics import bisect_root, normal_cdf, normal_quantile
from clo_engine.valuation import discounted_value, discount_margin, equity_irr, cash_multiple


class NumericsTests(unittest.TestCase):
    def test_bisection_sqrt_two(self):
        self.assertAlmostEqual(bisect_root(lambda x: x * x - 2, 0, 2), math.sqrt(2), places=9)

    def test_bisection_endpoint(self):
        self.assertEqual(bisect_root(lambda x: x - 1, 1, 3), 1)

    def test_bisection_bad_bracket(self):
        with self.assertRaises(ValueError):
            bisect_root(lambda x: x * x + 1, -1, 1)

    def test_bisection_nonfinite(self):
        with self.assertRaises(ValueError):
            bisect_root(lambda x: float("nan"), 0, 1)

    def test_bisection_iteration_limit(self):
        with self.assertRaises(RuntimeError):
            bisect_root(lambda x: x * x - 2, 0, 2, max_iterations=1)

    def test_normal_cdf_symmetry_and_center(self):
        self.assertEqual(normal_cdf(0), 0.5)
        self.assertAlmostEqual(normal_cdf(-1) + normal_cdf(1), 1)

    def test_normal_cdf_benchmark(self):
        self.assertAlmostEqual(normal_cdf(1), 0.8413447460685429, places=14)

    def test_quantile_round_trip(self):
        for p in [0.0001, 0.01, 0.5, 0.99, 0.9999]:
            with self.subTest(p=p):
                self.assertAlmostEqual(normal_cdf(normal_quantile(p)), p, places=10)

    def test_quantile_boundaries(self):
        self.assertEqual(normal_quantile(0), -math.inf)
        self.assertEqual(normal_quantile(1), math.inf)
        with self.assertRaises(ValueError):
            normal_quantile(1.01)


class ValuationTests(unittest.TestCase):
    def test_par_floater_analytic(self):
        curve = np.array([0.02, 0.03, 0.01, 0.04])
        cash = 100 * (curve + 0.015) * 0.25
        cash[-1] += 100
        self.assertAlmostEqual(discounted_value(cash, curve, 0.015), 100)

    def test_dcf_additivity(self):
        curve = np.full(4, 0.03)
        first, second = np.array([1, 1, 1, 100]), np.array([0, 5, 3, 20])
        self.assertAlmostEqual(discounted_value(first + second, curve, 0.01),
                               discounted_value(first, curve, 0.01) + discounted_value(second, curve, 0.01))

    def test_dcf_margin_monotonic(self):
        cash, curve = np.array([2, 2, 2, 102]), np.full(4, 0.03)
        self.assertGreater(discounted_value(cash, curve, 0.01), discounted_value(cash, curve, 0.02))

    def test_discount_margin_round_trip(self):
        curve = np.array([0.01, 0.02, 0.03, 0.04])
        cash = np.array([1, 2, 3, 103])
        for margin in [-0.01, 0.015, 0.10]:
            with self.subTest(margin=margin):
                price = discounted_value(cash, curve, margin)
                self.assertAlmostEqual(discount_margin(cash, curve, price), margin, places=8)

    def test_discount_margin_requires_positive_price(self):
        with self.assertRaises(ValueError):
            discount_margin(np.ones(4), np.zeros(4), 0)

    def test_discount_margin_near_factor_boundary(self):
        cash, curve = np.array([1, 1, 1, 100]), np.full(4, 0.01)
        margin = -3.99
        price = discounted_value(cash, curve, margin)
        self.assertAlmostEqual(discount_margin(cash, curve, price), margin, places=8)

    def test_dcf_bad_shapes(self):
        with self.assertRaises(ValueError):
            discounted_value(np.ones(4), np.zeros(3), 0.01)

    def test_dcf_invalid_discount_factor(self):
        with self.assertRaises(ValueError):
            discounted_value(np.ones(4), np.zeros(4), -4)

    def test_equity_irr_annual_benchmark(self):
        self.assertAlmostEqual(equity_irr(100, np.array([0, 0, 0, 110])), 0.10, places=8)

    def test_equity_irr_quarterly_annualization(self):
        self.assertAlmostEqual(equity_irr(100, np.array([105])), 1.05 ** 4 - 1, places=8)

    def test_equity_irr_discount_reconciliation(self):
        cash = np.array([10, 15, 20, 90])
        irr = equity_irr(100, cash)
        value = np.sum(cash / (1 + irr) ** (np.arange(1, 5) * 0.25))
        self.assertAlmostEqual(value, 100, places=7)

    def test_equity_total_loss(self):
        self.assertEqual(equity_irr(100, np.zeros(4)), -1)
        self.assertEqual(cash_multiple(100, np.zeros(4)), 0)

    def test_equity_negative_return(self):
        self.assertAlmostEqual(equity_irr(100, np.array([0, 0, 0, 50])), -0.5, places=8)

    def test_equity_negative_distribution_rejected(self):
        with self.assertRaises(ValueError):
            equity_irr(100, np.array([-1, 110]))

    def test_multiple_hand_calculation(self):
        self.assertAlmostEqual(cash_multiple(100, np.array([10, 20, 150])), 1.8)
