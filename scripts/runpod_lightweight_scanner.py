#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

STATUS = ROOT / "data" / "runpod_lightweight_scanner_status.json"
LOCK = ROOT / "data" / "runpod_lightweight_scanner.lock"
LOG = ROOT / "logs" / "runpod_lightweight_scanner.jsonl"
WATCHLIST = ROOT / "data" / "blue_chip_watchlist.txt"
CRYPTO_CANDIDATES = ROOT / "data" / "volatile_crypto_candidates.json"
CRYPTO_QUOTE_INPUTS = [
    ROOT / "data" / "robinhood_crypto_quote_snapshot.json",
    ROOT / "data" / "sample_robinhood_volatile_crypto_input.json",
    ROOT / "data" / "sample_robinhood_crypto_input.json",
    ROOT / "data" / "sample_crypto_input.json",
]
USER_SETTINGS = ROOT / "rules" / "user_settings.json"
PLUGIN_SNAPSHOT = ROOT / "data" / "plugin_runtime_snapshot.json"
CANDIDATE_ENVELOPE = ROOT / "data" / "current_candidate_envelope.json"
LANE_STATUS_DIR = ROOT / "data" / "scanner_lanes"
LANE_ENVELOPE_DIR = ROOT / "data" / "candidate_lanes"
PLUGIN_STACK = ROOT / "rules" / "plugin_runtime_stack.json"
ARCHITECTURE_NAME = "ABSOLUTE INFINITE +775% TACTICAL APPRECIATION OPERATIONS COMPOUNDING — APEX PRESTIGE ARCHITECTURE"
USER_ALGORITHM_ID = "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING"
APEX_VALUE_DOCTRINE = "MICRO TRADES - ABSOLUTE INFINITE +775% OPTIMALLY APPRECIATE TACTICAL COMPOUNDING OF CAPITAL"
MAX_SOURCE_AGE_SECONDS = 300
DEFAULT_MAX_CRYPTO_QUOTE_AGE_SECONDS = 15


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value):
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def timestamp_age_seconds(value):
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds()


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


def lane_slug(lane):
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in lane)


def lane_paths(lane):
    slug = lane_slug(lane)
    if lane == "primary":
        return STATUS, CANDIDATE_ENVELOPE, LOCK, LOG
    return (
        LANE_STATUS_DIR / f"{slug}_status.json",
        LANE_ENVELOPE_DIR / f"{slug}_candidate_envelope.json",
        ROOT / "data" / f"runpod_lightweight_scanner_{slug}.lock",
        ROOT / "logs" / f"runpod_lightweight_scanner_{slug}.jsonl",
    )


def append_log(path, event, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp_utc": iso_now(), "architecture": ARCHITECTURE_NAME, "event": event, **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def acquire_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", encoding="utf-8")
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


def load_active_crypto_symbol():
    candidates = load_json(CRYPTO_CANDIDATES, {})
    if not isinstance(candidates, dict):
        candidates = {}
    symbol = str(candidates.get("active_symbol") or candidates.get("fallback_symbol") or "BTC").strip().upper()
    return symbol or "BTC", candidates


def symbol_matches(candidate, target):
    candidate = str(candidate or "").strip().upper()
    target = str(target or "").strip().upper()
    return candidate == target or candidate == f"{target}USD" or candidate == f"{target}-USD"


