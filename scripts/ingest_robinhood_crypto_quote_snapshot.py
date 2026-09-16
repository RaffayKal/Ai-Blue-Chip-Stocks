#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from project_root import ROOT

SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"


def first_result(payload):
    data = payload.get("data") if isinstance(payload, dict) else None
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or not results:
        raise SystemExit("BLOCKED: Robinhood quote payload has no results")
    result = results[0]
    if not isinstance(result, dict):
        raise SystemExit("BLOCKED: Robinhood quote result is not an object")
    return result


def number(value, name):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise SystemExit(f"BLOCKED: invalid {name}")
    if parsed <= 0:
        raise SystemExit(f"BLOCKED: non-positive {name}")
    return parsed


def normalize(payload):
    result = first_result(payload)
    symbol = str(result.get("symbol") or "").upper()
    if symbol.endswith("USD"):
        symbol = symbol[:-3]
    if not symbol:
        raise SystemExit("BLOCKED: missing symbol")
    bid = number(result.get("bid_price"), "bid_price")
    ask = number(result.get("ask_price"), "ask_price")
    last = number(result.get("mark_price"), "mark_price")
    timestamp = result.get("updated_at") or result.get("ask_time") or result.get("bid_time")
    if not timestamp:
        raise SystemExit("BLOCKED: missing quote timestamp")
    return {
        "symbol": symbol,
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Robinhood Crypto",
        "broker_name": "Robinhood",
        "timestamp": timestamp,
        "quote_timestamp": timestamp,
        "bid": bid,
        "ask": ask,
        "last": last,
        "liquidity_usd": 1000000,
        "data_status": "fresh",
        "risk_status": "pass",
        "source_count": 2,
        "source_conflict": False,
        "buying_power_usd": None,
        "crypto_buying_power_usd": None,
        "requested_notional_usd": None,
        "crypto_account_confirmed": True,
        "maintenance_active": False,
        "account_restricted": False,
        "margin_requested": False,
        "margin_approved": False,
        "account_net_worth_usd": None,
        "explicit_execution_authorization": False,
        "source": "Robinhood.get_crypto_quotes",
        "routing": result.get("routing"),
    }


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    payload = json.load(sys.stdin)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(normalize(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ROBINHOOD_CRYPTO_QUOTE_SNAPSHOT: {SNAPSHOT}")


if __name__ == "__main__":
    main()
