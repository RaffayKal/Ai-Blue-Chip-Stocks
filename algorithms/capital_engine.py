#!/usr/bin/env python3
"""Entry-validation gate for a single candidate (see CAPITAL_ALGORITHM.md).

Structural eligibility only -- no concept of hold time or cadence, and it
does not decide when to exit. The wait/grow/harvest exit-patience doctrine
lives in rules/APEX_AUM_COMPOUNDING_ALGORITHM.md and
apex_micro_crypto_ledger.should_harvest(); this module never authorizes
fast cycling or scalping speed on its own.
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

BLUE_CHIP_WATCHLIST = ROOT / "data" / "blue_chip_watchlist.txt"
APEX_EXPANSION_WATCHLIST = ROOT / "data" / "apex_expansion_watchlist.txt"

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
# Robinhood crypto fractional-order minimums differ by routing: $0.01 for
# confirmed market-maker routing, $0.03 for smart exchange routing. Without
# a confirmed routing on the candidate, use the higher (more conservative)
# figure so a sized order is never rejected by the broker as too small.
ROBINHOOD_CRYPTO_MINIMUM_BY_ROUTING_USD = {
    "market maker routing": 0.01,
    "smart exchange routing": 0.03,
}
ROBINHOOD_CRYPTO_MINIMUM_DEFAULT_USD = 0.03
BROKER_MARGIN_MINIMUM_USD = {
    "robinhood": 2000.0,
}
MAX_POSITION_SNAPSHOT_AGE_SECONDS = 420


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


def fresh_position_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    return 0 <= age <= MAX_POSITION_SNAPSHOT_AGE_SECONDS


def evaluate(data: dict) -> dict:
    failed: list[str] = []
    watch_only: list[str] = []

    symbol = str(data.get("symbol") or "").strip().upper()
    asset_class = str(data.get("asset_class") or "UNKNOWN").strip().upper()
    side = str(data.get("side") or "buy").strip().lower()
    session = str(data.get("session") or "UNKNOWN").strip().upper()
    data_status = str(data.get("data_status") or "missing").strip().lower()
    risk_status = str(data.get("risk_status") or "needs settings").strip().lower()
    watchlist = load_watchlist(BLUE_CHIP_WATCHLIST)
    expansion_watchlist = load_watchlist(APEX_EXPANSION_WATCHLIST)
    market_focus = str(data.get("market_focus") or "").strip().upper()

    if not symbol:
        failed.append("missing symbol")
    if side not in {"buy", "sell"}:
        failed.append("side must be buy or sell")
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
    if asset_class == "US_EQUITY" and watchlist and symbol not in watchlist and market_focus != "APEX_EXPANSION":
        failed.append("symbol not in blue-chip watchlist")
    if market_focus == "APEX_EXPANSION":
        if asset_class in {"CRYPTO"}:
            failed.append("crypto cannot use APEX_EXPANSION market focus")
        if expansion_watchlist and symbol not in expansion_watchlist:
            failed.append("symbol not in Apex expansion watchlist")

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

    buying_power = None
    requested_quantity = None
    if side == "sell":
        # A sell is backed by confirmed inventory, not cash buying power.
        # Do not count marked-to-market holdings as buy capital: proceeds only
        # become buy capital after the broker confirms the sale and a fresh
        # account refresh reports the resulting buying power.
        sellable_quantity = number(data.get("sellable_quantity"), "sellable_quantity", failed)
        requested_quantity = number(data.get("requested_quantity"), "requested_quantity", failed)
        if data.get("position_status") != "fresh" or not fresh_position_timestamp(data.get("position_timestamp")):
            failed.append("sellable position data not fresh")
        if not str(data.get("position_source") or "").startswith("Robinhood."):
            failed.append("sellable position source not verified Robinhood")
        if data.get("position_account_matches_verified_account") is not True:
            failed.append("sellable position account does not match verified agentic account")
        if sellable_quantity is not None and requested_quantity is not None:
            if requested_quantity > sellable_quantity:
                failed.append("requested sell quantity exceeds broker-confirmed sellable quantity")
    else:
        if asset_class == "CRYPTO":
            buying_power = number(data.get("crypto_buying_power_usd"), "crypto_buying_power_usd", failed)
        else:
            buying_power = number(data.get("buying_power_usd"), "buying_power_usd", failed)
    requested_notional = None
    if data.get("requested_notional_usd") is not None:
        requested_notional = number(data.get("requested_notional_usd"), "requested_notional_usd", failed)
    elif side == "buy":
        failed.append("missing requested_notional_usd")
    elif side == "sell" and bid is not None and requested_quantity is not None:
        # Conservative liquidation mark: use the live bid, never the last or
        # mid, when a sell ticket's notional was not precomputed.
        requested_notional = requested_quantity * bid
    broker_name = str(data.get("broker_name") or "Robinhood").strip().lower()
    margin_requested = data.get("margin_requested") is True
    margin_approved = data.get("margin_approved") is True
    account_net_worth = number(data.get("account_net_worth_usd"), "account_net_worth_usd", failed) if data.get("account_net_worth_usd") is not None else None
    explicit_execution_authorization = data.get("explicit_execution_authorization") is True

    if broker_name == "robinhood" and asset_class == "CRYPTO":
        routing = str(data.get("routing") or "").strip().lower()
        broker_minimum = ROBINHOOD_CRYPTO_MINIMUM_BY_ROUTING_USD.get(
            routing, ROBINHOOD_CRYPTO_MINIMUM_DEFAULT_USD
        )
    else:
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
    if side == "buy" and requested_notional is not None and buying_power is not None:
        if requested_notional > buying_power and not margin_requested:
            failed.append("requested notional exceeds live buying power without margin")

    if side == "buy" and asset_class == "US_EQUITY" and ask is not None and buying_power is not None:
        if ask > buying_power:
            if data.get("fractional_shares_supported") is True and data.get("fractional_asset_eligible") is True:
                if requested_notional is None or requested_notional > buying_power:
                    watch_only.append("full share above live buying power; fractional notional exceeds live buying power")
            else:
                watch_only.append("full share above live buying power and fractional support not confirmed")

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
