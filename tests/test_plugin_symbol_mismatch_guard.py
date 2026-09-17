#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import runpod_lightweight_scanner as scanner


def iso_before(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def eth_quote():
    return {
        "fresh": True,
        "timestamp": iso_before(1),
        "path": "test",
        "age_seconds": 1,
        "max_age_seconds": 15,
        "quote_source_count": 2,
        "fresh_quote_source_count": 2,
        "fresh_optional_quote_source_count": 0,
        "source_conflict": False,
        "has_bid_ask_last": True,
        "scanner_refresh_timestamp": iso_before(1),
        "required_quote_quorum_ok": True,
        "missing_required_quote_sources": [],
        "required_quote_sources": {},
        "payload": {
            "bid": 2400.0, "ask": 2400.5, "last": 2400.25,
            "crypto_buying_power_usd": 10000.0,
            "crypto_account_confirmed": True,
            "maintenance_active": False,
            "account_restricted": False,
            "liquidity_usd": 1000000,
            "venue": "Coinbase", "broker_name": "Robinhood",
        },
    }


class PluginSymbolMismatchGuardTests(unittest.TestCase):
    def test_plugin_symbol_matches_handles_stocktwits_dot_x_suffix(self):
        self.assertTrue(scanner.plugin_symbol_matches({"symbol": "BTC.X"}, "BTC"))
        self.assertFalse(scanner.plugin_symbol_matches({"symbol": "BTC.X"}, "ETH"))

    def test_plugin_symbol_matches_handles_tradingcursor_pair_suffix(self):
        self.assertTrue(scanner.plugin_symbol_matches({"symbol": "BTCUSD"}, "BTC"))
        self.assertFalse(scanner.plugin_symbol_matches({"symbol": "ETHUSD"}, "BTC"))

    def test_plugin_symbol_matches_rejects_missing_symbol(self):
        self.assertFalse(scanner.plugin_symbol_matches({}, "BTC"))
        self.assertFalse(scanner.plugin_symbol_matches(None, "BTC"))

    def test_btc_scoped_sentiment_is_not_applied_when_active_symbol_is_eth(self):
        sources = {
            "Stocktwits": {"sentiment": {"label": "BEARISH", "score": 1, "symbol": "BTC.X", "retrieved_at": iso_before(1)}},
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("ETH", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=eth_quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        # BEARISH score=1 would fail apex_requires_positive_sentiment if it were
        # (wrongly) applied to the ETH decision; it must be dropped as mismatched.
        sentiment_score = envelope["projection"]["crypto"]["projection_scores"]["sentiment_score"]
        self.assertEqual(sentiment_score, 50.0)  # neutral, not the BTC BEARISH score

    def test_btc_scoped_tradingcursor_entry_price_is_not_applied_to_eth(self):
        sources = {
            "TradingCursor": {
                "status": "completed",
                "analysis": {
                    "usable": True,
                    "status": "completed",
                    "symbol": "BTCUSD",
                    "retrieved_at": iso_before(1),
                    "analysis": {"potentialPosition": {"entryPrice": 100000.0, "stopLoss": 90000.0}},
                },
            },
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("ETH", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=eth_quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        # The BTC entry price (100000) must never leak into the ETH envelope.
        self.assertNotEqual(envelope["market_input"].get("entry_price"), 100000.0)

    def test_matching_symbol_sentiment_still_applies_normally(self):
        sources = {
            "Stocktwits": {"sentiment": {"label": "BULLISH", "score": 90, "symbol": "ETH.X", "retrieved_at": iso_before(1)}},
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("ETH", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=eth_quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        sentiment_score = envelope["projection"]["crypto"]["projection_scores"]["sentiment_score"]
        self.assertGreater(sentiment_score, 50.0)


if __name__ == "__main__":
    unittest.main()
