#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

from project_root import ROOT

BLUE_CHIP_WATCHLIST = ROOT / "data" / "blue_chip_watchlist.txt"

VALID_ASSET_CLASSES = {"CRYPTO", "US_EQUITY", "ETF", "OPTION", "FUND"}
VALID_SESSIONS = {
    "CRYPTO_24_7",
    "PRE_MARKET",
    "REGULAR",
    "AFTER_HOURS",
    "OVERNIGHT",
    "HOLIDAY",
    "HALTED",
    "CLOSED",
    "UNKNOWN",
}
BLOCKED_SESSIONS = {"HOLIDAY", "HALTED", "CLOSED", "UNKNOWN"}
EXTENDED_EQUITY_SESSIONS = {"PRE_MARKET", "AFTER_HOURS", "OVERNIGHT"}
BROKER_MINIMUM_ORDER_USD = {
    "robinhood": 1.0,
}
BROKER_MARGIN_MINIMUM_USD = {
    "robinhood": 2000.0,
}


def load_watchlist(path: Path) -> set[str]:
    try:
        return {
            line.strip().upper()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
    except FileNotFoundError:
        return set()


def fail(message: str, code: int = 1) -> None:
    print("RESULT: NO ACTION")
    print(f"FAILED_CHECKS: {message}")
    raise SystemExit(code)


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        fail(f"input file missing: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid json: {exc}")

    if not isinstance(data, dict):
        fail("input json must be an object")
    return data


def number(value, name: str, failed: list[str]) -> float | None:
    if value is None:
        failed.append(f"missing {name}")
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        failed.append(f"invalid {name}")
        return None
    if not math.isfinite(parsed):
        failed.append(f"invalid {name}")
        return None
    return parsed


def evaluate(data: dict) -> dict:
    failed: list[str] = []
    watch_only: list[str] = []

    symbol = str(data.get("symbol") or "").strip().upper()
    asset_class = str(data.get("asset_class") or "UNKNOWN").strip().upper()
    session = str(data.get("session") or "UNKNOWN").strip().upper()
    data_status = str(data.get("data_status") or "missing").strip().lower()
    risk_status = str(data.get("risk_status") or "needs settings").strip().lower()
    watchlist = load_watchlist(BLUE_CHIP_WATCHLIST)

    if not symbol:
        failed.append("missing symbol")
    if asset_class not in VALID_ASSET_CLASSES:
        failed.append("unknown asset class")
    if session not in VALID_SESSIONS:
        failed.append("invalid session")
    if session in BLOCKED_SESSIONS:
        failed.append("unsupported or inactive session")
    if asset_class == "CRYPTO" and session != "CRYPTO_24_7":
        failed.append("crypto session not confirmed as CRYPTO_24_7")
    if asset_class in {"US_EQUITY", "ETF", "OPTION"} and session == "CRYPTO_24_7":
        failed.append("crypto session applied to non-crypto asset")
    if asset_class in {"US_EQUITY", "ETF", "OPTION"} and session in EXTENDED_EQUITY_SESSIONS:
        if data.get("broker_extended_session_supported") is not True:
            failed.append("extended equity session not confirmed by broker")
    if asset_class == "US_EQUITY" and watchlist and symbol not in watchlist:
        failed.append("symbol not in blue-chip watchlist")

    bid = number(data.get("bid"), "bid", failed)
    ask = number(data.get("ask"), "ask", failed)
    last = number(data.get("last"), "last", failed)
    liquidity = number(data.get("liquidity_usd"), "liquidity_usd", failed)

    if bid is not None and ask is not None:
        if bid <= 0:
            failed.append("bid must be positive")
        if ask <= 0:
            failed.append("ask must be positive")
        if ask < bid:
            failed.append("ask below bid")
    if last is not None and last <= 0:
        failed.append("last must be positive")
    if liquidity is not None and liquidity <= 0:
        failed.append("liquidity_usd must be positive")

    available_capital = number(data.get("available_trading_capital", 5.0), "available_trading_capital", failed)
    requested_notional = number(data.get("requested_notional_usd", data.get("available_trading_capital", 5.0)), "requested_notional_usd", failed)
    broker_name = str(data.get("broker_name") or "Robinhood").strip().lower()
    margin_requested = data.get("margin_requested") is True
    margin_approved = data.get("margin_approved") is True
    account_net_worth = number(data.get("account_net_worth_usd", available_capital), "account_net_worth_usd", failed)
    explicit_execution_authorization = data.get("explicit_execution_authorization") is True

    broker_minimum = BROKER_MINIMUM_ORDER_USD.get(broker_name)
    if broker_minimum is not None and requested_notional is not None and requested_notional < broker_minimum:
        failed.append(f"{broker_name.title()} minimum order is ${broker_minimum:.2f}")

    if broker_name == "robinhood" and asset_class in {"US_EQUITY", "ETF"} and session != "REGULAR":
        watch_only.append(f"{broker_name.title()} fractional stock/ETF execution limited to regular market hours")

    if broker_name == "robinhood" and asset_class == "CRYPTO":
        if data.get("crypto_account_confirmed") is not True:
            failed.append("Robinhood Crypto account not confirmed")
        if data.get("maintenance_active") is True:
            failed.append("Robinhood Crypto maintenance active")
        if data.get("account_restricted") is True:
            failed.append("Robinhood account restricted")

    if margin_requested:
        if not margin_approved:
            failed.append("margin requested but not approved")
        broker_margin_minimum = BROKER_MARGIN_MINIMUM_USD.get(broker_name, 2000.0)
        if account_net_worth is not None and account_net_worth < broker_margin_minimum:
            failed.append(f"{broker_name.title()} margin minimum not met")
    if requested_notional is not None and available_capital is not None:
        if requested_notional > available_capital and not margin_requested:
            failed.append("requested notional exceeds available cash without margin")

    if asset_class == "US_EQUITY" and ask is not None and available_capital is not None:
        if ask > available_capital:
            if data.get("fractional_shares_supported") is True and data.get("fractional_asset_eligible") is True:
                if requested_notional is None or requested_notional > available_capital:
                    watch_only.append("full share above capital; fractional notional exceeds available capital")
            else:
                watch_only.append("full share above $5 capital and fractional support not confirmed")

    if data_status != "fresh":
        failed.append("data not fresh")
    if data.get("source_conflict") is True:
        failed.append("source conflict")
    if int(data.get("source_count") or 0) < 2:
        failed.append("less than two source confirmations")
    if not explicit_execution_authorization:
        watch_only.append("explicit execution authorization required before real order")

    result = "NO ACTION"
    if not failed:
        result = "WATCHLIST ONLY" if watch_only else "NEEDS USER CAPITAL SETTINGS" if risk_status == "needs settings" else "VALIDATED SETUP"
        if risk_status not in {"pass", "needs settings"}:
            result = "NO ACTION"
            failed.append("risk not passed")

    return {
        "RESULT": result,
        "SYMBOL": symbol or "missing",
        "ASSET_CLASS": asset_class,
        "SESSION": session,
        "DATA_STATUS": data_status,
        "RISK_STATUS": risk_status,
        "FAILED_CHECKS": ", ".join(failed) if failed else "none",
        "NEXT_ALLOWED_STEP": next_step(result, watch_only),
    }


def next_step(result: str, watch_only: list[str]) -> str:
    if result == "NEEDS USER CAPITAL SETTINGS":
        return "set user capital settings"
    if result == "WATCHLIST ONLY":
        return "; ".join(watch_only)
    return "none"


def main() -> None:
    if Path.cwd() != ROOT:
        fail("wrong working directory")
    if len(sys.argv) != 2:
        fail("usage: python3 algorithms/capital_engine.py <input.json>")

    result = evaluate(load_json(Path(sys.argv[1])))
    for key in [
        "RESULT",
        "SYMBOL",
        "ASSET_CLASS",
        "SESSION",
        "DATA_STATUS",
        "RISK_STATUS",
        "FAILED_CHECKS",
        "NEXT_ALLOWED_STEP",
    ]:
        print(f"{key}: {result[key]}")


if __name__ == "__main__":
    main()
