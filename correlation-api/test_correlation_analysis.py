import unittest

import numpy as np
import pandas as pd


class TestCorrelationAnalysis(unittest.TestCase):
    def test_lagged_correlation_uses_daily_log_returns(self):
        from analysis.correlation import compute_lagged_correlation

        prices_a = pd.Series([100.0, 110.0, 99.0, 118.8, 95.04, 104.544])
        prices_b = pd.Series([200.0, 180.0, 207.0, 165.6, 207.0, 186.3])
        expected = np.log(prices_a).diff().corr(np.log(prices_b).diff())
        price_level_correlation = prices_a.corr(prices_b)

        result = compute_lagged_correlation(prices_a, prices_b, max_lag=0)

        self.assertAlmostEqual(result.iloc[0]["Correlation"], expected)
        self.assertNotAlmostEqual(result.iloc[0]["Correlation"], price_level_correlation)

    def test_breakdown_reports_its_actual_trigger(self):
        from analysis.risk import detect_correlation_breakdown

        rng = np.random.default_rng(7)
        returns_a = rng.normal(0, 0.02, 80)
        returns_b = returns_a + rng.normal(0, 0.001, 80)
        returns_b[-8:] = -returns_a[-8:]
        dates = pd.date_range("2024-01-01", periods=81, freq="B")
        prices_a = pd.Series(100 * np.exp(np.r_[0, returns_a].cumsum()), index=dates)
        prices_b = pd.Series(100 * np.exp(np.r_[0, returns_b].cumsum()), index=dates)

        result = detect_correlation_breakdown(
            prices_a,
            prices_b,
            recent_window=8,
            baseline_window=20,
        )

        self.assertTrue(result["broken"])
        self.assertEqual(result["breakdown_reason"], "relative_and_absolute")

    def test_pairs_api_includes_datadog_and_cloudflare(self):
        from app import app

        with app.test_client() as client:
            response = client.get("/api/pairs")

        self.assertEqual(response.status_code, 200)
        pairs = response.get_json()
        self.assertTrue(
            any(pair["ticker_a"] == "DDOG" and pair["ticker_b"] == "NET" for pair in pairs)
        )


if __name__ == "__main__":
    unittest.main()
