from dataclasses import replace
from datetime import date
import unittest
import numpy as np
import pandas as pd
import _support
from clo_engine import (Mortgage, CMBSScenario, synthetic_mortgages, conduit_structure,
                        run_cmbs, cmbs_scenarios)


class CMBSTests(unittest.TestCase):
    def setUp(self):
        self.loan = Mortgage("M1", "office", 100_000, .06, 1.5, .65, date(2027, 1, 1), 12)
        self.safe = CMBSScenario(annual_default_rate=0, minimum_refi_dscr=0, maximum_refi_ltv=10)

    def test_io_balloon_and_coupon(self):
        result = run_cmbs([self.loan], scenario=self.safe)
        self.assertEqual(result.ledger.amortization.sum(), 0)
        self.assertEqual(result.ledger.balloon.iloc[11], self.loan.par)
        np.testing.assert_allclose(result.ledger.collateral_interest.iloc[:12], 500)
        self.assertEqual(result.losses.sum(), 0)

    def test_amortizing_balloon(self):
        result = run_cmbs([replace(self.loan, io_months=0)], scenario=self.safe)
        self.assertGreater(result.ledger.amortization.sum(), 0)
        self.assertLess(result.ledger.balloon.sum(), self.loan.par)
        self.assertAlmostEqual(result.ledger.amortization.sum() + result.ledger.balloon.sum(), self.loan.par)

    def test_refinance_failure_defaults_at_maturity(self):
        scenario = replace(self.safe, minimum_refi_dscr=100, extension_probability=0)
        result = run_cmbs([self.loan], scenario=scenario)
        event = result.events[result.events.event == "balloon_default"].iloc[0]
        self.assertEqual(event.month, 12)
        self.assertEqual(event.balance, self.loan.par)

    def test_ltv_test_alone_causes_default(self):
        scenario = replace(self.safe, maximum_refi_ltv=.1, extension_probability=0)
        result = run_cmbs([self.loan], scenario=scenario)
        self.assertEqual(result.events.event.iloc[0], "balloon_default")

    def test_special_servicing_recovery_and_loss_lag(self):
        scenario = replace(self.safe, minimum_refi_dscr=100, extension_probability=0,
                           loss_severity=.4, servicing_lag_months=3)
        result = run_cmbs([self.loan], scenario=scenario)
        self.assertEqual(result.ledger.recovery.iloc[11], 0)
        self.assertEqual(result.ledger.special_servicing_par.iloc[11], self.loan.par)
        self.assertEqual(result.ledger.recovery.iloc[14], 60_000)
        self.assertEqual(result.ledger.credit_loss.iloc[14], 40_000)
        self.assertEqual(result.ledger.collateral_interest.iloc[12:].sum(), 0)

    def test_extension_once_then_default(self):
        scenario = replace(self.safe, minimum_refi_dscr=100, extension_probability=1, extension_months=6)
        result = run_cmbs([self.loan], scenario=scenario)
        extension = result.events[result.events.event == "extension"]
        default = result.events[result.events.event == "extension_default"]
        self.assertEqual(list(extension.month), [12])
        self.assertEqual(list(default.month), [18])
        self.assertEqual(result.ledger.special_servicing_par.iloc[-1], 0)

    def test_zero_lag_recovers_on_default_date(self):
        result = run_cmbs([self.loan], scenario=replace(self.safe, annual_default_rate=1,
                                                       servicing_lag_months=0))
        self.assertEqual(result.ledger.recovery.iloc[0], 65_000)

    def test_realized_losses_bottom_up(self):
        result = run_cmbs([self.loan], scenario=replace(self.safe, annual_default_rate=1, loss_severity=.2))
        np.testing.assert_allclose(result.losses.sum(axis=0), [0, 0, 7000, 5000, 3000, 5000])
        self.assertAlmostEqual(result.losses.sum(), result.ledger.credit_loss.sum())

    def test_interest_shortfalls_carried_and_reported(self):
        result = run_cmbs([self.loan], scenario=replace(self.safe, annual_default_rate=1))
        self.assertGreater(result.unpaid_interest.sum(), 0)
        self.assertGreater(result.ledger.A_interest_shortfall.max(), 0)

    def test_cash_collateral_and_debt_conservation(self):
        loans = synthetic_mortgages(count=20, total_par=1_000_000)
        for scenario in cmbs_scenarios():
            result = run_cmbs(loans, scenario=scenario)
            self.assertLess(result.ledger.reconciliation_error.abs().max(), 1e-8)
            self.assertLess(result.ledger.collateral_reconciliation.abs().max(), 1e-8)
            cash_in = result.ledger.collateral_interest + result.ledger.collateral_principal
            cash_out = (result.interest.sum(axis=1) + result.principal.sum(axis=1)
                        + result.ledger.fee_paid + result.ledger.residual)
            np.testing.assert_allclose(cash_in, cash_out, rtol=0, atol=1e-8)
            np.testing.assert_allclose(result.principal.sum(axis=0) + result.losses.sum(axis=0)
                                       + result.ending_balances,
                                       [x.notional for x in result.structure.tranches], atol=1e-8)
            self.assertEqual(result.ledger.special_servicing_par.iloc[-1], 0)
            self.assertEqual(result.ledger.closing_par.iloc[-1], 0)
            self.assertAlmostEqual(result.losses.sum(), result.ledger.credit_loss.sum())
            self.assertEqual(result.ledger.turbo.sum(), 0)

    def test_seed_determinism_pool_and_path(self):
        loans = synthetic_mortgages(count=10)
        self.assertEqual(loans, synthetic_mortgages(count=10))
        self.assertNotEqual(loans, synthetic_mortgages(count=10, seed=1))
        pd.testing.assert_frame_equal(run_cmbs(loans, seed=42).ledger, run_cmbs(loans, seed=42).ledger)
        scenario = replace(self.safe, annual_default_rate=.2)
        first = run_cmbs(loans, scenario=scenario, seed=42)
        second = run_cmbs(loans, scenario=scenario, seed=43)
        self.assertFalse(first.ledger.equals(second.ledger))

    def test_stress_loss_monotonicity(self):
        loans = synthetic_mortgages(count=20, total_par=1_000_000)
        losses = np.array([run_cmbs(loans, scenario=s).losses.sum(axis=0) for s in cmbs_scenarios()])
        self.assertTrue((np.diff(losses, axis=0) >= -1e-8).all())

    def test_off_grid_maturity_next_month(self):
        result = run_cmbs([replace(self.loan, maturity_date=date(2027, 1, 15), io_months=13)], scenario=self.safe)
        self.assertEqual(result.ledger.balloon.iloc[12], self.loan.par)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.loan, ltv=0)
        with self.assertRaises(ValueError):
            replace(self.safe, loss_severity=1.1)
        with self.assertRaises(ValueError):
            run_cmbs([self.loan, self.loan])
        with self.assertRaises(ValueError):
            run_cmbs([self.loan], structure=conduit_structure(1))

    def test_sequential_principal_never_pays_junior_before_senior(self):
        result = run_cmbs(synthetic_mortgages(count=20), scenario=self.safe)
        for row in result.ledger.itertuples():
            for index, tranche in enumerate(result.structure.tranches[1:], start=1):
                if getattr(row, f"{tranche.name}_principal") > 1e-8:
                    self.assertTrue(all(getattr(row, f"{senior.name}_balance") < 1e-8
                                        for senior in result.structure.tranches[:index]))

    def test_rates_up_alone_increases_balloon_defaults(self):
        loans = synthetic_mortgages(count=20)
        low = replace(self.safe, refinance_rate=.055, minimum_refi_dscr=1.1,
                      maximum_refi_ltv=.8, extension_probability=0)
        high = replace(low, refinance_rate=.10)
        base = run_cmbs(loans, scenario=low)
        stress = run_cmbs(loans, scenario=high)
        self.assertGreater(stress.ledger.defaulted_par.sum(), base.ledger.defaulted_par.sum())
        self.assertTrue((stress.losses.sum(axis=0) >= base.losses.sum(axis=0) - 1e-8).all())

    def test_synthetic_pool_property_types_io_balloon_and_subordination(self):
        loans = synthetic_mortgages()
        self.assertEqual(len({loan.property_type for loan in loans}), 5)
        self.assertTrue(any(loan.io_months == 0 for loan in loans))
        self.assertTrue(any(loan.io_months >= 60 for loan in loans))
        structure = conduit_structure()
        np.testing.assert_allclose([structure.subordination(i) for i in range(6)],
                                   [.30, .20, .13, .08, .05, 0])
