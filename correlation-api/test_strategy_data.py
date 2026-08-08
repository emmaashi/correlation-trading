import unittest


class TestStrategyUniverses(unittest.TestCase):
    def test_presets_are_unique_and_within_supported_size(self):
        from analysis.universes import (
            MAX_UNIVERSE_SIZE,
            MIN_UNIVERSE_SIZE,
            PEER_GROUPS,
        )

        group_ids = [group["id"] for group in PEER_GROUPS]
        self.assertEqual(len(group_ids), len(set(group_ids)))

        for group in PEER_GROUPS:
            tickers = [member["ticker"] for member in group["members"]]
            self.assertGreaterEqual(len(tickers), MIN_UNIVERSE_SIZE)
            self.assertLessEqual(len(tickers), MAX_UNIVERSE_SIZE)
            self.assertEqual(len(tickers), len(set(tickers)))

    def test_universe_api_returns_editable_presets_and_limits(self):
        from app import app

        with app.test_client() as client:
            response = client.get("/api/strategy/universes")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["version"], 1)
        self.assertGreaterEqual(len(payload["groups"]), 10)
        self.assertEqual(payload["limits"]["minimum_tickers"], 4)
        self.assertEqual(payload["limits"]["maximum_tickers"], 8)
        self.assertIn("survivorship bias", payload["methodology_note"])


if __name__ == "__main__":
    unittest.main()
