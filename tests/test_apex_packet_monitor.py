#!/usr/bin/env python3
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import sys

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
BLUE_CHIP_STOCKS_TOOL_CACHE = Path("/Users/raffaykal/.codex/cache/codex_apps_tools/027177012f23aef4b50848614ac1ef5465cf3c97.json")
BLUE_CHIP_STOCKS_PLUGIN_META = Path("/Users/raffaykal/.codex/plugins/cache/created-by-me-remote/dev-6aa6d5085e9881918fd038256bf08a06/1.0.0/.codex-plugin/plugin.json")
sys.path.insert(0, str(ROOT / "algorithms"))

import apex_packet_monitor as monitor
import autonomous_order_gate


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def viable_envelope() -> dict:
    ts = now()
    return {
        "envelope_id": "env-1",
        "idempotency_key": "env-1:AAPL:test",
        "created_by": "CHATGPT_PLUGIN_SCANNER",
        "user_algorithm_id": monitor.USER_ALGORITHM_ID,
        "scanner_viable": True,
        "requested_codex_activation": True,
        "plugins_execute_trades": False,
        "broker_order_submitted": False,
        "candidate_decision": "WATCHLIST ONLY",
        "apex_score": 88,
        "confidence": 0.82,
        "technical_state": {"trend": "confirmed"},
        "fundamental_state": {"quality": "confirmed"},
        "catalyst_news_state": {"catalyst": "confirmed"},
        "volatility": {"state": "bounded"},
        "invalidation_conditions": ["quote stale", "source conflict"],
        "supporting_evidence": [{"source": "mock scanner", "timestamp": ts}],
        "data_provenance": [
            {"source": "source-a", "timestamp": ts, "status": "fresh"},
            {"source": "source-b", "timestamp": ts, "status": "fresh"},
        ],
        "market_input": {
            "symbol": "AAPL",
            "asset_class": "US_EQUITY",
            "session": "REGULAR",
            "venue": "NASDAQ",
            "broker_name": "Robinhood",
            "timestamp": ts,
            "quote_timestamp": ts,
            "bid": 200.0,
            "ask": 200.1,
            "last": 200.05,
            "liquidity_usd": 10000000,
            "data_status": "fresh",
            "risk_status": "pass",
            "source_count": 2,
            "source_conflict": False,
            "buying_power_usd": 25.0,
            "requested_notional_usd": 1.0,
            "fractional_shares_supported": True,
            "fractional_asset_eligible": True,
            "margin_requested": False,
            "margin_approved": False,
            "account_net_worth_usd": 25.0,
            "explicit_execution_authorization": False,
        },
    }


