#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import lane_synergy_engine as engine


class LaneSynergyEngineTests(unittest.TestCase):
    def test_role_assignment_covers_every_symbol_role_combo_exactly_once(self):
        symbols = ["AAPL", "BTC"]
        combos = {engine.role_assignment(i, symbols) for i in range(1, len(symbols) * len(engine.ROLES) + 1)}
        expected = {(symbol, role) for symbol in symbols for role in engine.ROLES}
        self.assertEqual(combos, expected)

    def test_role_assignment_wraps_around_so_any_number_of_lanes_can_share_a_symbol(self):
        # With 700+ lanes available, any number of lanes may watch one
        # blue-chip/crypto symbol: once every combo has a lane, further
        # lane indices wrap around and pile onto earlier combos again.
        symbols = ["AAPL"]
        combos = len(engine.ROLES)
        self.assertEqual(engine.role_assignment(1, symbols), engine.role_assignment(combos + 1, symbols))
        self.assertEqual(engine.role_assignment(1, symbols), engine.role_assignment(combos * 5 + 1, symbols))

    def test_dedicated_role_lane_count_covers_every_combo_then_grows_with_share(self):
        symbols = ["AAPL", "MSFT", "BTC"]
        combos = len(symbols) * len(engine.ROLES)
        # Below the full combo count, every lane is dedicated (no legacy
        # fallback lanes at all when capacity can't even cover one pass).
        self.assertEqual(engine.dedicated_role_lane_count(2, symbols, share=0.6), 2)
        # At capacity for exactly one pass, all of it is dedicated.
        self.assertEqual(engine.dedicated_role_lane_count(combos, symbols, share=0.1), combos)
        # With ample capacity, the configured share determines how many
        # extra lanes pile onto the same combos instead of idling on the
        # legacy path.
        self.assertEqual(engine.dedicated_role_lane_count(700, symbols, share=0.6), round(700 * 0.6))
        self.assertEqual(engine.dedicated_role_lane_count(700, symbols, share=1.0), 700)

    def test_math_reports_insufficient_data_below_minimum_window(self):
        thin_window = [{"price": 100.0, "timestamp_utc": "2026-01-01T00:00:00Z"}]
        result = engine.compute_math("AAPL", thin_window)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")

    def test_math_computes_momentum_and_volatility_from_real_window(self):
        window = [
            {"price": 100.0, "timestamp_utc": "2026-01-01T00:00:00Z"},
            {"price": 101.0, "timestamp_utc": "2026-01-01T00:01:00Z"},
            {"price": 102.0, "timestamp_utc": "2026-01-01T00:02:00Z"},
            {"price": 103.0, "timestamp_utc": "2026-01-01T00:03:00Z"},
            {"price": 104.0, "timestamp_utc": "2026-01-01T00:04:00Z"},
        ]
        result = engine.compute_math("AAPL", window)
        self.assertEqual(result["status"], "OK")
        self.assertGreater(result["momentum_pct_per_sample"], 0)

    def test_research_reports_plugin_unavailable_when_no_source_matches(self):
        result = engine.compute_research("__NO_SUCH_SYMBOL__")
        self.assertEqual(result["status"], "PLUGIN_UNAVAILABLE")

    def test_run_role_never_fabricates_when_no_fresh_price_exists(self):
        payload = engine.run_role("__NO_SUCH_SYMBOL__", "MATH")
        self.assertEqual(payload["status"], "DATA_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
