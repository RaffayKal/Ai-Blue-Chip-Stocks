#!/usr/bin/env python3
"""Pull snapshots from a secured Robinhood MCP relay into the local scanner."""

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT
from quote_time_policy import quote_age_is_fresh

URL = os.getenv("ROBINHOOD_MCP_RELAY_URL", "").rstrip("/") + "/v1/robinhood/crypto-quote"
TOKEN = os.getenv("ROBINHOOD_MCP_RELAY_TOKEN", "")
INTERVAL = max(4.0, min(420.0, float(os.getenv("ROBINHOOD_MCP_RELAY_INTERVAL_SECONDS", "7"))))
SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"
MAX_QUOTE_AGE_SECONDS = 420


def normalized_symbol(value):
    symbol = str(value or "").strip().upper().replace("-", "")
    if symbol.endswith("USD"):
        symbol = symbol[:-3]
    if not symbol:
        raise ValueError("relay payload has an invalid crypto symbol")
    return symbol


def write_snapshot(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def validated_public_snapshot(payload):
    if not isinstance(payload, dict) or payload.get("source") not in {"Robinhood.get_crypto_quotes", "robinhood"} or str(payload.get("asset_class", "")).upper() != "CRYPTO":
        raise ValueError("relay payload is not a Robinhood crypto quote snapshot")
    for field in ("bid", "ask", "last", "quote_timestamp", "symbol", "routing"):
        if not payload.get(field):
            raise ValueError(f"relay payload missing {field}")
    try:
        stamp = datetime.fromisoformat(str(payload["quote_timestamp"]).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("quote timestamp has no timezone")
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
        if not quote_age_is_fresh(age, MAX_QUOTE_AGE_SECONDS):
            raise ValueError("relay quote is stale")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"relay quote timestamp invalid or stale: {exc}") from exc
    for field in ("bid", "ask", "last"):
        try:
            if float(payload[field]) <= 0:
                raise ValueError(f"relay {field} is not positive")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"relay {field} invalid: {exc}") from exc
    return {
        "symbol": normalized_symbol(payload["symbol"]),
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Robinhood Crypto",
        "broker_name": "Robinhood",
        "bid": payload["bid"],
        "ask": payload["ask"],
        "last": payload["last"],
        "routing": payload["routing"],
        "quote_timestamp": payload["quote_timestamp"],
        "timestamp": payload["quote_timestamp"],
        "data_status": "fresh",
        "source": "Robinhood.get_crypto_quotes",
    }


def poll_once():
    request = urllib.request.Request(URL, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(request, timeout=10) as response:
        response_payload = json.load(response)
    payload = response_payload.get("snapshot", response_payload)
    payload = validated_public_snapshot(payload)
    # The scanner selects quotes by symbol. Keep the latest snapshot for each
    # symbol as well as the legacy "latest quote" file; otherwise a dynamic
    # candidate can silently fall back to a stale or wrong-symbol snapshot.
    symbol_snapshot = SNAPSHOT.with_name(f"robinhood_crypto_quote_snapshot_{payload['symbol']}.json")
    write_snapshot(symbol_snapshot, payload)
    write_snapshot(SNAPSHOT, payload)


if __name__ == "__main__":
    if not TOKEN or not os.getenv("ROBINHOOD_MCP_RELAY_URL"):
        raise SystemExit("BLOCKED: ROBINHOOD_MCP_RELAY_URL and ROBINHOOD_MCP_RELAY_TOKEN are required")
    while True:
        try:
            poll_once()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ROBINHOOD_MCP_RELAY_RETRY: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(INTERVAL)
