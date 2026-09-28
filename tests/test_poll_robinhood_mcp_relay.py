#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import poll_robinhood_mcp_relay as relay


class PollRobinhoodRelayTests(unittest.TestCase):
    def snapshot(self, age=0):
        return {
            "source": "Robinhood.get_crypto_quotes",
            "asset_class": "CRYPTO",
            "symbol": "BTCUSD",
            "bid": 100,
            "ask": 101,
            "last": 100.5,
            "routing": "Market Maker Routing",
            "quote_timestamp": (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat(),
            "account_number": "must-not-cross-relay",
            "crypto_buying_power_usd": 25,
        }

    def test_matches_relay_endpoint_and_keeps_only_public_fields(self):
        self.assertTrue(relay.URL.endswith("/v1/robinhood/crypto-quote"))
        public = relay.validated_public_snapshot(self.snapshot())
        self.assertEqual(public["symbol"], "BTC")
        self.assertEqual(public["routing"], "Market Maker Routing")
        self.assertNotIn("account_number", public)
        self.assertNotIn("crypto_buying_power_usd", public)

    def test_stale_quote_is_rejected_without_retimestamping(self):
        with self.assertRaisesRegex(ValueError, "stale"):
            relay.validated_public_snapshot(self.snapshot(age=421))

    def test_wrong_source_and_missing_routing_are_rejected(self):
        value = self.snapshot()
        value["source"] = "unknown"
        with self.assertRaisesRegex(ValueError, "not a Robinhood"):
            relay.validated_public_snapshot(value)
        value = self.snapshot()
        value.pop("routing")
        with self.assertRaisesRegex(ValueError, "missing routing"):
            relay.validated_public_snapshot(value)


if __name__ == "__main__":
    unittest.main()
