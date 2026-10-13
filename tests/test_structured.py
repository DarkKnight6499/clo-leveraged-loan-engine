from dataclasses import replace
from datetime import date
import unittest
import numpy as np
import _support
from clo_engine import CreditStructure, Tranche, level_payment
from clo_engine.structured import allocate_credit
from clo_engine.waterfall import WaterfallState, pay_principal, allocate_losses


class StructuredWaterfallTests(unittest.TestCase):
    def setUp(self):
        self.structure = CreditStructure((Tranche("A", "AAA", 70, .12, 1, 1),
                                          Tranche("B", "BBB", 30, .24, 1, 1)), 100,
                                         servicing_fee=0, reserve_fraction=.01)

    def test_payment_closed_form_and_zero_rate(self):
        self.assertAlmostEqual(level_payment(100, .12, 12), 100 * .01 / (1 - 1.01 ** -12))
        self.assertEqual(level_payment(120, 0, 12), 10)

    def test_sequential_principal(self):
        balances = np.array([70., 30.])
        np.testing.assert_allclose(pay_principal(balances, 80), [70, 10])
        np.testing.assert_allclose(balances, [0, 20])

    def test_pro_rata_principal(self):
        balances = np.array([70., 30.])
        np.testing.assert_allclose(pay_principal(balances, 20, False), [14, 6])
        np.testing.assert_allclose(balances, [56, 24])

    def test_bottom_up_losses_are_not_payments(self):
        balances = np.array([70., 30.])
        np.testing.assert_allclose(allocate_losses(balances, 40), [10, 30])
        np.testing.assert_allclose(balances, [60, 0])

    def test_reserve_supports_interest_in_priority_order(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_credit(self.structure, state, 0, 0, 100, 100, 1, True)
        np.testing.assert_allclose(allocation.interest, [.7, .3])
        np.testing.assert_allclose(state.interest_arrears, [0, .3])
        self.assertEqual(allocation.reserve, 0)
        self.assertAlmostEqual(allocation.reconciliation_error, 0)

    def test_reserve_refills_before_residual(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_credit(self.structure, state, 3, 0, 100, 100, 0, True)
        self.assertEqual(allocation.reserve_deposit, 1)
        self.assertAlmostEqual(allocation.residual, .7)
        self.assertAlmostEqual(allocation.reconciliation_error, 0)

    def test_final_reserve_release_cash_conservation(self):
        state = WaterfallState.initial(self.structure)
        allocation = allocate_credit(self.structure, state, 2, 99, 100, 0, 1, True, final=True)
        self.assertEqual(allocation.reserve_release, 1)
        self.assertEqual(allocation.reserve, 0)
        self.assertEqual(allocation.principal.sum(), 100)
        self.assertAlmostEqual(allocation.reconciliation_error, 0)

    def test_oc_turbo_hand_calculation(self):
        structure = replace(self.structure, reserve_fraction=0, oc_target=.1)
        state = WaterfallState.initial(structure)
        allocation = allocate_credit(structure, state, 5, 10, 100, 90, 0, False)
        self.assertAlmostEqual(allocation.turbo, 3.7)
        np.testing.assert_allclose(allocation.principal, [3.7 + 10 * 66.3 / 96.3, 10 * 30 / 96.3])
        self.assertEqual(allocation.residual, 0)

    def test_arrears_carry_without_compounding(self):
        state = WaterfallState.initial(self.structure)
        allocate_credit(self.structure, state, 0, 0, 100, 100, 0, True)
        allocation = allocate_credit(self.structure, state, 3, 0, 100, 100, 0, True)
        np.testing.assert_allclose(allocation.interest, [1.4, 1.2])
        np.testing.assert_allclose(state.interest_arrears, [0, 0])

    def test_invalid_inputs(self):
        for args in [(-1, .1, 12), (100, float("nan"), 12), (100, .1, 0)]:
            with self.assertRaises(ValueError):
                level_payment(*args)
        with self.assertRaises(ValueError):
            replace(self.structure, loss_trigger=1.1)
        with self.assertRaises(ValueError):
            pay_principal(np.array([1.]), -1)
