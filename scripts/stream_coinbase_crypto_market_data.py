#!/usr/bin/env python3
"""Persist free public Coinbase ticker WebSocket data as a read-only cross-check.

Tracks multiple products (default BTC-USD, ETH-USD, SOL-USD) so the
volatility ranker has more than BTC to compare — previously this only ever
tracked BTC-USD.
"""

import asyncio
import json
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path

import certifi
import websockets

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
URL = "wss://advanced-trade-ws.coinbase.com"


def _configured_products():
    # BNB is intentionally excluded here: Coinbase does not list a BNB-USD
    # product (Binance's own coin isn't traded on a competing exchange).
    # It still has live CoinGecko and Binance-ticker coverage.
    raw = (
        os.environ.get("COINBASE_CRYPTO_PRODUCTS")
        or os.environ.get("COINBASE_CRYPTO_PRODUCT")
        or "BTC-USD,ETH-USD,SOL-USD,XRP-USD,ADA-USD,DOGE-USD,LTC-USD,DOT-USD,AVAX-USD,LINK-USD,BCH-USD,ETC-USD,XLM-USD,HBAR-USD,ALGO-USD,UNI-USD,NEAR-USD,ATOM-USD,SUI-USD"
    )
    products = [p.strip().upper() for p in raw.split(",") if p.strip()]
    return products or ["BTC-USD"]


PRODUCT_IDS = _configured_products()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def snapshot_paths(symbol):
    paths = [ROOT / "data" / f"coinbase_crypto_quote_snapshot_{symbol}.json"]
    if symbol == "BTC":
        paths.append(ROOT / "data" / "coinbase_crypto_quote_snapshot.json")
    return paths


def write_snapshot(ticker):
    bid = float(ticker["best_bid"])
    ask = float(ticker["best_ask"])
    last = float(ticker["price"])
    if min(bid, ask, last) <= 0 or ask < bid:
        raise ValueError("invalid Coinbase quote")
    timestamp = ticker.get("time") or now_iso()
    product_id = ticker.get("product_id", "")
    symbol = product_id.replace("-USD", "")
    payload = {
        "symbol": symbol,
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Coinbase Advanced Trade",
        "broker_name": "Coinbase",
        "provider": "Coinbase",
        "source": "Coinbase Advanced Trade public ticker WebSocket",
        "quote_timestamp": timestamp,
        "timestamp": timestamp,
        "bid": bid,
        "ask": ask,
        "last": last,
        "liquidity_usd": None,
        "data_status": "fresh",
        "usable": True,
        "execution_authority": False,
    }
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for path in snapshot_paths(symbol):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + f".{symbol}.{os.getpid()}.tmp")
        temporary.write_text(body, encoding="utf-8")
        temporary.replace(path)


async def run():
    tls_context = ssl.create_default_context(cafile=certifi.where())
    while True:
        try:
            async with websockets.connect(URL, ssl=tls_context, ping_interval=20, ping_timeout=20) as socket:
                await socket.send(json.dumps({
                    "type": "subscribe",
                    "channel": "ticker",
                    "product_ids": PRODUCT_IDS,
                }))
                async for raw in socket:
                    message = json.loads(raw)
                    for event in message.get("events", []):
                        for ticker in event.get("tickers", []):
                            if ticker.get("product_id") in PRODUCT_IDS:
                                write_snapshot(ticker)
        except (OSError, asyncio.TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f"COINBASE_STREAM_RECONNECT: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
