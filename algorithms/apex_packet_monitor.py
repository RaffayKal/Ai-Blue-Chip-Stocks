#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from capital_engine import evaluate, load_json
from project_root import ROOT

DEFAULT_CONFIG = ROOT / "rules" / "apex_packet_monitor.template.json"
DEFAULT_STATE = ROOT / "data" / "apex_packet_monitor_state.json"
DEFAULT_SCANNER_OUTPUT = ROOT / "data" / "current_candidate_envelope.json"
DEFAULT_LOCAL_INBOX = ROOT / "data" / "codex_inbox"
DEFAULT_LOG = ROOT / "logs" / "apex_packet_monitor.jsonl"
LEGACY_MAC_ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")

USER_ALGORITHM_ID = "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING"
ALLOWED_DECISIONS = {
    "WATCHLIST ONLY",
    "HOLD CANDIDATE",
    "BUY CANDIDATE",
    "SELL CANDIDATE",
    "PARTIAL SELL CANDIDATE",
    "HUMAN APPROVAL REQUIRED",
    "RE-ENTER CANDIDATE",
}
BLOCKED_MARKET_RESULTS = {"NO ACTION", "NEEDS USER CAPITAL SETTINGS"}
BLOCKED_REQUEST_FLAGS = {
    "margin_requested": "margin requested",
    "short_requested": "short requested",
    "options_requested": "options requested",
    "leverage_requested": "leverage requested",
    "account_mutation_requested": "account mutation requested",
    "order_placement_requested": "order placement requested",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def age_seconds(value: Any) -> float | None:
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    return max(0.0, (utc_now() - parsed).total_seconds())


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def packet_hash(packet: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json(packet).encode("utf-8")).hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    config.setdefault("scanner_output_path", str(DEFAULT_SCANNER_OUTPUT))
    config.setdefault("state_path", str(DEFAULT_STATE))
    config.setdefault("log_path", str(DEFAULT_LOG))
    config.setdefault("transport", {"type": "local_file", "inbox_dir": str(DEFAULT_LOCAL_INBOX)})
    config.setdefault("loop", {"interval_seconds": 18000, "max_iterations": None})
    config.setdefault("freshness", {"max_quote_age_seconds": 180, "max_provenance_age_seconds": 300})
    config.setdefault("viability", {"min_apex_score": 75, "min_confidence": 0.65})
    config.setdefault("retry", {"max_attempts": 3, "base_backoff_seconds": 1.0, "max_backoff_seconds": 30.0})
    config.setdefault("rate_limit", {"min_emit_interval_seconds": 18000})
    config.setdefault("circuit_breaker", {"failure_threshold": 3, "cooldown_seconds": 900})
    config.setdefault("heartbeat", {"path": str(ROOT / "data" / "apex_packet_monitor_health.json")})
    for key in ("scanner_output_path", "state_path", "log_path"):
        config[key] = str(resolve_runtime_path(config[key]))
    transport = config.get("transport")
    if isinstance(transport, dict):
        for key in ("inbox_dir", "queue_dir", "resource_dir"):
            if key in transport:
                transport[key] = str(resolve_runtime_path(transport[key]))
    heartbeat = config.get("heartbeat")
    if isinstance(heartbeat, dict) and "path" in heartbeat:
        heartbeat["path"] = str(resolve_runtime_path(heartbeat["path"]))
    return config


def resolve_runtime_path(value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        try:
            return ROOT / path.relative_to(LEGACY_MAC_ROOT)
        except ValueError:
            return path
    return ROOT / path


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "emitted_idempotency_keys": [],
            "last_emit_at": None,
            "consecutive_transport_failures": 0,
            "circuit_open_until": None,
        }
    try:
        with path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
    except (json.JSONDecodeError, OSError):
        state = {}
    state.setdefault("emitted_idempotency_keys", [])
    state.setdefault("last_emit_at", None)
    state.setdefault("consecutive_transport_failures", 0)
    state.setdefault("circuit_open_until", None)
    return state


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def log_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": iso_now(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")


@dataclass
class GateResult:
    viable: bool
    failed: list[str]
    risk_flags: list[str]
    contradictions: list[str]
    market_decision: dict[str, Any]


