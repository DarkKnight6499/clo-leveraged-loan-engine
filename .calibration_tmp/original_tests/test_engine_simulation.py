from dataclasses import replace
import math
import unittest
import numpy as np
import _support
from clo_engine import (
    synthetic_portfolio, illustrative_structure, run_deal, monte_carlo,
    break_even_default_rate, stress_table, sofr_curve,
)


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loans = synthetic_portfolio(count=30, total_par=10_000_000)
        cost = sum(x.purchase_cost for x in cls.loans)
        cls.structure = replace(illustrative_structure(10_000_000, cost),
                                admin_expense=4000, admin_cap=5000)
        cls.base = run_deal(cls.loans, cls.structure)

    def test_cash_conservation_every_period_and_stress(self):
        for rate in [0, 0.10, 0.50, 1]:
            result = run_deal(self.loans, self.structure, annual_default_rate=rate, recovery=0.30)
            np.testing.assert_allclose(result.ledger.reconciliation_error, 0, atol=1e-7)

    def test_collateral_conservation_every_period(self):
        result = run_deal(self.loans, self.structure, annual_default_rate=0.10)
        np.testing.assert_allclose(result.ledger.collateral_reconciliation, 0, atol=1e-7)

    def test_tranche_principal_reconciles(self):
        initial = np.array([x.notional for x in self.structure.tranches])
        np.testing.assert_allclose(self.base.principal.sum(axis=0) + self.base.ending_balances, initial)

    def test_tranche_balances_never_negative(self):
        for tranche in self.structure.tranches:
            self.assertTrue((self.base.ledger[f"{tranche.name}_balance"] >= 0).all())

    def test_zero_defaults_no_loss(self):
        np.testing.assert_allclose(self.base.ending_balances, 0, atol=1e-7)
        self.assertEqual(self.base.ledger.defaulted_par.sum(), 0)

    def test_reinvestment_par_build(self):
        rows = self.base.ledger[self.base.ledger.reinvestment_cash > 0]
        np.testing.assert_allclose(rows.purchased_par * self.structure.reinvestment_price,
                                   rows.reinvestment_cash)
        self.assertTrue((rows.purchased_par > rows.reinvestment_cash).all())

    def test_reinvestment_stops(self):
        later = self.base.ledger[self.base.ledger.time > self.structure.reinvestment_years]
        self.assertEqual(later.reinvestment_cash.sum(), 0)

    def test_final_collateral_zero(self):
        self.assertAlmostEqual(self.base.ledger.closing_par.iloc[-1], 0)

    def test_total_default_no_recovery_total_loss(self):
        result = run_deal(self.loans, self.structure, annual_default_rate=1, recovery=0)
        self.assertEqual(result.equity_irr, -1)
        self.assertEqual(result.principal.sum(), 0)
        self.assertAlmostEqual(result.ledger.credit_loss.sum(), 10_000_000)

    def test_no_reinvestment_no_default_principal_conservation(self):
        structure = replace(self.structure, reinvestment_years=0)
        result = run_deal(self.loans, structure, prepayment=0)
        self.assertAlmostEqual(result.ledger.collateral_principal.sum(), 10_000_000, places=5)

    def test_stochastic_seed_reproduces(self):
        first = run_deal(self.loans, self.structure, annual_default_rate=None, rng=np.random.default_rng(1))
        second = run_deal(self.loans, self.structure, annual_default_rate=None, rng=np.random.default_rng(1))
        np.testing.assert_array_equal(first.equity, second.equity)
        np.testing.assert_array_equal(first.principal, second.principal)

    def test_stochastic_requires_explicit_generator(self):
        with self.assertRaises(ValueError):
            run_deal(self.loans, self.structure, annual_default_rate=None)

    def test_curve_shape_rejected(self):
        with self.assertRaises(ValueError):
            run_deal(self.loans, self.structure, curve=np.zeros(2))

    def test_invalid_correlation(self):
        with self.assertRaises(ValueError):
            run_deal(self.loans, self.structure, correlation=1)

    def test_funding_reconciles_purchase_cost(self):
        self.assertAlmostEqual(self.structure.equity + sum(x.notional for x in self.structure.tranches),
                               sum(x.purchase_cost for x in self.loans))

    def test_payment_dates_quarterly(self):
        dates = self.structure.payment_dates()
        self.assertEqual(str(dates[0]), "2026-04-01")
        self.assertEqual(str(dates[3]), "2027-01-01")
        self.assertEqual(len(dates), self.structure.periods)

    def test_invalid_structure(self):
        with self.assertRaises(ValueError):
            replace(self.structure, reinvestment_years=10)

    def test_borrower_facilities_default_together(self):
        first = replace(self.loans[0], par=5_000_000, rating="Caa3", borrower="same")
        second = replace(first, spread=0.08)
        structure = replace(self.structure, reinvestment_years=0)
        result = run_deal([first, second], structure, prepayment=0, annual_default_rate=None,
                          rng=np.random.default_rng(42))
        defaults = result.ledger.defaulted_par
        nonzero = result.ledger[defaults > 0]
        self.assertEqual(len(nonzero), 1)
        self.assertAlmostEqual(nonzero.defaulted_par.iloc[0], nonzero.opening_par.iloc[0])

    def test_conflicting_borrower_ratings_rejected(self):
        first = self.loans[0]
        second = replace(first, rating="B3" if first.rating != "B3" else "B1")
        with self.assertRaises(ValueError):
            run_deal([first, second], self.structure)


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loans = synthetic_portfolio(count=25, total_par=10_000_000)
        cls.structure = replace(illustrative_structure(10_000_000), admin_expense=4000, admin_cap=5000)
        cls.thresholds = [break_even_default_rate(cls.loans, cls.structure, x.name)
                          for x in cls.structure.tranches]

    def test_break_even_monotone_seniority(self):
        self.assertTrue(all(math.isfinite(x) for x in self.thresholds))
        self.assertTrue(all(a > b for a, b in zip(self.thresholds, self.thresholds[1:])))

    def test_break_even_brackets_actual_loss(self):
        for tranche, boundary in zip(self.structure.tranches, self.thresholds):
            slot = list(self.structure.tranches).index(tranche)
            below = run_deal(self.loans, self.structure, annual_default_rate=boundary - 2e-6, recovery=0.4)
            above = run_deal(self.loans, self.structure, annual_default_rate=boundary + 2e-6, recovery=0.4)
            self.assertLess(below.ending_balances[slot] / tranche.notional, 1e-8)
            self.assertGreater(above.ending_balances[slot] / tranche.notional, 1e-8)

    def test_constant_cdr_loss_monotonic_grid(self):
        previous = np.zeros(5)
        for rate in np.linspace(0, 1, 21):
            result = run_deal(self.loans, self.structure, annual_default_rate=float(rate), recovery=0.4)
            self.assertTrue((result.ending_balances + 1e-6 >= previous).all())
            previous = result.ending_balances

    def test_zero_default_loss_probability_zero(self):
        result = monte_carlo(self.loans, self.structure, paths=8, default_multiplier=0)
        self.assertEqual(result.tranches.loss_probability.sum(), 0)
        self.assertEqual(result.tranches.expected_principal_loss.sum(), 0)

    def test_mc_expected_loss_reconciles_raw_paths(self):
        result = monte_carlo(self.loans, self.structure, paths=12, default_multiplier=4)
        for row in result.tranches.itertuples(index=False):
            class_name = result.tranches.loc[result.tranches.rating_label == row.rating_label, "class"].iloc[0]
            self.assertAlmostEqual(row.expected_principal_loss, result.paths[f"{class_name}_loss"].mean())
            self.assertAlmostEqual(row.oc_breach_probability, result.paths[f"{class_name}_oc_breach"].mean())

    def test_mc_quantiles_ordered_and_bounded(self):
        result = monte_carlo(self.loans, self.structure, paths=8)
        row = result.equity.iloc[0]
        self.assertLessEqual(row.irr_p05, row.irr_median)
        self.assertLessEqual(row.irr_median, row.irr_p95)
        self.assertTrue((result.paths.equity_irr >= -1).all())

    def test_stress_grid_dimensions(self):
        table = stress_table(self.loans, self.structure, (0, 0.1), (0.3, 0.7))
        self.assertEqual(len(table), 4)
        self.assertTrue((table.cash_reconciliation_max < 1e-7).all())

    def test_unreachable_break_even_returns_nan(self):
        loans = [replace(x, price=1, amortization=0) for x in self.loans]
        structure = replace(self.structure, reinvestment_years=0, senior_fee=0, subordinated_fee=0,
                            admin_expense=0, admin_cap=0)
        self.assertTrue(math.isnan(break_even_default_rate(loans, structure, "A", recovery=1)))

    def test_bad_class_rejected(self):
        with self.assertRaises(ValueError):
            break_even_default_rate(self.loans, self.structure, "unknown")
