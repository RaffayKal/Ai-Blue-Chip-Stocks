#!/usr/bin/env python3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import rank_volatile_crypto_candidates as ranker
import runpod_lightweight_scanner as scanner


def iso_before(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RankVolatileCryptoCandidatesTests(unittest.TestCase):
    def test_volatility_percent_requires_minimum_samples(self):
        self.assertIsNone(ranker.volatility_percent([(0, 100.0), (1, 101.0)]))

    def test_volatility_percent_computes_range_over_mean(self):
        window = [(0, 100.0), (1, 110.0), (2, 90.0)]
        # mean=100, range=20 -> 20%
        self.assertAlmostEqual(ranker.volatility_percent(window), 20.0)

    def test_update_history_evicts_samples_outside_window(self):
        history = {}
        ranker.update_history(history, "BTC", 100.0, now_seconds=0.0)
        ranker.update_history(history, "BTC", 101.0, now_seconds=ranker.HISTORY_WINDOW_SECONDS + 10.0)
        # First sample should have been evicted as too old relative to the second call's "now".
        remaining = list(history["BTC"])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0][1], 101.0)

    def test_freshest_quote_picks_freshest_across_providers(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            scanner.write_json(data_dir / "coinbase_crypto_quote_snapshot_BTC.json", {
                "usable": True, "last": 100.0, "quote_timestamp": iso_before(20),
            })
            scanner.write_json(data_dir / "binance_crypto_quote_snapshot_BTC.json", {
                "usable": True, "last": 101.0, "quote_timestamp": iso_before(2),
            })
            with patch.object(ranker, "ROOT", Path(tmp)):
                price, age = ranker.freshest_quote("BTC")
            self.assertEqual(price, 101.0)
            self.assertLess(age, 5)

    def test_freshest_quote_ignores_stale_and_unusable(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            scanner.write_json(data_dir / "coinbase_crypto_quote_snapshot_ETH.json", {
                "usable": True, "last": 2000.0, "quote_timestamp": iso_before(120),
            })
            scanner.write_json(data_dir / "binance_crypto_quote_snapshot_ETH.json", {
                "usable": False, "last": 2001.0, "quote_timestamp": iso_before(1),
            })
            with patch.object(ranker, "ROOT", Path(tmp)):
                price, age = ranker.freshest_quote("ETH")
            self.assertIsNone(price)
            self.assertIsNone(age)

    def test_rank_once_prefers_highest_measured_volatility(self):
        history = {
            "BTC": [(0.0, 100.0), (1.0, 100.5), (2.0, 99.8)],   # small range
            "ETH": [(0.0, 100.0), (1.0, 120.0), (2.0, 80.0)],   # large range
        }
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            for symbol in ("BTC", "ETH", "SOL"):
                scanner.write_json(data_dir / f"coinbase_crypto_quote_snapshot_{symbol}.json", {
                    "usable": True, "last": 100.0, "quote_timestamp": iso_before(1),
                })
            with patch.object(ranker, "ROOT", Path(tmp)):
                ranked, fresh_symbols = ranker.rank_once(history, now_seconds=3.0)
        self.assertEqual(ranked[0][0], "ETH")
        self.assertIn("SOL", fresh_symbols)

    def test_write_active_symbol_falls_back_when_nothing_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates_path = Path(tmp) / "volatile_crypto_candidates.json"
            scanner.write_json(candidates_path, {"fallback_symbol": "BTC", "selection_rule": "TEST"})
            with patch.object(ranker, "CANDIDATES_PATH", candidates_path):
                payload = ranker.write_active_symbol(ranked=[], fresh_symbols={})
        self.assertEqual(payload["active_symbol"], "BTC")
        self.assertIn("no tracked symbol has a fresh quote", payload["active_symbol_reason"])
        self.assertEqual(payload["selection_rule"], "TEST")

    def test_write_active_symbol_uses_top_ranked_volatility_leader(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates_path = Path(tmp) / "volatile_crypto_candidates.json"
            scanner.write_json(candidates_path, {"fallback_symbol": "BTC"})
            with patch.object(ranker, "CANDIDATES_PATH", candidates_path):
                payload = ranker.write_active_symbol(ranked=[("SOL", 5.2), ("BTC", 1.1)], fresh_symbols={"SOL": 1.0, "BTC": 1.0})
        self.assertEqual(payload["active_symbol"], "SOL")
        self.assertEqual(payload["volatility_scores"], {"SOL": 5.2, "BTC": 1.1})


if __name__ == "__main__":
    unittest.main()