def validate_freshness(envelope: dict[str, Any], config: dict[str, Any], failed: list[str]) -> str:
    freshness = config["freshness"]
    market_input = envelope.get("market_input") if isinstance(envelope.get("market_input"), dict) else {}
    quote_age = age_seconds(market_input.get("quote_timestamp") or market_input.get("timestamp"))
    if quote_age is None:
        failed.append("market quote timestamp missing or unparsable")
        return "failed"
    if quote_age > float(freshness["max_quote_age_seconds"]):
        failed.append(f"market quote stale: {quote_age:.0f}s old")
        return "failed"

    provenance = envelope.get("data_provenance")
    if not isinstance(provenance, list) or len(provenance) < 2:
        failed.append("data_provenance must contain at least two fresh sources")
        return "failed"
    for index, source in enumerate(provenance, start=1):
        if not isinstance(source, dict):
            failed.append(f"data_provenance[{index}] must be an object")
            continue
        if source.get("status") != "fresh":
            failed.append(f"data_provenance[{index}] is not fresh")
        source_age = age_seconds(source.get("timestamp"))
        if source_age is None:
            failed.append(f"data_provenance[{index}] timestamp missing or unparsable")
        elif source_age > float(freshness["max_provenance_age_seconds"]):
            failed.append(f"data_provenance[{index}] stale: {source_age:.0f}s old")
    return "fresh" if not failed else "failed"


def deterministic_gate(envelope: dict[str, Any], config: dict[str, Any]) -> GateResult:
    failed: list[str] = []
    risk_flags: list[str] = []
    contradictions: list[str] = []

    if envelope.get("user_algorithm_id") != USER_ALGORITHM_ID:
        failed.append(f"user_algorithm_id must be {USER_ALGORITHM_ID}")
    if envelope.get("scanner_viable") is not True:
        failed.append("scanner_viable is not true")
    if envelope.get("requested_codex_activation") is not True:
        failed.append("requested_codex_activation is not true")
    if envelope.get("plugins_execute_trades") is not False:
        failed.append("plugins_execute_trades must be false")
    if envelope.get("broker_order_submitted") is not False:
        failed.append("broker_order_submitted must be false")
    if envelope.get("candidate_decision") not in ALLOWED_DECISIONS:
        failed.append("candidate_decision is not an allowed plausible opportunity")

    if envelope.get("source_conflict") is True:
        contradictions.append("envelope source_conflict is true")
    if envelope.get("contradictions"):
        contradictions.extend([str(item) for item in envelope.get("contradictions")])

    market_input = envelope.get("market_input")
    if not isinstance(market_input, dict) or not market_input:
        failed.append("market_input missing")
        market_decision = {"RESULT": "NO ACTION", "FAILED_CHECKS": "market_input missing"}
    else:
        market_decision = evaluate(market_input)
        if market_decision["RESULT"] in BLOCKED_MARKET_RESULTS:
            failed.append(f"capital engine result is {market_decision['RESULT']}")
        if market_decision.get("FAILED_CHECKS") not in {"none", None, ""}:
            failed.append(f"capital engine failed checks: {market_decision['FAILED_CHECKS']}")
        if market_input.get("source_conflict") is True:
            contradictions.append("market_input source_conflict is true")
        for key, label in BLOCKED_REQUEST_FLAGS.items():
            if market_input.get(key) is True or envelope.get(key) is True:
                risk_flags.append(label)

    freshness = validate_freshness(envelope, config, failed)
    if freshness != "fresh":
        risk_flags.append("freshness failed")

    score = float(envelope.get("apex_score") or 0)
    confidence = float(envelope.get("confidence") or 0)
    if score < float(config["viability"]["min_apex_score"]):
        failed.append("apex_score below configured threshold")
    if confidence < float(config["viability"]["min_confidence"]):
        failed.append("confidence below configured threshold")

    if risk_flags:
        failed.extend([f"blocked risk flag: {flag}" for flag in risk_flags])
    if contradictions:
        failed.extend([f"contradiction: {item}" for item in contradictions])

    return GateResult(not failed, failed, risk_flags, contradictions, market_decision)


