import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import ingest_robinhood_crypto_quote_snapshot as ingest
import poll_robinhood_mcp_relay as relay
import runpod_lightweight_scanner as scanner


class RobinhoodSnapshotRoutingTests(unittest.TestCase):
    def broker_payload(self, routing="Market Maker Routing"):
        return {
            "data": {
                "results": [{
                    "symbol": "BTCUSD",
                    "bid_price": "83610.57823",
                    "ask_price": "85201.0382994",
                    "mark_price": "84405.8082647",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "routing": routing,
                }]
            }
        }

    def test_snapshot_preserves_route_without_fabricating_other_market_facts(self):
        result = ingest.normalize(self.broker_payload())
        self.assertEqual(result["routing"], "Market Maker Routing")
        for field in ("liquidity_usd", "source_count", "risk_status", "source_conflict", "crypto_account_confirmed"):
            self.assertNotIn(field, result)

    def test_multisymbol_payload_keeps_each_symbol_and_its_route(self):
        payload = self.broker_payload()
        second = dict(payload["data"]["results"][0])
        second.update({"symbol": "XLMUSD", "routing": "Smart Exchange Routing"})
        payload["data"]["results"].append(second)
        snapshots = ingest.normalize_many(payload)
        self.assertEqual([item["symbol"] for item in snapshots], ["BTC", "XLM"])
        self.assertEqual(snapshots[0]["routing"], "Market Maker Routing")
        self.assertEqual(snapshots[1]["routing"], "Smart Exchange Routing")

    def test_missing_route_is_rejected_instead_of_using_generic_spread_limit(self):
        payload = self.broker_payload()
        del payload["data"]["results"][0]["routing"]
        with self.assertRaisesRegex(SystemExit, "missing Robinhood crypto routing"):
            ingest.normalize(payload)

    def test_relay_writes_route_preserving_per_symbol_and_latest_snapshots(self):
        relay_payload = {
            "source": "robinhood",
            "asset_class": "crypto",
            "symbol": "XLM-USD",
            "bid": "0.217",
            "ask": "0.221",
            "last": "0.219",
            "quote_timestamp": datetime.now(timezone.utc).isoformat(),
            "routing": "Market Maker Routing",
        }
        response = io.BytesIO(json.dumps({"snapshot": relay_payload}).encode())
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_path = Path(temporary) / "data" / "robinhood_crypto_quote_snapshot.json"
            with patch.object(relay, "SNAPSHOT", snapshot_path), patch.object(relay, "URL", "https://relay.example/v1/robinhood/snapshot"), patch.object(relay.urllib.request, "urlopen", return_value=response):
                relay.poll_once()
            latest = json.loads(snapshot_path.read_text())
            per_symbol = json.loads(snapshot_path.with_name("robinhood_crypto_quote_snapshot_XLM.json").read_text())
        self.assertEqual(latest["symbol"], "XLM")
        self.assertEqual(latest["routing"], "Market Maker Routing")
        self.assertEqual(per_symbol, latest)

    def test_relay_rejects_missing_routing_without_writing_quote(self):
        relay_payload = {
            "source": "robinhood",
            "asset_class": "crypto",
            "symbol": "BTCUSD",
            "bid": "83610",
            "ask": "85201",
            "last": "84405",
            "quote_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        response = io.BytesIO(json.dumps({"snapshot": relay_payload}).encode())
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_path = Path(temporary) / "data" / "robinhood_crypto_quote_snapshot.json"
            with patch.object(relay, "SNAPSHOT", snapshot_path), patch.object(relay, "URL", "https://relay.example/v1/robinhood/snapshot"), patch.object(relay.urllib.request, "urlopen", return_value=response):
                with self.assertRaisesRegex(ValueError, "missing routing"):
                    relay.poll_once()
            self.assertFalse(snapshot_path.exists())
            self.assertFalse(snapshot_path.with_name("robinhood_crypto_quote_snapshot_BTC.json").exists())

    def micro_trade(self, routing):
        quote = {
            "payload": {
                "bid": 83610.57823,
                "ask": 85201.0382994,
                "last": 84405.8082647,
                "crypto_buying_power_usd": 100.0,
                "requested_notional_usd": 1.0,
                "routing": routing,
            },
            "fresh": True,
            "scanner_refresh_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return scanner.build_micro_trade_value(quote)

    def test_market_maker_quote_uses_configured_two_percent_limit(self):
        result = self.micro_trade("Market Maker Routing")
        self.assertEqual(result["max_spread_decimal"], 0.02)
        self.assertLessEqual(result["spread_decimal"], result["max_spread_decimal"])
        self.assertEqual(result["micro_trade_value_status"], "VIABLE_FOR_GATE_RECHECK")

    def test_unknown_route_keeps_conservative_generic_limit(self):
        result = self.micro_trade("")
        self.assertEqual(result["max_spread_decimal"], 0.0007)
        self.assertEqual(result["micro_trade_value_status"], "NO_ACTION_GATE_LOCKED")


if __name__ == "__main__":
    unittest.main()
