#!/usr/bin/env python3
"""Multi-lane synergy research engine.

Implements rules/MULTI_LANE_SYNERGY_RESEARCH_LAW.md: with hundreds of
concurrent medium-weight scanner lanes available, multiple lanes are
dedicated per blue-chip/crypto symbol, each looking in a different
direction (MATH, HISTORY, RESEARCH, TEMPORAL), and their outputs are
synergized into one appreciation/depreciation forecast per symbol.

This module is read-only market research. It has no execution authority,
no order-gate access, and does not modify AUM, position, or capital state.
Its output is corroborating evidence only, consumed the same way Longbridge/
TradingCursor/Stocktwits evidence already is in
rules/MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md -- never sole trade authority.
"""
import os
import statistics

from project_root import ROOT
from runpod_lightweight_scanner import (
    iso_now,
    load_json,
    load_watchlist,
    timestamp_age_seconds,
    write_json,
)

ALPACA_STREAM_DIR = ROOT / "data" / "alpaca_stream"
PLUGIN_SNAPSHOT = ROOT / "data" / "plugin_runtime_snapshot.json"
HISTORY_DIR = ROOT / "data" / "lane_synergy_history"
OUTPUT_DIR = ROOT / "data" / "lane_synergy"
ROLLUP_PATH = ROOT / "data" / "lane_synergy_status.json"

