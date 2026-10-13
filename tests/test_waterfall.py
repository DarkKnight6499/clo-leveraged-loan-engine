from dataclasses import replace
import unittest
import numpy as np
import _support
from clo_engine.structure import illustrative_structure
from clo_engine.waterfall import WaterfallState, allocate_period


class WaterfallTests(unittest.TestCase):
    def setUp(self):
        self.structure = replace(illustrative_structure(100), admin_expense=0, admin_cap=0)

    def test_cash_conservation_regular(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 3, 2, 98, 100, 0.03, False)
        self.assertAlmostEqual(allocation.reconciliation_error, 0)
        uses = (allocation.interest_paid.sum() + allocation.principal_paid.sum()
                + allocation.expenses_paid + allocation.subordinated_paid + allocation.equity)
        self.assertAlmostEqual(uses, 5)

    def test_oc_breach_diverts_interest_to_senior(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 3, 0, 70, 100, 0, True)
        self.assertTrue(allocation.oc_breaches[1])
        self.assertGreater(allocation.coverage_diversion, 0)
        self.assertLess(state.balances[0], 63)
        self.assertAlmostEqual(allocation.principal_paid[0], 3 - 0.025 - 0.23625 - 0.05775)
        self.assertEqual(allocation.equity, 0)

    def test_oc_cure_pays_only_required_amount(self):
        state = WaterfallState.initial(self.structure)
        structure = replace(self.structure, tranches=tuple(
            replace(x, oc_trigger=1, ic_trigger=1) for x in self.structure.tranches))
        # Leave enough interest to cure all 21 of excess debt after coupons.
        allocation = allocate_period(structure, state, 25, 0, 69, 100, 0, True)
        self.assertAlmostEqual(allocation.coverage_diversion, 21)
        self.assertAlmostEqual(state.balances.sum(), 69)

    def test_ic_breach_detected(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 0.5, 0, 100, 100, 0.08, True)
        self.assertTrue(allocation.ic_breaches[1])

    def test_shared_ab_tests(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 3, 0, 70, 100, 0, True)
        self.assertEqual(allocation.oc_ratios[0], allocation.oc_ratios[1])
        self.assertEqual(allocation.ic_ratios[0], allocation.ic_ratios[1])

    def test_zero_debt_tests_pass(self):
        state = WaterfallState.initial(self.structure)
        state.balances.fill(0)
        allocation = allocate_period(self.structure, state, 1, 0, 100, 100, 0.03, False)
        self.assertFalse(allocation.oc_breaches.any())
        self.assertFalse(allocation.ic_breaches.any())

    def test_principal_pays_sequentially(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 10, 65, 35, 100, 0.03, False)
        np.testing.assert_allclose(allocation.principal_paid, [63, 2, 0, 0, 0])

    def test_balances_never_negative(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 10, 1000, 0, 100, 0.03, False, True)
        self.assertTrue((state.balances >= 0).all())
        self.assertAlmostEqual(state.balances.sum(), 0)
        self.assertAlmostEqual(allocation.principal_paid.sum(), 90)

    def test_equity_receives_only_residual(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 10, 100, 0, 100, 0.03, False, True)
        self.assertAlmostEqual(allocation.equity_principal, 10)
        self.assertAlmostEqual(allocation.equity_interest,
                               10 - allocation.interest_paid.sum() - allocation.expenses_paid
                               - allocation.subordinated_paid)

    def test_equity_zero_under_interest_shortfall(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 0.01, 0, 100, 100, 0.03, True)
        self.assertEqual(allocation.equity, 0)
        self.assertTrue((state.interest_arrears > 0).any())

    def test_principal_supports_senior_interest(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 0, 1, 100, 100, 0.03, True)
        self.assertAlmostEqual(allocation.interest_paid[0], 63 * 0.045 * 0.25)
        self.assertAlmostEqual(allocation.interest_paid[1], 11 * 0.051 * 0.25)
        self.assertAlmostEqual(allocation.reconciliation_error, 0)

    def test_unpaid_interest_carried(self):
        state = WaterfallState.initial(self.structure)
        allocate_period(self.structure, state, 0, 0, 100, 100, 0, True)
        prior = state.interest_arrears.copy()
        allocation = allocate_period(self.structure, state, 10, 0, 100, 100, 0, True)
        np.testing.assert_allclose(allocation.interest_paid, prior * 2)
        np.testing.assert_allclose(state.interest_arrears, 0)

    def test_admin_cap_applied(self):
        structure = replace(self.structure, admin_expense=8, admin_cap=4)
        state = WaterfallState.initial(structure)
        allocation = allocate_period(structure, state, 10, 0, 100, 100, 0, True)
        self.assertAlmostEqual(allocation.expenses_paid, 1 + 0.025)

    def test_taxes_top_priority(self):
        structure = replace(self.structure, annual_tax=4)
        state = WaterfallState.initial(structure)
        allocation = allocate_period(structure, state, 0.5, 0, 100, 100, 0, True)
        self.assertEqual(allocation.expenses_paid, 0.5)
        self.assertEqual(allocation.interest_paid.sum(), 0)
        self.assertAlmostEqual(state.expense_arrears[0], 0.5)

    def test_reinvestment_uses_principal(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 5, 2, 98, 100, 0.03, True)
        self.assertAlmostEqual(allocation.reinvestment_cash, 2)
        self.assertEqual(allocation.equity_principal, 0)
        self.assertEqual(allocation.principal_paid.sum(), 0)

    def test_interest_diversion_reinvests(self):
        structure = replace(self.structure, diversion_trigger=1.30)
        state = WaterfallState.initial(structure)
        allocation = allocate_period(structure, state, 5, 0, 100, 100, 0, True)
        self.assertTrue(allocation.diversion_breach)
        self.assertGreater(allocation.interest_diversion, 0)
        self.assertAlmostEqual(allocation.reinvestment_cash, allocation.interest_diversion)
        self.assertAlmostEqual(allocation.reconciliation_error, 0)

    def test_default_style_oc_flag(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_period(self.structure, state, 0, 0, 50, 100, 0, True)
        self.assertTrue(allocation.event_default)

    def test_negative_cash_rejected(self):
        with self.assertRaises(ValueError):
            allocate_period(self.structure, WaterfallState.initial(self.structure), -1, 0, 100, 100, 0, True)

    def test_final_reinvestment_rejected(self):
        with self.assertRaises(ValueError):
            allocate_period(self.structure, WaterfallState.initial(self.structure), 1, 0, 100, 100, 0, True, True)
