#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import math
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
    ROOT / "data" / "alpaca_crypto_quote_snapshot.json",
    ROOT / "data" / "robinhood_crypto_quote_snapshot.json",
    ROOT / "data" / "coinbase_crypto_quote_snapshot.json",
    ROOT / "data" / "binance_crypto_quote_snapshot.json",
    ROOT / "data" / "kraken_crypto_quote_snapshot.json",
    ROOT / "data" / "sample_robinhood_volatile_crypto_input.json",
    ROOT / "data" / "sample_robinhood_crypto_input.json",
    ROOT / "data" / "sample_crypto_input.json",
]
USER_SETTINGS = ROOT / "rules" / "user_settings.json"
PLUGIN_SNAPSHOT = ROOT / "data" / "plugin_runtime_snapshot.json"
COINGECKO_CRYPTO_SNAPSHOT = ROOT / "data" / "coingecko_crypto_quote_snapshot.json"
CANDIDATE_ENVELOPE = ROOT / "data" / "current_candidate_envelope.json"
ROBINHOOD_CRYPTO_CAPITAL = ROOT / "data" / "robinhood_crypto_capital_snapshot.json"
LANE_STATUS_DIR = ROOT / "data" / "scanner_lanes"
LANE_ENVELOPE_DIR = ROOT / "data" / "candidate_lanes"
PLUGIN_STACK = ROOT / "rules" / "plugin_runtime_stack.json"
STOCKTWITS_WIDGET = ROOT / "widgets" / "stocktwits_cards_widget.html"
ARCHITECTURE_NAME = "ABSOLUTE INFINITE +775% TACTICAL APPRECIATION OPERATIONS COMPOUNDING — APEX PRESTIGE ARCHITECTURE"
USER_ALGORITHM_ID = "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING"
APEX_VALUE_DOCTRINE = "MICRO TRADES - ABSOLUTE INFINITE +775% OPTIMALLY APPRECIATE TACTICAL COMPOUNDING OF CAPITAL"
MAX_SOURCE_AGE_SECONDS = 90  # ceiling for optional/cross-check sources (e.g. CoinGecko); see per-provider overrides for required crypto quotes
DEFAULT_MAX_CRYPTO_QUOTE_AGE_SECONDS = 15
REQUIRED_CRYPTO_QUOTE_PROVIDERS = ("Robinhood",)
MIN_LOOP_INTERVAL_SECONDS = 4.0
MAX_LOOP_INTERVAL_SECONDS = 420.0


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


def valid_positive_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None


def bounded_loop_interval(value):
    parsed = valid_positive_number(value)
    if parsed is None:
        parsed = MAX_LOOP_INTERVAL_SECONDS
    return max(MIN_LOOP_INTERVAL_SECONDS, min(MAX_LOOP_INTERVAL_SECONDS, parsed))


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


def crypto_quote_provider(payload, path):
    if path and Path(path).name.startswith("sample_"):
        return None
    haystack = " ".join(
        str(payload.get(key) or "")
        for key in ("provider", "source", "broker_name", "venue")
    )
    haystack = f"{haystack} {path}".lower()
    if "alpaca" in haystack:
        return "Alpaca"
    if "robinhood" in haystack:
        return "Robinhood"
    if "coinbase" in haystack:
        return "Coinbase"
    return None