# Crypto is the always-on 24/7 side of the fleet, but blue-chip stocks
# remain the primary focus (rules/BLUE_CHIP_RULES.md). This list is the
# *research* crypto universe for the multi-lane synergy layer only -- it is
# intentionally broader than, and separate from, the tradable/executable
# crypto set in rank_volatile_crypto_candidates.ROBINHOOD_SUPPORTED_TRACKED_SYMBOLS
# and runpod_lightweight_scanner.TRACKED_CRYPTO_SYMBOLS, which stay limited
# to what the broker can actually execute. Adding a coin here never grants
# it execution eligibility.
TRACKED_CRYPTO_SYMBOLS = ("BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "LTC", "DOT", "AVAX", "LINK", "BCH", "ETC", "XLM", "HBAR", "ALGO", "UNI", "NEAR", "ATOM", "SUI")
ROLES = ("MATH", "HISTORY", "RESEARCH", "TEMPORAL")

PRESENT_STALE_SECONDS = 120
ROLE_STALE_SECONDS = 180
HISTORY_WINDOW_CAP = 300
HISTORY_MIN_POINTS_FOR_SIGNAL = 5
FORECAST_NEUTRAL_BAND_PCT = 0.05  # momentum inside +-0.05% is NEUTRAL, not a call

# With 700+ lanes available, a single lane per (symbol, role) wastes most of
# the fleet's capacity. This fraction of the configured lane count is spent
# on the multi-lane synergy layer (piling multiple concurrent lanes onto the
# same symbol/role for finer-grained real-time sampling); the remainder
# keeps running the pre-existing generic single-active-symbol scan that the
# fleet consensus / candidate envelope already depends on. 1.0 would spend
# every lane on synergy research and none on the legacy path.
SYNERGY_LANE_SHARE = max(0.0, min(1.0, float(os.environ.get("RUNPOD_SYNERGY_LANE_SHARE", "0.6"))))


def synergy_symbols():
    """Full symbol universe this law applies to: every blue-chip watchlist
    entry plus every tracked crypto symbol. Order is stable so lane index
    N always maps to the same (symbol, role) pair run to run."""
    return list(dict.fromkeys(load_watchlist() + list(TRACKED_CRYPTO_SYMBOLS)))


def role_assignment(lane_index, symbols=None):
    """Map a 1-based lane index to a (symbol, role) pair. Wraps around once
    every (symbol, role) combo has one lane, so lane indices beyond the
    combo count deliberately pile additional concurrent lanes onto earlier
    combos -- any number of lanes can watch one blue-chip/crypto symbol.
    Returns None only when there is no symbol universe at all."""
    symbols = symbols if symbols is not None else synergy_symbols()
    combos = len(symbols) * len(ROLES)
    if combos == 0:
        return None
    combo_index = (lane_index - 1) % combos
    symbol = symbols[combo_index // len(ROLES)]
    role = ROLES[combo_index % len(ROLES)]
    return symbol, role


def dedicated_role_lane_count(lane_count, symbols=None, share=None):
    """How many of the configured lanes run the synergy layer (the rest run
    the legacy generic scan). Always at least one full pass over every
    (symbol, role) combo once lane_count allows it, then grows with
    SYNERGY_LANE_SHARE so extra capacity piles more lanes onto each symbol
    instead of sitting idle on the legacy path."""
    symbols = symbols if symbols is not None else synergy_symbols()
    combos = len(symbols) * len(ROLES)
    if combos == 0:
        return 0
    share = SYNERGY_LANE_SHARE if share is None else share
    target = max(combos, round(lane_count * share))
    return min(lane_count, target)


def _is_crypto(symbol):
    return symbol in TRACKED_CRYPTO_SYMBOLS


def present_price(symbol):
    """Read the freshest already-collected live price for this symbol from
    whichever real local feed already covers it. Never fabricates a price:
    returns None if nothing fresh is on disk."""
    if _is_crypto(symbol):
        record = load_json(ROOT / "data" / f"coingecko_crypto_quote_snapshot_{symbol}.json", None)
        if not isinstance(record, dict) or not record.get("usable"):
            return None
        price = record.get("last")
        timestamp = record.get("retrieved_at")
        source = record.get("source", "CoinGecko")
    else:
        record = load_json(ALPACA_STREAM_DIR / f"latest_stock_trade_{symbol}.json", None)
        if not isinstance(record, dict):
            return None
        price = (record.get("payload") or {}).get("price")
        timestamp = record.get("market_timestamp") or record.get("timestamp_utc")
        source = "AlpacaDataStream"
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    age = timestamp_age_seconds(timestamp)
    if age is None or age > PRESENT_STALE_SECONDS:
        return None
    return {"price": float(price), "timestamp_utc": timestamp, "source": source, "age_seconds": age}


def _history_path(symbol):
    return HISTORY_DIR / f"{symbol}.json"


def append_history(symbol, present):
    """Append this cycle's real observed price into a bounded rolling
    window on disk. This is the only source of PAST/HISTORY data -- no
    invented backfill."""
    path = _history_path(symbol)
    window = load_json(path, [])
    if not isinstance(window, list):
        window = []
    last_point = window[-1] if window else None
    if not last_point or last_point.get("timestamp_utc") != present["timestamp_utc"]:
        window.append({"price": present["price"], "timestamp_utc": present["timestamp_utc"]})
    if len(window) > HISTORY_WINDOW_CAP:
        window = window[-HISTORY_WINDOW_CAP:]
    write_json(path, window)
    return window


def _pct_changes(window):
    changes = []
    for previous, current in zip(window, window[1:]):
        if previous["price"] > 0:
            changes.append((current["price"] - previous["price"]) / previous["price"] * 100.0)
    return changes


def compute_math(symbol, window):
    """MATH lane: pure statistics over the real recorded window. No
    fabricated signal -- states INSUFFICIENT_DATA when the window is thin."""
    if len(window) < HISTORY_MIN_POINTS_FOR_SIGNAL:
        return {"status": "INSUFFICIENT_DATA", "points": len(window)}
    changes = _pct_changes(window)
    if not changes:
        return {"status": "INSUFFICIENT_DATA", "points": len(window)}
    momentum_pct = statistics.mean(changes)
    volatility_pct = statistics.pstdev(changes) if len(changes) > 1 else 0.0
    return {
        "status": "OK",
        "points": len(window),
        "momentum_pct_per_sample": round(momentum_pct, 6),
        "volatility_pct_per_sample": round(volatility_pct, 6),
    }


def compute_history(symbol, window):
    """HISTORY lane: recent range/trend context, read only -- what the
    real recorded window shows, not a projection."""
    if len(window) < 2:
        return {"status": "INSUFFICIENT_DATA", "points": len(window)}
    prices = [point["price"] for point in window]
    low, high = min(prices), max(prices)
    first, last = prices[0], prices[-1]
    span_pct = ((last - first) / first * 100.0) if first > 0 else 0.0
    return {
        "status": "OK",
        "points": len(window),
        "window_low": low,
        "window_high": high,
        "window_start_price": first,
        "window_latest_price": last,
        "window_change_pct": round(span_pct, 6),
        "trend_direction": "UP" if span_pct > 0 else ("DOWN" if span_pct < 0 else "FLAT"),
    }


def _sentiment_for_symbol(symbol):
    snapshot = load_json(PLUGIN_SNAPSHOT, {})
    stocktwits = (snapshot.get("sources") or {}).get("Stocktwits") or {}
    for block_name in ("sentiment", "symbol_pulse"):
        block = stocktwits.get(block_name) or {}
        scope = str(block.get("scope") or block.get("symbol") or "").strip().upper()
        if not block.get("usable"):
            continue
        if scope == symbol or scope == f"{symbol}.X" or scope == f"{symbol}USD":
            return block_name, block
    return None, None


def compute_research(symbol):
    """RESEARCH lane: news/media/web/sentiment layer. Only Stocktwits
    sentiment is connected today, and only for the plugin's active crypto
    scope. Per the Missing Plugin Rule (MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md),
    an unconnected source is reported as PLUGIN_UNAVAILABLE, never faked."""
    block_name, block = _sentiment_for_symbol(symbol)
    if block is None:
        return {
            "status": "PLUGIN_UNAVAILABLE",
            "reason": "No connected news/media/web/sentiment source currently covers this symbol",
        }
    retrieved_at = block.get("retrieved_at")
    age = timestamp_age_seconds(retrieved_at)
    if age is not None and age > ROLE_STALE_SECONDS * 10:
        return {"status": "STALE", "source_block": block_name, "age_seconds": age}
    return {
        "status": "OK",
        "source": "Stocktwits",
        "source_block": block_name,
        "label": block.get("label"),
        "score": block.get("score"),
        "summary": block.get("summary"),
        "age_seconds": age,
    }


def compute_temporal(symbol, present, window, math_result):
    """TEMPORAL lane: assembles PAST (oldest point still in the real
    window) / PRESENT (latest live read) / FUTURE (a labeled linear
    extrapolation of MATH's own momentum -- a projection, never claimed as
    fact) into one frame."""
    past = window[0] if window else None
    future = None
    if math_result.get("status") == "OK":
        momentum = math_result["momentum_pct_per_sample"]
        future = {
            "projected_change_pct_next_sample": round(momentum, 6),
            "basis": "linear_extrapolation_of_recent_momentum",
            "disclaimer": "PROJECTION_NOT_GUARANTEE",
        }
    return {
        "status": "OK" if past else "INSUFFICIENT_DATA",
        "past": past,
        "present": {"price": present["price"], "timestamp_utc": present["timestamp_utc"]},
        "future": future,
    }


def run_role(symbol, role):
    """Compute one role's output for one symbol and persist it. Returns
    the payload written (or a DATA_UNAVAILABLE stub if there is no fresh
    live price to work from at all)."""
    if role == "RESEARCH":
        # News/media/web/sentiment is independent of live price freshness --
        # never gate it behind a price tick that may legitimately lag.
        payload = compute_research(symbol)
    else:
        present = present_price(symbol)
        if present is None:
            payload = {"status": "DATA_UNAVAILABLE", "reason": "No fresh live price on disk for this symbol"}
        elif role == "MATH":
            payload = compute_math(symbol, append_history(symbol, present))
        elif role == "HISTORY":
            payload = compute_history(symbol, append_history(symbol, present))
        else:  # TEMPORAL
            window = append_history(symbol, present)
            math_result = compute_math(symbol, window)
            payload = compute_temporal(symbol, present, window, math_result)
    payload.update({"symbol": symbol, "role": role, "timestamp_utc": iso_now()})
    write_json(OUTPUT_DIR / symbol / f"{role.lower()}.json", payload)
    return payload


def _role_fresh(role_payload):
    if not isinstance(role_payload, dict):
        return False
    age = timestamp_age_seconds(role_payload.get("timestamp_utc"))
    return age is not None and age <= ROLE_STALE_SECONDS


def run_synergy(symbol):
    """Combine this symbol's four role outputs into one forecast. Requires
    MATH, HISTORY, and TEMPORAL to be fresh and OK; RESEARCH is
    corroborating only, since it is frequently PLUGIN_UNAVAILABLE today."""
    roles = {role: load_json(OUTPUT_DIR / symbol / f"{role.lower()}.json", None) for role in ROLES}
    fresh_core = [
        roles[name] for name in ("MATH", "HISTORY", "TEMPORAL")
        if _role_fresh(roles[name]) and roles[name].get("status") == "OK"
    ]
    research = roles.get("RESEARCH")
    research_ok = _role_fresh(research) and (research or {}).get("status") == "OK"

    if len(fresh_core) < 3:
        forecast = "INSUFFICIENT_SYNERGY_DATA"
        momentum = None
    else:
        momentum = roles["MATH"]["momentum_pct_per_sample"]
        if momentum > FORECAST_NEUTRAL_BAND_PCT:
            forecast = "APPRECIATION_LIKELY"
        elif momentum < -FORECAST_NEUTRAL_BAND_PCT:
            forecast = "DEPRECIATION_LIKELY"
        else:
            forecast = "NEUTRAL"

    payload = {
        "symbol": symbol,
        "timestamp_utc": iso_now(),
        "forecast": forecast,
        "momentum_pct_per_sample": momentum,
        "roles_fresh_ok_count": len(fresh_core),
        "research_corroboration": "OK" if research_ok else (research or {}).get("status", "UNKNOWN"),
        "note": "Read-only research synergy. Not trade execution authority.",
    }
    write_json(OUTPUT_DIR / symbol / "synergy.json", payload)
    return payload


def run_rollup(symbols=None):
    symbols = symbols if symbols is not None else synergy_symbols()
    per_symbol = {}
    for symbol in symbols:
        synergy = load_json(OUTPUT_DIR / symbol / "synergy.json", None)
        if isinstance(synergy, dict):
            per_symbol[symbol] = {
                "forecast": synergy.get("forecast"),
                "momentum_pct_per_sample": synergy.get("momentum_pct_per_sample"),
                "roles_fresh_ok_count": synergy.get("roles_fresh_ok_count"),
                "timestamp_utc": synergy.get("timestamp_utc"),
            }
    payload = {
        "timestamp_utc": iso_now(),
        "symbols_tracked": len(symbols),
        "symbols_with_synergy_output": len(per_symbol),
        "per_symbol": per_symbol,
        "note": "Read-only multi-lane synergy research rollup. Not trade execution authority.",
    }
    write_json(ROLLUP_PATH, payload)
    return payload
