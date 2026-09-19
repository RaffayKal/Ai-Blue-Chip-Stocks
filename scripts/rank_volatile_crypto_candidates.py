#!/usr/bin/env python3
"""Select the active crypto symbol by actual measured short-window volatility.

Before this script existed, data/volatile_crypto_candidates.json was a
static file whose own "active_symbol_reason" field admitted it was a
"fallback until a live volatile crypto scanner writes a verified
higher-ranked ... symbol" -- that scanner never existed, so every cycle of
the entire system only ever analyzed BTC, regardless of what the rules say
about tracking the most volatile verified Robinhood-supported crypto.

This only ranks candidates using public, credential-free market data
(Coinbase/Binance/Kraken/CoinGecko quote snapshots already written by the
stream_*.py scripts). It never claims to check broker-side facts it cannot
know from here (account restrictions, maintenance mode, broker preview) --
those remain Codex/Robinhood-side gates, enforced downstream.
"""
import argparse
import time
from collections import deque
from pathlib import Path

from project_root import ROOT
from runpod_lightweight_scanner import iso_now, load_json, timestamp_age_seconds, write_json

CANDIDATES_PATH = ROOT / "data" / "volatile_crypto_candidates.json"
# Real, currently-supported Robinhood Crypto symbols this script has live
# quote data for. Never add a symbol here without a matching stream writer.
# Crypto is a 24/7 micro-trading system here, secondary to blue-chip stocks.
# Confirmed tradable on Robinhood as of 2026-09-17
# (robinhood.com/us/en/support/articles/coin-availability/); each has a
# live CoinGecko quote writer at minimum (stream_coingecko_market_data.py).
ROBINHOOD_SUPPORTED_TRACKED_SYMBOLS = ("BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "LTC", "DOT", "AVAX", "LINK", "BCH", "ETC", "XLM", "HBAR", "ALGO", "UNI", "NEAR", "ATOM", "SUI")
PROVIDERS = ("coinbase", "binance", "kraken", "coingecko")
MAX_QUOTE_AGE_SECONDS = 30.0
MIN_VOLATILITY_SAMPLES = 3
HISTORY_WINDOW_SECONDS = 300.0
DEFAULT_INTERVAL_SECONDS = 15.0


def freshest_quote(symbol):
    """Return (last_price, age_seconds) from whichever provider has the
    freshest usable quote for this symbol, or (None, None) if none qualify."""
    best = None
    for provider in PROVIDERS:
        path = ROOT / "data" / f"{provider}_crypto_quote_snapshot_{symbol}.json"
        payload = load_json(path, {})
        if not isinstance(payload, dict) or payload.get("usable") is False:
            continue
        last = payload.get("last")
        if not isinstance(last, (int, float)) or last <= 0:
            continue
        timestamp = payload.get("quote_timestamp") or payload.get("timestamp") or payload.get("retrieved_at")
        age = timestamp_age_seconds(timestamp)
        if age is None or age < 0 or age > MAX_QUOTE_AGE_SECONDS:
            continue
        if best is None or age < best[1]:
            best = (float(last), age)
    return best if best is not None else (None, None)


def update_history(history, symbol, price, now_seconds):
    window = history.setdefault(symbol, deque())
    window.append((now_seconds, price))
    cutoff = now_seconds - HISTORY_WINDOW_SECONDS
    while window and window[0][0] < cutoff:
        window.popleft()


def volatility_percent(window):
    if len(window) < MIN_VOLATILITY_SAMPLES:
        return None
    prices = [price for _, price in window]
    mean_price = sum(prices) / len(prices)
    if mean_price <= 0:
        return None
    return round((max(prices) - min(prices)) / mean_price * 100.0, 6)


def rank_once(history, now_seconds):
    """One evaluation pass. Returns (ranked, fresh_symbols) where ranked is a
    list of (symbol, volatility_percent) sorted highest-volatility first,
    restricted to symbols with a fresh quote and enough history to measure."""
    fresh_symbols = {}
    for symbol in ROBINHOOD_SUPPORTED_TRACKED_SYMBOLS:
        price, age = freshest_quote(symbol)
        if price is None:
            continue
        fresh_symbols[symbol] = age
        update_history(history, symbol, price, now_seconds)

    ranked = []
    for symbol in fresh_symbols:
        score = volatility_percent(history.get(symbol, ()))
        if score is not None:
            ranked.append((symbol, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked, fresh_symbols


def write_active_symbol(ranked, fresh_symbols):
    existing = load_json(CANDIDATES_PATH, {})
    if not isinstance(existing, dict):
        existing = {}
    fallback_symbol = existing.get("fallback_symbol", "BTC")
    if ranked:
        active_symbol, top_score = ranked[0]
        reason = f"measured short-window volatility leader ({top_score}% over up to {int(HISTORY_WINDOW_SECONDS)}s)"
    elif fresh_symbols:
        # Fresh data exists but not enough history yet to measure volatility.
        active_symbol = fallback_symbol if fallback_symbol in fresh_symbols else next(iter(fresh_symbols))
        reason = "fresh quote available but insufficient history to measure volatility yet"
    else:
        active_symbol = fallback_symbol
        reason = "no tracked symbol has a fresh quote; holding fallback symbol"

    payload = {
        **existing,
        "active_symbol": active_symbol,
        "active_symbol_reason": reason,
        "fallback_symbol": fallback_symbol,
        "tracked_symbols": list(ROBINHOOD_SUPPORTED_TRACKED_SYMBOLS),
        "volatility_scores": {symbol: score for symbol, score in ranked},
        "fresh_symbols": sorted(fresh_symbols),
        "ranked_at": iso_now(),
    }
    write_json(CANDIDATES_PATH, payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Rank tracked crypto symbols by measured volatility.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    args = parser.parse_args()

    history = {}
    while True:
        now_seconds = time.time()
        ranked, fresh_symbols = rank_once(history, now_seconds)
        payload = write_active_symbol(ranked, fresh_symbols)
        print(
            f"VOLATILE_CRYPTO_RANK active_symbol={payload['active_symbol']} "
            f"scores={payload['volatility_scores']} fresh={payload['fresh_symbols']}",
            flush=True,
        )
        if args.once:
            return
        time.sleep(max(4.0, args.interval_seconds))


if __name__ == "__main__":
    main()
