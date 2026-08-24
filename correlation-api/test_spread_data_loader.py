import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import numpy as np
import pandas as pd


def downloaded_market_data(
    dates,
    adjusted_close=None,
    raw_close=None,
    dividends=None,
    stock_splits=None,
):
    row_count = len(dates)
    adjusted_close = (
        np.arange(row_count, dtype=float) + 100.0
        if adjusted_close is None
        else adjusted_close
    )
    raw_close = adjusted_close if raw_close is None else raw_close
    dividends = np.zeros(row_count) if dividends is None else dividends
    stock_splits = np.zeros(row_count) if stock_splits is None else stock_splits
    return pd.DataFrame(
        {
            "Adj Close": adjusted_close,
            "Close": raw_close,
            "Dividends": dividends,
            "Stock Splits": stock_splits,
        },
        index=dates,
    )


def cached_market_data(dates, ticker):
    prices = np.arange(len(dates), dtype=float) + 100.0
    return pd.DataFrame(
        {
            "Date": dates,
            "Close": prices,
            "RawClose": prices,
            "Dividends": 0.0,
            "StockSplits": 0.0,
            "Ticker": ticker,
        }
    )


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
        self.assertEqual(CACHE_VERSION, "v4")
        self.assertIn(f"_{CACHE_VERSION}_raw.csv", path)

    def test_stock_data_cache_accepts_long_range_later_listing(self):
        from analysis.data_loader import _cache_is_valid

        dates = pd.date_range(start="2018-06-28", end="2026-08-03", freq="B")
        df = cached_market_data(dates, "BJ")

        self.assertTrue(_cache_is_valid(df, "BJ", "2016-08-04", "2026-08-04"))

    def test_stock_data_cache_rejects_short_three_year_coverage(self):
        from analysis.data_loader import _cache_is_valid

        dates = pd.date_range(start="2025-02-10", end="2026-08-03", freq="B")
        df = cached_market_data(dates, "AMD")

        self.assertFalse(_cache_is_valid(df, "AMD", "2023-08-04", "2026-08-04"))

    def test_stock_data_cache_rejects_invalid_price_rows(self):
        from analysis.data_loader import _cache_is_valid

        dates = pd.date_range(start="2026-07-27", end="2026-08-03", freq="B")
        valid = cached_market_data(dates, "DDOG")
        invalid_frames = []

        missing_close = valid.copy()
        missing_close.loc[1, "Close"] = np.nan
        invalid_frames.append(missing_close)

        infinite_close = valid.copy()
        infinite_close.loc[1, "Close"] = np.inf
        invalid_frames.append(infinite_close)

        nonpositive_close = valid.copy()
        nonpositive_close.loc[1, "Close"] = 0.0
        invalid_frames.append(nonpositive_close)

        missing_raw_close = valid.drop(columns="RawClose")
        invalid_frames.append(missing_raw_close)

        invalid_dividend = valid.copy()
        invalid_dividend.loc[1, "Dividends"] = np.inf
        invalid_frames.append(invalid_dividend)

        duplicate_date = pd.concat([valid, valid.iloc[[0]]], ignore_index=True)
        invalid_frames.append(duplicate_date)

        unsorted_dates = valid.iloc[::-1].reset_index(drop=True)
        invalid_frames.append(unsorted_dates)

        for frame in invalid_frames:
            with self.subTest(frame=frame):
                self.assertFalse(
                    _cache_is_valid(frame, "DDOG", "2026-07-27", "2026-08-04")
                )

    def test_split_raw_jump_is_not_used_as_research_close(self):
        from analysis.data_loader import get_stock_data

        dates = pd.date_range(start="2023-01-02", end="2023-01-06", freq="B")
        downloaded = downloaded_market_data(
            dates,
            adjusted_close=[50.0, 51.0, 51.0, 52.0, 53.0],
            raw_close=[100.0, 102.0, 51.0, 52.0, 53.0],
            dividends=[0.0, 0.0, 0.0, 0.25, 0.0],
            stock_splits=[0.0, 0.0, 2.0, 0.0, 0.0],
        )
        downloaded["Capital Gains"] = [0.0, 0.0, 0.0, 0.1, 0.0]
        downloaded.columns = pd.MultiIndex.from_tuples(
            [(field, "SPLT") for field in downloaded.columns],
            names=["Price", "Ticker"],
        )

        with patch(
            "analysis.data_loader.yf.download",
            return_value=downloaded,
        ) as mock_download:
            result = get_stock_data(
                "SPLT",
                "2023-01-01",
                "2023-01-06",
                cache=False,
            )

        self.assertEqual(result["Close"].tolist(), [50.0, 51.0, 51.0, 52.0, 53.0])
        self.assertLess(result["RawClose"].pct_change().min(), -0.4)
        self.assertGreater(result["Close"].pct_change().min(), -0.1)
        self.assertEqual(result["StockSplits"].tolist(), [0.0, 0.0, 2.0, 0.0, 0.0])
        self.assertEqual(result["CapitalGains"].iloc[3], 0.1)
        self.assertFalse(mock_download.call_args.kwargs["auto_adjust"])
        self.assertTrue(mock_download.call_args.kwargs["actions"])

    def test_missing_or_invalid_adjusted_close_is_rejected(self):
        from analysis.data_loader import get_stock_data

        dates = pd.date_range(start="2023-01-02", end="2023-01-06", freq="B")
        missing_adjusted = downloaded_market_data(dates).drop(columns="Adj Close")
        with patch(
            "analysis.data_loader.yf.download",
            return_value=missing_adjusted,
        ):
            with self.assertRaisesRegex(ValueError, "missing required 'Adj Close'"):
                get_stock_data("MISS", "2023-01-01", "2023-01-06", cache=False)

        for invalid_value in (np.nan, np.inf, 0.0):
            with self.subTest(invalid_value=invalid_value):
                invalid_adjusted = downloaded_market_data(dates)
                invalid_adjusted.loc[dates[2], "Adj Close"] = invalid_value
                with patch(
                    "analysis.data_loader.yf.download",
                    return_value=invalid_adjusted,
                ):
                    with self.assertRaisesRegex(ValueError, "Close"):
                        get_stock_data(
                            "BAD",
                            "2023-01-01",
                            "2023-01-06",
                            cache=False,
                        )

    def test_invalid_requested_dates_are_rejected_before_download(self):
        from analysis.data_loader import get_stock_data

        invalid_ranges = (
            ("not-a-date", "2023-01-06"),
            ("2023-01-07", "2023-01-06"),
        )
        with patch("analysis.data_loader.yf.download") as mock_download:
            for start_date, end_date in invalid_ranges:
                with self.subTest(start_date=start_date, end_date=end_date):
                    with self.assertRaises(ValueError):
                        get_stock_data(
                            "MSFT",
                            start_date,
                            end_date,
                            cache=False,
                        )
        mock_download.assert_not_called()

    def test_pair_data_keeps_raw_and_action_fields_for_each_ticker(self):
        from analysis.data_loader import load_pair_data

        dates = pd.date_range(start="2023-01-02", periods=3)
        frames = {
            "AAA": cached_market_data(dates, "AAA"),
            "BBB": cached_market_data(dates, "BBB"),
        }

        with patch(
            "analysis.data_loader.get_stock_data",
            side_effect=lambda ticker, *_args: frames[ticker].copy(),
        ):
            result = load_pair_data(
                "AAA",
                "BBB",
                "2023-01-01",
                "2023-01-06",
                cache=False,
            )

        self.assertIn("Close_AAA", result)
        self.assertIn("RawClose_AAA", result)
        self.assertIn("StockSplits_AAA", result)
        self.assertIn("Close_BBB", result)
        self.assertIn("RawClose_BBB", result)
        self.assertIn("Dividends_BBB", result)
        self.assertFalse(any(column.endswith(("_x", "_y")) for column in result))

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
            return downloaded_market_data(dates)

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
        downloaded = downloaded_market_data(dates)

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
