import unittest
from unittest.mock import patch

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

    def test_correlation_request_validation_returns_400(self):
        from app import app

        cases = [
            ("max_lag=abc", "max_lag must be an integer"),
            ("max_lag=-1", "max_lag must be non-negative"),
            (
                "start=2024-02-01&end=2024-02-01",
                "start must be before end",
            ),
        ]

        with patch("app.load_pair_data") as mock_load:
            with app.test_client() as client:
                for query, expected_error in cases:
                    with self.subTest(query=query):
                        response = client.get(
                            "/api/correlation?ticker_a=MSFT&ticker_b=GOOGL&"
                            + query
                        )
                        self.assertEqual(response.status_code, 400)
                        self.assertEqual(
                            response.get_json()["error"], expected_error
                        )

        mock_load.assert_not_called()

    def test_too_few_correlation_observations_returns_400(self):
        from app import app

        periods = 5
        mock_df = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=periods),
            "Close_MSFT": 100.0 + np.arange(periods),
            "Close_GOOGL": 90.0 + np.arange(periods),
        })

        with patch("app.load_pair_data", return_value=mock_df):
            with app.test_client() as client:
                response = client.get(
                    "/api/correlation?ticker_a=MSFT&ticker_b=GOOGL&max_lag=3"
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("6 overlapping observations", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
