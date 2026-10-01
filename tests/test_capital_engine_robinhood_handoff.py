#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "algorithms"))

from capital_engine import evaluate


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RobinhoodHandoffCapitalTests(unittest.TestCase):
    def market(self):
        timestamp = now()
        return {
            "symbol": "BTC",
            "asset_class": "CRYPTO",
            "side": "buy",
            "session": "CRYPTO_24_7",
            "venue": "Robinhood Crypto",
            "broker_name": "Robinhood",
            "bid": 100.0,
            "ask": 100.1,
            "last": 100.05,
            "timestamp": timestamp,
            "quote_timestamp": timestamp,
            "data_status": "fresh",
            "risk_status": "pass",
            "source_count": 1,
            "required_quote_quorum_ok": True,
            "quote_authority": "Robinhood",
            "crypto_buying_power_usd": 7.11,
            "requested_notional_usd": 1.42,
            "crypto_account_confirmed": True,
            "routing": "Market Maker Routing",
            "explicit_execution_authorization": True,
            "apex_net_profit_gate_required": True,
            "expected_net_profit": 0.07,
        }

    def test_routed_robinhood_quorum_can_activate_before_preview(self):
        result = evaluate(self.market())
        self.assertEqual(result["RESULT"], "VALIDATED SETUP", result)
        self.assertNotIn("missing liquidity_usd", result["FAILED_CHECKS"])
        self.assertNotIn("less than two source confirmations", result["FAILED_CHECKS"])

    def test_buy_profit_gate_rejects_missing_or_nonpositive_estimate(self):
        market = self.market()
        market.pop("expected_net_profit")
        result = evaluate(market)
        self.assertIn("missing expected_net_profit", result["FAILED_CHECKS"])

        market["expected_net_profit"] = 0.0
        result = evaluate(market)
        self.assertIn("expected net profit is below", result["FAILED_CHECKS"])

    def test_unverified_non_robinhood_handoff_still_requires_liquidity_and_quorum(self):
        market = self.market()
        market["quote_authority"] = "Other"
        market["required_quote_quorum_ok"] = False
        result = evaluate(market)
        self.assertIn("missing liquidity_usd", result["FAILED_CHECKS"])
        self.assertIn("less than two source confirmations", result["FAILED_CHECKS"])


if __name__ == "__main__":
    unittest.main()
