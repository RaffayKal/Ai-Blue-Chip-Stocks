#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from project_root import ROOT

SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"


def number(value, name):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise SystemExit(f"BLOCKED: invalid {name}")
    if parsed <= 0:
        raise SystemExit(f"BLOCKED: non-positive {name}")
    return parsed


def normalize_result(result):
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
    routing = result.get("routing")
    if not isinstance(routing, str) or not routing.strip():
        raise SystemExit("BLOCKED: missing Robinhood crypto routing")
    # Keep this adapter strictly factual. Liquidity, source quorum, risk,
    # account restrictions, and buying power come from their own live sources;
    # a quote response cannot establish them.
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
        "source": "Robinhood.get_crypto_quotes",
        "routing": routing.strip(),
        # The relay's authority label identifies the provenance of this quote;
        # it does not grant order-submission authority to the scanner.
        "execution_authority": "robinhood",
        "explicit_execution_authorization": False,
    }


def normalize_many(payload):
    data = payload.get("data") if isinstance(payload, dict) else None
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or not results:
        raise SystemExit("BLOCKED: Robinhood quote payload has no results")
    normalized = []
    failures = []
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            failures.append(f"result {index}: not an object")
            continue
        try:
            normalized.append(normalize_result(result))
        except SystemExit as exc:
            failures.append(f"result {index}: {exc}")
    if not normalized:
        raise SystemExit("BLOCKED: no valid routed Robinhood quotes: " + "; ".join(failures))
    return normalized


def normalize(payload):
    return normalize_many(payload)[0]


def write_snapshot(path, snapshot):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    payload = json.load(sys.stdin)
    snapshots = normalize_many(payload)
    for snapshot in snapshots:
        symbol_path = SNAPSHOT.with_name(f"robinhood_crypto_quote_snapshot_{snapshot['symbol']}.json")
        write_snapshot(symbol_path, snapshot)
    write_snapshot(SNAPSHOT, snapshots[0])
    print(f"ROBINHOOD_CRYPTO_QUOTE_SNAPSHOTS: {len(snapshots)} routed quote(s) written")


if __name__ == "__main__":
    main()
