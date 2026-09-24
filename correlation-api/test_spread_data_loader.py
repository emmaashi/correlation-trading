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
    raw_open=None,
    raw_high=None,
    raw_low=None,
    volume=None,
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
    raw_open = raw_close if raw_open is None else raw_open
    raw_high = np.asarray(raw_close) * 1.01 if raw_high is None else raw_high
    raw_low = np.asarray(raw_close) * 0.99 if raw_low is None else raw_low
    volume = np.full(row_count, 1_000_000.0) if volume is None else volume
    dividends = np.zeros(row_count) if dividends is None else dividends
    stock_splits = np.zeros(row_count) if stock_splits is None else stock_splits
    return pd.DataFrame(
        {
            "Adj Close": adjusted_close,
            "Open": raw_open,
            "High": raw_high,
            "Low": raw_low,
            "Close": raw_close,
            "Volume": volume,
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
            "Open": prices,
            "High": prices * 1.01,
            "Low": prices * 0.99,
            "Close": prices,
            "RawOpen": prices,
            "RawHigh": prices * 1.01,
            "RawLow": prices * 0.99,
            "RawClose": prices,
            "Volume": 1_000_000.0,
            "Dividends": 0.0,
            "StockSplits": 0.0,
            "Ticker": ticker,
        }
    )


