#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from project_root import ROOT

sys.path.insert(0, str(ROOT / "algorithms"))
from capital_engine import evaluate  # noqa: E402

ALPACA_STATUS = ROOT / "data" / "alpaca_market_access_status.json"
OUTPUT = ROOT / "data" / "apex_expansion_viability.json"
USER_SETTINGS = ROOT / "rules" / "user_settings.json"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"BLOCKED: missing {path}")
    if not isinstance(data, dict):
        raise SystemExit(f"BLOCKED: invalid object {path}")
    return data


def number(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def candidate_input(symbol, quote, buying_power, allocation):
    bid = number(quote.get("bid"))
    ask = number(quote.get("ask"))
    last = (bid + ask) / 2 if bid is not None and ask is not None else None
    requested_notional = buying_power * allocation if buying_power is not None and allocation is not None else None
    return {
        "symbol": symbol,
        "asset_class": "ETF",
        "market_focus": "APEX_EXPANSION",
        "session": "REGULAR",
        "venue": "Alpaca/IEX",
        "broker_name": "Alpaca",
        "timestamp": quote.get("timestamp"),
        "quote_timestamp": quote.get("timestamp"),
        "bid": bid,
        "ask": ask,
        "last": last,
        "liquidity_usd": None,
        "data_status": "fresh" if quote.get("has_bid_ask") else "unusable",
        "risk_status": "fail",
        "source_count": 1,
        "source_conflict": False,
        "buying_power_usd": buying_power,
        "requested_notional_usd": requested_notional,
        "margin_requested": False,
        "margin_approved": False,
        "account_net_worth_usd": None,
        "explicit_execution_authorization": False,
    }


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    status = load_json(ALPACA_STATUS)
    settings = load_json(USER_SETTINGS)
    account = status.get("account") if isinstance(status.get("account"), dict) else {}
    buying_power = number(account.get("buying_power"))
    allocation = number(((settings.get("asset_limits") or {}).get("etf_max_allocation_decimal")))
    quotes = ((status.get("apex_expansion_quotes") or {}).get("quotes") or {})
    if not isinstance(quotes, dict) or not quotes:
        raise SystemExit("BLOCKED: no Apex expansion quotes in Alpaca status")

    candidates = []
    for symbol, quote in quotes.items():
        market_input = candidate_input(symbol, quote if isinstance(quote, dict) else {}, buying_power, allocation)
        decision = evaluate(market_input)
        candidates.append({
            "symbol": symbol,
            "market_input": market_input,
            "decision": decision,
            "apex_viability": decision["RESULT"] in {"WATCHLIST ONLY", "NEEDS USER CAPITAL SETTINGS", "VALIDATED SETUP"},
            "execution_authority": False,
        })

    viable = [item for item in candidates if item["apex_viability"]]
    result = {
        "timestamp_utc": status.get("timestamp_utc"),
        "source": str(ALPACA_STATUS),
        "market_focus": "APEX_EXPANSION",
        "apex_viability_true_count": len(viable),
        "apex_viability_any_true": bool(viable),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "trade_execution_allowed": False,
        "order_preview_called": False,
        "order_placement_called": False,
    }
    write_json(OUTPUT, result)
    print(f"APEX_EXPANSION_VIABILITY: {OUTPUT}")
    print(f"CANDIDATE_COUNT: {len(candidates)}")
    print(f"APEX_VIABILITY_TRUE_COUNT: {len(viable)}")
    print(f"APEX_VIABILITY_ANY_TRUE: {bool(viable)}")
    print("TRADE_EXECUTION_ALLOWED: false")


if __name__ == "__main__":
    main()