def load_crypto_quote(symbol):
    scanner_refresh_timestamp = iso_now()
    settings = load_json(USER_SETTINGS, {})
    data_quality = (settings.get("data_quality") or {}) if isinstance(settings, dict) else {}
    max_age = data_quality.get("max_quote_age_seconds_crypto")
    if not isinstance(max_age, (int, float)) or max_age <= 0:
        max_age = DEFAULT_MAX_CRYPTO_QUOTE_AGE_SECONDS
    # Tactical-optimality per-provider freshness: a single global threshold
    # either false-flags a healthy continuous stream (too tight) or lets a
    # rarely-refreshed source pass as if it were live (too loose). Each
    # provider gets a ceiling matched to how it actually refreshes, bounded
    # within the 4-second to 7-minute band. Falls back to `max_age` above if
    # unset.
    per_provider_max_age = data_quality.get("max_quote_age_seconds_by_provider")
    if not isinstance(per_provider_max_age, dict):
        per_provider_max_age = {}

    quote_sources = []
    for path in CRYPTO_QUOTE_INPUTS:
        payload = load_json(path, {})
        if not isinstance(payload, dict) or payload.get("asset_class") != "CRYPTO":
            continue
        if not symbol_matches(payload.get("symbol"), symbol):
            continue
        provider = crypto_quote_provider(payload, path)
        provider_max_age = per_provider_max_age.get(provider, max_age)
        if not isinstance(provider_max_age, (int, float)) or provider_max_age <= 0:
            provider_max_age = max_age
        timestamp = payload.get("quote_timestamp") or payload.get("timestamp")
        age_seconds = timestamp_age_seconds(timestamp)
        has_quote = all(numeric(payload.get(field)) is not None for field in ("bid", "ask", "last"))
        is_fresh = has_quote and age_seconds is not None and 0 <= age_seconds <= provider_max_age
        quote_sources.append({
            "path": str(path),
            "payload": payload,
            "provider": provider,
            "required_provider": provider in REQUIRED_CRYPTO_QUOTE_PROVIDERS,
            "timestamp": timestamp,
            "scanner_refresh_timestamp": scanner_refresh_timestamp,
            "age_seconds": age_seconds,
            "max_age_seconds": provider_max_age,
            "has_bid_ask_last": has_quote,
            "fresh": is_fresh,
            "bid": numeric(payload.get("bid")),
            "ask": numeric(payload.get("ask")),
            "last": numeric(payload.get("last")),
        })

    required_fresh = {}
    for provider in REQUIRED_CRYPTO_QUOTE_PROVIDERS:
        source = next(
            (
                candidate
                for candidate in quote_sources
                if candidate["provider"] == provider and candidate["fresh"]
            ),
            None,
        )
        if source is not None:
            required_fresh[provider] = source
    missing_required = [
        provider
        for provider in REQUIRED_CRYPTO_QUOTE_PROVIDERS
        if provider not in required_fresh
    ]
    source_conflict = quote_sources_conflict(list(required_fresh.values()), settings)
    required_quorum_ok = not missing_required and not source_conflict
    # Alpaca is legacy optional data only. It must never become the selected
    # quote for a new candidate when the broker-authoritative source is absent.
    primary = required_fresh.get("Robinhood") or next(
        (source for source in quote_sources if source["fresh"] and source["provider"] != "Alpaca"),
        next((source for source in quote_sources if source["provider"] != "Alpaca"), None),
    )
    if primary is not None:
        primary = {**primary}
        primary["quote_sources"] = quote_sources
        primary["required_quote_sources"] = required_fresh
        primary["missing_required_quote_sources"] = missing_required
        primary["required_quote_quorum_ok"] = required_quorum_ok
        primary["fresh_quote_source_count"] = len(required_fresh)
        primary["fresh_optional_quote_source_count"] = sum(
            1 for source in quote_sources if source["fresh"] and not source["required_provider"]
        )
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
        "required_quote_sources": {},
        "missing_required_quote_sources": list(REQUIRED_CRYPTO_QUOTE_PROVIDERS),
        "required_quote_quorum_ok": False,
        "fresh_quote_source_count": 0,
        "fresh_optional_quote_source_count": 0,
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
    return valid_positive_number(value)