def build_packet(envelope: dict[str, Any], gate: GateResult, freshness: str) -> dict[str, Any]:
    market_input = envelope.get("market_input") if isinstance(envelope.get("market_input"), dict) else {}
    bid = market_input.get("bid")
    ask = market_input.get("ask")
    spread = None if bid is None or ask is None else float(ask) - float(bid)
    packet = {
        "packet_type": "APEX_PACKET",
        "viable": True,
        "timestamp": iso_now(),
        "symbol": market_input.get("symbol") or gate.market_decision.get("SYMBOL"),
        "opportunity_type": envelope.get("candidate_decision"),
        "market_data": {
            "asset_class": market_input.get("asset_class"),
            "session": market_input.get("session"),
            "venue": market_input.get("venue"),
            "bid": bid,
            "ask": ask,
            "last": market_input.get("last"),
            "quote_timestamp": market_input.get("quote_timestamp") or market_input.get("timestamp"),
            "source_count": market_input.get("source_count"),
            "data_status": market_input.get("data_status"),
        },
        "technical_state": envelope.get("technical_state", {}),
        "trend_state": envelope.get("trend_state", envelope.get("technical_state", {})),
        "multi_timeframe_state": envelope.get("multi_timeframe_state", {}),
        "appreciation_regime": envelope.get("appreciation_regime", {
            "past": envelope.get("past_appreciation_regime"),
            "present": envelope.get("present_appreciation_regime"),
            "projected": envelope.get("projected_appreciation_regime"),
        }),
        "fundamental_state": envelope.get("fundamental_state", {}),
        "catalyst_news_state": envelope.get("catalyst_news_state", envelope.get("news_state", {})),
        "catalyst_state": envelope.get("catalyst_state", envelope.get("catalyst_news_state", envelope.get("news_state", {}))),
        "liquidity": {
            "liquidity_usd": market_input.get("liquidity_usd"),
            "spread": spread,
        },
        "volatility": envelope.get("volatility", {}),
        "volatility_quality": envelope.get("volatility_quality", {}),
        "volume_state": envelope.get("volume_state", {}),
        "position_state": envelope.get("position_state", {
            "existing_position": market_input.get("existing_position"),
            "cost_basis": market_input.get("cost_basis"),
        }),
        "duplicate_entry_status": envelope.get("duplicate_entry_status", market_input.get("duplicate_entry_status")),
        "capital": {
            "required": envelope.get("capital_required", market_input.get("requested_notional_usd")),
            "at_risk": envelope.get("capital_at_risk", market_input.get("requested_notional_usd")),
            "available_trading_capital": market_input.get("available_trading_capital"),
        },
        "projection": {
            "continuation_estimate": envelope.get("continuation_estimate", envelope.get("continuation_probability")),
            "reversal_estimate": envelope.get("reversal_estimate", envelope.get("reversal_probability")),
            "expected_net_profit": envelope.get("expected_net_profit", market_input.get("expected_net_profit")),
            "confidence_decay_rate": envelope.get("confidence_decay_rate"),
        },
        "trigger_reason": envelope.get("trigger_reason"),
        "material_change_since_prior_state": envelope.get("material_change_since_prior_state"),
        "contradictions": gate.contradictions,
        "risk_flags": gate.risk_flags,
        "invalidation_conditions": envelope.get("invalidation_conditions", gate.failed),
        "apex_score": envelope.get("apex_score"),
        "confidence": envelope.get("confidence"),
        "freshness": freshness,
        "reasoning_summary": envelope.get(
            "reasoning_summary",
            "Deterministic gate passed on fresh scanner output; Codex must independently revalidate before entering broker-gated execution workflow.",
        ),
        "supporting_evidence": envelope.get("supporting_evidence", envelope.get("data_provenance", [])),
        "codex_directive": "ACTIVATE_AGENTIC_WORKFLOW",
        "execution_authority": "GATED_BY_EXISTING_APEX_BROKER_RISK_RUNTIME_CHECKS",
        "execution_allowed": False,
        "execution_gate_required": True,
        "codex_revalidation_required": True,
        "new_activation_requires_new_fresh_packet": True,
        "idempotency_key": envelope.get("idempotency_key"),
        "source_envelope_id": envelope.get("envelope_id"),
    }
    packet["packet_hash"] = packet_hash(packet)
    return packet


class Transport:
    def send(self, packet: dict[str, Any]) -> None:
        raise NotImplementedError


class LocalFileTransport(Transport):
    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir

    def send(self, packet: dict[str, Any]) -> None:
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        key = str(packet["idempotency_key"]).replace("/", "_").replace(":", "_")
        write_json(self.inbox_dir / f"{key}.json", packet)


class WebhookTransport(Transport):
    def __init__(self, url: str, timeout_seconds: float):
        self.url = url
        self.timeout_seconds = timeout_seconds

    def send(self, packet: dict[str, Any]) -> None:
        body = json.dumps(packet, sort_keys=True).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status >= 300:
                raise RuntimeError(f"webhook returned HTTP {response.status}")


class QueueTransport(LocalFileTransport):
    pass


class McpResourceTransport(LocalFileTransport):
    pass


def make_transport(config: dict[str, Any]) -> Transport:
    transport = config["transport"]
    kind = transport.get("type", "local_file")
    if kind == "local_file":
        return LocalFileTransport(Path(transport.get("inbox_dir") or DEFAULT_LOCAL_INBOX))
    if kind == "webhook":
        endpoint = os.environ.get(str(transport.get("url_env") or "")) or transport.get("url")
        if not endpoint:
            raise RuntimeError("webhook transport requires url or url_env")
        return WebhookTransport(endpoint, float(transport.get("timeout_seconds", 10)))
    if kind == "queue":
        return QueueTransport(Path(transport.get("queue_dir") or transport.get("inbox_dir") or DEFAULT_LOCAL_INBOX))
    if kind == "mcp_resource":
        return McpResourceTransport(Path(transport.get("resource_dir") or transport.get("inbox_dir") or DEFAULT_LOCAL_INBOX))
    raise RuntimeError(f"unknown transport type: {kind}")


