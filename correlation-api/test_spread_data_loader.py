import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import numpy as np
import pandas as pd


class TestSpreadDataLoader(unittest.TestCase):
    def test_spread_api_returns_current_zscore_components(self):
        from app import app

        dates = pd.date_range(start="2023-01-01", periods=100)
        mock_df = pd.DataFrame({
            "Date": dates,
            "Close_MSFT": 100.0 + np.arange(100) * 0.5,
            "Ticker_MSFT": ["MSFT"] * 100,
            "Close_GOOGL": [100.0] * 100,
            "Ticker_GOOGL": ["GOOGL"] * 100,
        })

        with patch("app.load_pair_data") as mock_load:
            mock_load.return_value = mock_df
            with app.test_client() as client:
                resp = client.get(
                    "/api/spread?ticker_a=MSFT&ticker_b=GOOGL&window=20&spread_type=log_ratio"
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.get_json()
                metrics = data["metrics"]

                self.assertLess(abs(metrics["current"]), 1.0)
                self.assertEqual(metrics["zscore_window"], 20.0)
                self.assertIn("current_mean", metrics)
                self.assertIn("current_std", metrics)

                expected_zscore = (
                    metrics["current"] - metrics["current_mean"]
                ) / metrics["current_std"]
                self.assertAlmostEqual(
                    metrics["current_zscore"],
                    expected_zscore,
                    places=6,
                )

    def test_stock_data_cache_path_is_versioned(self):
        from analysis.data_loader import CACHE_VERSION, get_data_path

        path = get_data_path("MSFT", "2023-01-01", "2023-02-01")
        self.assertIn(f"_{CACHE_VERSION}_raw.csv", path)

    def test_stock_data_cache_accepts_long_range_later_listing(self):
        from analysis.data_loader import _cache_is_valid

        dates = pd.date_range(start="2018-06-28", end="2026-08-03", freq="B")
        df = pd.DataFrame({
            "Date": dates,
            "Close": range(1, len(dates) + 1),
            "Ticker": "BJ",
        })

        self.assertTrue(_cache_is_valid(df, "BJ", "2016-08-04", "2026-08-04"))

    def test_stock_data_cache_rejects_short_three_year_coverage(self):
        from analysis.data_loader import _cache_is_valid

        dates = pd.date_range(start="2025-02-10", end="2026-08-03", freq="B")
        df = pd.DataFrame({
            "Date": dates,
            "Close": range(1, len(dates) + 1),
            "Ticker": "AMD",
        })

        self.assertFalse(_cache_is_valid(df, "AMD", "2023-08-04", "2026-08-04"))

    def test_stock_downloads_are_serialized(self):
        from analysis.data_loader import get_stock_data

        active = 0
        max_active = 0
        active_lock = threading.Lock()

        def fake_download(ticker, *args, **kwargs):
            nonlocal active, max_active
            with active_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with active_lock:
                active -= 1

            dates = pd.date_range(start="2023-01-02", periods=3)
            return pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=dates)

        with patch("analysis.data_loader.yf.download", side_effect=fake_download):
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(
                    lambda ticker: get_stock_data(
                        ticker,
                        "2023-01-01",
                        "2023-01-06",
                        cache=False,
                    ),
                    ["AAA", "BBB", "CCC", "DDD"],
                ))

        self.assertEqual(max_active, 1)
        self.assertEqual([df["Ticker"].iloc[0] for df in results], ["AAA", "BBB", "CCC", "DDD"])

    def test_stock_download_includes_requested_end_date(self):
        from analysis.data_loader import get_stock_data

        dates = pd.date_range(start="2023-01-02", end="2023-01-06", freq="B")
        downloaded = pd.DataFrame(
            {"Close": np.arange(len(dates), dtype=float) + 100.0},
            index=dates,
        )

        with patch(
            "analysis.data_loader.yf.download",
            return_value=downloaded,
        ) as mock_download:
            get_stock_data(
                "MSFT",
                "2023-01-01",
                "2023-01-06",
                cache=False,
            )

        self.assertEqual(mock_download.call_args.kwargs["end"], "2023-01-07")


if __name__ == "__main__":
    unittest.main()
