#!/usr/bin/env python3
"""Pull snapshots from a secured Robinhood MCP relay into the local scanner."""

import json
import os
import time
import urllib.request
from pathlib import Path

from project_root import ROOT

URL = os.getenv("ROBINHOOD_MCP_RELAY_URL", "").rstrip("/") + "/v1/robinhood/snapshot"
TOKEN = os.getenv("ROBINHOOD_MCP_RELAY_TOKEN", "")
INTERVAL = max(4.0, min(420.0, float(os.getenv("ROBINHOOD_MCP_RELAY_INTERVAL_SECONDS", "7"))))
SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"


def poll_once():
    request = urllib.request.Request(URL, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(request, timeout=10) as response:
        response_payload = json.load(response)
    payload = response_payload.get("snapshot", response_payload)
    if payload.get("source") != "robinhood" or payload.get("asset_class") != "crypto":
        raise ValueError("relay payload is not a Robinhood crypto snapshot")
    for field in ("bid", "ask", "last", "quote_timestamp", "symbol"):
        if not payload.get(field):
            raise ValueError(f"relay payload missing {field}")
    payload = {
        **payload,
        "symbol": str(payload["symbol"]).upper().removesuffix("USD"),
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Robinhood Crypto",
        "broker_name": "Robinhood",
        "timestamp": payload["quote_timestamp"],
        "data_status": "fresh",
        "source": "Robinhood.get_crypto_quotes",
    }
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(SNAPSHOT)


if __name__ == "__main__":
    if not TOKEN or not os.getenv("ROBINHOOD_MCP_RELAY_URL"):
        raise SystemExit("BLOCKED: ROBINHOOD_MCP_RELAY_URL and ROBINHOOD_MCP_RELAY_TOKEN are required")
    while True:
        try:
            poll_once()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ROBINHOOD_MCP_RELAY_RETRY: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(INTERVAL)
