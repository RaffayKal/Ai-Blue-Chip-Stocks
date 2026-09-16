#!/usr/bin/env python3
"""Free, no-signup, no-API-key crypto price cross-check via CoinGecko's
public REST API. Read-only. Writes a snapshot file in the same shape as
ingest_robinhood_crypto_quote_snapshot.py so it can serve as an independent
second/third source confirmation for the crypto lane, per the Cross-Source
Rule in rules/MARKET_SESSION_RULES.md.

CoinGecko's simple/price endpoint has no bid/ask book, only a last price, so
this cannot replace Robinhood/Alpaca for spread checks -- it exists purely
as an additional freshness/sanity cross-check.
"""
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import certifi

from project_root import ROOT

SNAPSHOT = ROOT / "data" / "coingecko_crypto_quote_snapshot.json"
COINGECKO_IDS = {"BTC": "bitcoin", "ETH": "ethereum"}
URL = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_last_updated_at=true"


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch(symbols):
    ids = ",".join(COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS)
    if not ids:
        raise SystemExit("BLOCKED: no supported symbols requested")
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(URL.format(ids=ids), headers={"User-Agent": "ai-blue-chip-stocks/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
        return json.load(response)


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    symbols = [s.upper() for s in (sys.argv[1:] or ["BTC"])]
    payload = fetch(symbols)

    results = {}
    for symbol in symbols:
        coingecko_id = COINGECKO_IDS.get(symbol)
        entry = payload.get(coingecko_id) if coingecko_id else None
        if not entry or "usd" not in entry:
            continue
        results[symbol] = {
            "symbol": symbol,
            "asset_class": "CRYPTO",
            "source": "CoinGecko.simple_price",
            "last": entry["usd"],
            "bid": None,
            "ask": None,
            "timestamp": iso(entry["last_updated_at"]) if entry.get("last_updated_at") else None,
            "note": "no order-book data; last price only, cross-check use",
        }

    if not results:
        raise SystemExit("BLOCKED: CoinGecko returned no usable results")

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"COINGECKO_CRYPTO_QUOTE_SNAPSHOT: {SNAPSHOT}")
    for symbol, quote in results.items():
        print(f"  {symbol}: last={quote['last']} as_of={quote['timestamp']}")


if __name__ == "__main__":
    main()
