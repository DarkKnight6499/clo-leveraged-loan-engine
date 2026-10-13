"""Economic acceptance checks for the supplied illustrative deal inputs."""

import unittest
import _support
from clo_engine import illustrative_structure, monte_carlo, portfolio_metrics, run_deal, synthetic_portfolio


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loans = synthetic_portfolio()
        cls.metrics = portfolio_metrics(cls.loans)
        cls.structure = illustrative_structure(cls.metrics["par"], cls.metrics["purchase_cost"])
        cls.base = run_deal(cls.loans, cls.structure)
        cls.flat = monte_carlo(cls.loans, cls.structure, paths=200)

    def test_equity_share_and_base_return(self):
        share = self.structure.equity / self.metrics["purchase_cost"]
        self.assertGreaterEqual(share, 0.08)
        self.assertLessEqual(share, 0.10)
        self.assertGreaterEqual(self.base.equity_irr, 0.10)
        self.assertLessEqual(self.base.equity_irr, 0.16)
        self.assertGreaterEqual(self.base.equity_multiple, 1.6)
        self.assertLessEqual(self.base.equity_multiple, 2.2)

    def test_flat_mean_and_visible_left_tail(self):
        equity = self.flat.equity.iloc[0]
        self.assertGreaterEqual(equity.irr_mean, 0.07)
        self.assertLessEqual(equity.irr_mean, 0.14)
        self.assertLess(equity.irr_mean, self.base.equity_irr)
        self.assertLess(equity.irr_p05, equity.irr_mean - 0.02)
        self.assertGreater(equity.negative_irr_probability, 0)

    def test_flat_senior_protection_and_equity_absorbs_losses(self):
        aaa = self.flat.tranches.iloc[0]
        self.assertEqual(aaa.loss_probability, 0)
        self.assertEqual(aaa.expected_principal_loss, 0)
        self.assertEqual(self.flat.tranches.expected_principal_loss.sum(), 0)
        self.assertGreater(self.flat.paths.credit_loss.mean(), 0)
        self.assertLess(self.flat.equity.iloc[0].multiple_mean, self.base.equity_multiple)

    def test_base_coverage_passes(self):
        self.assertFalse(self.base.ledger.filter(regex="_(oc|ic)_breach$").to_numpy().any())
        self.assertFalse(self.base.ledger.interest_diversion_breach.any())
        self.assertEqual(self.base.ending_balances.sum(), 0)

    def test_stress_breaches_both_coverage_tests(self):
        stress = run_deal(self.loans, self.structure, annual_default_rate=0.10, recovery=0.30)
        self.assertTrue(stress.ledger.filter(regex="_oc_breach$").to_numpy().any())
        self.assertTrue(stress.ledger.filter(regex="_ic_breach$").to_numpy().any())
        self.assertTrue(stress.ledger.interest_diversion_breach.any())
        self.assertLess(stress.equity_irr, 0)


if __name__ == "__main__":
    unittest.main()