def load_crypto_capital_snapshot():
    snapshot = load_json(ROBINHOOD_CRYPTO_CAPITAL, {})
    if not isinstance(snapshot, dict):
        return {}
    value = valid_positive_number(snapshot.get("crypto_buying_power_usd"))
    source = snapshot.get("crypto_capital_source")
    retrieved_at = snapshot.get("crypto_capital_retrieved_at")
    age_seconds = timestamp_age_seconds(retrieved_at)
    if (
        value is None
        or source != "robinhood.get_portfolio.crypto_buying_power.buying_power"
        or age_seconds is None
        or age_seconds < 0
        or age_seconds > MAX_SOURCE_AGE_SECONDS
    ):
        return {}
    return {
        "crypto_buying_power_usd": round(value, 6),
        "crypto_capital_source": source,
        "crypto_capital_retrieved_at": retrieved_at,
        "crypto_capital_age_seconds": round(age_seconds, 3),
    }


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
    buying_power = numeric(payload.get("crypto_buying_power_usd"))
    requested_notional = numeric(payload.get("requested_notional_usd"))
    max_allocation_decimal = 0.2
    max_micro_notional = buying_power * max_allocation_decimal if buying_power is not None else None
    spread = ask - bid if bid is not None and ask is not None else None
    mid = (ask + bid) / 2 if bid is not None and ask is not None else None
    spread_decimal = spread / mid if spread is not None and mid and mid > 0 else None
    spread_cost_usd = (
        requested_notional * spread_decimal
        if requested_notional is not None and spread_decimal is not None
        else None
    )
    ticket_within_cap = (
        requested_notional is not None
        and max_micro_notional is not None
        and requested_notional <= max_micro_notional
    )
    quote_fresh = crypto_quote["fresh"] is True
    viable = quote_fresh and ticket_within_cap and spread_decimal is not None and spread_decimal <= 0.002
    return {
        "doctrine": APEX_VALUE_DOCTRINE,
        "execution_authority": False,
        "requested_micro_notional_usd": round(requested_notional, 6) if requested_notional is not None else None,
        "crypto_buying_power_usd": round(buying_power, 6) if buying_power is not None else None,
        "max_allocation_decimal": max_allocation_decimal,
        "max_micro_notional_usd": round(max_micro_notional, 6) if max_micro_notional is not None else None,
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


def tradingcursor_apex_fields(analysis):
    if not isinstance(analysis, dict) or analysis.get("usable") is False:
        return {}
    parsed = analysis.get("analysis")
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            parsed = {}
    if not isinstance(parsed, dict):
        parsed = analysis
    position = parsed.get("potentialPosition") if isinstance(parsed.get("potentialPosition"), dict) else {}
    entry = valid_positive_number(
        position.get("entryPrice")
        or position.get("entry_price")
        or analysis.get("entry_price")
        or analysis.get("entry_price_usd")
    )
    invalidation = valid_positive_number(
        position.get("stopLoss")
        or position.get("stop_loss")
        or position.get("invalidationPrice")
        or analysis.get("invalidation_price")
        or analysis.get("stop_price")
    )
    maximum = valid_positive_number(
        position.get("maximumNotional")
        or position.get("maxNotional")
        or analysis.get("maximum_notional_usd")
    )
    result = {}
    if entry is not None:
        result["entry_price_usd"] = entry
    if invalidation is not None:
        result["invalidation_price_usd"] = invalidation
        if entry is not None:
            result["stop_distance_usd"] = abs(entry - invalidation)
    if maximum is not None:
        result["maximum_position_size_usd"] = maximum
    return result


def apex_requested_notional(payload, settings, asset_class):
    buying_power_key = "crypto_buying_power_usd" if asset_class == "CRYPTO" else "buying_power_usd"
    allocation_key = "crypto_max_allocation_decimal" if asset_class == "CRYPTO" else "us_equity_max_allocation_decimal"
    risk = valid_positive_number(payload.get("risk_per_action_decimal"))
    if risk is None:
        risk = valid_positive_number((settings.get("capital") or {}).get("max_risk_per_action_decimal"))
    capital = valid_positive_number(payload.get(buying_power_key))
    entry = valid_positive_number(payload.get("entry_price_usd") or payload.get("entry_price"))
    invalidation = valid_positive_number(
        payload.get("invalidation_price_usd")
        or payload.get("invalidation_price")
        or payload.get("stop_price_usd")
        or payload.get("stop_price")
    )
    distance = valid_positive_number(payload.get("stop_distance_usd"))
    if distance is None and entry is not None and invalidation is not None:
        distance = abs(entry - invalidation)
    allocation = valid_positive_number((settings.get("asset_limits") or {}).get(allocation_key))
    maximum = valid_positive_number(payload.get("maximum_position_size_usd"))
    minimum = valid_positive_number(payload.get("minimum_position_size_usd"))
    broker_minimum = valid_positive_number((settings.get("broker") or {}).get("minimum_order_value_usd"))
    if minimum is None:
        minimum = broker_minimum

    required = {
        "available_broker_capital": capital,
        "risk_per_action_decimal": risk,
        "invalidation_price_usd": invalidation,
        "invalidation_distance_usd": distance,
        "entry_price_usd": entry,
        "allocation_percentage": allocation,
    }
    if any(value is None for value in required.values()):
        return None, "APEX_HAS_NO_NUMERIC_NOTIONAL_OUTPUT", required
    if distance <= 0 or entry <= 0:
        return None, "APEX_NUMERIC_NOTIONAL_REJECTED_BY_FORMULA", required

    risk_dollars = capital * risk
    quantity = math.floor(risk_dollars / distance)
    notional = quantity * entry
    max_allocation_notional = capital * allocation
    max_allowed = min(value for value in (capital, max_allocation_notional, maximum) if value is not None)
    if quantity <= 0 or notional <= 0:
        return None, "APEX_NUMERIC_NOTIONAL_REJECTED_BY_FORMULA", required
    if minimum is not None and notional < minimum:
        return None, "APEX_NUMERIC_NOTIONAL_BELOW_MINIMUM_POSITION_SIZE", required
    if notional > max_allowed:
        return None, "APEX_NUMERIC_NOTIONAL_EXCEEDS_LIMITS", required
    return round(notional, 2), "APEX_CAPITAL_RULES_POSITION_SIZING_FORMULA", {
        **required,
        "risk_dollars": round(risk_dollars, 6),
        "position_quantity": quantity,
        "maximum_allowed_notional": round(max_allowed, 6),
        "minimum_position_size_usd": minimum,
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
    change = pulse.get("change") if isinstance(pulse, dict) else None
    change = float(change) if isinstance(change, (int, float)) else 0.0
    if change >= 2.0:
        regime = "MOMENTUM_UP"
        weights = (0.15, 0.25, 0.2, 0.15, 0.1, 0.15)
    elif change <= -2.0:
        regime = "MOMENTUM_DOWN"
        weights = (0.15, 0.1, 0.2, 0.15, 0.1, 0.3)
    elif abs(change) < 0.5:
        regime = "RANGE_OR_LOW_MOMENTUM"
        weights = (0.3, 0.15, 0.2, 0.15, 0.1, 0.1)
    else:
        regime = "TRANSITION"
        weights = (0.25, 0.2, 0.2, 0.15, 0.1, 0.1)
    continuation_probability = clamp(
        (freshness_score * weights[0])
        + (sentiment_score * weights[1])
        + (temperature_score * weights[2])
        + (session_score * weights[3])
        + (capital_fit_score * weights[4])
        + (source_depth_score * weights[5])
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
        "forecasting_enabled": True,
        "forecast_type": "MEDIUM_WEIGHT_FORWARD_PROJECTION",
        "forecast_horizon": "next viable tactical window; not a guarantee",
        "projection_count": 8,
        "projection_scores": medium8,
        "adaptive_regime": regime,
        "adaptive_weights": {
            "freshness": weights[0],
            "sentiment": weights[1],
            "temperature": weights[2],
            "session": weights[3],
            "capital_fit": weights[4],
            "source_depth": weights[5],
        },
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


def online_source_coverage(sources):
    expected = ("Longbridge", "Stocktwits", "TradingCursor")
    records = []
    for name in expected:
        payload = sources.get(name)
        status = source_record(f"{name}.online_market_context", payload)
        records.append({
            **status,
            "online_context_role": {
                "Longbridge": "markets/news/reports confirmation",
                "Stocktwits": "media/sentiment/attention confirmation",
                "TradingCursor": "technical/report context confirmation",
            }[name],
        })
    fresh = [item for item in records if item.get("status") == "fresh"]
    return {
        "expected_sources": list(expected),
        "fresh_online_source_count": len(fresh),
        "online_source_count": len(records),
        "records": records,
        "all_online_sources_fresh": len(fresh) == len(records),
    }


def source_refresh_policy():
    return {
        "runs_24_7": True,
        "medium_weight_interval_min_seconds": MIN_LOOP_INTERVAL_SECONDS,
        "medium_weight_interval_max_seconds": MAX_LOOP_INTERVAL_SECONDS,
        "freshness_model": "websocket/live-feed artifacts first; REST snapshots only as bounded fallback or independent cross-check",
        "required_quote_sources": list(REQUIRED_CRYPTO_QUOTE_PROVIDERS),
        "market_data_sources": [
            {"name": "Alpaca", "artifact": "data/alpaca_crypto_quote_snapshot.json", "role": "websocket quote/trade freshness"},
            {"name": "Robinhood", "artifact": "data/robinhood_crypto_quote_snapshot.json", "role": "broker-side quote/capital confirmation"},
            {"name": "Coinbase", "artifact": "data/coinbase_crypto_quote_snapshot.json", "role": "free public WebSocket independent crypto cross-check"},
            {"name": "Binance", "artifact": "data/binance_crypto_quote_snapshot.json", "role": "free public WebSocket independent crypto cross-check"},
            {"name": "Kraken", "artifact": "data/kraken_crypto_quote_snapshot.json", "role": "free public WebSocket independent crypto cross-check"},
            {"name": "CoinGecko", "artifact": "data/coingecko_crypto_quote_snapshot.json", "role": "independent crypto quote cross-check"},
        ],
        "plugin_context_sources": [
            {"name": "Longbridge", "artifact": "data/plugin_runtime_snapshot.json sources.Longbridge", "role": "market/news/report context"},
            {"name": "Stocktwits", "artifact": "data/plugin_runtime_snapshot.json sources.Stocktwits", "role": "media/sentiment/attention context"},
            {"name": "TradingCursor", "artifact": "data/plugin_runtime_snapshot.json sources.TradingCursor", "role": "technical/report context"},
        ],
        "forecasting": {
            "continuous": True,
            "engine": "MEDIUM8",
            "outputs": [
                "continuation_probability",
                "reversal_risk_score",
                "stale_penalty_score",
                "net_opportunity_score",
                "spread_quality",
            ],
        },
        "execution_authority": False,
    }


def source_record(name, payload):
    if not isinstance(payload, dict):
        return {"source": name, "status": "unavailable", "timestamp": iso_now(), "summary": "missing payload"}
    status = payload.get("status") or payload.get("trade_status") or payload.get("label")
    timestamp = payload.get("retrieved_at") or payload.get("timestamp") or payload.get("price_time")
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


def required_quote_record(name, crypto_quote, source=None):
    if source is None:
        provider = name.split(".", 1)[0]
        any_source_for_provider = next(
            (s for s in crypto_quote.get("quote_sources", []) if s["provider"] == provider),
            None,
        )
        return {
            "source": name,
            "provider": provider,
            "status": "missing",
            "timestamp": iso_now(),
            "summary": "missing required quote source",
            "age_seconds": any_source_for_provider["age_seconds"] if any_source_for_provider else None,
            "max_age_seconds": any_source_for_provider["max_age_seconds"] if any_source_for_provider else crypto_quote["max_age_seconds"],
        }
    return {
        "source": name,
        "provider": source["provider"],
        "status": "fresh" if source["fresh"] else "stale_or_unusable",
        "timestamp": source["timestamp"] or iso_now(),
        "summary": source["path"],
        "age_seconds": round(source["age_seconds"], 3) if source["age_seconds"] is not None else None,
        "max_age_seconds": source["max_age_seconds"],
        "bid": source["bid"],
        "ask": source["ask"],
        "last": source["last"],
    }


def optional_source_record(name, payload):
    if not isinstance(payload, dict):
        return {"source": name, "status": "UNAVAILABLE", "timestamp": iso_now(), "summary": "missing payload"}
    status = payload.get("status") or payload.get("trade_status") or payload.get("label")
    status_text = str(status or "").strip().lower()
    usable = payload.get("usable", True) is not False
    if not usable or status_text in {"rejected", "unavailable", "cooldown", "rate_limited"}:
        return {
            "source": name,
            "status": "UNAVAILABLE",
            "timestamp": payload.get("retrieved_at") or payload.get("timestamp") or iso_now(),
            "summary": status or "unavailable",
        }
    timestamp = payload.get("retrieved_at") or payload.get("timestamp") or payload.get("price_time")
    age_seconds = timestamp_age_seconds(timestamp)
    is_fresh = timestamp and age_seconds is not None and 0 <= age_seconds <= MAX_SOURCE_AGE_SECONDS
    return {
        "source": name,
        "status": "FRESH" if is_fresh else "STALE",
        "timestamp": timestamp or iso_now(),
        "summary": status,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "max_age_seconds": MAX_SOURCE_AGE_SECONDS,
    }


def apex_requires_positive_sentiment(settings):
    apex = settings.get("apex") if isinstance(settings, dict) else {}
    if not isinstance(apex, dict):
        return False
    return apex.get("requires_positive_stocktwits_sentiment") is True


def build_non_executable_envelope(symbols, sources, codex_heavy_state, lane):
    crypto_symbol, crypto_candidates = load_active_crypto_symbol()
    crypto_quote = load_crypto_quote(crypto_symbol)
    crypto_capital = load_crypto_capital_snapshot()
    if crypto_capital:
        crypto_quote["payload"].update(crypto_capital)
    longbridge = sources.get("Longbridge", {})
    stocktwits = sources.get("Stocktwits", {})
    tradingcursor = sources.get("TradingCursor", {})
    market_status = longbridge.get("market_status", {})
    temperature = longbridge.get("market_temperature", {})
    sentiment = stocktwits.get("sentiment", {})
    pulse = stocktwits.get("symbol_pulse", {})
    settings = load_json(USER_SETTINGS, {})

    symbol = crypto_symbol
    required_quote_sources = crypto_quote.get("required_quote_sources") or {}
    required_sources = [
        {
            "source": "volatile_crypto_candidates.active_symbol",
            "status": "fresh",
            "timestamp": iso_now(),
            "summary": crypto_candidates.get("active_symbol_reason"),
            "age_seconds": 0,
            "max_age_seconds": MAX_SOURCE_AGE_SECONDS,
        }
    ]
    # Robinhood is broker-authoritative. Other quote feeds remain optional
    # cross-checks and must not silently become viability gates.
    for provider in REQUIRED_CRYPTO_QUOTE_PROVIDERS:
        required_sources.append(
            required_quote_record(
                f"{provider}.crypto_quote",
                crypto_quote,
                required_quote_sources.get(provider),
            )
        )
    coingecko_quote = load_json(COINGECKO_CRYPTO_SNAPSHOT, {"usable": False, "status": "unavailable"})
    # NOT a hard gate: CoinGecko's free public API is rate-limited (confirmed
    # HTTP 429 in practice at <10s polling) and shared across all anonymous
    # callers, not just us. Gating live viability on it would make an
    # external, uncontrolled rate limit a single point of failure for the
    # whole system. It stays an informational cross-check in optional_sources.
    optional_sources = [
        optional_source_record("Longbridge.market_status", market_status),
        optional_source_record("Longbridge.market_temperature", temperature),
        optional_source_record("Stocktwits.sentiment", sentiment),
        optional_source_record("CoinGecko.last_price", coingecko_quote),
        optional_source_record("Stocktwits.symbol_pulse", pulse),
        optional_source_record("TradingCursor.analysis", tradingcursor.get("analysis", {"usable": False, "status": "unavailable"})),
    ]
    unavailable_optional_sources = [
        item for item in optional_sources if item.get("status") == "UNAVAILABLE"
    ]
    source_by_name = {item["source"]: item for item in required_sources}
    fresh_count = sum(1 for item in required_sources if item["status"] == "fresh")
    raw_market_open = any(
        isinstance(item, dict) and item.get("market") == "US" and item.get("trade_status") == "Trading"
        for item in market_status.get("market_time", []) if isinstance(market_status.get("market_time"), list)
    )
    market_status_record = next((item for item in optional_sources if item["source"] == "Longbridge.market_status"), {})
    market_status_fresh = market_status_record.get("status") == "FRESH"
    market_open = raw_market_open and market_status_fresh
    crypto_session_confirmed = True
    sentiment_score = sentiment.get("score")
    sentiment_label = sentiment.get("label")
    temperature_value = temperature.get("temperature")
    tradingcursor_rejected = str(tradingcursor.get("status") or "").lower() == "rejected"
    apex_sizing_fields = tradingcursor_apex_fields(tradingcursor.get("analysis", {}))
    if apex_sizing_fields:
        crypto_quote["payload"].update(apex_sizing_fields)

    failed = []
    if not crypto_quote["has_bid_ask_last"]:
        failed.append("APEX crypto bid/ask/last feed required but not populated")
    elif not crypto_quote["fresh"]:
        failed.append("APEX crypto bid/ask/last feed is stale")
    if not crypto_quote.get("required_quote_quorum_ok"):
        missing = ", ".join(crypto_quote.get("missing_required_quote_sources") or [])
        failed.append(f"required Robinhood crypto quote source not satisfied: missing {missing or 'required source freshness'}")
    if crypto_quote["source_conflict"]:
        failed.append("crypto quote sources conflict")
    if apex_requires_positive_sentiment(settings) and (
        sentiment_label == "BEARISH" or (isinstance(sentiment_score, (int, float)) and sentiment_score < 50)
    ):
        failed.append("Stocktwits sentiment is not positive")
    micro_trade_value = build_micro_trade_value(crypto_quote)
    requested_notional, requested_notional_source, sizing_inputs = apex_requested_notional(
        crypto_quote["payload"],
        settings,
        "CRYPTO",
    )
    if requested_notional is None:
        failed.append(requested_notional_source)
    crypto_projection = build_medium8_projection(
        required_sources,
        crypto_session_confirmed,
        sentiment,
        temperature,
        pulse,
        "MEDIUM8_CRYPTO_24_7",
        micro_trade_value,
    )
    blue_chip_projection = build_medium8_projection(
        required_sources,
        market_open,
        sentiment,
        temperature,
        pulse,
        "MEDIUM8_BLUE_CHIPS_MARKET_HOURS",
        micro_trade_value,
    )
    projection = {
        "mode": "MEDIUM_WEIGHT_DUAL_LANE",
        "forecasting_enabled": True,
        "forecasting_scope": "future continuation/reversal/net-opportunity projection for crypto 24/7 and blue-chip market-hours lanes",
        "forecasting_authority": "scanner forecast only; not trade execution authority",
        "execution_authority": False,
        "active_lane": "CRYPTO_24_7",
        "crypto": crypto_projection,
        "blue_chips": blue_chip_projection,
        "blue_chip_status": "ACTIVE_WHEN_EQUITY_MARKET_VERIFIED_OPEN" if market_open else "WATCH_ONLY_UNTIL_EQUITY_MARKET_VERIFIED_OPEN",
    }
    viable = not failed
    risk_status = "pass" if viable else "fail"
    broker_settings = settings.get("broker") if isinstance(settings, dict) else {}
    explicit_execution_authorization = (
        isinstance(broker_settings, dict)
        and broker_settings.get("explicit_execution_authorization") is True
    )

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
                "buying_power_usd",
                "crypto_buying_power_usd",
                "crypto_capital_source",
                "crypto_capital_retrieved_at",
                "entry_price_usd",
                "invalidation_price_usd",
                "stop_distance_usd",
                "maximum_position_size_usd",
            )
            if key in crypto_quote["payload"]
        },
        "symbol": symbol,
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": crypto_quote["payload"].get("venue", "UNKNOWN"),
        "broker_name": crypto_quote["payload"].get("broker_name", "Robinhood"),
        "algorithm_quote_contract": "APEX_REQUIRES_FRESH_CRYPTO_BID_ASK_LAST",
        "timestamp": iso_now(),
        "scanner_quote_stream": {
            "active": True,
            "owner": "RUNPOD_MEDIUM_WEIGHT_SCANNER",
            "cadence_seconds": MAX_LOOP_INTERVAL_SECONDS,
            "cadence_role": "envelope heartbeat only; not a REST market-data polling interval",
            "freshness_driver": "quote/trade timestamps written by websocket quote sources",
            "rest_snapshot_polling": False,
            "refresh_timestamp": crypto_quote["scanner_refresh_timestamp"],
            "source_path": crypto_quote["path"],
            "quote_source_count": crypto_quote["quote_source_count"],
            "fresh_quote_source_count": crypto_quote["fresh_quote_source_count"],
            "required_sources": list(REQUIRED_CRYPTO_QUOTE_PROVIDERS),
            "required_quote_quorum_ok": crypto_quote.get("required_quote_quorum_ok"),
            "missing_required_quote_sources": crypto_quote.get("missing_required_quote_sources"),
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
        "data_status": "fresh" if crypto_quote.get("required_quote_quorum_ok") else "stale" if crypto_quote["has_bid_ask_last"] else "unusable",
        "risk_status": risk_status,
        "source_count": fresh_count,
        "source_conflict": False,
        "buying_power_usd": crypto_quote["payload"].get("buying_power_usd"),
        "crypto_buying_power_usd": crypto_quote["payload"].get("crypto_buying_power_usd"),
        "crypto_capital_source": crypto_quote["payload"].get("crypto_capital_source"),
        "crypto_capital_retrieved_at": crypto_quote["payload"].get("crypto_capital_retrieved_at"),
        "requested_notional_usd": requested_notional,
        "requested_notional_source": requested_notional_source,
        "requested_notional_retrieved_at": iso_now(),
        "apex_sizing_inputs": sizing_inputs,
        "entry_price": crypto_quote["payload"].get("entry_price_usd"),
        "invalidation_price": crypto_quote["payload"].get("invalidation_price_usd"),
        "stop_distance_usd": crypto_quote["payload"].get("stop_distance_usd"),
        "crypto_account_confirmed": crypto_quote["payload"].get("crypto_account_confirmed", False),
        "maintenance_active": crypto_quote["payload"].get("maintenance_active"),
        "account_restricted": crypto_quote["payload"].get("account_restricted"),
        "margin_requested": False,
        "margin_approved": False,
        "account_net_worth_usd": crypto_quote["payload"].get("account_net_worth_usd"),
        "explicit_execution_authorization": explicit_execution_authorization,
    }
    envelope = {
        "architecture": ARCHITECTURE_NAME,
        "envelope_id": f"runpod-scan-{stable_hash({'symbol': symbol, 'sources': required_sources})[:16]}",
        "idempotency_key": f"{symbol}:{stable_hash({'sources': required_sources})[:24]}",
        "created_by": "CHATGPT_PLUGIN_SCANNER",
        "producer": {
            "file": "scripts/runpod_lightweight_scanner.py",
            "function": "build_non_executable_envelope",
            "runtime": "RUNPOD_MEDIUM_WEIGHT_SCANNER",
        },
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
        "data_provenance": required_sources,
        "required_sources": required_sources,
        "optional_sources": optional_sources,
        "unavailable_optional_sources": unavailable_optional_sources,
        "fresh_quote_source_count": crypto_quote["fresh_quote_source_count"],
        "entry_price": crypto_quote["payload"].get("entry_price_usd"),
        "invalidation_price": crypto_quote["payload"].get("invalidation_price_usd"),
        "stop_distance_usd": crypto_quote["payload"].get("stop_distance_usd"),
        "requested_notional_usd": requested_notional,
        "requested_notional_source": requested_notional_source,
        "source_quality": {
            "fresh_source_count": fresh_count,
            "apex_crypto_quote_feed": "fresh" if crypto_quote.get("required_quote_quorum_ok") else "stale_or_unusable",
            "apex_crypto_quote_source": crypto_quote["path"],
            "crypto_quote_source_count": crypto_quote["quote_source_count"],
            "fresh_crypto_quote_source_count": crypto_quote["fresh_quote_source_count"],
            "required_quote_quorum_ok": crypto_quote.get("required_quote_quorum_ok"),
            "missing_required_quote_sources": crypto_quote.get("missing_required_quote_sources"),
            "optional_source_count": len(optional_sources),
            "unavailable_optional_source_count": len(unavailable_optional_sources),
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
    online_coverage = online_source_coverage(sources)
    envelope = build_non_executable_envelope(symbols, sources, codex_heavy_state, lane)
    write_json(envelope_path, envelope)
    if lane == "primary":
        write_json(CANDIDATE_ENVELOPE, envelope)
    status = {
        "timestamp_utc": iso_now(),
        "architecture": ARCHITECTURE_NAME,
        "runtime": "RUNPOD_24_7_MEDIUM_WEIGHT_SCANNER",
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
        "stocktwits_widget_display_path": str(STOCKTWITS_WIDGET),
        "stocktwits_widget_market_pricing_display": True,
        "stocktwits_widget_scanner_ingest_authority": False,
        "stocktwits_widget_execution_authority": False,
        "stocktwits_fresh_scanner_input": "data/plugin_runtime_snapshot.json sources.Stocktwits with timestamped sentiment and symbol_pulse payloads",
        "online_market_media_reports_coverage": online_coverage,
        "source_refresh_policy": source_refresh_policy(),
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
            "future continuation forecasting",
            "future reversal-risk forecasting",
            "future net-opportunity forecasting",
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
        quote_last=envelope["market_input"].get("last"),
        source_quality=envelope["source_quality"],
    )
    print("RUNPOD_MEDIUM_WEIGHT_SCANNER: ACTIVE")
    print(f"SCANNER_LANE: {lane}")
    print(f"CODEX_HEAVY_STATE: {codex_heavy_state}")
    print(f"CANDIDATE_DECISION: {envelope['candidate_decision']}")
    print(f"SCANNER_VIABLE: {str(envelope['scanner_viable']).lower()}")
    print("TRADE_EXECUTION_ALLOWED: false")
    print("HEAVY_OPERATIONS_DEFAULT: ASLEEP")
    return status


def main():
    parser = argparse.ArgumentParser(description="Runpod 24/7 medium-weight scanner.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=MAX_LOOP_INTERVAL_SECONDS)
    parser.add_argument("--codex-heavy-state", default="UNKNOWN_OR_FROZEN")
    parser.add_argument("--lane", default="primary")
    parser.add_argument("--no-lock", action="store_true")
    args = parser.parse_args()

    if Path.cwd() != ROOT:
        print("RUNPOD_MEDIUM_WEIGHT_SCANNER: BLOCKED")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(1)

    lock = None
    if not args.once and not args.no_lock:
        lock_path = lane_paths(args.lane)[2]
        lock = acquire_lock(lock_path)
        if lock is None:
            print("RUNPOD_MEDIUM_WEIGHT_SCANNER: DUPLICATE_BLOCKED")
            print(f"LOCK_FILE: {lock_path}")
            return

    while True:
        scan_once(args.codex_heavy_state, args.lane)
        if args.once:
            return
        time.sleep(bounded_loop_interval(args.interval_seconds))


if __name__ == "__main__":
    main()
