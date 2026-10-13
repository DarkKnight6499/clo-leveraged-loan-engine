from dataclasses import replace
import math
import unittest
import numpy as np
import _support
from clo_engine.loans import Loan
from clo_engine.structure import illustrative_structure
from clo_engine.engine import run_deal
from clo_engine.numerics import normal_quantile, period_probability


class StatisticalValidationTests(unittest.TestCase):
    def test_copula_marginal_default_frequency(self):
        loans = [Loan(str(i), "Food", "Caa1", 100, recovery=0.65) for i in range(2000)]
        structure = replace(illustrative_structure(200_000), reinvestment_years=0,
                            horizon_years=0.25, admin_expense=0, admin_cap=0)
        counts = []
        for seed in range(40):
            result = run_deal(loans, structure, annual_default_rate=None,
                              rng=np.random.default_rng(seed), correlation=0, prepayment=0)
            counts.append(result.ledger.defaulted_par.iloc[0] / 200_000)
        observed = float(np.mean(counts))
        expected = period_probability(0.10)
        standard_error = math.sqrt(expected * (1 - expected) / (2000 * 40))
        self.assertLess(abs(observed - expected), 5 * standard_error)

    def test_recovery_mean_and_support(self):
        loans = [Loan(str(i), "Food", "B2", 100, recovery=0.65) for i in range(2000)]
        structure = replace(illustrative_structure(200_000), reinvestment_years=0,
                            horizon_years=0.25, admin_expense=0, admin_cap=0)
        result = run_deal(loans, structure, annual_default_rate=1,
                          rng=np.random.default_rng(30), prepayment=0)
        observed = result.ledger.recovery.iloc[0] / 200_000
        variance = 0.65 * 0.35 / 21
        self.assertLess(abs(observed - 0.65), 5 * math.sqrt(variance / 2000))
        self.assertGreaterEqual(observed, 0)
        self.assertLessEqual(observed, 1)

    def test_copula_correlation_increases_default_clustering(self):
        loans = [Loan(str(i), "Food", "Caa1", 100) for i in range(300)]
        structure = replace(illustrative_structure(30_000), reinvestment_years=0,
                            horizon_years=0.25, admin_expense=0, admin_cap=0)
        independent, correlated = [], []
        for seed in range(100):
            for correlation, observations in [(0.0, independent), (0.60, correlated)]:
                result = run_deal(loans, structure, annual_default_rate=None,
                                  rng=np.random.default_rng(seed), correlation=correlation, prepayment=0)
                observations.append(result.ledger.defaulted_par.iloc[0] / 30_000)
        self.assertGreater(np.var(correlated), 5 * np.var(independent))

    def test_gaussian_latent_covariance_benchmark(self):
        rng = np.random.default_rng(777)
        common = rng.normal(size=100_000)
        individual = rng.normal(size=(2, 100_000))
        rho = 0.35
        latent = math.sqrt(rho) * common + math.sqrt(1 - rho) * individual
        self.assertAlmostEqual(float(np.corrcoef(latent)[0, 1]), rho, delta=0.01)
        threshold = normal_quantile(0.05)
        self.assertAlmostEqual(float((latent[0] < threshold).mean()), 0.05, delta=0.003)

    def test_recovery_endpoints(self):
        for recovery in (0.0, 1.0):
            loans = [Loan("endpoint", "Food", "B2", 100, recovery=recovery)]
            structure = replace(illustrative_structure(100), horizon_years=0.25, reinvestment_years=0,
                                admin_expense=0, admin_cap=0)
            result = run_deal(loans, structure, annual_default_rate=1, rng=np.random.default_rng(1))
            self.assertEqual(result.ledger.recovery.iloc[0], 100 * recovery)