def load_crypto_quote(symbol):
    scanner_refresh_timestamp = iso_now()
    settings = load_json(USER_SETTINGS, {})
    max_age = (
        ((settings.get("data_quality") or {}).get("max_quote_age_seconds_crypto"))
        if isinstance(settings, dict)
        else None
    )
    if not isinstance(max_age, (int, float)) or max_age <= 0:
        max_age = DEFAULT_MAX_CRYPTO_QUOTE_AGE_SECONDS

    quote_sources = []
    for path in CRYPTO_QUOTE_INPUTS:
        payload = load_json(path, {})
        if not isinstance(payload, dict) or payload.get("asset_class") != "CRYPTO":
            continue
        if not symbol_matches(payload.get("symbol"), symbol):
            continue
        timestamp = payload.get("quote_timestamp") or payload.get("timestamp")
        age_seconds = timestamp_age_seconds(timestamp)
        has_quote = all(numeric(payload.get(field)) is not None for field in ("bid", "ask", "last"))
        is_fresh = has_quote and age_seconds is not None and 0 <= age_seconds <= max_age
        quote_sources.append({
            "path": str(path),
            "payload": payload,
            "timestamp": timestamp,
            "scanner_refresh_timestamp": scanner_refresh_timestamp,
            "age_seconds": age_seconds,
            "max_age_seconds": max_age,
            "has_bid_ask_last": has_quote,
            "fresh": is_fresh,
            "bid": numeric(payload.get("bid")),
            "ask": numeric(payload.get("ask")),
            "last": numeric(payload.get("last")),
        })

    primary = next((source for source in quote_sources if source["fresh"]), quote_sources[0] if quote_sources else None)
    source_conflict = quote_sources_conflict(quote_sources, settings)
    if primary is not None:
        primary = {**primary}
        primary["quote_sources"] = quote_sources
        primary["fresh_quote_source_count"] = sum(1 for source in quote_sources if source["fresh"])
        primary["quote_source_count"] = len(quote_sources)
        primary["source_conflict"] = source_conflict
        return primary
    return {
        "path": None,
        "payload": {},
        "timestamp": None,
        "scanner_refresh_timestamp": scanner_refresh_timestamp,
        "age_seconds": None,
        "max_age_seconds": max_age,
        "has_bid_ask_last": False,
        "fresh": False,
        "quote_sources": quote_sources,
        "fresh_quote_source_count": 0,
        "quote_source_count": 0,
        "source_conflict": source_conflict,
    }


def quotes_percent_difference(a, b):
    if a is None or b is None:
        return None
    midpoint = (a + b) / 2
    if midpoint <= 0:
        return None
    return abs(a - b) / midpoint


def quote_sources_conflict(quote_sources, settings):
    max_difference = (
        ((settings.get("data_quality") or {}).get("max_allowed_source_price_difference_decimal"))
        if isinstance(settings, dict)
        else None
    )
    if not isinstance(max_difference, (int, float)) or max_difference <= 0:
        max_difference = 0.002
    usable = [source for source in quote_sources if source["fresh"]]
    for index, left in enumerate(usable):
        for right in usable[index + 1:]:
            for field in ("bid", "ask", "last"):
                difference = quotes_percent_difference(left.get(field), right.get(field))
                if difference is not None and difference > max_difference:
                    return True
    return False


def stable_hash(data):
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def numeric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def clamp(value, lower=0.0, upper=100.0):
    return max(lower, min(upper, value))


def projection_score(value, neutral=50.0, scale=1.0):
    number = numeric(value)
    if number is None:
        return neutral
    return clamp(number * scale)


def build_micro_trade_value(crypto_quote):
    payload = crypto_quote["payload"]
    bid = numeric(payload.get("bid"))
    ask = numeric(payload.get("ask"))
    last = numeric(payload.get("last"))
    available_capital = numeric(payload.get("available_trading_capital")) or 5.0
    requested_notional = numeric(payload.get("requested_notional_usd")) or 1.0
    max_allocation_decimal = 0.2
    max_micro_notional = available_capital * max_allocation_decimal
    spread = ask - bid if bid is not None and ask is not None else None
    mid = (ask + bid) / 2 if bid is not None and ask is not None else None
    spread_decimal = spread / mid if spread is not None and mid and mid > 0 else None
    spread_cost_usd = requested_notional * spread_decimal if spread_decimal is not None else None
    ticket_within_cap = requested_notional <= max_micro_notional
    quote_fresh = crypto_quote["fresh"] is True
    viable = quote_fresh and ticket_within_cap and spread_decimal is not None and spread_decimal <= 0.002
    return {
        "doctrine": APEX_VALUE_DOCTRINE,
        "execution_authority": False,
        "requested_micro_notional_usd": round(requested_notional, 6),
        "available_capital_usd": round(available_capital, 6),
        "max_allocation_decimal": max_allocation_decimal,
        "max_micro_notional_usd": round(max_micro_notional, 6),
        "ticket_within_cap": ticket_within_cap,
        "bid": bid,
        "ask": ask,
        "last": last,
        "spread": round(spread, 12) if spread is not None else None,
        "spread_decimal": round(spread_decimal, 12) if spread_decimal is not None else None,
        "estimated_spread_cost_usd": round(spread_cost_usd, 8) if spread_cost_usd is not None else None,
        "quote_fresh": quote_fresh,
        "quote_stream_active_by_scanner": True,
        "quote_stream_refresh_timestamp": crypto_quote["scanner_refresh_timestamp"],
        "micro_trade_value_status": "VIABLE_FOR_GATE_RECHECK" if viable else "NO_ACTION_GATE_LOCKED",
    }


