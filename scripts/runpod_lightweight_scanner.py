#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
STATUS = ROOT / "data" / "runpod_lightweight_scanner_status.json"
LOCK = ROOT / "data" / "runpod_lightweight_scanner.lock"
LOG = ROOT / "logs" / "runpod_lightweight_scanner.jsonl"
WATCHLIST = ROOT / "data" / "blue_chip_watchlist.txt"
PLUGIN_SNAPSHOT = ROOT / "data" / "plugin_runtime_snapshot.json"
CANDIDATE_ENVELOPE = ROOT / "data" / "current_candidate_envelope.json"
PLUGIN_STACK = ROOT / "rules" / "plugin_runtime_stack.json"
ARCHITECTURE_NAME = "ABSOLUTE INFINITE +775% TACTICAL APPRECIATION OPERATIONS COMPOUNDING — APEX PRESTIGE ARCHITECTURE"
USER_ALGORITHM_ID = "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING"


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def load_json(path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def append_log(event, **fields):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp_utc": iso_now(), "architecture": ARCHITECTURE_NAME, "event": event, **fields}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def acquire_lock():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open("w", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def load_watchlist():
    if not WATCHLIST.exists():
        return []
    symbols = []
    for raw in WATCHLIST.read_text(encoding="utf-8").splitlines():
        symbol = raw.strip().upper()
        if symbol and not symbol.startswith("#"):
            symbols.append(symbol)
    return symbols


def stable_hash(data):
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def normalize_plugin_snapshot():
    snapshot = load_json(PLUGIN_SNAPSHOT, {})
    if not isinstance(snapshot, dict):
        snapshot = {}
    sources = snapshot.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    return snapshot, sources


def source_record(name, payload):
    if not isinstance(payload, dict):
        return {"source": name, "status": "unavailable", "timestamp": iso_now()}
    status = payload.get("status") or payload.get("trade_status") or payload.get("label")
    timestamp = payload.get("timestamp") or payload.get("retrieved_at") or payload.get("price_time")
    return {
        "source": name,
        "status": "fresh" if timestamp and payload.get("usable", True) is not False else "unavailable",
        "timestamp": timestamp or iso_now(),
        "summary": status,
    }


def build_non_executable_envelope(symbols, sources, codex_heavy_state):
    longbridge = sources.get("Longbridge", {})
    stocktwits = sources.get("Stocktwits", {})
    tradingcursor = sources.get("TradingCursor", {})
    market_status = longbridge.get("market_status", {})
    temperature = longbridge.get("market_temperature", {})
    sentiment = stocktwits.get("sentiment", {})
    pulse = stocktwits.get("symbol_pulse", {})

    symbol = str(pulse.get("symbol") or sentiment.get("symbol") or (symbols[0] if symbols else "WATCHLIST")).upper()
    source_records = [
        source_record("Longbridge.market_status", market_status),
        source_record("Longbridge.market_temperature", temperature),
        source_record("Stocktwits.sentiment", sentiment),
        source_record("Stocktwits.symbol_pulse", pulse),
        source_record("TradingCursor.analysis", tradingcursor.get("analysis", {"usable": False, "status": "unavailable"})),
    ]
    fresh_count = sum(1 for item in source_records if item["status"] == "fresh")
    market_open = any(
        isinstance(item, dict) and item.get("market") == "US" and item.get("trade_status") == "Trading"
        for item in market_status.get("market_time", []) if isinstance(market_status.get("market_time"), list)
    )
    sentiment_score = sentiment.get("score")
    sentiment_label = sentiment.get("label")
    temperature_value = temperature.get("temperature")
    tradingcursor_rejected = str(tradingcursor.get("status") or "").lower() == "rejected"

    viable = False
    failed = []
    if not market_open:
        failed.append("US market status is not verified Trading")
    if fresh_count < 2:
        failed.append("fewer than two fresh plugin source records")
    if tradingcursor_rejected:
        failed.append("TradingCursor unavailable due to plan or cooldown")
    if sentiment_label == "BEARISH" or (isinstance(sentiment_score, (int, float)) and sentiment_score < 50):
        failed.append("Stocktwits sentiment is not positive")
    if codex_heavy_state != "AVAILABLE_IF_VIABILITY_GATES_TRUE":
        failed.append("Codex heavy workflow remains frozen/dormant")

    market_input = {
        "symbol": symbol,
        "asset_class": "US_EQUITY",
        "session": "REGULAR" if market_open else "UNKNOWN",
        "venue": pulse.get("exchange") or "UNKNOWN",
        "broker_name": "Robinhood",
        "timestamp": iso_now(),
        "quote_timestamp": pulse.get("price_time") or iso_now(),
        "last": pulse.get("price"),
        "data_status": "fresh" if fresh_count >= 2 else "unusable",
        "risk_status": "fail",
        "source_count": fresh_count,
        "source_conflict": False,
        "available_trading_capital": 5.0,
        "requested_notional_usd": 1.0,
        "fractional_shares_supported": True,
        "fractional_asset_eligible": True,
        "margin_requested": False,
        "margin_approved": False,
        "account_net_worth_usd": 5.0,
        "explicit_execution_authorization": False,
    }
    envelope = {
        "architecture": ARCHITECTURE_NAME,
        "envelope_id": f"runpod-scan-{stable_hash({'symbol': symbol, 'sources': source_records})[:16]}",
        "idempotency_key": f"{symbol}:{stable_hash({'sources': source_records})[:24]}",
        "created_by": "RUNPOD_LIGHTWEIGHT_SCANNER",
        "user_algorithm_id": USER_ALGORITHM_ID,
        "scanner_viable": viable,
        "requested_codex_activation": viable,
        "plugins_execute_trades": False,
        "broker_order_submitted": False,
        "candidate_decision": "NO ACTION" if failed else "WATCHLIST ONLY",
        "apex_score": 0,
        "confidence": 0,
        "codex_heavy_state": codex_heavy_state,
        "market_input": market_input,
        "data_provenance": source_records,
        "source_quality": {
            "fresh_source_count": fresh_count,
            "market_open": market_open,
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score,
            "market_temperature": temperature_value,
            "tradingcursor_available": not tradingcursor_rejected,
        },
        "failed_checks": failed,
        "next_allowed_step": "continue Runpod 24/7 scanning; do not wake Codex unless a new fresh non-duplicate envelope passes every APEX gate",
    }
    return envelope


def scan_once(codex_heavy_state):
    symbols = load_watchlist()
    plugin_snapshot, sources = normalize_plugin_snapshot()
    envelope = build_non_executable_envelope(symbols, sources, codex_heavy_state)
    write_json(CANDIDATE_ENVELOPE, envelope)
    status = {
        "timestamp_utc": iso_now(),
        "architecture": ARCHITECTURE_NAME,
        "runtime": "RUNPOD_24_7_LIGHTWEIGHT_SCANNER",
        "scanner_active": True,
        "codex_heavy_state": codex_heavy_state,
        "heavy_operations_default": "ASLEEP",
        "trade_execution_allowed": False,
        "plugins_execute_trades": False,
        "watchlist_symbol_count": len(symbols),
        "watchlist_symbols": symbols[:100],
        "plugin_snapshot_path": str(PLUGIN_SNAPSHOT),
        "plugin_stack_path": str(PLUGIN_STACK),
        "candidate_envelope_path": str(CANDIDATE_ENVELOPE),
        "candidate_decision": envelope["candidate_decision"],
        "scanner_viable": envelope["scanner_viable"],
        "source_quality": envelope["source_quality"],
        "continuous_operations": [
            "watching",
            "deterministic calculations",
            "projection bookkeeping",
            "cooldowns",
            "deduplication",
            "candidate envelope readiness checks",
            "health logging",
        ],
        "burst_only_plugins": [
            "Superpowers",
            "OpenAI Developers",
            "NVIDIA Skills",
            "TradingCursor",
            "Stocktwits",
            "Longbridge",
            "Finances",
            "2+2 Calculator",
            "Precise Special Functions",
            "Cloudflare",
            "Amplitude",
            "Notion",
            "Carta CRM",
            "Rosalind Workbench",
            "Figma",
            "productivity",
            "Ace Knowledge Graph",
        ],
        "plugin_execution_authority": "NONE",
        "next_allowed_step": "continue scanning; wake heavy workflow only after fresh non-duplicate viability gates are true",
    }
    write_json(STATUS, status)
    append_log(
        "scan_once",
        codex_heavy_state=codex_heavy_state,
        watchlist_symbol_count=len(symbols),
        candidate_decision=envelope["candidate_decision"],
        scanner_viable=envelope["scanner_viable"],
        source_quality=envelope["source_quality"],
    )
    print("RUNPOD_LIGHTWEIGHT_SCANNER: ACTIVE")
    print(f"CODEX_HEAVY_STATE: {codex_heavy_state}")
    print(f"CANDIDATE_DECISION: {envelope['candidate_decision']}")
    print(f"SCANNER_VIABLE: {str(envelope['scanner_viable']).lower()}")
    print("TRADE_EXECUTION_ALLOWED: false")
    print("HEAVY_OPERATIONS_DEFAULT: ASLEEP")
    return status


def main():
    parser = argparse.ArgumentParser(description="Runpod 24/7 lightweight scanner heartbeat.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=300)
    parser.add_argument("--codex-heavy-state", default="UNKNOWN_OR_FROZEN")
    parser.add_argument("--no-lock", action="store_true")
    args = parser.parse_args()

    if Path.cwd() != ROOT:
        print("RUNPOD_LIGHTWEIGHT_SCANNER: BLOCKED")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(1)

    lock = None
    if not args.once and not args.no_lock:
        lock = acquire_lock()
        if lock is None:
            print("RUNPOD_LIGHTWEIGHT_SCANNER: DUPLICATE_BLOCKED")
            print(f"LOCK_FILE: {LOCK}")
            return

    while True:
        scan_once(args.codex_heavy_state)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
