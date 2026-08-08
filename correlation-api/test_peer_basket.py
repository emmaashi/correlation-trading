import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd


TICKERS = ["AAA", "BBB", "CCC", "DDD"]


def synthetic_universe(
    periods=700,
    *,
    phi=0.82,
    residual_scale=0.002,
    final_state=None,
    seed=41,
):
    rng = np.random.default_rng(seed)
    peer_returns = rng.normal(0.0003, 0.012, size=(periods - 1, 3))
    residual_state = np.zeros(periods - 1)
    for index in range(1, periods - 1):
        residual_state[index] = (
            phi * residual_state[index - 1]
            + rng.normal(0, residual_scale)
        )
    if final_state is not None:
        residual_state[-1] = final_state
    residual_returns = np.diff(residual_state, prepend=0.0)
    target_returns = peer_returns @ np.array([0.5, 0.3, 0.2]) + residual_returns
    all_returns = np.column_stack([target_returns, peer_returns])
    prices = 100 * np.exp(np.vstack([np.zeros(4), np.cumsum(all_returns, axis=0)]))

    frame = pd.DataFrame({"Date": pd.date_range("2022-01-03", periods=periods, freq="B")})
    for index, ticker in enumerate(TICKERS):
        frame[f"Close_{ticker}"] = prices[:, index]
        frame[f"Open_{ticker}"] = prices[:, index]
        frame[f"Volume_{ticker}"] = 5_000_000.0
    return frame


class TestPeerBasketModel(unittest.TestCase):
    def test_recovers_peer_weights_and_mean_reverting_signal(self):
        from analysis.peer_basket import fit_peer_basket

        result = fit_peer_basket(
            synthetic_universe(final_state=-0.08),
            "AAA",
            ["BBB", "CCC", "DDD"],
        )

        weights = {entry["ticker"]: entry["weight"] for entry in result["peer_weights"]}
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertAlmostEqual(weights["BBB"], 0.5, delta=0.12)
        self.assertAlmostEqual(weights["CCC"], 0.3, delta=0.12)
        self.assertAlmostEqual(weights["DDD"], 0.2, delta=0.12)
        self.assertGreater(result["hedge_beta"], 0)
        self.assertEqual(result["action"], "long_target")
        self.assertLess(result["zscore"], -2)
        self.assertIn(result["model_quality"], ("strong", "moderate"))

    def test_random_walk_residual_is_advisory_not_unavailable(self):
        from analysis.peer_basket import fit_peer_basket

        result = fit_peer_basket(
            synthetic_universe(phi=1.0, residual_scale=0.01, final_state=0.30),
            "AAA",
            ["BBB", "CCC", "DDD"],
        )

        self.assertNotEqual(result["action"], "unavailable")
        self.assertEqual(result["model_quality"], "weak")
        self.assertTrue(result["cautions"])

    def test_series_is_only_returned_when_requested(self):
        from analysis.peer_basket import fit_peer_basket

        frame = synthetic_universe()
        compact = fit_peer_basket(frame, "AAA", TICKERS[1:])
        detailed = fit_peer_basket(
            frame, "AAA", TICKERS[1:], include_series=True
        )

        self.assertNotIn("residual_series", compact)
        self.assertEqual(len(detailed["residual_series"]), 252)
        self.assertEqual(detailed["residual_series"][-1]["date"], detailed["as_of"])

    def test_scan_api_returns_ranked_candidates(self):
        from app import app

        with patch("app.load_universe_data", return_value=synthetic_universe()):
            with app.test_client() as client:
                response = client.post(
                    "/api/strategy/scan",
                    json={"tickers": TICKERS},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["strategy_version"], "peer_residual_v1")
        self.assertEqual(len(payload["candidates"]), 4)
        scores = [abs(candidate["zscore"] or 0) for candidate in payload["candidates"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(payload["parameters"]["formation_window"], 252)

    def test_scan_api_rejects_invalid_universe_before_loading(self):
        from app import app

        with patch("app.load_universe_data") as mock_load:
            with app.test_client() as client:
                response = client.post(
                    "/api/strategy/scan",
                    json={"tickers": ["AAA", "BBB", "CCC"]},
                )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_request")
        mock_load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
