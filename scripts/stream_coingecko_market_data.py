#!/usr/bin/env python3
"""Continuous, free, no-key crypto price poller (CoinGecko public API).

Runs forever, polling on an interval that respects CoinGecko's free-tier
rate limit, and writes data/coingecko_crypto_quote_snapshot.json in the
shape runpod_lightweight_scanner.py's optional_source_record() expects.
Read-only market data only -- no broker calls, no order placement.

Meant to run alongside stream_alpaca_market_data.py under
scripts/start_runpod_scanner_24_7.sh (or the LaunchAgent), so the scanner
always has a fresh third-source crypto cross-check without depending on
an MCP-only connection.
"""
import json
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import certifi

from project_root import ROOT

SYMBOL_TO_COINGECKO_ID = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
COINGECKO_IDS = ",".join(SYMBOL_TO_COINGECKO_ID.values())
URL = f"https://api.coingecko.com/api/v3/simple/price?ids={COINGECKO_IDS}&vs_currencies=usd&include_last_updated_at=true"
POLL_INTERVAL_SECONDS = 20  # confirmed HTTP 429 at 5s polling; 20s (~3/min) is the safe sustained rate observed; one request covers every tracked symbol


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def snapshot_paths(symbol):
    paths = [ROOT / "data" / f"coingecko_crypto_quote_snapshot_{symbol}.json"]
    if symbol == "BTC":
        paths.append(ROOT / "data" / "coingecko_crypto_quote_snapshot.json")
    return paths


def fetch_all(ctx):
    req = Request(URL, headers={"User-Agent": "ai-blue-chip-stocks/1.0"})
    with urlopen(req, timeout=10, context=ctx) as response:
        payload = json.load(response)
    snapshots = {}
    for symbol, coingecko_id in SYMBOL_TO_COINGECKO_ID.items():
        entry = payload.get(coingecko_id)
        if not entry or "usd" not in entry:
            continue
        snapshots[symbol] = {
            "status": "ok",
            "usable": True,
            "symbol": symbol,
            "source": "CoinGecko.simple_price",
            "last": entry["usd"],
            "retrieved_at": iso(entry["last_updated_at"]) if entry.get("last_updated_at") else iso_now(),
        }
    if not snapshots:
        raise ValueError("missing usd price for every tracked symbol in CoinGecko response")
    return snapshots


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    once = "--once" in sys.argv
    ctx = ssl.create_default_context(cafile=certifi.where())

    while True:
        try:
            snapshots = fetch_all(ctx)
            for symbol, snapshot in snapshots.items():
                for path in snapshot_paths(symbol):
                    write_json(path, snapshot)
                print(f"COINGECKO_QUOTE symbol={symbol} last={snapshot['last']} retrieved_at={snapshot['retrieved_at']}", flush=True)
        except (URLError, ValueError, TimeoutError) as exc:
            for symbol in SYMBOL_TO_COINGECKO_ID:
                for path in snapshot_paths(symbol):
                    write_json(path, {
                        "status": "unavailable",
                        "usable": False,
                        "symbol": symbol,
                        "source": "CoinGecko.simple_price",
                        "retrieved_at": iso_now(),
                        "error": str(exc),
                    })
            print(f"COINGECKO_QUOTE_ERROR {exc}", flush=True)

        if once:
            return
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
