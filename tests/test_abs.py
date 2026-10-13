from dataclasses import replace
import unittest
import numpy as np
import pandas as pd
import _support
from clo_engine import (AutoPool, ABSScenario, auto_schedule, auto_structure,
                        run_abs, abs_scenarios, abs_break_even_cnl, level_payment)


class ABSTests(unittest.TestCase):
    def setUp(self):
        self.pool = AutoPool(par=100_000)
        self.structure = auto_structure(self.pool.par)

    def test_level_pay_balance_matches_closed_form_every_month(self):
        schedule = auto_schedule(self.pool, ABSScenario(annual_default_curve=0, abs_speed=0))
        rate = self.pool.annual_rate / 12
        payment = level_payment(self.pool.par, self.pool.annual_rate, self.pool.months)
        for row in schedule.itertuples():
            growth = (1 + rate) ** row.month
            expected = self.pool.par * growth - payment * (growth - 1) / rate
            self.assertAlmostEqual(row.closing_par, expected, places=6)
            self.assertAlmostEqual(row.collateral_interest + row.amortization, payment, places=6)

    def test_absolute_speed_removes_original_count(self):
        schedule = auto_schedule(self.pool, ABSScenario(annual_default_curve=0, abs_speed=.01))
        np.testing.assert_allclose(schedule.prepaid_count.iloc[:59], 100)
        self.assertEqual(schedule.surviving_count.iloc[1], 9800)
        self.assertEqual(schedule.prepaid_count.iloc[-1], 0)

    def test_high_absolute_speed_cannot_overdraw_count(self):
        schedule = auto_schedule(self.pool, ABSScenario(annual_default_curve=0, abs_speed=1))
        self.assertEqual(schedule.surviving_count.iloc[0], 0)
        self.assertTrue((schedule.closing_par >= 0).all())

    def test_cash_collateral_and_debt_conservation_all_scenarios(self):
        for scenario in abs_scenarios():
            result = run_abs(self.pool, self.structure, scenario)
            self.assertLess(result.ledger.reconciliation_error.abs().max(), 1e-8)
            self.assertLess(result.ledger.collateral_reconciliation.abs().max(), 1e-8)
            opening_reserve = np.r_[self.structure.reserve_fraction * self.pool.par,
                                    result.ledger.reserve.to_numpy()[:-1]]
            cash_in = result.ledger.collateral_interest + result.ledger.collateral_principal + opening_reserve
            cash_out = (result.interest.sum(axis=1) + result.principal.sum(axis=1)
                        + result.ledger.fee_paid + result.ledger.residual + result.ledger.reserve)
            np.testing.assert_allclose(cash_in, cash_out, rtol=0, atol=1e-8)
            notionals = np.array([x.notional for x in self.structure.tranches])
            np.testing.assert_allclose(result.principal.sum(axis=0) + result.losses.sum(axis=0)
                                       + result.ending_balances, notionals, atol=1e-8)
            self.assertEqual(result.ledger.reserve.iloc[-1], 0)

    def test_cnl_trigger_latches_and_switches_mode(self):
        result = run_abs(self.pool, self.structure, abs_scenarios()[1])
        breach = result.ledger.trigger_breach.to_numpy()
        first = np.flatnonzero(breach)[0]
        self.assertGreater(first, 0)
        self.assertTrue(breach[first:].all())
        self.assertTrue((result.ledger.principal_mode.iloc[:first] == "pro_rata").all())
        self.assertTrue((result.ledger.principal_mode.iloc[first:] == "sequential").all())
        self.assertLess(result.ledger.cumulative_net_loss.iloc[first - 1], self.structure.loss_trigger)
        self.assertGreaterEqual(result.ledger.cumulative_net_loss.iloc[first], self.structure.loss_trigger)

    def test_sequential_option_never_pro_rata(self):
        result = run_abs(self.pool, replace(self.structure, pro_rata=False))
        self.assertTrue((result.ledger.principal_mode == "sequential").all())

    def test_zero_defaults_no_principal_loss(self):
        result = run_abs(self.pool, self.structure, ABSScenario(annual_default_curve=0))
        self.assertAlmostEqual(result.losses.sum(), 0)
        self.assertAlmostEqual(result.ending_balances.sum(), 0)

    def test_bottom_up_loss_on_total_default(self):
        result = run_abs(self.pool, self.structure, ABSScenario(annual_default_curve=1, severity_curve=1))
        np.testing.assert_allclose(result.losses.sum(axis=0)[1:],
                                   [x.notional for x in self.structure.tranches[1:]])
        self.assertGreater(result.losses.sum(axis=0)[0], 0)
        self.assertTrue((result.principal >= 0).all())

    def test_determinism(self):
        pd.testing.assert_frame_equal(run_abs(self.pool).ledger, run_abs(self.pool).ledger)

    def test_stress_losses_monotone(self):
        loss = np.array([run_abs(self.pool, self.structure, s).losses.sum(axis=0)
                         for s in abs_scenarios()])
        self.assertTrue((np.diff(loss, axis=0) >= -1e-8).all())

    def test_fixed_family_first_loss_indicator_is_monotone(self):
        loss = np.array([run_abs(self.pool, self.structure,
                                ABSScenario(annual_default_curve=rate, severity_curve=.8)).losses.sum(axis=0)
                         for rate in np.linspace(0, 1, 15)])
        self.assertTrue((np.diff((loss > self.pool.par * 1e-10).astype(int), axis=0) >= 0).all())

    def test_break_even_boundary_straddles_first_loss(self):
        template = ABSScenario(severity_curve=.8)
        boundaries = abs_break_even_cnl(self.pool, self.structure, template)
        values = boundaries.break_even_cumulative_net_loss.to_numpy()
        self.assertTrue((np.diff(values) <= 1e-8).all())
        for index, row in enumerate(boundaries.itertuples()):
            rate = .025 * row.default_curve_multiplier
            below = run_abs(self.pool, self.structure, replace(template, annual_default_curve=rate * (1 - 1e-5)))
            above = run_abs(self.pool, self.structure, replace(template, annual_default_curve=rate * (1 + 1e-5)))
            self.assertLessEqual(below.losses[:, index].sum(), row.loss_tolerance)
            self.assertGreater(above.losses[:, index].sum(), row.loss_tolerance)

    def test_unreachable_boundary_is_nan(self):
        rows = abs_break_even_cnl(self.pool, self.structure, ABSScenario(severity_curve=0))
        self.assertTrue(rows.break_even_cumulative_net_loss.isna().all())

    def test_scenario_family_boundaries_and_impairment_grids(self):
        for template in abs_scenarios():
            shape = np.array(template.annual_default_curve)
            upper = 1 / shape.min()
            impairment = []
            for scale in np.linspace(0, upper, 15):
                result = run_abs(self.pool, self.structure,
                                 replace(template, annual_default_curve=tuple(np.minimum(1, shape * scale))))
                impairment.append(result.losses.sum(axis=0) > self.pool.par * 1e-10)
            self.assertTrue((np.diff(np.array(impairment).astype(int), axis=0) >= 0).all())
            boundaries = abs_break_even_cnl(self.pool, self.structure, template)
            for index, row in enumerate(boundaries.itertuples()):
                for direction, expected in [(1 - 1e-5, False), (1 + 1e-5, True)]:
                    result = run_abs(self.pool, self.structure, replace(
                        template, annual_default_curve=tuple(np.minimum(1, shape * row.default_curve_multiplier * direction))))
                    self.assertEqual(result.losses[:, index].sum() > row.loss_tolerance, expected)

    def test_default_survival_and_severity_hand_calculation(self):
        schedule = auto_schedule(self.pool, ABSScenario(annual_default_curve=.12, severity_curve=.6, abs_speed=0))
        expected = self.pool.par * (1 - .88 ** (1 / 12))
        self.assertAlmostEqual(schedule.defaulted_par.iloc[0], expected)
        self.assertAlmostEqual(schedule.credit_loss.iloc[0], expected * .6)
        self.assertAlmostEqual(schedule.recovery.iloc[0], expected * .4)

    def test_invalid_curve_rejected(self):
        for value in [(0.1,), float("nan"), -0.1, 1.1]:
            with self.assertRaises(ValueError):
                run_abs(self.pool, scenario=ABSScenario(annual_default_curve=value))
