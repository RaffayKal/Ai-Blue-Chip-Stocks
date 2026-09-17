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


def external_quorum_quote():
    """A quote as load_crypto_quote() actually returns it on RunPod, where
    RUNPOD_MARKET_QUORUM=external swaps the quorum to Coinbase+Binance+Kraken
    because Robinhood MCP is unreachable from the pod."""
    payload = {
        "bid": 100.0,
        "ask": 100.1,
        "last": 100.05,
        "crypto_buying_power_usd": 10000.0,
        "crypto_account_confirmed": True,
        "maintenance_active": False,
        "account_restricted": False,
        "liquidity_usd": 1000000,
        "entry_price_usd": 100.0,
        "invalidation_price_usd": 90.0,
        "minimum_position_size_usd": 1.0,
        "venue": "Coinbase",
        "broker_name": "Robinhood",
    }
    fresh_source = {
        "provider": "placeholder",
        "fresh": True,
        "timestamp": iso_before(1),
        "path": "test",
        "age_seconds": 1,
        "max_age_seconds": 15,
        "bid": 100.0,
        "ask": 100.1,
        "last": 100.05,
    }
    required_quote_sources = {
        provider: {**fresh_source, "provider": provider}
        for provider in ("Coinbase", "Binance", "Kraken")
    }
    return {
        "fresh": True,
        "timestamp": iso_before(1),
        "path": "test",
        "age_seconds": 1,
        "max_age_seconds": 15,
        "quote_source_count": 3,
        "fresh_quote_source_count": 3,
        "fresh_optional_quote_source_count": 0,
        "source_conflict": False,
        "has_bid_ask_last": True,
        "scanner_refresh_timestamp": iso_before(1),
        "required_quote_quorum_ok": True,
        "missing_required_quote_sources": [],
        "required_quote_sources": required_quote_sources,
        "quorum_providers": ["Coinbase", "Binance", "Kraken"],
        "payload": payload,
    }


class ExternalQuorumRequiredSourcesTests(unittest.TestCase):
    def test_external_quorum_envelope_does_not_falsely_mark_robinhood_missing(self):
        quote = external_quorum_quote()
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")

        source_names = [item["source"] for item in envelope["required_sources"]]
        self.assertNotIn("Robinhood.crypto_quote", source_names)
        self.assertIn("Coinbase.crypto_quote", source_names)
        self.assertIn("Binance.crypto_quote", source_names)
        self.assertIn("Kraken.crypto_quote", source_names)
        # Every configured quorum provider is actually fresh in this fixture,
        # so nothing should be reported as a missing/stale source.
        statuses = {item["source"]: item["status"] for item in envelope["required_sources"]}
        for name in ("Coinbase.crypto_quote", "Binance.crypto_quote", "Kraken.crypto_quote"):
            self.assertEqual(statuses[name], "fresh", statuses)

    def test_default_quorum_still_uses_robinhood_and_coinbase(self):
        quote = external_quorum_quote()
        quote["quorum_providers"] = None  # simulate a quote object without the new field
        quote["required_quote_sources"] = {
            "Robinhood": {**quote["required_quote_sources"]["Coinbase"], "provider": "Robinhood"},
            "Coinbase": quote["required_quote_sources"]["Coinbase"],
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")

        source_names = [item["source"] for item in envelope["required_sources"]]
        self.assertIn("Robinhood.crypto_quote", source_names)
        self.assertIn("Coinbase.crypto_quote", source_names)


if __name__ == "__main__":
    unittest.main()
