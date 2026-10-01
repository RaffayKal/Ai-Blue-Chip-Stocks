#!/usr/bin/env python3
"""Persist factual Robinhood equity quote responses without inventing routing."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

SNAPSHOT = ROOT / "data" / "robinhood_equity_quote_snapshot.json"


def positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def parsed_time(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def normalize(result):
    quote = result.get("quote") if isinstance(result, dict) else None
    if not isinstance(quote, dict):
        raise ValueError("missing equity quote")
    symbol = str(quote.get("symbol") or result.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("missing symbol")
    regular_time = parsed_time(quote.get("venue_last_trade_time"))
    nonregular_time = parsed_time(quote.get("venue_last_non_reg_trade_time"))
    last = positive(quote.get("last_trade_price"))
    if nonregular_time and (not regular_time or nonregular_time > regular_time):
        last = positive(quote.get("last_non_reg_trade_price")) or last
        last_time = nonregular_time
    else:
        last_time = regular_time
    bid_time = parsed_time(quote.get("venue_bid_time"))
    ask_time = parsed_time(quote.get("venue_ask_time"))
    quote_timestamp = max((stamp for stamp in (bid_time, ask_time, last_time) if stamp), default=None)
    if not quote_timestamp:
        raise ValueError("missing quote timestamp")
    return {
        "symbol": symbol,
        "asset_class": "EQUITY",
        "broker_name": "Robinhood",
        "venue": "Robinhood Financial",
        "routing": None,
        "routing_source": "not_returned_by_get_equity_quotes",
        "bid": positive(quote.get("bid_price")),
        "ask": positive(quote.get("ask_price")),
        "last": last,
        "quote_timestamp": quote_timestamp,
        "quote_received_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "Robinhood.get_equity_quotes",
        "instrument_state": quote.get("state"),
        "has_traded": quote.get("has_traded"),
        "venue_bid_time": bid_time,
        "venue_ask_time": ask_time,
        "venue_last_trade_time": regular_time,
        "venue_last_non_reg_trade_time": nonregular_time,
        "previous_close": quote.get("previous_close"),
        "adjusted_previous_close": quote.get("adjusted_previous_close"),
        "previous_close_date": quote.get("previous_close_date"),
        "official_close": result.get("close"),
    }


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    payload = json.load(sys.stdin)
    results = payload.get("data", {}).get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        raise SystemExit("BLOCKED: Robinhood equity quote payload has no results")
    normalized = []
    failures = []
    for index, result in enumerate(results):
        try:
            normalized.append(normalize(result))
        except ValueError as exc:
            failures.append(f"result {index}: {exc}")
    if not normalized:
        raise SystemExit("BLOCKED: no valid Robinhood equity quotes: " + "; ".join(failures))
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    for snapshot in normalized:
        path = SNAPSHOT.with_name(f"robinhood_equity_quote_snapshot_{snapshot['symbol']}.json")
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SNAPSHOT.write_text(json.dumps({"asset_class": "EQUITY", "broker_name": "Robinhood", "quotes": normalized}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ROBINHOOD_EQUITY_QUOTE_SNAPSHOTS: {len(normalized)} quote(s) written")


if __name__ == "__main__":
    main()
