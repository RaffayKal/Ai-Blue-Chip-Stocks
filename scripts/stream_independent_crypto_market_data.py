#!/usr/bin/env python3
"""Persist free public Binance and Kraken ticker streams as cross-checks."""

import asyncio
import json
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path

import certifi
import websockets

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
SYMBOL = os.environ.get("INDEPENDENT_CRYPTO_SYMBOL", "BTC").upper()
BINANCE_URL = "wss://data-stream.binance.vision:443/ws/btcusdt@ticker"
KRAKEN_URL = "wss://ws.kraken.com/v2"
ANNOUNCED = set()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_snapshot(provider, venue, bid, ask, last, timestamp):
    bid, ask, last = float(bid), float(ask), float(last)
    if min(bid, ask, last) <= 0 or ask < bid:
        raise ValueError(f"invalid {provider} quote")
    payload = {
        "symbol": SYMBOL,
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": venue,
        "broker_name": provider,
        "provider": provider,
        "source": f"{venue} public ticker WebSocket",
        "quote_timestamp": timestamp or now_iso(),
        "timestamp": timestamp or now_iso(),
        "bid": bid,
        "ask": ask,
        "last": last,
        "liquidity_usd": None,
        "data_status": "fresh",
        "usable": True,
        "execution_authority": False,
    }
    path = ROOT / "data" / f"{provider.lower()}_crypto_quote_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    if provider not in ANNOUNCED:
        ANNOUNCED.add(provider)
        print(f"{provider.upper()}_STREAM_FRESH: symbol={SYMBOL} quote_timestamp={payload['quote_timestamp']}", flush=True)


async def binance_loop(tls_context):
    while True:
        try:
            async with websockets.connect(BINANCE_URL, ssl=tls_context, ping_interval=20, ping_timeout=20) as socket:
                async for raw in socket:
                    message = json.loads(raw)
                    write_snapshot("Binance", "Binance Spot", message["b"], message["a"], message["c"], now_iso())
        except Exception as exc:
            print(f"BINANCE_STREAM_RECONNECT: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)


async def kraken_loop(tls_context):
    while True:
        try:
            async with websockets.connect(KRAKEN_URL, ssl=tls_context, ping_interval=20, ping_timeout=20) as socket:
                await socket.send(json.dumps({
                    "method": "subscribe",
                    "params": {"channel": "ticker", "symbol": ["BTC/USD"], "snapshot": True},
                }))
                async for raw in socket:
                    message = json.loads(raw)
                    if message.get("channel") != "ticker" or not message.get("data"):
                        continue
                    ticker = message["data"][0]
                    write_snapshot("Kraken", "Kraken Spot", ticker["bid"], ticker["ask"], ticker["last"], ticker.get("timestamp") or now_iso())
        except Exception as exc:
            print(f"KRAKEN_STREAM_RECONNECT: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)


async def main():
    tls_context = ssl.create_default_context(cafile=certifi.where())
    await asyncio.gather(binance_loop(tls_context), kraken_loop(tls_context))


if __name__ == "__main__":
    asyncio.run(main())
