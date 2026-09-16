#!/usr/bin/env python3
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import alpaca_market_data_adapter as adapter


class FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class AlpacaMarketDataAdapterTests(unittest.TestCase):
    def test_missing_credentials_rejected(self):
        result = adapter.load_credentials({})
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], ["ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY"])

    def test_alpaca_and_apca_credential_aliases_supported(self):
        result = adapter.load_credentials({
            "APCA_API_KEY_ID": "key",
            "APCA_API_SECRET_KEY": "secret",
        })
        self.assertTrue(result["ok"])
        self.assertEqual(result["api_key_id"], "key")
        self.assertEqual(result["api_secret_key"], "secret")

    def test_fast_rest_snapshot_loop_blocked(self):
        scanner = adapter.AlpacaReadOnlyAdapter(
            {"ok": True, "api_key_id": "key", "api_secret_key": "secret"},
            {
                "quote_max_age_seconds": 15,
                "scan_interval_seconds": 7,
                "min_rest_scan_interval_seconds": 60,
                "stock_feed": "iex",
            },
        )
        with self.assertRaises(SystemExit):
            scanner.reconcile_rest_loop_blocked()

    def test_symbol_routing_separates_equities_and_crypto(self):
        routes = adapter.read_symbol_routes()
        self.assertIn("AAPL", routes["equities"])
        self.assertIn("BTC/USD", routes["crypto"])
        self.assertNotIn("BTC/USD", routes["equities"])

    def test_stale_data_rejected(self):
        old = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
        quote = adapter.NormalizedQuote(
            provider="Alpaca",
            symbol="AAPL",
            asset_class="US_EQUITY",
            bid=100.0,
            ask=100.1,
            last=100.05,
            timestamp=old,
        )
        status = adapter.quote_status(quote, max_age_seconds=15)
        self.assertFalse(status["ok"])
        self.assertTrue(status["stale"])

    def test_crypto_24_7_symbol_normalization(self):
        self.assertEqual(adapter.normalize_crypto_pair("BTC"), "BTC/USD")
        self.assertEqual(adapter.normalize_crypto_pair("ETHUSD"), "ETH/USD")
        quote = adapter.normalize_quote(
            {"bid_price": 100.0, "ask_price": 100.2, "timestamp": adapter.iso_now()},
            "BTC/USD",
            "CRYPTO",
        )
        self.assertEqual(quote.asset_class, "CRYPTO")
        self.assertEqual(quote.symbol, "BTC/USD")
        self.assertEqual(quote.last, 100.1)

    def test_market_session_separation_is_asset_class_based(self):
        equity = adapter.normalize_quote(
            {"bid_price": 100.0, "ask_price": 100.2, "timestamp": adapter.iso_now()},
            "AAPL",
            "US_EQUITY",
        )
        crypto = adapter.normalize_quote(
            {"bid_price": 100.0, "ask_price": 100.2, "timestamp": adapter.iso_now()},
            "BTC/USD",
            "CRYPTO",
        )
        self.assertEqual(equity.asset_class, "US_EQUITY")
        self.assertEqual(crypto.asset_class, "CRYPTO")

    def test_auth_required_for_cloudflare_interface(self):
        self.assertFalse(adapter.auth_ok(FakeHeaders({}), env={}))
        self.assertFalse(adapter.auth_ok(FakeHeaders({"Authorization": "Bearer bad"}), env={"CLOUDFLARE_SCAN_TOKEN": "good"}))
        self.assertTrue(adapter.auth_ok(FakeHeaders({"Authorization": "Bearer good"}), env={"CLOUDFLARE_SCAN_TOKEN": "good"}))
        self.assertTrue(adapter.auth_ok(FakeHeaders({"X-Scan-Token": "good"}), env={"SCAN_INTERFACE_TOKEN": "good"}))

    def test_health_payload_shape(self):
        state = {
            "last_event_at": "2026-09-15T00:00:00Z",
            "scanner_viable": True,
            "capital_status": {"status": "NO ACTION"},
            "quotes": {
                "AAPL": {"status": {"ok": True}},
                "BTC/USD": {"status": {"ok": False}},
            },
        }
        payload = adapter.health_payload(state)
        self.assertEqual(payload["last_event_at"], "2026-09-15T00:00:00Z")
        self.assertEqual(payload["symbols_ok"], ["AAPL"])
        self.assertEqual(payload["stale_count"], 1)
        self.assertFalse(payload["scanner_viable"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["capital_status"], {"status": "NO ACTION"})


if __name__ == "__main__":
    unittest.main()
