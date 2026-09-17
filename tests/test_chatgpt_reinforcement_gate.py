#!/usr/bin/env python3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import runpod_lightweight_scanner as scanner


def iso_before(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ChatgptReinforcementGateTests(unittest.TestCase):
    def check_status(self, fleet_payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chatgpt_medium_scanner_fleet.json"
            if fleet_payload is not None:
                scanner.write_json(path, fleet_payload)
            with patch.object(scanner, "CHATGPT_FLEET_AGGREGATE", path):
                return scanner.chatgpt_reinforcement_status()

    def test_missing_fleet_file_is_not_fresh(self):
        result = self.check_status(None)
        self.assertEqual(result["status"], "stale_or_unusable")

    def test_real_openai_success_counts_as_fresh(self):
        result = self.check_status({"status": "OK", "timestamp": iso_before(5)})
        self.assertEqual(result["status"], "fresh")

    def test_runpod_deterministic_fallback_counts_as_fresh(self):
        # RunPod stands in for ChatGPT's job when OpenAI is unavailable; that
        # fallback must satisfy this gate, not fail it.
        result = self.check_status({"status": "OK_DETERMINISTIC_FALLBACK", "timestamp": iso_before(5)})
        self.assertEqual(result["status"], "fresh")

    def test_partial_or_error_does_not_count_as_fresh(self):
        result = self.check_status({"status": "PARTIAL_OR_ERROR", "timestamp": iso_before(5)})
        self.assertEqual(result["status"], "stale_or_unusable")

    def test_stale_timestamp_does_not_count_as_fresh(self):
        result = self.check_status({"status": "OK", "timestamp": iso_before(scanner.MAX_CHATGPT_REINFORCEMENT_AGE_SECONDS + 30)})
        self.assertEqual(result["status"], "stale_or_unusable")

    def test_envelope_is_not_viable_without_fresh_chatgpt_reinforcement(self):
        quote = {
            "fresh": True, "timestamp": iso_before(1), "path": "test", "age_seconds": 1, "max_age_seconds": 15,
            "quote_source_count": 2, "fresh_quote_source_count": 2, "fresh_optional_quote_source_count": 0,
            "source_conflict": False, "has_bid_ask_last": True, "scanner_refresh_timestamp": iso_before(1),
            "required_quote_quorum_ok": True, "missing_required_quote_sources": [],
            "required_quote_sources": {
                "Robinhood": {"provider": "Robinhood", "fresh": True, "timestamp": iso_before(1), "path": "x",
                              "age_seconds": 1, "max_age_seconds": 15, "bid": 100.0, "ask": 100.1, "last": 100.05},
                "Coinbase": {"provider": "Coinbase", "fresh": True, "timestamp": iso_before(1), "path": "x",
                             "age_seconds": 1, "max_age_seconds": 15, "bid": 100.0, "ask": 100.1, "last": 100.05},
            },
            "payload": {
                "bid": 100.0, "ask": 100.1, "last": 100.05, "crypto_buying_power_usd": 10000.0,
                "crypto_account_confirmed": True, "maintenance_active": False, "account_restricted": False,
                "liquidity_usd": 1000000, "venue": "Robinhood Crypto", "broker_name": "Robinhood",
            },
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}), \
             patch.object(scanner, "chatgpt_reinforcement_status", return_value={"status": "stale_or_unusable"}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertFalse(envelope["scanner_viable"])
        self.assertIn("chatgpt medium-scanner reinforcement is missing, stale, or failed", envelope["failed_checks"])


if __name__ == "__main__":
    unittest.main()