class TestSpreadDataLoader(unittest.TestCase):
    @staticmethod
    def _pair_frame(periods):
        return pd.DataFrame({
            "Date": pd.date_range(start="2023-01-01", periods=periods),
            "Close_MSFT": 100.0 + np.arange(periods) * 0.5,
            "Ticker_MSFT": ["MSFT"] * periods,
            "Close_GOOGL": [100.0] * periods,
            "Ticker_GOOGL": ["GOOGL"] * periods,
        })

    def test_spread_api_signal_uses_model_residual_zscore(self):
        from app import app

        rng = np.random.default_rng(29)
        observations = 700
        window = 40
        log_b = 4.5 + np.cumsum(rng.normal(0.0003, 0.012, observations))
        residual = np.zeros(observations)
        innovations = rng.normal(0, 0.006, observations)
        for index in range(1, observations):
            residual[index] = 0.75 * residual[index - 1] + innovations[index]
        log_a = 0.4 + 1.7 * log_b + residual
        dates = pd.date_range("2020-01-01", periods=observations, freq="B")
        mock_df = pd.DataFrame({
            "Date": dates,
            "Close_AAA": np.exp(log_a),
            "Ticker_AAA": ["AAA"] * observations,
            "Close_BBB": np.exp(log_b),
            "Ticker_BBB": ["BBB"] * observations,
        })

        design = np.column_stack([np.ones(observations), log_b])
        coefficients = np.linalg.lstsq(design, log_a, rcond=None)[0]
        fitted_residual = log_a - design @ coefficients
        residual_window = fitted_residual[-window:]
        expected_zscore = (
            fitted_residual[-1] - residual_window.mean()
        ) / residual_window.std(ddof=1)

        with patch("app.load_pair_data", return_value=mock_df):
            with app.test_client() as client:
                response = client.get(
                    f"/api/spread?ticker_a=AAA&ticker_b=BBB&window={window}&spread_type=log_ratio&start=2020-01-01"
                )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        model = data["pair_model"]
        self.assertTrue(model["eligible"])
        self.assertAlmostEqual(model["hedge_ratio"], 1.7, delta=0.05)
        self.assertAlmostEqual(model["current_residual_zscore"], expected_zscore)
        self.assertAlmostEqual(model["signal_zscore"], expected_zscore)
        self.assertNotAlmostEqual(
            model["signal_zscore"],
            data["metrics"]["current_zscore"],
            places=2,
        )

    def test_signal_api_returns_compact_trading_direction(self):
        from app import app

        mock_df = self._pair_frame(100)
        mock_df.loc[mock_df.index[-1], "Close_MSFT"] = 250.0

        with patch("app.load_pair_data") as mock_load:
            mock_load.return_value = mock_df
            with app.test_client() as client:
                response = client.get(
                    "/api/signal?ticker_a=MSFT&ticker_b=GOOGL&window=20"
                )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["ticker_a"], "MSFT")
        self.assertEqual(data["ticker_b"], "GOOGL")
        self.assertEqual(data["direction"], "short")
        self.assertGreater(data["zscore"], 2)
        self.assertEqual(data["window"], 20)
        self.assertNotIn("data", data)
        self.assertNotIn("metrics", data)

    def test_spread_api_returns_current_zscore_components(self):
        from app import app

        mock_df = self._pair_frame(100)

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
                self.assertNotIn("mean", metrics)

                first_signal_point = data["data"][19]
                expected_window = np.log(
                    mock_df["Close_MSFT"].iloc[:20]
                    / mock_df["Close_GOOGL"].iloc[:20]
                )
                self.assertIsNone(data["data"][18]["rolling_mean"])
                self.assertIsNone(data["data"][18]["band_2_upper"])
                self.assertAlmostEqual(
                    first_signal_point["rolling_mean"],
                    expected_window.mean(),
                )
                self.assertAlmostEqual(
                    first_signal_point["rolling_std"],
                    expected_window.std(),
                )
                self.assertAlmostEqual(
                    first_signal_point["band_2_upper"],
                    expected_window.mean() + 2 * expected_window.std(),
                )

                expected_zscore = (
                    metrics["current"] - metrics["current_mean"]
                ) / metrics["current_std"]
                self.assertAlmostEqual(
                    metrics["current_zscore"],
                    expected_zscore,
                    places=6,
                )
                self.assertFalse(data["pair_model"]["eligible"])
                self.assertIn(
                    "insufficient_history",
                    data["pair_model"]["rejection_reasons"],
                )
                self.assertIsNone(data["pair_model"]["signal_zscore"])

    def test_historical_bands_do_not_use_future_spread_values(self):
        from analysis.spread import calculate_spread_metrics

        base = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=6),
            "Close_A": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            "Close_B": [10.0] * 6,
        })
        changed_future = base.copy()
        changed_future.loc[3:, "Close_A"] = [1000.0, 2000.0, 3000.0]

        result, _ = calculate_spread_metrics(
            base, "A", "B", spread_type="difference", window=3
        )
        changed_result, _ = calculate_spread_metrics(
            changed_future, "A", "B", spread_type="difference", window=3
        )

        for field in (
            "rolling_mean",
            "rolling_std",
            "band_1_upper",
            "band_1_lower",
            "band_2_upper",
            "band_2_lower",
            "zscore",
        ):
            self.assertAlmostEqual(result.loc[2, field], changed_result.loc[2, field])

    def test_insufficient_signal_history_is_unavailable(self):
        from analysis.spread import calculate_spread_metrics

        result, metrics = calculate_spread_metrics(
            self._pair_frame(20),
            "MSFT",
            "GOOGL",
            spread_type="log_ratio",
            window=60,
        )

        self.assertIsNone(metrics["current_mean"])
        self.assertIsNone(metrics["current_std"])
        self.assertIsNone(metrics["current_zscore"])
        self.assertTrue(pd.isna(result.iloc[-1]["rolling_mean"]))
        self.assertTrue(pd.isna(result.iloc[-1]["zscore"]))

    def test_zero_variance_signal_is_unavailable_not_zero(self):
        from app import app

        mock_df = self._pair_frame(60)
        mock_df["Close_MSFT"] = 100.0

        with patch("app.load_pair_data", return_value=mock_df):
            with app.test_client() as client:
                response = client.get(
                    "/api/spread?ticker_a=MSFT&ticker_b=GOOGL&window=60"
                )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["metrics"]["current_std"], 0.0)
        self.assertIsNone(payload["metrics"]["current_zscore"])
        self.assertEqual(
            payload["data"][-1]["band_2_upper"],
            payload["data"][-1]["rolling_mean"],
        )
        self.assertIsNone(payload["data"][-1]["zscore"])

    def test_spread_request_validation_returns_400(self):
        from app import app

        cases = [
            ("window=abc", "window must be an integer"),
            ("window=1", "window must be at least 2"),
            (
                "start=2024-02-01&end=2024-01-01",
                "start must be before end",
            ),
            ("start=not-a-date", "start must be in YYYY-MM-DD format"),
        ]

        with patch("app.load_pair_data") as mock_load:
            with app.test_client() as client:
                for query, expected_error in cases:
                    with self.subTest(query=query):
                        response = client.get(
                            "/api/spread?ticker_a=MSFT&ticker_b=GOOGL&" + query
                        )
                        self.assertEqual(response.status_code, 400)
                        self.assertEqual(
                            response.get_json()["error"], expected_error
                        )

        mock_load.assert_not_called()

    def test_fewer_observations_than_window_returns_400(self):
        from app import app

        with patch("app.load_pair_data", return_value=self._pair_frame(20)):
            with app.test_client() as client:
                response = client.get(
                    "/api/spread?ticker_a=MSFT&ticker_b=GOOGL"
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("60 overlapping observations", response.get_json()["error"])

    def test_stock_data_cache_path_is_versioned(self):
        from analysis.data_loader import CACHE_VERSION, get_data_path

        path = get_data_path("MSFT", "2023-01-01", "2023-02-01")
        self.assertEqual(CACHE_VERSION, "v5")
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


        missing_raw_close = valid.drop(columns="RawClose")
        invalid_frames.append(missing_raw_close)

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
        self.assertEqual(result["Open"].tolist(), [50.0, 51.0, 51.0, 52.0, 53.0])
        self.assertLess(result["RawClose"].pct_change().min(), -0.4)
        self.assertGreater(result["Close"].pct_change().min(), -0.1)
        self.assertEqual(result["StockSplits"].tolist(), [0.0, 0.0, 2.0, 0.0, 0.0])
        self.assertEqual(result["CapitalGains"].iloc[3], 0.1)
        self.assertFalse(mock_download.call_args.kwargs["auto_adjust"])
        self.assertTrue(mock_download.call_args.kwargs["actions"])

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
        self.assertIn("Open_AAA", result)
        self.assertIn("Volume_AAA", result)
        self.assertIn("RawClose_AAA", result)
        self.assertIn("StockSplits_AAA", result)
        self.assertIn("Close_BBB", result)
        self.assertIn("RawClose_BBB", result)
        self.assertIn("Dividends_BBB", result)
        self.assertFalse(any(column.endswith(("_x", "_y")) for column in result))

    def test_universe_loader_aligns_each_ticker_once(self):
        from analysis.data_loader import load_universe_data

        dates = pd.date_range(start="2023-01-02", periods=3)
        frames = {
            ticker: cached_market_data(dates, ticker)
            for ticker in ("AAA", "BBB", "CCC")
        }

        with patch(
            "analysis.data_loader.get_stock_data",
            side_effect=lambda ticker, *_args: frames[ticker].copy(),
        ) as mock_get:
            result = load_universe_data(
                ["aaa", "BBB", "AAA", "ccc"],
                "2023-01-01",
                "2023-01-06",
                cache=False,
            )

        self.assertEqual([call.args[0] for call in mock_get.call_args_list], ["AAA", "BBB", "CCC"])
        self.assertEqual(len(result), 3)
        self.assertIn("Open_AAA", result)
        self.assertIn("Close_BBB", result)
        self.assertIn("Volume_CCC", result)

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
