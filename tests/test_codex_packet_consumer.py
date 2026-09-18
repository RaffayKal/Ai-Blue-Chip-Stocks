#!/usr/bin/env python3
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "algorithms"))
import codex_packet_consumer as consumer
import apex_packet_monitor as monitor


def timestamp(offset=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset)).isoformat().replace("+00:00", "Z")


def packet(key="packet-1", viable=True, **runtime):
    value = {
        "packet_type": "APEX_PACKET",
        "viable": viable,
        "timestamp": timestamp(),
        "symbol": "AAPL",
        "opportunity_type": "BUY CANDIDATE",
        "market_data": {"asset_class": "US_EQUITY", "venue": "NASDAQ", "quote_timestamp": timestamp(), "bid": 200, "ask": 200.1, "last": 200.05, "data_status": "fresh", "source_count": 2},
        "capital": {"required": 1.0},
        "codex_directive": "ACTIVATE_AGENTIC_WORKFLOW",
        "execution_gate_required": True,
        "codex_revalidation_required": True,
        "idempotency_key": key,
        "execution_request": {"side": "buy", "type": "market", "dollar_amount": "1.00"},
        "runtime_revalidation": {
            "timestamp": timestamp(), "final_viability": True, "broker_state": "fresh", "market_state": "fresh",
            "instrument": "AAPL", "asset_class": "US_EQUITY", "venue": "NASDAQ", "quote": {"last": 200.05},
            "buying_power": 25, "position": "clear", "duplicate_order_state": "clear", "execution_eligibility": True,
        },
    }
    value["runtime_revalidation"].update(runtime)
    value["packet_hash"] = consumer.packet_hash(value)
    return value


class ConsumerTests(unittest.TestCase):
    def test_codex_result_uses_final_agent_message_only(self):
        output = "\n".join([
            json.dumps({"type": "item.completed", "item": {"type": "function_call_output", "output": "WOULD_EXECUTE"}}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "NO ACTION\nreason"}}),
        ])
        self.assertEqual(consumer.final_codex_message(output), "NO ACTION\nreason")

    def make(self, root, calls):
        def workflow(market, ticket, shadow):
            calls.append((market.read_text(encoding="utf-8"), ticket, shadow))
            return True, "EXECUTION_ALLOWED: true\nWOULD_EXECUTE"
        return consumer.Consumer(
            root / "inbox", root / "processing", root / "processed", root / "rejected",
            root / "state.json", root / "status.json", max_age=300, shadow=True, workflow=workflow,
        )

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_a_nonviable_rejected_without_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); self.write(root / "inbox" / "a.json", packet(viable=False)); self.assertEqual(c.once(), "rejected"); self.assertFalse(calls)

    def test_b_malformed_rejected_without_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); value = packet(); del value["packet_hash"]; self.write(root / "inbox" / "b.json", value); self.assertEqual(c.once(), "rejected"); self.assertFalse(calls)

    def test_c_duplicate_is_processed_once(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); value = packet("same-key"); self.write(root / "inbox" / "first.json", value); self.assertEqual(c.once(), "would_execute"); self.write(root / "inbox" / "second.json", value); self.assertEqual(c.once(), "rejected"); self.assertEqual(len(calls), 1)

    def test_d_options_hard_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); value = packet(asset_class="OPTIONS", options_requested=True); self.write(root / "inbox" / "d.json", value); self.assertEqual(c.once(), "rejected"); self.assertFalse(calls)

    def test_e_stale_packet_hard_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); value = packet(); value["timestamp"] = timestamp(-301); value["packet_hash"] = consumer.packet_hash({k: v for k, v in value.items() if k != "packet_hash"}); self.write(root / "inbox" / "e.json", value); self.assertEqual(c.once(), "rejected"); self.assertFalse(calls)

    def test_f_qualified_equity_shadow_would_execute(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); self.write(root / "inbox" / "f.json", packet()); self.assertEqual(c.once(), "would_execute"); self.assertEqual(len(calls), 1); self.assertTrue(calls[0][2]); self.assertEqual(len(list((root / "processed").glob("*.json"))), 1)

    def test_g_restart_cannot_reexecute_processed_packet(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls); self.write(root / "inbox" / "g.json", packet("restart-key")); self.assertEqual(c.once(), "would_execute"); restarted = self.make(root, calls); self.assertEqual(restarted.once(), "dormant"); self.assertEqual(len(calls), 1)

    def test_new_candidate_requires_robinhood_refresh_marker(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; c = self.make(root, calls)
            self.write(root / "inbox" / "refresh.json", packet())
            self.assertEqual(c.once(), "would_execute")
            market = (root / "processing" / "runtime_market_input.json")
            self.assertFalse(market.exists())
            self.assertIn("robinhood_mcp_refresh_required", calls[0][0])

    def test_end_to_end_monitor_to_consumer_shadow(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []; ts = timestamp()
            envelope = {
                "envelope_id": "e2e-envelope", "idempotency_key": "e2e-key", "created_by": "CHATGPT_PLUGIN_SCANNER",
                "user_algorithm_id": monitor.USER_ALGORITHM_ID, "scanner_viable": True, "requested_codex_activation": True,
                "plugins_execute_trades": False, "broker_order_submitted": False, "candidate_decision": "BUY CANDIDATE",
                "apex_score": 88, "confidence": 0.82,
                "data_provenance": [{"source": "a", "timestamp": ts, "status": "fresh"}, {"source": "b", "timestamp": ts, "status": "fresh"}],
                "market_input": {"symbol": "AAPL", "asset_class": "US_EQUITY", "session": "REGULAR", "venue": "NASDAQ", "broker_name": "Robinhood", "timestamp": ts, "quote_timestamp": ts, "bid": 200, "ask": 200.1, "last": 200.05, "liquidity_usd": 10000000, "data_status": "fresh", "risk_status": "pass", "source_count": 2, "source_conflict": False, "buying_power_usd": 25, "requested_notional_usd": 1, "fractional_shares_supported": True, "fractional_asset_eligible": True, "margin_requested": False, "margin_approved": False, "account_net_worth_usd": 25, "explicit_execution_authorization": False},
            }
            scanner = root / "scanner.json"; scanner.write_text(json.dumps(envelope), encoding="utf-8")
            config = {"scanner_output_path": str(scanner), "state_path": str(root / "monitor-state.json"), "log_path": str(root / "monitor.log"), "transport": {"type": "local_file", "inbox_dir": str(root / "inbox")}, "freshness": {"max_quote_age_seconds": 180, "max_provenance_age_seconds": 300}, "viability": {"min_apex_score": 75, "min_confidence": 0.65}, "rate_limit": {"min_emit_interval_seconds": 0}, "retry": {"max_attempts": 1, "base_backoff_seconds": 0, "max_backoff_seconds": 0}, "circuit_breaker": {"failure_threshold": 2, "cooldown_seconds": 60}, "heartbeat": {"path": str(root / "health.json")}}
            self.assertEqual(monitor.monitor_once(config), "packet_emitted")
            emitted = next((root / "inbox").glob("*.json"))
            c = self.make(root, calls)
            self.assertEqual(c.once(), "would_execute"); self.assertEqual(len(calls), 1); self.assertTrue(calls[0][2])


if __name__ == "__main__":
    unittest.main()
