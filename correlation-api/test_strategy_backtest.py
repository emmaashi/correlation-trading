import unittest
from unittest.mock import patch

from test_peer_basket import TICKERS, synthetic_universe


class TestStrategyBacktest(unittest.TestCase):
    def test_hedge_exposures_preserve_gross_and_beta_split(self):
        from analysis.strategy_backtest import desired_exposures

        exposures = desired_exposures(
            1,
            "AAA",
            [
                {"ticker": "BBB", "weight": 0.5},
                {"ticker": "CCC", "weight": 0.3},
                {"ticker": "DDD", "weight": 0.2},
            ],
            hedge_beta=1.5,
            gross_exposure=1.0,
        )

        self.assertAlmostEqual(sum(abs(value) for value in exposures.values()), 1.0)
        self.assertAlmostEqual(exposures["AAA"], 0.4)
        self.assertAlmostEqual(sum(exposures[ticker] for ticker in TICKERS[1:]), -0.6)

    def test_signals_fill_on_the_next_session(self):
        from analysis.strategy_backtest import run_walk_forward_backtest

        result = run_walk_forward_backtest(
            synthetic_universe(periods=700, phi=0.75, residual_scale=0.008),
            "AAA",
            TICKERS[1:],
        )

        self.assertTrue(result["trades"])
        for trade in result["trades"]:
            self.assertLess(trade["signal_date"], trade["entry_date"])
        self.assertEqual(result["costs"]["transaction_cost_bps"], 5.0)
        self.assertGreater(result["costs"]["total"], 0)

    def test_higher_costs_cannot_improve_net_equity(self):
        from analysis.strategy_backtest import run_walk_forward_backtest

        frame = synthetic_universe(periods=700, phi=0.75, residual_scale=0.008)
        no_cost = run_walk_forward_backtest(
            frame,
            "AAA",
            TICKERS[1:],
            transaction_cost_bps=0,
            annual_borrow_rate=0,
        )
        high_cost = run_walk_forward_backtest(
            frame,
            "AAA",
            TICKERS[1:],
            transaction_cost_bps=50,
            annual_borrow_rate=0.10,
        )

        self.assertGreater(
            no_cost["summary"]["final_equity"],
            high_cost["summary"]["final_equity"],
        )

    def test_appending_future_data_does_not_change_earlier_results(self):
        from analysis.strategy_backtest import run_walk_forward_backtest

        full_frame = synthetic_universe(periods=760, phi=0.75, residual_scale=0.008)
        earlier = run_walk_forward_backtest(
            full_frame.iloc[:650].copy(), "AAA", TICKERS[1:]
        )
        extended = full_frame.copy()
        extended.loc[extended.index[-1], "Close_AAA"] *= 4
        later = run_walk_forward_backtest(extended, "AAA", TICKERS[1:])

        earlier_curve = earlier["equity_curve"][:-1]
        later_by_date = {point["date"]: point for point in later["equity_curve"]}
        for point in earlier_curve:
            self.assertAlmostEqual(
                point["equity"], later_by_date[point["date"]]["equity"], places=8
            )

    def test_missing_execution_data_is_rejected(self):
        from analysis.strategy_backtest import run_walk_forward_backtest

        frame = synthetic_universe(periods=600).drop(columns="Volume_CCC")
        with self.assertRaisesRegex(ValueError, "Volume_CCC"):
            run_walk_forward_backtest(frame, "AAA", TICKERS[1:])

    def test_backtest_api_returns_costs_holdout_and_sensitivity(self):
        from app import app

        frame = synthetic_universe(periods=800, phi=0.75, residual_scale=0.008)
        with patch("app.load_universe_data", return_value=frame):
            with app.test_client() as client:
                response = client.post(
                    "/api/strategy/backtest",
                    json={
                        "target": "AAA",
                        "peers": TICKERS[1:],
                        "transaction_cost_bps": 7,
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["config"]["execution"], "next_adjusted_open")
        self.assertEqual(payload["costs"]["transaction_cost_bps"], 7)
        self.assertIn("holdout", payload["summary"])
        self.assertEqual(
            [entry["formation_window"] for entry in payload["sensitivity"]],
            [126, 252, 504],
        )
        self.assertTrue(payload["equity_curve"])
        self.assertTrue(payload["residual_series"])


if __name__ == "__main__":
    unittest.main()
