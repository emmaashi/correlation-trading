import unittest

import numpy as np
import pandas as pd

from analysis.pair_model import (
    FAILED_COINTEGRATION,
    FAILED_STATIONARITY,
    INSUFFICIENT_HISTORY,
    INVALID_DATA,
    INVALID_HEDGE_RATIO,
    MIN_OBSERVATIONS,
    validate_pair_model,
)


def _cointegrated_prices(seed=17, observations=700, hedge_ratio=1.25):
    rng = np.random.default_rng(seed)
    log_b = 4.5 + np.cumsum(rng.normal(0.0003, 0.012, observations))
    residual = np.zeros(observations)
    innovations = rng.normal(0, 0.006, observations)
    for index in range(1, observations):
        residual[index] = 0.75 * residual[index - 1] + innovations[index]
    log_a = 0.35 + hedge_ratio * log_b + residual
    index = pd.date_range("2020-01-01", periods=observations, freq="B")
    return pd.Series(np.exp(log_a), index=index), pd.Series(np.exp(log_b), index=index)


class TestPairModelValidation(unittest.TestCase):
    def test_cointegrated_pair_is_eligible(self):
        prices_a, prices_b = _cointegrated_prices()

        result = validate_pair_model(prices_a, prices_b)

        self.assertTrue(result["eligible"])
        self.assertEqual(result["rejection_reasons"], [])
        self.assertEqual(result["observation_count"], 700)
        self.assertAlmostEqual(result["hedge_ratio"], 1.25, delta=0.05)
        self.assertLess(result["cointegration_pvalue"], 0.05)
        self.assertLess(result["adf_pvalue"], 0.05)
        self.assertGreaterEqual(result["half_life_days"], 1.0)
        self.assertLessEqual(result["half_life_days"], 126.0)

    def test_current_signal_zscore_uses_fitted_residual(self):
        prices_a, prices_b = _cointegrated_prices(hedge_ratio=1.7)
        window = 40
        log_a = np.log(prices_a.to_numpy())
        log_b = np.log(prices_b.to_numpy())
        design = np.column_stack([np.ones(len(log_b)), log_b])
        coefficients = np.linalg.lstsq(design, log_a, rcond=None)[0]
        residual = log_a - design @ coefficients
        expected_window = residual[-window:]
        expected_zscore = (
            residual[-1] - expected_window.mean()
        ) / expected_window.std(ddof=1)
        legacy_log_ratio = log_a - log_b
        legacy_window = legacy_log_ratio[-window:]
        legacy_zscore = (
            legacy_log_ratio[-1] - legacy_window.mean()
        ) / legacy_window.std(ddof=1)

        result = validate_pair_model(
            prices_a,
            prices_b,
            zscore_window=window,
        )

        self.assertTrue(result["eligible"])
        self.assertAlmostEqual(result["hedge_ratio"], 1.7, delta=0.05)
        self.assertNotAlmostEqual(result["hedge_ratio"], 1.0, places=1)
        self.assertEqual(result["residual_zscore_window"], window)
        self.assertEqual(result["residual_zscore_observations"], window)
        self.assertAlmostEqual(result["current_residual_zscore"], expected_zscore)
        self.assertAlmostEqual(result["signal_zscore"], expected_zscore)
        self.assertNotAlmostEqual(result["signal_zscore"], legacy_zscore, places=2)

    def test_independent_random_walks_are_ineligible(self):
        rng = np.random.default_rng(21)
        observations = 900
        log_a = 4.5 + np.cumsum(rng.normal(0.0002, 0.012, observations))
        log_b = 4.8 + np.cumsum(rng.normal(0.0002, 0.011, observations))
        index = pd.date_range("2019-01-01", periods=observations, freq="B")

        result = validate_pair_model(
            pd.Series(np.exp(log_a), index=index),
            pd.Series(np.exp(log_b), index=index),
        )

        self.assertFalse(result["eligible"])
        self.assertIn(FAILED_COINTEGRATION, result["rejection_reasons"])
        self.assertIn(FAILED_STATIONARITY, result["rejection_reasons"])

    def test_insufficient_history_is_rejected_before_fitting(self):
        observations = MIN_OBSERVATIONS - 1
        prices_b = pd.Series(np.exp(np.linspace(4.0, 4.2, observations)))
        prices_a = pd.Series(np.exp(0.2 + 1.1 * np.log(prices_b)))

        result = validate_pair_model(prices_a, prices_b)

        self.assertFalse(result["eligible"])
        self.assertEqual(result["rejection_reasons"], [INSUFFICIENT_HISTORY])
        self.assertEqual(result["observation_count"], observations)
        self.assertIsNone(result["hedge_ratio"])
        self.assertIsNone(result["signal_zscore"])

    def test_nonfinite_and_nonpositive_prices_are_rejected(self):
        prices_a, prices_b = _cointegrated_prices()

        for invalid_value in (np.nan, np.inf, 0.0, -1.0):
            invalid_prices = prices_a.copy()
            invalid_prices.iloc[10] = invalid_value
            with self.subTest(invalid_value=invalid_value):
                result = validate_pair_model(invalid_prices, prices_b)
                self.assertEqual(result["rejection_reasons"], [INVALID_DATA])

    def test_nonpositive_hedge_ratio_is_rejected(self):
        prices_a, prices_b = _cointegrated_prices(hedge_ratio=-0.8)

        result = validate_pair_model(prices_a, prices_b)

        self.assertFalse(result["eligible"])
        self.assertLess(result["hedge_ratio"], 0)
        self.assertIn(INVALID_HEDGE_RATIO, result["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