def build_medium8_projection(source_records, session_confirmed, sentiment, temperature, pulse, tier, micro_trade_value=None):
    fresh_count = sum(1 for item in source_records if item["status"] == "fresh")
    freshness_score = clamp((fresh_count / max(len(source_records), 1)) * 100)
    sentiment_score = projection_score(sentiment.get("score"))
    temperature_score = projection_score(temperature.get("temperature"))
    last_price = numeric((micro_trade_value or {}).get("last")) or numeric(pulse.get("price"))
    capital_fit_score = 100.0 if last_price is not None and last_price > 0 else 0.0
    session_score = 100.0 if session_confirmed else 0.0
    source_depth_score = clamp(fresh_count * 20.0)
    stale_penalty_score = clamp(100.0 - freshness_score)
    continuation_probability = clamp(
        (freshness_score * 0.25)
        + (sentiment_score * 0.2)
        + (temperature_score * 0.2)
        + (session_score * 0.15)
        + (capital_fit_score * 0.1)
        + (source_depth_score * 0.1)
    )
    reversal_risk_score = clamp(100.0 - continuation_probability + stale_penalty_score * 0.25)
    spread_decimal = numeric((micro_trade_value or {}).get("spread_decimal"))
    spread_quality_score = 100.0 if spread_decimal is not None and spread_decimal <= 0.002 else 0.0
    net_opportunity_score = clamp(continuation_probability - reversal_risk_score * 0.35 + spread_quality_score * 0.1)
    medium8 = {
        "freshness_score": round(freshness_score, 3),
        "sentiment_score": round(sentiment_score, 3),
        "market_temperature_score": round(temperature_score, 3),
        "session_confirmation_score": round(session_score, 3),
        "capital_fit_score": round(capital_fit_score, 3),
        "source_depth_score": round(source_depth_score, 3),
        "continuation_probability": round(continuation_probability, 3),
        "net_opportunity_score": round(net_opportunity_score, 3),
    }
    return {
        "tier": tier,
        "execution_authority": False,
        "projection_count": 8,
        "projection_scores": medium8,
        "micro_trade_value": micro_trade_value or {},
        "reversal_risk_score": round(reversal_risk_score, 3),
        "stale_penalty_score": round(stale_penalty_score, 3),
    }


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
        return {"source": name, "status": "unavailable", "timestamp": iso_now(), "summary": "missing payload"}
    status = payload.get("status") or payload.get("trade_status") or payload.get("label")
    timestamp = payload.get("timestamp") or payload.get("retrieved_at") or payload.get("price_time")
    age_seconds = timestamp_age_seconds(timestamp)
    usable = payload.get("usable", True) is not False
    is_fresh = timestamp and usable and age_seconds is not None and 0 <= age_seconds <= MAX_SOURCE_AGE_SECONDS
    source_status = "fresh" if is_fresh else "stale_or_unusable"
    return {
        "source": name,
        "status": source_status,
        "timestamp": timestamp or iso_now(),
        "summary": status,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "max_age_seconds": MAX_SOURCE_AGE_SECONDS,
    }


