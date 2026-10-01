import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import robinhood_mcp_quote_refresh_daemon as daemon  # noqa: E402


class RobinhoodQuoteRefreshDaemonTests(unittest.TestCase):
    def test_symbol_pool_prioritizes_active_fallback_and_ranked(self):
        original = daemon.VOLATILE_CANDIDATES
        try:
            daemon.VOLATILE_CANDIDATES = ROOT / "tests" / "fixtures" / "volatile_crypto_candidates_test.json"
            symbols = daemon.tracked_symbols(5)
        finally:
            daemon.VOLATILE_CANDIDATES = original
        self.assertEqual(symbols, ["NEAR", "BTC", "SUI", "UNI", "DOT"])

    def test_extracts_structured_quote_result(self):
        payload = {"data": {"results": [{"symbol": "BTCUSD", "bid_price": "1", "ask_price": "2", "mark_price": "1.5", "updated_at": "2026-10-01T15:00:00-04:00", "routing": "Market Maker Routing"}]}}
        output = json.dumps({"item": {"result": {"structured_content": payload}}})
        self.assertEqual(daemon.extract_quote_payload(output), payload)


if __name__ == "__main__":
    unittest.main()
