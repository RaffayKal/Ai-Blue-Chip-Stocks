#!/usr/bin/env python3
"""Persist a free public Coinbase ticker WebSocket as a read-only cross-check."""

import asyncio
import json
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path

import certifi
import websockets

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
SNAPSHOT = ROOT / "data" / "coinbase_crypto_quote_snapshot.json"
URL = "wss://advanced-trade-ws.coinbase.com"
PRODUCT_ID = os.environ.get("COINBASE_CRYPTO_PRODUCT", "BTC-USD").upper()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_snapshot(ticker):
    bid = float(ticker["best_bid"])
    ask = float(ticker["best_ask"])
    last = float(ticker["price"])
    if min(bid, ask, last) <= 0 or ask < bid:
        raise ValueError("invalid Coinbase quote")
    timestamp = ticker.get("time") or now_iso()
    payload = {
        "symbol": PRODUCT_ID.replace("-USD", ""),
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
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(SNAPSHOT)


async def run():
    tls_context = ssl.create_default_context(cafile=certifi.where())
    while True:
        try:
            async with websockets.connect(URL, ssl=tls_context, ping_interval=20, ping_timeout=20) as socket:
                await socket.send(json.dumps({
                    "type": "subscribe",
                    "channel": "ticker",
                    "product_ids": [PRODUCT_ID],
                }))
                async for raw in socket:
                    message = json.loads(raw)
                    for event in message.get("events", []):
                        for ticker in event.get("tickers", []):
                            if ticker.get("product_id") == PRODUCT_ID:
                                write_snapshot(ticker)
        except (OSError, asyncio.TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f"COINBASE_STREAM_RECONNECT: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