def build_non_executable_envelope(symbols, sources, codex_heavy_state, lane):
    crypto_symbol, crypto_candidates = load_active_crypto_symbol()
    crypto_quote = load_crypto_quote(crypto_symbol)
    longbridge = sources.get("Longbridge", {})
    stocktwits = sources.get("Stocktwits", {})
    tradingcursor = sources.get("TradingCursor", {})
    market_status = longbridge.get("market_status", {})
    temperature = longbridge.get("market_temperature", {})
    sentiment = stocktwits.get("sentiment", {})
    pulse = stocktwits.get("symbol_pulse", {})

    symbol = crypto_symbol
    source_records = [
        {
            "source": "volatile_crypto_candidates.active_symbol",
            "status": "fresh",
            "timestamp": iso_now(),
            "summary": crypto_candidates.get("active_symbol_reason"),
            "age_seconds": 0,
            "max_age_seconds": MAX_SOURCE_AGE_SECONDS,
        },
        {
            "source": "APEX.crypto_quote_file",
            "status": "fresh" if crypto_quote["fresh"] else "stale_or_unusable",
            "timestamp": crypto_quote["timestamp"] or iso_now(),
            "summary": crypto_quote["path"],
            "age_seconds": round(crypto_quote["age_seconds"], 3) if crypto_quote["age_seconds"] is not None else None,
            "max_age_seconds": crypto_quote["max_age_seconds"],
            "quote_source_count": crypto_quote["quote_source_count"],
            "fresh_quote_source_count": crypto_quote["fresh_quote_source_count"],
            "source_conflict": crypto_quote["source_conflict"],
        },
        source_record("Longbridge.market_status", market_status),
        source_record("Longbridge.market_temperature", temperature),
        source_record("Stocktwits.sentiment", sentiment),
        source_record("Stocktwits.symbol_pulse", pulse),
        source_record("TradingCursor.analysis", tradingcursor.get("analysis", {"usable": False, "status": "unavailable"})),
    ]
    source_by_name = {item["source"]: item for item in source_records}
    fresh_count = sum(1 for item in source_records if item["status"] == "fresh")
    raw_market_open = any(
        isinstance(item, dict) and item.get("market") == "US" and item.get("trade_status") == "Trading"
        for item in market_status.get("market_time", []) if isinstance(market_status.get("market_time"), list)
    )
    market_status_fresh = source_by_name["Longbridge.market_status"]["status"] == "fresh"
    market_open = raw_market_open and market_status_fresh
    crypto_session_confirmed = True
    sentiment_score = sentiment.get("score")
    sentiment_label = sentiment.get("label")
    temperature_value = temperature.get("temperature")
    tradingcursor_rejected = str(tradingcursor.get("status") or "").lower() == "rejected"

    viable = False
    failed = []
    if not crypto_quote["has_bid_ask_last"]:
        failed.append("APEX crypto bid/ask/last feed required but not populated")
    elif not crypto_quote["fresh"]:
        failed.append("APEX crypto bid/ask/last feed is stale")
    if fresh_count < 2:
        failed.append("fewer than two fresh plugin source records")
    if crypto_quote["fresh_quote_source_count"] < 2:
        failed.append("fewer than two fresh crypto quote sources")
    if crypto_quote["source_conflict"]:
        failed.append("crypto quote sources conflict")
    if tradingcursor_rejected:
        failed.append("TradingCursor unavailable due to plan or cooldown")
    if sentiment_label == "BEARISH" or (isinstance(sentiment_score, (int, float)) and sentiment_score < 50):
        failed.append("Stocktwits sentiment is not positive")
    if codex_heavy_state != "AVAILABLE_IF_VIABILITY_GATES_TRUE":
        failed.append("Codex heavy workflow remains frozen/dormant")
    micro_trade_value = build_micro_trade_value(crypto_quote)
    crypto_projection = build_medium8_projection(
        source_records,
        crypto_session_confirmed,
        sentiment,
        temperature,
        pulse,
        "MEDIUM8_CRYPTO_24_7",
        micro_trade_value,
    )
    blue_chip_projection = build_medium8_projection(
        source_records,
        market_open,
        sentiment,
        temperature,
        pulse,
        "MEDIUM8_BLUE_CHIPS_MARKET_HOURS",
        micro_trade_value,
    )
    projection = {
        "mode": "MEDIUM_WEIGHT_DUAL_LANE",
        "execution_authority": False,
        "active_lane": "CRYPTO_24_7",
        "crypto": crypto_projection,
        "blue_chips": blue_chip_projection,
        "blue_chip_status": "ACTIVE_WHEN_EQUITY_MARKET_VERIFIED_OPEN" if market_open else "WATCH_ONLY_UNTIL_EQUITY_MARKET_VERIFIED_OPEN",
    }

    market_input = {
        **{
            key: crypto_quote["payload"].get(key)
            for key in (
                "bid",
                "ask",
                "last",
                "liquidity_usd",
                "crypto_account_confirmed",
                "maintenance_active",
                "account_restricted",
            )
            if key in crypto_quote["payload"]
        },
        "symbol": symbol,
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Robinhood Crypto",
        "broker_name": "Robinhood",
        "algorithm_quote_contract": "APEX_REQUIRES_FRESH_CRYPTO_BID_ASK_LAST",
        "timestamp": iso_now(),
        "scanner_quote_stream": {
            "active": True,
            "owner": "RUNPOD_LIGHTWEIGHT_SCANNER",
            "cadence_seconds": 1,
            "refresh_timestamp": crypto_quote["scanner_refresh_timestamp"],
            "source_path": crypto_quote["path"],
            "quote_source_count": crypto_quote["quote_source_count"],
            "fresh_quote_source_count": crypto_quote["fresh_quote_source_count"],
            "source_has_bid_ask_last": crypto_quote["has_bid_ask_last"],
            "source_fresh": crypto_quote["fresh"],
            "source_conflict": crypto_quote["source_conflict"],
        },
        "quote_timestamp": crypto_quote["timestamp"],
        "quote_source_path": crypto_quote["path"],
        "quote_source_count": crypto_quote["quote_source_count"],
        "fresh_quote_source_count": crypto_quote["fresh_quote_source_count"],
        "quote_age_seconds": round(crypto_quote["age_seconds"], 3) if crypto_quote["age_seconds"] is not None else None,
        "quote_max_age_seconds": crypto_quote["max_age_seconds"],
        "data_status": "fresh" if crypto_quote["fresh"] and fresh_count >= 2 else "stale" if crypto_quote["has_bid_ask_last"] else "unusable",
        "risk_status": "fail",
        "source_count": fresh_count,
        "source_conflict": False,
        "available_trading_capital": 5.0,
        "requested_notional_usd": 1.0,
        "crypto_account_confirmed": crypto_quote["payload"].get("crypto_account_confirmed", False),
        "maintenance_active": crypto_quote["payload"].get("maintenance_active"),
        "account_restricted": crypto_quote["payload"].get("account_restricted"),
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
        "scanner_lane": lane,
        "user_algorithm_id": USER_ALGORITHM_ID,
        "scanner_viable": viable,
        "requested_codex_activation": viable,
        "plugins_execute_trades": False,
        "broker_order_submitted": False,
        "candidate_decision": "NO ACTION" if failed else "WATCHLIST ONLY",
        "apex_score": 0,
        "confidence": 0,
        "codex_heavy_state": codex_heavy_state,
        "projection": projection,
        "market_input": market_input,
        "micro_trade_value": micro_trade_value,
        "data_provenance": source_records,
        "source_quality": {
            "fresh_source_count": fresh_count,
            "apex_crypto_quote_feed": "fresh" if crypto_quote["fresh"] else "stale_or_unusable",
            "apex_crypto_quote_source": crypto_quote["path"],
            "crypto_quote_source_count": crypto_quote["quote_source_count"],
            "fresh_crypto_quote_source_count": crypto_quote["fresh_quote_source_count"],
            "crypto_quote_source_conflict": crypto_quote["source_conflict"],
            "scanner_quote_stream_active": True,
            "scanner_quote_stream_refresh_timestamp": crypto_quote["scanner_refresh_timestamp"],
            "crypto_24_7_session": crypto_session_confirmed,
            "equity_market_open": market_open,
            "blue_chip_symbols_tracked": len(symbols),
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score,
            "market_temperature": temperature_value,
            "tradingcursor_available": not tradingcursor_rejected,
        },
        "failed_checks": failed,
        "next_allowed_step": "continue crypto 24/7 medium8 scanning; do not wake Codex unless a new fresh non-duplicate crypto envelope passes every APEX gate",
    }
    return envelope