def circuit_is_open(state: dict[str, Any]) -> bool:
    until = parse_timestamp(state.get("circuit_open_until"))
    return until is not None and utc_now() < until


def rate_limited(state: dict[str, Any], config: dict[str, Any]) -> bool:
    last_emit = parse_timestamp(state.get("last_emit_at"))
    if last_emit is None:
        return False
    minimum = float(config["rate_limit"]["min_emit_interval_seconds"])
    return (utc_now() - last_emit).total_seconds() < minimum


def send_with_retries(transport: Transport, packet: dict[str, Any], config: dict[str, Any]) -> None:
    retry = config["retry"]
    max_attempts = int(retry["max_attempts"])
    backoff = float(retry["base_backoff_seconds"])
    max_backoff = float(retry["max_backoff_seconds"])
    for attempt in range(1, max_attempts + 1):
        try:
            transport.send(packet)
            return
        except (OSError, RuntimeError, urllib.error.URLError) as exc:
            if attempt == max_attempts:
                raise RuntimeError(f"transport failed after {max_attempts} attempts: {exc}") from exc
            time.sleep(min(backoff, max_backoff))
            backoff *= 2


def monitor_once(config: dict[str, Any]) -> str:
    if Path.cwd() != ROOT:
        return "dormant_wrong_directory"

    state_path = Path(config["state_path"])
    log_path = Path(config["log_path"])
    state = read_state(state_path)

    heartbeat_path = Path(config["heartbeat"]["path"])
    write_json(heartbeat_path, {"timestamp": iso_now(), "status": "running", "circuit_open": circuit_is_open(state)})

    if circuit_is_open(state):
        log_event(log_path, "silent_dormant", reason="circuit_open")
        return "circuit_open"

    scanner_output = Path(config["scanner_output_path"])
    if not scanner_output.exists():
        log_event(log_path, "silent_dormant", reason="scanner_output_missing")
        return "scanner_output_missing"

    envelope = load_json(scanner_output)
    gate = deterministic_gate(envelope, config)
    if not gate.viable:
        log_event(log_path, "silent_dormant", reason="gate_failed", failed_checks=gate.failed)
        return "viable_false"

    idempotency_key = envelope.get("idempotency_key")
    if not idempotency_key:
        log_event(log_path, "silent_dormant", reason="idempotency_key_missing")
        return "idempotency_key_missing"
    if idempotency_key in state["emitted_idempotency_keys"]:
        log_event(log_path, "deduplicated", idempotency_key=idempotency_key)
        return "deduplicated"
    if rate_limited(state, config):
        log_event(log_path, "silent_dormant", reason="rate_limited", idempotency_key=idempotency_key)
        return "rate_limited"

    packet = build_packet(envelope, gate, "fresh")
    try:
        send_with_retries(make_transport(config), packet, config)
    except RuntimeError as exc:
        state["consecutive_transport_failures"] = int(state.get("consecutive_transport_failures") or 0) + 1
        threshold = int(config["circuit_breaker"]["failure_threshold"])
        if state["consecutive_transport_failures"] >= threshold:
            cooldown = float(config["circuit_breaker"]["cooldown_seconds"])
            state["circuit_open_until"] = datetime.fromtimestamp(time.time() + cooldown, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        write_json(state_path, state)
        log_event(log_path, "transport_failed", error=str(exc), idempotency_key=idempotency_key)
        return "transport_failed"

    state["emitted_idempotency_keys"] = (state["emitted_idempotency_keys"] + [idempotency_key])[-500:]
    state["last_emit_at"] = iso_now()
    state["consecutive_transport_failures"] = 0
    state["circuit_open_until"] = None
    write_json(state_path, state)
    log_event(log_path, "packet_emitted", idempotency_key=idempotency_key, packet_hash=packet["packet_hash"], transport=config["transport"]["type"])
    return "packet_emitted"


def run_loop(config: dict[str, Any]) -> None:
    interval = float(config["loop"]["interval_seconds"])
    max_iterations = config["loop"].get("max_iterations")
    iteration = 0
    while True:
        status = monitor_once(config)
        print(f"APEX_PACKET_MONITOR: {status}")
        iteration += 1
        if max_iterations is not None and iteration >= int(max_iterations):
            break
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor scanner output and emit broker-gated APEX_PACKET activations for Codex.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = load_config(Path(args.config))
    if args.once:
        print(f"APEX_PACKET_MONITOR: {monitor_once(config)}")
        return
    run_loop(config)


if __name__ == "__main__":
    main()
