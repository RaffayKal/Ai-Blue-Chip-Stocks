#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "algorithms"))

from capital_engine import evaluate


class CapitalEngineLiquidationTests(unittest.TestCase):
    def sell_input(self, **overrides):
        payload = {
            "symbol": "BTC",
            "asset_class": "CRYPTO",
            "side": "sell",
            "session": "CRYPTO_24_7",
            "data_status": "fresh",
            "risk_status": "pass",
            "bid": 99.9,
            "ask": 100.0,
            "last": 99.95,
            "liquidity_usd": 100000.0,
            "requested_notional_usd": 5.0,
            "requested_quantity": 0.05,
            "sellable_quantity": 0.10,
            "position_status": "fresh",
            "position_source": "Robinhood.get_crypto_positions",
            "position_timestamp": datetime.now(timezone.utc).isoformat(),
            "position_account_matches_verified_account": True,
            "source_count": 2,
            "source_conflict": False,
            "crypto_account_confirmed": True,
            "maintenance_active": False,
            "account_restricted": False,
            "explicit_execution_authorization": True,
        }
        payload.update(overrides)
        return payload

    def test_sell_uses_fresh_sellable_inventory_when_buying_power_is_zero(self):
        result = evaluate(self.sell_input(crypto_buying_power_usd=0.0))
        self.assertEqual(result["RESULT"], "VALIDATED SETUP")
        self.assertEqual(result["FAILED_CHECKS"], "none")

    def test_equity_sell_uses_sellable_shares_without_equity_buying_power(self):
        result = evaluate(self.sell_input(
            symbol="AAPL",
            asset_class="US_EQUITY",
            side="sell",
            session="REGULAR",
            bid=335.60,
            ask=335.80,
            last=335.70,
            requested_quantity=0.024646,
            sellable_quantity=0.024646,
            position_source="Robinhood.get_equity_positions",
            buying_power_usd=0.0,
            crypto_account_confirmed=None,
        ))
        self.assertEqual(result["RESULT"], "VALIDATED SETUP")

    def test_sell_rejects_quantity_above_sellable_inventory(self):
        result = evaluate(self.sell_input(requested_quantity=0.100001))
        self.assertEqual(result["RESULT"], "NO ACTION")
        self.assertIn("exceeds broker-confirmed sellable quantity", result["FAILED_CHECKS"])

    def test_sell_rejects_stale_or_unverified_position_source(self):
        stale = evaluate(self.sell_input(position_status="stale"))
        wrong_source = evaluate(self.sell_input(position_source="Coinbase.positions"))
        self.assertIn("sellable position data not fresh", stale["FAILED_CHECKS"])
        self.assertIn("sellable position source not verified Robinhood", wrong_source["FAILED_CHECKS"])

    def test_sell_notional_without_precomputed_amount_uses_live_bid_and_exact_quantity(self):
        result = evaluate(self.sell_input(requested_notional_usd=None))
        self.assertEqual(result["RESULT"], "VALIDATED SETUP")

    def test_sell_rejects_missing_or_stale_position_timestamp(self):
        missing = evaluate(self.sell_input(position_timestamp=None))
        stale = evaluate(self.sell_input(position_timestamp="2020-01-01T00:00:00+00:00"))
        self.assertIn("sellable position data not fresh", missing["FAILED_CHECKS"])
        self.assertIn("sellable position data not fresh", stale["FAILED_CHECKS"])

    def test_zero_buying_power_does_not_fund_a_buy_from_unsold_market_value(self):
        payload = self.sell_input(
            side="buy",
            buying_power_usd=0.0,
            requested_notional_usd=5.0,
            requested_quantity=None,
            sellable_quantity=100.0,
            position_status="fresh",
            position_source="Robinhood.get_equity_positions",
            asset_class="US_EQUITY",
            session="REGULAR",
            crypto_account_confirmed=None,
        )
        result = evaluate(payload)
        self.assertEqual(result["RESULT"], "NO ACTION")
        self.assertIn("exceeds live buying power", result["FAILED_CHECKS"])

    def test_follow_on_buy_can_use_only_refreshed_broker_buying_power(self):
        result = evaluate(self.sell_input(
            side="buy",
            crypto_buying_power_usd=5.0,
            requested_notional_usd=5.0,
        ))
        self.assertEqual(result["RESULT"], "VALIDATED SETUP")

    def test_sell_rejects_naive_timestamp_instead_of_assuming_timezone(self):
        result = evaluate(self.sell_input(position_timestamp="2026-09-24T12:00:00"))
        self.assertIn("sellable position data not fresh", result["FAILED_CHECKS"])

    def test_sell_rejects_inventory_from_another_or_unverified_account(self):
        result = evaluate(self.sell_input(position_account_matches_verified_account=False))
        self.assertIn("position account does not match", result["FAILED_CHECKS"])


if __name__ == "__main__":
    unittest.main()