def scan_once(codex_heavy_state, lane):
    status_path, envelope_path, _lock_path, log_path = lane_paths(lane)
    symbols = load_watchlist()
    plugin_snapshot, sources = normalize_plugin_snapshot()
    envelope = build_non_executable_envelope(symbols, sources, codex_heavy_state, lane)
    write_json(envelope_path, envelope)
    if lane == "primary":
        write_json(CANDIDATE_ENVELOPE, envelope)
    status = {
        "timestamp_utc": iso_now(),
        "architecture": ARCHITECTURE_NAME,
        "runtime": "RUNPOD_24_7_LIGHTWEIGHT_SCANNER",
        "scanner_lane": lane,
        "scanner_active": True,
        "codex_heavy_state": codex_heavy_state,
        "heavy_operations_default": "ASLEEP",
        "trade_execution_allowed": False,
        "plugins_execute_trades": False,
        "watchlist_symbol_count": len(symbols),
        "watchlist_symbols": symbols[:100],
        "plugin_snapshot_path": str(PLUGIN_SNAPSHOT),
        "plugin_stack_path": str(PLUGIN_STACK),
        "candidate_envelope_path": str(envelope_path),
        "candidate_decision": envelope["candidate_decision"],
        "scanner_viable": envelope["scanner_viable"],
        "source_quality": envelope["source_quality"],
        "projection": envelope["projection"],
        "micro_trade_value": envelope["micro_trade_value"],
        "scanner_quote_stream": envelope["market_input"]["scanner_quote_stream"],
        "continuous_operations": [
            "watching",
            "24/7 scanner-owned quote refresh",
            "deterministic calculations",
            "medium8 projection calculations",
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
    write_json(status_path, status)
    if lane == "primary":
        write_json(STATUS, status)
    append_log(
        log_path,
        "scan_once",
        scanner_lane=lane,
        codex_heavy_state=codex_heavy_state,
        watchlist_symbol_count=len(symbols),
        candidate_decision=envelope["candidate_decision"],
        scanner_viable=envelope["scanner_viable"],
        source_quality=envelope["source_quality"],
    )
    print("RUNPOD_LIGHTWEIGHT_SCANNER: ACTIVE")
    print(f"SCANNER_LANE: {lane}")
    print(f"CODEX_HEAVY_STATE: {codex_heavy_state}")
    print(f"CANDIDATE_DECISION: {envelope['candidate_decision']}")
    print(f"SCANNER_VIABLE: {str(envelope['scanner_viable']).lower()}")
    print("TRADE_EXECUTION_ALLOWED: false")
    print("HEAVY_OPERATIONS_DEFAULT: ASLEEP")
    return status


def main():
    parser = argparse.ArgumentParser(description="Runpod 24/7 lightweight scanner heartbeat.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=1)
    parser.add_argument("--codex-heavy-state", default="UNKNOWN_OR_FROZEN")
    parser.add_argument("--lane", default="primary")
    parser.add_argument("--no-lock", action="store_true")
    args = parser.parse_args()

    if Path.cwd() != ROOT:
        print("RUNPOD_LIGHTWEIGHT_SCANNER: BLOCKED")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(1)

    lock = None
    if not args.once and not args.no_lock:
        lock_path = lane_paths(args.lane)[2]
        lock = acquire_lock(lock_path)
        if lock is None:
            print("RUNPOD_LIGHTWEIGHT_SCANNER: DUPLICATE_BLOCKED")
            print(f"LOCK_FILE: {lock_path}")
            return

    while True:
        scan_once(args.codex_heavy_state, args.lane)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
