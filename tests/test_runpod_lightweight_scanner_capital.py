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


class RunpodLightweightScannerCapitalTests(unittest.TestCase):
    def write_snapshot(self, directory, payload):
        path = Path(directory) / "robinhood_crypto_capital_snapshot.json"
        scanner.write_json(path, payload)
        return path

    def quote(self, **overrides):
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
            "venue": "Robinhood Crypto",
            "broker_name": "Robinhood",
        }
        quote = {
            "fresh": True,
            "timestamp": iso_before(1),
            "path": "test",
            "age_seconds": 1,
            "max_age_seconds": 15,
            "quote_source_count": 2,
            "fresh_quote_source_count": 1,
            "fresh_optional_quote_source_count": 1,
            "source_conflict": False,
            "has_bid_ask_last": True,
            "scanner_refresh_timestamp": iso_before(1),
            "required_quote_quorum_ok": True,
            "missing_required_quote_sources": [],
            "required_quote_sources": {
                "Robinhood": {
                    "provider": "Robinhood",
                    "fresh": True,
                    "timestamp": iso_before(1),
                    "path": "data/robinhood_crypto_quote_snapshot.json",
                    "age_seconds": 1,
                    "max_age_seconds": 15,
                    "bid": 100.0,
                    "ask": 100.1,
                    "last": 100.05,
                },
            },
            "payload": payload,
        }
        quote.update(overrides)
        if "payload" in overrides:
            merged = payload.copy()
            merged.update(overrides["payload"])
            quote["payload"] = merged
        return quote

    def test_fresh_robinhood_crypto_buying_power_snapshot_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_snapshot(tmp, {
                "crypto_buying_power_usd": "10.9700",
                "crypto_capital_source": "robinhood.get_portfolio.crypto_buying_power.buying_power",
                "crypto_capital_retrieved_at": iso_before(10),
            })
            with patch.object(scanner, "ROBINHOOD_CRYPTO_CAPITAL", path):
                result = scanner.load_crypto_capital_snapshot()
        self.assertEqual(result["crypto_buying_power_usd"], 10.97)
        self.assertEqual(result["crypto_capital_source"], "robinhood.get_portfolio.crypto_buying_power.buying_power")
        self.assertIn("crypto_capital_retrieved_at", result)

    def test_stale_robinhood_crypto_buying_power_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_snapshot(tmp, {
                "crypto_buying_power_usd": "10.9700",
                "crypto_capital_source": "robinhood.get_portfolio.crypto_buying_power.buying_power",
                "crypto_capital_retrieved_at": iso_before(scanner.MAX_SOURCE_AGE_SECONDS + 60),
            })
            with patch.object(scanner, "ROBINHOOD_CRYPTO_CAPITAL", path):
                result = scanner.load_crypto_capital_snapshot()
        self.assertEqual(result, {})

    def test_wrong_capital_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_snapshot(tmp, {
                "crypto_buying_power_usd": "400000",
                "crypto_capital_source": "alpaca.paper.buying_power",
                "crypto_capital_retrieved_at": iso_before(10),
            })
            with patch.object(scanner, "ROBINHOOD_CRYPTO_CAPITAL", path):
                result = scanner.load_crypto_capital_snapshot()
        self.assertEqual(result, {})

    def test_envelope_includes_robinhood_crypto_capital_without_manual_viability(self):
        quote = {
            "fresh": False,
            "timestamp": iso_before(600),
            "path": "test",
            "age_seconds": 600,
            "max_age_seconds": 15,
            "quote_source_count": 1,
            "fresh_quote_source_count": 0,
            "source_conflict": False,
            "has_bid_ask_last": True,
            "scanner_refresh_timestamp": iso_before(1),
            "payload": {
                "bid": 100.0,
                "ask": 101.0,
                "last": 100.5,
                "requested_notional_usd": None,
            },
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={
                 "crypto_buying_power_usd": 10.97,
                 "crypto_capital_source": "robinhood.get_portfolio.crypto_buying_power.buying_power",
                 "crypto_capital_retrieved_at": iso_before(1),
             }):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertEqual(envelope["created_by"], "CHATGPT_PLUGIN_SCANNER")
        self.assertFalse(envelope["scanner_viable"])
        self.assertFalse(envelope["requested_codex_activation"])
        self.assertFalse(envelope["plugins_execute_trades"])
        self.assertEqual(envelope["market_input"]["crypto_buying_power_usd"], 10.97)
        self.assertEqual(
            envelope["market_input"]["crypto_capital_source"],
            "robinhood.get_portfolio.crypto_buying_power.buying_power",
        )

    def test_requested_notional_remains_null_without_quote_input_policy(self):
        quote = {
            "fresh": True,
            "timestamp": iso_before(1),
            "path": "test",
            "age_seconds": 1,
            "max_age_seconds": 15,
            "quote_source_count": 2,
            "fresh_quote_source_count": 2,
            "source_conflict": False,
            "has_bid_ask_last": True,
            "scanner_refresh_timestamp": iso_before(1),
            "payload": {
                "bid": 100.0,
                "ask": 100.1,
                "last": 100.05,
                "crypto_buying_power_usd": 10.97,
                "requested_notional_usd": None,
            },
        }
        sources = {"Stocktwits": {"sentiment": {"label": "BEARISH", "score": 26, "retrieved_at": iso_before(1)}}}
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertIsNone(envelope["market_input"]["requested_notional_usd"])
        self.assertNotIn("Stocktwits sentiment is not positive", envelope["failed_checks"])
        self.assertIn("APEX_HAS_NO_NUMERIC_NOTIONAL_OUTPUT", envelope["failed_checks"])

    def test_sentiment_records_do_not_count_as_crypto_quote_sources(self):
        quote = {
            "fresh": True,
            "timestamp": iso_before(1),
            "path": "test",
            "age_seconds": 1,
            "max_age_seconds": 15,
            "quote_source_count": 1,
            "fresh_quote_source_count": 1,
            "source_conflict": False,
            "has_bid_ask_last": True,
            "scanner_refresh_timestamp": iso_before(1),
            "payload": {
                "bid": 100.0,
                "ask": 100.1,
                "last": 100.05,
                "crypto_buying_power_usd": 10.97,
                "requested_notional_usd": None,
            },
        }
        sources = {
            "Stocktwits": {
                "sentiment": {"label": "BULLISH", "score": 80, "retrieved_at": iso_before(1)},
                "symbol_pulse": {"price": 100.05, "retrieved_at": iso_before(1)},
            }
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertEqual(envelope["market_input"]["fresh_quote_source_count"], 1)
        self.assertIn("required Robinhood crypto quote source not satisfied", " ".join(envelope["failed_checks"]))

    def test_load_crypto_quote_requires_fresh_robinhood_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            alpaca = Path(tmp) / "alpaca_crypto_quote_snapshot.json"
            robinhood = Path(tmp) / "robinhood_crypto_quote_snapshot.json"
            sample = Path(tmp) / "sample_crypto_input.json"
            base = {
                "asset_class": "CRYPTO",
                "symbol": "BTC",
                "quote_timestamp": iso_before(1),
                "bid": 100.0,
                "ask": 100.1,
                "last": 100.05,
            }
            scanner.write_json(alpaca, {**base, "provider": "Alpaca"})
            scanner.write_json(robinhood, {**base, "provider": "Robinhood"})
            scanner.write_json(sample, {**base, "provider": "Robinhood", "bid": 1.0, "ask": 1.1, "last": 1.05})
            with patch.object(scanner, "CRYPTO_QUOTE_INPUTS", [alpaca, robinhood, sample]):
                result = scanner.load_crypto_quote("BTC")
        self.assertTrue(result["required_quote_quorum_ok"])
        self.assertEqual(result["fresh_quote_source_count"], 1)
        self.assertEqual(result["fresh_optional_quote_source_count"], 2)
        self.assertFalse(result["source_conflict"])

    def test_load_crypto_quote_blocks_missing_required_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            alpaca = Path(tmp) / "alpaca_crypto_quote_snapshot.json"
            scanner.write_json(alpaca, {
                "asset_class": "CRYPTO",
                "symbol": "BTC",
                "quote_timestamp": iso_before(1),
                "provider": "Alpaca",
                "bid": 100.0,
                "ask": 100.1,
                "last": 100.05,
            })
            with patch.object(scanner, "CRYPTO_QUOTE_INPUTS", [alpaca]):
                result = scanner.load_crypto_quote("BTC")
        self.assertFalse(result["required_quote_quorum_ok"])
        self.assertEqual(result["missing_required_quote_sources"], ["Robinhood"])

    def test_apex_numeric_sizing_reaches_requested_notional(self):
        payload = {
            "crypto_buying_power_usd": 10000.0,
            "entry_price_usd": 100.0,
            "invalidation_price_usd": 90.0,
            "minimum_position_size_usd": 1.0,
        }
        settings = {
            "capital": {"max_risk_per_action_decimal": 0.01},
            "asset_limits": {"crypto_max_allocation_decimal": 0.2},
            "broker": {"minimum_order_value_usd": 1.0},
        }
        amount, source, inputs = scanner.apex_requested_notional(payload, settings, "CRYPTO")
        self.assertEqual(amount, 1000.0)
        self.assertEqual(source, "APEX_CAPITAL_RULES_POSITION_SIZING_FORMULA")
        self.assertEqual(inputs["position_quantity"], 10)

    def test_apex_numeric_sizing_cannot_exceed_verified_crypto_buying_power(self):
        payload = {
            "crypto_buying_power_usd": 10.97,
            "entry_price_usd": 100.0,
            "invalidation_price_usd": 99.99,
            "minimum_position_size_usd": 1.0,
        }
        settings = {
            "capital": {"max_risk_per_action_decimal": 0.5},
            "asset_limits": {"crypto_max_allocation_decimal": 0.2},
            "broker": {"minimum_order_value_usd": 1.0},
        }
        amount, source, _inputs = scanner.apex_requested_notional(payload, settings, "CRYPTO")
        self.assertIsNone(amount)
        self.assertEqual(source, "APEX_NUMERIC_NOTIONAL_EXCEEDS_LIMITS")

    def test_missing_apex_sizing_remains_no_action_reason(self):
        payload = {
            "crypto_buying_power_usd": 10.97,
            "entry_price_usd": 100.0,
        }
        settings = {
            "capital": {"max_risk_per_action_decimal": 0.01},
            "asset_limits": {"crypto_max_allocation_decimal": 0.2},
        }
        amount, source, inputs = scanner.apex_requested_notional(payload, settings, "CRYPTO")
        self.assertIsNone(amount)
        self.assertEqual(source, "APEX_HAS_NO_NUMERIC_NOTIONAL_OUTPUT")
        self.assertIsNone(inputs["invalidation_distance_usd"])

    def test_tradingcursor_apex_fields_map_entry_and_stop_loss(self):
        fields = scanner.tradingcursor_apex_fields({
            "usable": True,
            "analysis": {
                "potentialPosition": {
                    "entryPrice": 100.0,
                    "stopLoss": 95.0,
                }
            },
        })
        self.assertEqual(fields["entry_price_usd"], 100.0)
        self.assertEqual(fields["invalidation_price_usd"], 95.0)
        self.assertEqual(fields["stop_distance_usd"], 5.0)

    def test_zero_stop_distance_rejected(self):
        payload = {
            "crypto_buying_power_usd": 10000.0,
            "entry_price_usd": 100.0,
            "invalidation_price_usd": 100.0,
        }
        settings = {
            "capital": {"max_risk_per_action_decimal": 0.01},
            "asset_limits": {"crypto_max_allocation_decimal": 0.2},
        }
        amount, source, inputs = scanner.apex_requested_notional(payload, settings, "CRYPTO")
        self.assertIsNone(amount)
        self.assertEqual(source, "APEX_NUMERIC_NOTIONAL_REJECTED_BY_FORMULA")
        self.assertEqual(inputs["invalidation_distance_usd"], 0.0)

    def test_stale_apex_provenance_rejected_by_source_record(self):
        stale = iso_before(scanner.MAX_SOURCE_AGE_SECONDS + 30)
        record = scanner.source_record("APEX.crypto_quote_file", {"timestamp": stale, "usable": True})
        self.assertEqual(record["status"], "stale_or_unusable")

    def test_stale_tradingcursor_provenance_rejected_by_source_record(self):
        stale = iso_before(scanner.MAX_SOURCE_AGE_SECONDS + 30)
        record = scanner.source_record("TradingCursor.analysis", {"retrieved_at": stale, "usable": True, "status": "completed"})
        self.assertEqual(record["status"], "stale_or_unusable")

    def test_execution_allowed_remains_false_without_gate_pass(self):
        quote = {
            "fresh": True,
            "timestamp": iso_before(1),
            "path": "test",
            "age_seconds": 1,
            "max_age_seconds": 15,
            "quote_source_count": 2,
            "fresh_quote_source_count": 2,
            "source_conflict": False,
            "has_bid_ask_last": True,
            "scanner_refresh_timestamp": iso_before(1),
            "payload": {
                "bid": 100.0,
                "ask": 100.1,
                "last": 100.05,
                "crypto_buying_power_usd": 10.97,
            },
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertFalse(envelope["plugins_execute_trades"])
        self.assertFalse(envelope["broker_order_submitted"])
        self.assertFalse(envelope["requested_codex_activation"])

    def test_valid_sizing_still_leaves_execution_disabled_until_gate_passes(self):
        quote = self.quote(payload={"entry_price_usd": None, "invalidation_price_usd": None})
        sources = {
            "TradingCursor": {
                "status": "completed",
                "analysis": {
                    "usable": True,
                    "status": "completed",
                    "retrieved_at": iso_before(1),
                    "analysis": {
                        "potentialPosition": {"entryPrice": 100.0, "stopLoss": 90.0}
                    },
                },
            },
            "Stocktwits": {"sentiment": {"label": "BEARISH", "score": 26, "retrieved_at": iso_before(1)}},
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertEqual(envelope["market_input"]["requested_notional_usd"], 1000.0)
        self.assertFalse(envelope["plugins_execute_trades"])
        self.assertFalse(envelope["broker_order_submitted"])
        self.assertFalse(envelope["plugins_execute_trades"])

    def test_tradingcursor_cooldown_does_not_block_when_required_sources_pass(self):
        sources = {
            "TradingCursor": {
                "status": "rejected",
                "analysis": {"usable": False, "status": "cooldown", "retrieved_at": iso_before(1)},
            }
        }
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=self.quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertNotIn("TradingCursor unavailable due to plan or cooldown", envelope["failed_checks"])
        self.assertIn("TradingCursor.analysis", [item["source"] for item in envelope["unavailable_optional_sources"]])

    def test_stocktwits_bearish_sentiment_does_not_block_unless_apex_requires_it(self):
        sources = {"Stocktwits": {"sentiment": {"label": "BEARISH", "score": 1, "retrieved_at": iso_before(1)}}}
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=self.quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], sources, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertNotIn("Stocktwits sentiment is not positive", envelope["failed_checks"])

    def test_fresh_robinhood_quote_satisfies_required_source(self):
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=self.quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertEqual(envelope["fresh_quote_source_count"], 1)
        self.assertTrue(envelope["market_input"]["scanner_quote_stream"]["required_quote_quorum_ok"])

    def test_missing_robinhood_data_blocks_viability(self):
        quote = self.quote(
            fresh_quote_source_count=0,
            required_quote_quorum_ok=False,
            missing_required_quote_sources=["Robinhood"],
            required_quote_sources={},
        )
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertFalse(envelope["scanner_viable"])
        self.assertIn("required Robinhood crypto quote source not satisfied: missing Robinhood", envelope["failed_checks"])

    def test_missing_apex_stop_blocks_viability(self):
        quote = self.quote(payload={"invalidation_price_usd": None, "stop_distance_usd": None})
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=quote), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertFalse(envelope["scanner_viable"])
        self.assertIn("APEX_HAS_NO_NUMERIC_NOTIONAL_OUTPUT", envelope["failed_checks"])

    def test_no_order_tool_is_called_or_enabled(self):
        with patch.object(scanner, "load_active_crypto_symbol", return_value=("BTC", {"active_symbol_reason": "test"})), \
             patch.object(scanner, "load_crypto_quote", return_value=self.quote()), \
             patch.object(scanner, "load_crypto_capital_snapshot", return_value={}):
            envelope = scanner.build_non_executable_envelope([], {}, "AVAILABLE_IF_VIABILITY_GATES_TRUE", "primary")
        self.assertFalse(envelope["plugins_execute_trades"])
        self.assertFalse(envelope["broker_order_submitted"])


if __name__ == "__main__":
    unittest.main()
