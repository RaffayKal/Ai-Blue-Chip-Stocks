#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import medium_market_orchestrator as orchestrator


def iso_before(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


class MediumMarketOrchestratorTests(unittest.TestCase):
    def test_blue_chip_watchlist_has_no_crypto_pairs(self):
        stocks, crypto_from_combined_routes = orchestrator.symbols()
        blue_chip_symbols = orchestrator.WATCHLIST.read_text().splitlines()
        self.assertIn("AAPL", stocks)
        self.assertIn("BTC/USD", crypto_from_combined_routes)
        self.assertFalse(any("/" in symbol.strip() for symbol in blue_chip_symbols if symbol.strip()))

    def test_separate_crypto_watchlist_contains_approved_pairs(self):
        self.assertEqual(orchestrator.read_crypto_symbols(), ["BTC/USD", "ETH/USD"])

    def test_paper_buying_power_labeled_paper(self):
        with patch.object(orchestrator, "alpaca_request", return_value={
            "buying_power": "400000",
            "crypto_buying_power": "1000",
        }):
            status = orchestrator.alpaca_capital_status()
        self.assertEqual(status["label"], "capital")
        self.assertEqual(status["account_type"], "paper")
        self.assertEqual(status["buying_power_usd"], 400000.0)
        self.assertEqual(status["crypto_buying_power_usd"], 1000.0)
        self.assertEqual(status["status"], "OK")

    def test_missing_crypto_buying_power_is_no_action(self):
        with patch.object(orchestrator, "alpaca_request", return_value={"buying_power": "400000"}):
            status = orchestrator.alpaca_capital_status()
        self.assertEqual(status["status"], "NO ACTION")
        self.assertIn("crypto_buying_power_usd", status["missing"])
        self.assertNotEqual(status["crypto_buying_power_usd"], status["buying_power_usd"])

    def test_stale_quote_rejected(self):
        quote = orchestrator.normalize_quote(
            "AAPL",
            "stock",
            {"bp": "100", "ap": "100.2", "t": iso_before(orchestrator.MAX_AGE + 60)},
            {"p": "100.1", "t": iso_before(5)},
        )
        self.assertFalse(quote["ok"])
        self.assertTrue(quote["stale"])
        self.assertGreater(quote["age_seconds"], orchestrator.MAX_AGE)

    def test_valid_fresh_quote_uses_latest_trade_for_last(self):
        quote = orchestrator.normalize_quote(
            "AAPL",
            "stock",
            {"bp": "100", "ap": "100.2", "t": iso_before(5)},
            {"p": "100.1", "t": iso_before(4)},
        )
        self.assertTrue(quote["ok"])
        self.assertFalse(quote["stale"])
        self.assertEqual(quote["last"], 100.1)
        self.assertEqual(quote["last_source"], "latest_trade")

    def test_execution_allowed_always_false_even_when_scan_viable(self):
        with patch.object(orchestrator, "symbols", return_value=(["AAPL"], [])), \
             patch.object(orchestrator, "alpaca_market_session", return_value={
                 "market_session": "OPEN",
                 "market_session_source": "alpaca_clock",
                 "raw": {},
             }), \
             patch.object(orchestrator, "alpaca_capital_status", return_value={
                 "label": "capital",
                 "account_type": "paper",
                 "status": "OK",
                 "buying_power_usd": 400000.0,
                 "crypto_buying_power_usd": 1000.0,
                 "missing": [],
             }), \
             patch.object(orchestrator, "latest_trades", return_value={
                 "AAPL": {"p": "100.1", "t": iso_before(3)}
             }), \
             patch.object(orchestrator, "alpaca_get", return_value={
                 "quotes": {"AAPL": {"bp": "100", "ap": "100.2", "t": iso_before(2)}}
             }), \
             patch.object(orchestrator, "print_stale_quote_diagnostics"):
            result = orchestrator.scan()
        self.assertTrue(result["data_viable"])
        self.assertTrue(result["scanner_viable"])
        self.assertFalse(result["execution_allowed"])

    def test_execution_allowed_false_when_crypto_buying_power_unavailable(self):
        with patch.object(orchestrator, "symbols", return_value=(["AAPL"], [])), \
             patch.object(orchestrator, "alpaca_market_session", return_value={
                 "market_session": "OPEN",
                 "market_session_source": "alpaca_clock",
                 "raw": {},
             }), \
             patch.object(orchestrator, "alpaca_capital_status", return_value={
                 "label": "capital",
                 "account_type": "paper",
                 "status": "NO ACTION",
                 "buying_power_usd": 400000.0,
                 "crypto_buying_power_usd": None,
                 "missing": ["crypto_buying_power_usd"],
             }), \
             patch.object(orchestrator, "latest_trades", return_value={
                 "AAPL": {"p": "100.1", "t": iso_before(3)}
             }), \
             patch.object(orchestrator, "alpaca_get", return_value={
                 "quotes": {"AAPL": {"bp": "100", "ap": "100.2", "t": iso_before(2)}}
             }), \
             patch.object(orchestrator, "print_stale_quote_diagnostics"):
            result = orchestrator.scan()
        self.assertTrue(result["data_viable"])
        self.assertFalse(result["scanner_viable"])
        self.assertFalse(result["execution_allowed"])

    def test_closed_equity_market_explains_expected_stale_quotes(self):
        stale_quote = orchestrator.normalize_quote(
            "AAPL",
            "stock",
            {"bp": "100", "ap": "100.2", "t": iso_before(orchestrator.MAX_AGE + 60)},
            {"p": "100.1", "t": iso_before(3)},
        )
        status = orchestrator.lane_data_status([stale_quote], "stock", "CLOSED")
        self.assertEqual(status["status"], "NO ACTION")
        self.assertEqual(status["reason"], "stale equity quotes are expected outside market hours")

    def test_crypto_lane_is_independent_24_7(self):
        equity = orchestrator.normalize_quote(
            "AAPL",
            "stock",
            {"bp": "100", "ap": "100.2", "t": iso_before(orchestrator.MAX_AGE + 60)},
            {"p": "100.1", "t": iso_before(3)},
        )
        crypto = orchestrator.normalize_quote(
            "BTC/USD",
            "crypto",
            {"bp": "100000", "ap": "100010", "t": iso_before(2)},
            {"p": "100005", "t": iso_before(1)},
        )
        self.assertEqual(orchestrator.lane_data_status([equity, crypto], "stock", "CLOSED")["status"], "NO ACTION")
        self.assertEqual(orchestrator.lane_data_status([equity, crypto], "crypto", "CLOSED")["status"], "OK")

    def test_data_viable_can_be_true_when_only_crypto_lane_is_fresh(self):
        with patch.object(orchestrator, "symbols", return_value=(["AAPL"], ["BTC/USD"])), \
             patch.object(orchestrator, "alpaca_market_session", return_value={
                 "market_session": "CLOSED",
                 "market_session_source": "alpaca_clock",
                 "raw": {},
             }), \
             patch.object(orchestrator, "alpaca_capital_status", return_value={
                 "label": "capital",
                 "account_type": "paper",
                 "status": "NO ACTION",
                 "buying_power_usd": 400000.0,
                 "crypto_buying_power_usd": None,
                 "missing": ["crypto_buying_power_usd"],
             }), \
             patch.object(orchestrator, "latest_trades", side_effect=[
                 {"AAPL": {"p": "100.1", "t": iso_before(3)}},
                 {"BTC/USD": {"p": "100005", "t": iso_before(1)}},
             ]), \
             patch.object(orchestrator, "alpaca_get", side_effect=[
                 {"quotes": {"AAPL": {"bp": "100", "ap": "100.2", "t": iso_before(orchestrator.MAX_AGE + 60)}}},
                 {"quotes": {"BTC/USD": {"bp": "100000", "ap": "100010", "t": iso_before(2)}}},
             ]), \
             patch.object(orchestrator, "print_stale_quote_diagnostics"):
            result = orchestrator.scan()
        self.assertTrue(result["data_viable"])
        self.assertFalse(result["scanner_viable"])
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(result["equity_data_status"]["reason"], "stale equity quotes are expected outside market hours")
        self.assertEqual(result["crypto_data_status"]["status"], "OK")


if __name__ == "__main__":
    unittest.main()
