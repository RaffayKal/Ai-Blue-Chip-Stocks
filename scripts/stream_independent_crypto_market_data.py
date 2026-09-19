#!/usr/bin/env python3
"""Persist free public Binance and Kraken ticker streams as cross-checks.

Tracks multiple symbols (default BTC, ETH, SOL) so the volatility ranker in
rank_volatile_crypto_candidates.py has more than one candidate to compare —
previously this only ever tracked BTC, which meant the "most volatile
verified crypto" selection described in the rules never had a second symbol
to rank against and the active symbol was permanently stuck on the BTC
fallback.
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


def _configured_symbols():
    raw = (
        os.environ.get("INDEPENDENT_CRYPTO_SYMBOLS")
        or os.environ.get("INDEPENDENT_CRYPTO_SYMBOL")
        or "BTC,ETH,SOL,XRP,BNB,ADA,DOGE,LTC,DOT,AVAX,LINK"
    )
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    return symbols or ["BTC"]


SYMBOLS = _configured_symbols()
BINANCE_STREAM_NAMES = {symbol: f"{symbol.lower()}usdt@ticker" for symbol in SYMBOLS}
BINANCE_URL = "wss://data-stream.binance.vision:443/stream?streams=" + "/".join(BINANCE_STREAM_NAMES.values())
KRAKEN_URL = "wss://ws.kraken.com/v2"
KRAKEN_PAIRS = [f"{symbol}/USD" for symbol in SYMBOLS]
ANNOUNCED = set()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_snapshot(provider, venue, symbol, bid, ask, last, timestamp):
    bid, ask, last = float(bid), float(ask), float(last)
    if min(bid, ask, last) <= 0 or ask < bid:
        raise ValueError(f"invalid {provider} quote")
    payload = {
        "symbol": symbol,
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
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    paths = [ROOT / "data" / f"{provider.lower()}_crypto_quote_snapshot_{symbol}.json"]
    if symbol == "BTC":
        # Legacy fixed path: keeps every existing BTC-only consumer working
        # unchanged while additional symbols become available alongside it.
        paths.append(ROOT / "data" / f"{provider.lower()}_crypto_quote_snapshot.json")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + f".{symbol}.{os.getpid()}.tmp")
        temporary.write_text(body, encoding="utf-8")
        temporary.replace(path)
    announce_key = (provider, symbol)
    if announce_key not in ANNOUNCED:
        ANNOUNCED.add(announce_key)
        print(f"{provider.upper()}_STREAM_FRESH: symbol={symbol} quote_timestamp={payload['quote_timestamp']}", flush=True)


async def binance_loop(tls_context):
    reverse_stream_names = {name: symbol for symbol, name in BINANCE_STREAM_NAMES.items()}
    while True:
        try:
            async with websockets.connect(BINANCE_URL, ssl=tls_context, ping_interval=20, ping_timeout=20) as socket:
                async for raw in socket:
                    message = json.loads(raw)
                    stream_name = message.get("stream")
                    data = message.get("data")
                    symbol = reverse_stream_names.get(stream_name)
                    if not symbol or not isinstance(data, dict):
                        continue
                    write_snapshot("Binance", "Binance Spot", symbol, data["b"], data["a"], data["c"], now_iso())
        except Exception as exc:
            print(f"BINANCE_STREAM_RECONNECT: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)


async def kraken_loop(tls_context):
    while True:
        try:
            async with websockets.connect(KRAKEN_URL, ssl=tls_context, ping_interval=20, ping_timeout=20) as socket:
                await socket.send(json.dumps({
                    "method": "subscribe",
                    "params": {"channel": "ticker", "symbol": KRAKEN_PAIRS, "snapshot": True},
                }))
                async for raw in socket:
                    message = json.loads(raw)
                    if message.get("channel") != "ticker" or not message.get("data"):
                        continue
                    ticker = message["data"][0]
                    symbol = str(ticker.get("symbol", "")).split("/")[0].upper()
                    if symbol not in SYMBOLS:
                        continue
                    write_snapshot("Kraken", "Kraken Spot", symbol, ticker["bid"], ticker["ask"], ticker["last"], ticker.get("timestamp") or now_iso())
        except Exception as exc:
            print(f"KRAKEN_STREAM_RECONNECT: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(5)


async def main():
    tls_context = ssl.create_default_context(cafile=certifi.where())
    await asyncio.gather(binance_loop(tls_context), kraken_loop(tls_context))


if __name__ == "__main__":
    asyncio.run(main())
