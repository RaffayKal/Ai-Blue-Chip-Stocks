#!/usr/bin/env python3
"""Poll Robinhood's official Crypto Trading API for read-only quotes."""

import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from nacl.signing import SigningKey

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"
BASE_URL = "https://trading.robinhood.com"
SYMBOL = os.environ.get("ROBINHOOD_CRYPTO_SYMBOL", "BTC-USD").upper()
INTERVAL = max(4.0, min(420.0, float(os.environ.get("ROBINHOOD_CRYPTO_API_INTERVAL_SECONDS", "7"))))
API_KEY = os.environ.get("ROBINHOOD_CRYPTO_API_KEY", "")
PRIVATE_KEY_B64 = os.environ.get("ROBINHOOD_CRYPTO_PRIVATE_KEY_B64", "")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def signed_headers(method, path, body=""):
    timestamp = str(int(time.time()))
    message = f"{API_KEY}{timestamp}{path}{method}{body}"
    signing_key = SigningKey(base64.b64decode(PRIVATE_KEY_B64))
    signature = base64.b64encode(signing_key.sign(message.encode("utf-8")).signature).decode("ascii")
    return {
        "x-api-key": API_KEY,
        "x-signature": signature,
        "x-timestamp": timestamp,
        "Content-Type": "application/json; charset=utf-8",
    }


def fetch_quote():
    path = "/api/v1/crypto/marketdata/best_bid_ask/"
    response = requests.get(
        BASE_URL + path,
        params=[("symbol", SYMBOL)],
        headers=signed_headers("GET", path),
        timeout=15,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise ValueError("Robinhood API returned no quote")
    result = results[0]
    bid, ask = float(result["bid_price"]), float(result["ask_price"])
    if min(bid, ask) <= 0 or ask < bid:
        raise ValueError("invalid Robinhood API quote")
    timestamp = result.get("timestamp") or now_iso()
    payload = {
        "symbol": SYMBOL.split("-", 1)[0],
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Robinhood Crypto",
        "broker_name": "Robinhood",
        "provider": "Robinhood",
        "source": "Robinhood Crypto Trading API best_bid_ask",
        "quote_timestamp": timestamp,
        "timestamp": timestamp,
        "bid": bid,
        "ask": ask,
        "last": (bid + ask) / 2,
        "liquidity_usd": None,
        "data_status": "fresh",
        "usable": True,
        "execution_authority": True,
        "routing": result.get("routing"),
    }
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT.with_suffix(SNAPSHOT.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(SNAPSHOT)
    return payload


def main():
    if not API_KEY or not PRIVATE_KEY_B64:
        raise SystemExit("BLOCKED: ROBINHOOD_CRYPTO_API_KEY and ROBINHOOD_CRYPTO_PRIVATE_KEY_B64 are required")
    announced = False
    while True:
        try:
            payload = fetch_quote()
            if not announced:
                print(f"ROBINHOOD_CRYPTO_API_FRESH: symbol={payload['symbol']} quote_timestamp={payload['quote_timestamp']}", flush=True)
                announced = True
        except (OSError, ValueError, KeyError, requests.RequestException, base64.binascii.Error) as exc:
            print(f"ROBINHOOD_CRYPTO_API_RETRY: {type(exc).__name__}: {exc}", flush=True)
            announced = False
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
