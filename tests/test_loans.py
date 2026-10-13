import unittest
import numpy as np
import _support
from clo_engine.loans import Loan, loan_schedule, synthetic_portfolio, sofr_curve
from clo_engine.numerics import period_probability


class LoanTests(unittest.TestCase):
    def setUp(self):
        self.loan = Loan("Borrower", "Software", "B2", 100, spread=0.04, floor=0.01,
                         maturity=2, amortization=0.01, price=0.95)

    def test_coupon_floor_hand_calculation(self):
        self.assertAlmostEqual(self.loan.coupon(0.005) * 100 * 0.25, 1.25)

    def test_coupon_above_floor(self):
        self.assertAlmostEqual(self.loan.coupon(0.03), 0.07)

    def test_negative_benchmark_floor(self):
        self.assertAlmostEqual(self.loan.coupon(-0.01), 0.05)

    def test_coupon_monotone(self):
        coupons = [self.loan.coupon(x) for x in [-0.01, 0, 0.01, 0.02, 0.05]]
        self.assertEqual(coupons, sorted(coupons))

    def test_purchase_at_discount(self):
        self.assertAlmostEqual(self.loan.purchase_cost, 95)

    def test_amortization_schedule_sums(self):
        schedule = loan_schedule(self.loan, np.full(8, 0.03))
        self.assertAlmostEqual(schedule.principal.sum(), 100)
        self.assertAlmostEqual(schedule.amortization.sum(), 2)
        self.assertAlmostEqual(schedule.balloon.sum(), 98)

    def test_schedule_first_interest_hand_calculation(self):
        schedule = loan_schedule(self.loan, np.full(8, 0.03))
        self.assertAlmostEqual(schedule.interest.iloc[0], 1.75)

    def test_schedule_conservation_every_period(self):
        schedule = loan_schedule(self.loan, np.full(8, 0.03), prepayment=0.20)
        np.testing.assert_allclose(schedule.opening - schedule.principal, schedule.closing)

    def test_prepayment_conversion(self):
        q = period_probability(0.20)
        self.assertAlmostEqual((1 - q) ** 4, 0.80)

    def test_prepayment_shortens_life(self):
        slow = loan_schedule(self.loan, np.full(8, 0.03))
        fast = loan_schedule(self.loan, np.full(8, 0.03), prepayment=0.30)
        self.assertLess((fast.time * fast.principal).sum(), (slow.time * slow.principal).sum())

    def test_full_prepayment(self):
        schedule = loan_schedule(self.loan, np.full(8, 0.03), prepayment=1)
        self.assertEqual(len(schedule), 1)
        self.assertAlmostEqual(schedule.principal.sum(), 100)

    def test_no_amortization_bullet(self):
        loan = Loan("Bullet", "Food", "B1", 100, amortization=0, maturity=1)
        schedule = loan_schedule(loan, np.full(4, 0.03))
        self.assertEqual(schedule.principal.tolist(), [0, 0, 0, 100])

    def test_short_curve_rejected(self):
        with self.assertRaises(ValueError):
            loan_schedule(self.loan, np.full(2, 0.03))

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            Loan("Invalid", "Food", "B1", float("nan"))

    def test_unsupported_rating(self):
        with self.assertRaises(ValueError):
            Loan("Invalid", "Food", "AAA", 100)

    def test_invalid_probability(self):
        with self.assertRaises(ValueError):
            loan_schedule(self.loan, np.full(8, 0.03), prepayment=-0.01)

    def test_seed_reproduces(self):
        self.assertEqual(synthetic_portfolio(), synthetic_portfolio())
        self.assertNotEqual(synthetic_portfolio(seed=1), synthetic_portfolio(seed=2))

    def test_synthetic_par_and_industries(self):
        loans = synthetic_portfolio()
        self.assertEqual(len(loans), 150)
        self.assertEqual(len({x.industry for x in loans}), 25)
        self.assertAlmostEqual(sum(x.par for x in loans), 500_000_000, places=5)

    def test_curve_scenarios_ordered(self):
        self.assertTrue((sofr_curve(scenario="up") >= sofr_curve()).all())
        self.assertTrue((sofr_curve(scenario="down") <= sofr_curve()).all())
        self.assertTrue((sofr_curve(scenario="down") >= 0).all())

    def test_curve_invalid_scenario(self):
        with self.assertRaises(ValueError):
            sofr_curve(scenario="unknown")