class ApexPacketMonitorTests(unittest.TestCase):
    def config(self, temp: Path) -> dict:
        return {
            "scanner_output_path": str(temp / "scanner.json"),
            "state_path": str(temp / "state.json"),
            "log_path": str(temp / "monitor.jsonl"),
            "transport": {"type": "local_file", "inbox_dir": str(temp / "inbox")},
            "loop": {"interval_seconds": 1, "max_iterations": 1},
            "freshness": {"max_quote_age_seconds": 180, "max_provenance_age_seconds": 300},
            "viability": {"min_apex_score": 75, "min_confidence": 0.65},
            "retry": {"max_attempts": 1, "base_backoff_seconds": 0, "max_backoff_seconds": 0},
            "rate_limit": {"min_emit_interval_seconds": 0},
            "circuit_breaker": {"failure_threshold": 2, "cooldown_seconds": 60},
            "heartbeat": {"path": str(temp / "health.json")},
        }

    def test_default_false_stays_silent(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            cfg = self.config(temp)
            env = viable_envelope()
            env["scanner_viable"] = False
            write_json(Path(cfg["scanner_output_path"]), env)
            with patch.object(monitor.Path, "cwd", return_value=monitor.ROOT):
                self.assertEqual(monitor.monitor_once(cfg), "viable_false")
            self.assertFalse((temp / "inbox").exists())

    def test_viable_packet_activates_but_still_requires_execution_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            cfg = self.config(temp)
            write_json(Path(cfg["scanner_output_path"]), viable_envelope())
            with patch.object(monitor.Path, "cwd", return_value=monitor.ROOT):
                self.assertEqual(monitor.monitor_once(cfg), "packet_emitted")
            packets = list((temp / "inbox").glob("*.json"))
            self.assertEqual(len(packets), 1)
            packet = json.loads(packets[0].read_text(encoding="utf-8"))
            self.assertTrue(packet["viable"])
            self.assertEqual(packet["codex_directive"], "ACTIVATE_AGENTIC_WORKFLOW")
            self.assertEqual(packet["execution_authority"], "GATED_BY_EXISTING_APEX_BROKER_RISK_RUNTIME_CHECKS")
            self.assertFalse(packet["execution_allowed"])
            self.assertTrue(packet["execution_gate_required"])
            self.assertTrue(packet["codex_revalidation_required"])

    def test_duplicate_idempotency_key_does_not_emit_again(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            cfg = self.config(temp)
            write_json(Path(cfg["scanner_output_path"]), viable_envelope())
            with patch.object(monitor.Path, "cwd", return_value=monitor.ROOT):
                self.assertEqual(monitor.monitor_once(cfg), "packet_emitted")
                self.assertEqual(monitor.monitor_once(cfg), "deduplicated")
            self.assertEqual(len(list((temp / "inbox").glob("*.json"))), 1)

    def test_contradiction_blocks_packet(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            cfg = self.config(temp)
            env = viable_envelope()
            env["market_input"]["source_conflict"] = True
            write_json(Path(cfg["scanner_output_path"]), env)
            with patch.object(monitor.Path, "cwd", return_value=monitor.ROOT):
                self.assertEqual(monitor.monitor_once(cfg), "viable_false")
            self.assertFalse((temp / "inbox").exists())

    def run_order_gate(self, temp: Path, market_input: dict, order_ticket: dict, execution_log: dict | None = None) -> str:
        market_path = temp / "market.json"
        ticket_path = temp / "ticket.json"
        settings_path = temp / "user_settings.json"
        intake_path = temp / "brokerage_intake.json"
        log_path = temp / "execution_log.json"
        manifest_path = temp / "algorithm_sources.json"

        write_json(market_path, market_input)
        write_json(ticket_path, order_ticket)
        write_json(settings_path, {
            "capital": {"capital_source": "CONNECTED_BROKER_RUNTIME_ONLY"},
            "asset_limits": {"crypto_max_allocation_decimal": 0.2, "us_equity_max_allocation_decimal": 0.2},
            "broker": {"explicit_execution_authorization": True},
            "risk_limits": {"single_crypto_all_in_blocked": True, "single_stock_all_in_blocked": True},
        })
        write_json(intake_path, {
            "explicit_execution_authorization": True,
            "verified_agentic_account": {"crypto_buying_power_usd": 25.0, "buying_power_usd": 25.0},
            "minimum_order_value_usd": "1.00",
            "margin_approved": False,
        })
        write_json(log_path, execution_log or {"executions": []})
        write_json(manifest_path, {
            "root": str(monitor.ROOT),
            "required_algorithm_files": ["algorithms/capital_engine.py", "algorithms/autonomous_order_gate.py"],
        })

        stdout = StringIO()
        argv = ["autonomous_order_gate.py", str(market_path), str(ticket_path)]
        with patch.object(autonomous_order_gate.Path, "cwd", return_value=monitor.ROOT), \
             patch.object(autonomous_order_gate, "USER_SETTINGS", settings_path), \
             patch.object(autonomous_order_gate, "BROKERAGE_INTAKE", intake_path), \
             patch.object(autonomous_order_gate, "EXECUTION_LOG", log_path), \
             patch.object(autonomous_order_gate, "ALGORITHM_SOURCES", manifest_path), \
             patch.object(sys, "argv", argv), \
             redirect_stdout(stdout):
            try:
                autonomous_order_gate.main()
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
        return stdout.getvalue()

    def crypto_market_input(self) -> dict:
        ts = now()
        return {
            "symbol": "BTC",
            "asset_class": "CRYPTO",
            "session": "CRYPTO_24_7",
            "venue": "Robinhood Crypto",
            "broker_name": "Robinhood",
            "timestamp": ts,
            "quote_timestamp": ts,
            "bid": 100000.0,
            "ask": 100050.0,
            "last": 100025.0,
            "liquidity_usd": 1000000,
            "data_status": "fresh",
            "risk_status": "pass",
            "source_count": 2,
            "source_conflict": False,
            "crypto_buying_power_usd": 25.0,
            "requested_notional_usd": 1.0,
            "crypto_account_confirmed": True,
            "maintenance_active": False,
            "account_restricted": False,
            "margin_requested": False,
            "margin_approved": False,
            "account_net_worth_usd": 25.0,
            "explicit_execution_authorization": True,
        }

    def crypto_buy_ticket(self) -> dict:
        return {
            "autonomous_execution": True,
            "user_algorithm_id": monitor.USER_ALGORITHM_ID,
            "symbol": "BTC",
            "asset_class": "CRYPTO",
            "venue": "Robinhood Crypto",
            "side": "buy",
            "type": "market",
            "dollar_amount": "1.00",
            "requires_preview": True,
            "requires_algorithm_result": "VALIDATED SETUP",
            "ticket_id": "test-ticket",
            "max_executions": 7,
        }

    def equity_market_input(self) -> dict:
        ts = now()
        return {
            "symbol": "AAPL",
            "asset_class": "US_EQUITY",
            "session": "REGULAR",
            "venue": "NASDAQ",
            "broker_name": "Robinhood",
            "timestamp": ts,
            "quote_timestamp": ts,
            "bid": 200.0,
            "ask": 200.1,
            "last": 200.05,
            "liquidity_usd": 10000000,
            "data_status": "fresh",
            "risk_status": "pass",
            "source_count": 2,
            "source_conflict": False,
            "buying_power_usd": 25.0,
            "requested_notional_usd": 1.0,
            "fractional_shares_supported": True,
            "fractional_asset_eligible": True,
            "margin_requested": False,
            "margin_approved": False,
            "account_net_worth_usd": 25.0,
            "explicit_execution_authorization": True,
        }

    def equity_buy_ticket(self) -> dict:
        return {
            "autonomous_execution": True,
            "user_algorithm_id": monitor.USER_ALGORITHM_ID,
            "symbol": "AAPL",
            "asset_class": "US_EQUITY",
            "venue": "NASDAQ",
            "side": "buy",
            "type": "market",
            "dollar_amount": "1.00",
            "requires_preview": True,
            "requires_algorithm_result": "VALIDATED SETUP",
            "ticket_id": "test-equity-ticket",
            "max_executions": 7,
        }

    def test_failed_broker_or_risk_checks_cannot_execute(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            market_input = self.crypto_market_input()
            market_input["risk_status"] = "fail"
            output = self.run_order_gate(temp, market_input, self.crypto_buy_ticket())
            self.assertIn("AUTONOMOUS_DECISION: NO ACTION", output)
            self.assertIn("EXECUTION_ALLOWED: false", output)
            self.assertIn("ALGORITHM_RESULT: NO ACTION", output)

    def test_fully_valid_authorized_state_reaches_execution_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            output = self.run_order_gate(temp, self.crypto_market_input(), self.crypto_buy_ticket())
            self.assertIn("AUTONOMOUS_DECISION: APPROVED_FOR_PREVIEW_AND_PLACEMENT", output)
            self.assertIn("EXECUTION_ALLOWED: true", output)
            self.assertIn("NEXT_ALLOWED_STEP: preview Blue Chip Stocks crypto order, then place only that previewed order if the runtime permits it", output)

    def test_fractional_equity_authorized_state_reaches_blue_chip_stocks_review_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            output = self.run_order_gate(temp, self.equity_market_input(), self.equity_buy_ticket())
            self.assertIn("AUTONOMOUS_DECISION: APPROVED_FOR_PREVIEW_AND_PLACEMENT", output)
            self.assertIn("EXECUTION_ALLOWED: true", output)
            self.assertIn("NEXT_ALLOWED_STEP: review Blue Chip Stocks equity order, then place only that reviewed order if the runtime permits it", output)

    def test_blue_chip_stocks_runtime_contract_has_conditional_order_workflow(self):
        self.assertTrue(BLUE_CHIP_STOCKS_PLUGIN_META.is_file())
        cache = json.loads(BLUE_CHIP_STOCKS_TOOL_CACHE.read_text(encoding="utf-8"))
        tools = {}

        def collect(value):
            if isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                if value.get("connector_name") == "Blue Chip Stocks" and value.get("tool_name"):
                    tools[value["tool_name"]] = value.get("tool", {})
                for item in value.values():
                    collect(item)

        collect(cache)
        for name in ["_review_equity_order", "_place_equity_order", "_preview_crypto_order", "_place_crypto_order"]:
            self.assertIn(name, tools)

        combined = "\n".join(json.dumps(tools[name], sort_keys=True) for name in tools)
        self.assertNotIn("VALIDATE_ONLY", combined)
        self.assertNotIn("execution_authority=false", combined)
        self.assertNotIn("manual-confirmation-only", combined)
        self.assertIn("Requires an agentic_allowed=true account", tools["_review_equity_order"]["description"])
        self.assertIn("Requires an agentic-enabled crypto account", tools["_preview_crypto_order"]["description"])
        self.assertIn("Call this by default before place_equity_order", tools["_review_equity_order"]["description"])
        self.assertIn("Call this by default before place_crypto_order", tools["_preview_crypto_order"]["description"])


if __name__ == "__main__":
    unittest.main()
