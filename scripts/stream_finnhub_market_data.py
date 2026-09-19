#!/usr/bin/env python3
"""Persist authenticated Finnhub WebSocket trade evidence for stocks and crypto.

Finnhub's WebSocket contract provides trades (price/volume), not bid/ask. This
adapter therefore writes trade-fresh artifacts as corroborating market data;
the APEX quote gate must still obtain a real bid/ask/last quote elsewhere.
"""

import asyncio
import json
import os
import subprocess
import ssl
from datetime import datetime, timezone
from pathlib import Path

import certifi
import websockets

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
URL = "wss://ws.finnhub.io?token="
KEYCHAIN_SERVICE = "AI BLUE CHIP STOCKS Finnhub API"


def api_key():
    configured = os.environ.get("FINNHUB_API_KEY")
    if configured:
        return configured
    result = subprocess.run(
        ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def symbols():
    stock_file = ROOT / "data" / "blue_chip_watchlist.txt"
    crypto_file = ROOT / "data" / "crypto_watchlist.txt"
    stocks = [
        line.strip().upper()
        for line in stock_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    crypto = [
        "BINANCE:" + line.strip().upper().replace("/", "")
        for line in crypto_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return stocks + crypto


def write_trade(symbol, trade):
    timestamp = trade.get("t")
    timestamp_iso = (
        datetime.fromtimestamp(float(timestamp) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        if timestamp is not None else now_iso()
    )
    payload = {
        "symbol": symbol,
        "asset_class": "CRYPTO" if symbol.startswith("BINANCE:") else "US_EQUITY",
        "session": "CRYPTO_24_7" if symbol.startswith("BINANCE:") else "UNKNOWN_UNTIL_SESSION_CHECK",
        "provider": "Finnhub",
        "source": "Finnhub authenticated WebSocket trade stream",
        "venue": "Binance" if symbol.startswith("BINANCE:") else "Finnhub consolidated feed",
        "trade_timestamp": timestamp_iso,
        "timestamp": timestamp_iso,
        "last": float(trade["p"]),
        "volume": float(trade.get("v", 0)),
        "bid": None,
        "ask": None,
        "data_status": "trade_fresh_bid_ask_unavailable",
        "usable": True,
        "execution_authority": False,
    }
    safe = symbol.replace(":", "_").replace("/", "_")
    path = ROOT / "data" / f"finnhub_trade_snapshot_{safe}.json"
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


async def main():
    token = api_key()
    if not token:
        raise SystemExit("FINNHUB_API_KEY is required")
    tls = ssl.create_default_context(cafile=certifi.where())
    async with websockets.connect(URL + token, ssl=tls, ping_interval=20, ping_timeout=20) as socket:
        for symbol in symbols():
            await socket.send(json.dumps({"type": "subscribe", "symbol": symbol}))
        print(f"FINNHUB_CONNECTED symbols={len(symbols())}", flush=True)
        async for raw in socket:
            message = json.loads(raw)
            if message.get("type") != "trade":
                continue
            for trade in message.get("data", []):
                symbol = str(trade.get("s") or "").upper()
                if symbol and trade.get("p") is not None:
                    write_trade(symbol, trade)


if __name__ == "__main__":
    asyncio.run(main())
