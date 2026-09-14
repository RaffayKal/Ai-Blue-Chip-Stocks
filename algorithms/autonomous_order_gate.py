#!/usr/bin/env python3
import json
import sys
from decimal import Decimal, InvalidOperation
from decimal import ROUND_DOWN
from pathlib import Path

from capital_engine import evaluate, load_json

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
USER_SETTINGS = ROOT / "rules" / "user_settings.json"
BROKERAGE_INTAKE = ROOT / "rules" / "brokerage_intake.json"
EXECUTION_LOG = ROOT / "data" / "autonomous_execution_log.json"
ALGORITHM_SOURCES = ROOT / "rules" / "algorithm_sources.json"
USER_ALGORITHM_ID = "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING"
EXECUTABLE_ASSET_CLASSES = {"CRYPTO", "US_EQUITY", "ETF"}
EQUITY_ASSET_CLASSES = {"US_EQUITY", "ETF"}


def decimal_value(value, field_name, failed):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        failed.append(f"invalid {field_name}")
        return None
    if parsed <= 0:
        failed.append(f"{field_name} must be positive")
        return None
    return parsed


def money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_DOWN)



def logged_net_symbol_notional(executions, symbol):
    total = Decimal("0")
    if not isinstance(executions, list):
        return total
    for execution in executions:
        if not isinstance(execution, dict):
            continue
        if execution.get("symbol") != symbol:
            continue
        value = execution.get("net_rounded_executed_notional") or execution.get("rounded_executed_notional") or "0"
        try:
            notional = Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
        if execution.get("side") == "buy":
            total += notional
        elif execution.get("side") == "sell":
            total -= notional
    return total

def verify_algorithm_sources(failed):
    manifest = load_json(ALGORITHM_SOURCES)
    if Path(manifest.get("root", "")) != ROOT:
        failed.append("algorithm source root mismatch")
    for relative_path in manifest.get("required_algorithm_files", []):
        path = ROOT / relative_path
        if not path.is_file():
            failed.append(f"missing algorithm source {relative_path}")
        elif path.stat().st_size == 0:
            failed.append(f"empty algorithm source {relative_path}")


def main() -> None:
    if Path.cwd() != ROOT:
        print("AUTONOMOUS_DECISION: NO ACTION")
        print("FAILED_CHECKS: wrong working directory")
        raise SystemExit(0)
    if len(sys.argv) != 3:
        print("AUTONOMOUS_DECISION: NO ACTION")
        print("FAILED_CHECKS: usage: python3 algorithms/autonomous_order_gate.py <market_input.json> <order_ticket.json>")
        raise SystemExit(0)

    market_input = load_json(Path(sys.argv[1]))
    order_ticket = load_json(Path(sys.argv[2]))
    user_settings = load_json(USER_SETTINGS)
    brokerage_intake = load_json(BROKERAGE_INTAKE)
    execution_log = load_json(EXECUTION_LOG)

    failed = []
    verify_algorithm_sources(failed)
    decision = evaluate(market_input)

    required_result = order_ticket.get("requires_algorithm_result", "VALIDATED SETUP")
    if decision["RESULT"] != required_result:
        failed.append(f"algorithm result is {decision['RESULT']}, not {required_result}")
    if order_ticket.get("autonomous_execution") is not True:
        failed.append("autonomous_execution is not true")
    if order_ticket.get("user_algorithm_id") != USER_ALGORITHM_ID:
        failed.append(f"user algorithm is not {USER_ALGORITHM_ID}")
    if user_settings.get("broker", {}).get("explicit_execution_authorization") is not True:
        failed.append("user_settings execution authorization is not true")
    if brokerage_intake.get("explicit_execution_authorization") is not True:
        failed.append("brokerage_intake execution authorization is not true")
    if brokerage_intake.get("verified_agentic_account") is None:
        failed.append("verified agentic account missing")
    if order_ticket.get("symbol") != market_input.get("symbol"):
        failed.append("ticket symbol does not match market input")
    if order_ticket.get("asset_class") != market_input.get("asset_class"):
        failed.append("ticket asset class does not match market input")
    asset_class = order_ticket.get("asset_class")
    if asset_class not in EXECUTABLE_ASSET_CLASSES:
        failed.append("asset class is not enabled for autonomous execution gate")
    if order_ticket.get("side") not in {"buy", "sell"}:
        failed.append("side must be buy or sell")
    if asset_class == "CRYPTO":
        if order_ticket.get("type") not in {"market", "limit", "stop_loss", "stop_limit"}:
            failed.append("unsupported crypto order type")
    elif asset_class in EQUITY_ASSET_CLASSES:
        if order_ticket.get("type") not in {"market", "limit", "stop_market", "stop_limit"}:
            failed.append("unsupported equity order type")
    if order_ticket.get("requires_preview") is not True:
        failed.append("requires_preview must be true")
    if order_ticket.get("max_executions") != 7:
        failed.append("max_executions must be 7")
    ticket_id = order_ticket.get("ticket_id")
    if not ticket_id:
        failed.append("ticket_id missing")
    executions = execution_log.get("executions")
    if not isinstance(executions, list):
        failed.append("execution log must contain executions list")
    elif ticket_id:
        matching_executions = [
            execution
            for execution in executions
            if isinstance(execution, dict) and execution.get("ticket_id") == ticket_id
        ]
        if len(matching_executions) >= int(order_ticket.get("max_executions", 0)):
            failed.append("ticket execution limit reached")
    if market_input.get("margin_requested") is True:
        failed.append("margin requested")
    if brokerage_intake.get("margin_approved") is True:
        failed.append("margin must remain disabled for current autonomous mode")

    has_dollar_amount = "dollar_amount" in order_ticket
    has_dollar_amount_mode = "dollar_amount_mode" in order_ticket
    has_quantity = "quantity" in order_ticket
    has_quantity_mode = "quantity_mode" in order_ticket
    if sum([has_dollar_amount, has_dollar_amount_mode, has_quantity, has_quantity_mode]) != 1:
        failed.append("ticket must contain exactly one of dollar_amount, dollar_amount_mode, quantity, or quantity_mode")

    ticket_amount = None
    broker_minimum = None
    buying_power = None
    capital = None
    allocation = None
    if has_dollar_amount or has_dollar_amount_mode:
        broker_minimum = decimal_value(brokerage_intake.get("minimum_order_value_usd", "1.00"), "minimum_order_value_usd", failed)
        verified_account = brokerage_intake.get("verified_agentic_account") or {}
        if asset_class == "CRYPTO":
            buying_power = decimal_value(verified_account.get("crypto_buying_power_usd"), "crypto_buying_power_usd", failed)
        elif asset_class in EQUITY_ASSET_CLASSES:
            buying_power = decimal_value(verified_account.get("buying_power_usd"), "buying_power_usd", failed)
        capital = decimal_value(user_settings.get("capital", {}).get("available_trading_capital"), "available_trading_capital", failed)
        allocation_key = "crypto_max_allocation_decimal" if asset_class == "CRYPTO" else "us_equity_max_allocation_decimal"
        allocation = decimal_value(user_settings.get("asset_limits", {}).get(allocation_key), allocation_key, failed)
    if has_dollar_amount:
        ticket_amount = decimal_value(order_ticket.get("dollar_amount"), "dollar_amount", failed)
    if has_dollar_amount_mode:
        if order_ticket.get("dollar_amount_mode") != "AUTO_MAX_ALLOWED":
            failed.append("unsupported dollar_amount_mode")
        max_ticket_amount = decimal_value(order_ticket.get("max_dollar_amount"), "max_dollar_amount", failed)
        min_ticket_amount = decimal_value(order_ticket.get("min_dollar_amount", "1.00"), "min_dollar_amount", failed)
        if buying_power is not None and capital is not None and allocation is not None and max_ticket_amount is not None:
            ticket_amount = money(min(buying_power, capital * allocation, max_ticket_amount))
        if ticket_amount is not None and min_ticket_amount is not None and ticket_amount < min_ticket_amount:
            failed.append("calculated ticket amount below minimum ticket amount")
        if ticket_amount is not None:
            order_ticket["dollar_amount"] = f"{ticket_amount:.2f}"
            has_dollar_amount = True
    if has_quantity_mode:
        if asset_class != "CRYPTO":
            failed.append("quantity_mode is supported only for crypto sellable-position tickets")
        if order_ticket.get("side") != "sell":
            failed.append("quantity_mode is allowed only for sell tickets")
        if order_ticket.get("quantity_mode") != "AUTO_SELLABLE_POSITION":
            failed.append("unsupported quantity_mode")
        min_quantity = decimal_value(order_ticket.get("min_quantity", "0.00000001"), "min_quantity", failed)
        max_quantity = order_ticket.get("max_quantity")
        if max_quantity is not None:
            parsed_max_quantity = decimal_value(max_quantity, "max_quantity", failed)
            if min_quantity is not None and parsed_max_quantity is not None and parsed_max_quantity < min_quantity:
                failed.append("max_quantity below min_quantity")

    if ticket_amount is not None:
        if ticket_amount is not None and broker_minimum is not None and ticket_amount < broker_minimum:
            failed.append("ticket amount below broker minimum")
        if ticket_amount is not None and buying_power is not None and ticket_amount > buying_power:
            failed.append("ticket amount above verified buying power")
        if ticket_amount is not None and capital is not None and allocation is not None:
            max_allocation_amount = capital * allocation
            if ticket_amount > max_allocation_amount:
                failed.append("ticket amount above configured allocation cap")
            if order_ticket.get("side") == "buy":
                current_symbol_exposure = logged_net_symbol_notional(executions, order_ticket.get("symbol"))
                projected_symbol_exposure = current_symbol_exposure + ticket_amount
                if current_symbol_exposure >= max_allocation_amount:
                    failed.append("current symbol exposure already at or above configured allocation cap")
                elif projected_symbol_exposure > max_allocation_amount:
                    failed.append("projected symbol exposure above configured allocation cap")
            all_in_key = "single_crypto_all_in_blocked" if asset_class == "CRYPTO" else "single_stock_all_in_blocked"
            if user_settings.get("risk_limits", {}).get(all_in_key) is True and order_ticket.get("side") == "buy":
                current_symbol_exposure = logged_net_symbol_notional(executions, order_ticket.get("symbol"))
                if current_symbol_exposure + ticket_amount >= capital:
                    failed.append("single asset all-in exposure blocked")

    if failed:
        print("AUTONOMOUS_DECISION: NO ACTION")
        print("EXECUTION_ALLOWED: false")
        print(f"ALGORITHM_RESULT: {decision['RESULT']}")
        print(f"FAILED_CHECKS: {', '.join(failed)}")
        raise SystemExit(0)

    print("AUTONOMOUS_DECISION: APPROVED_FOR_PREVIEW_AND_PLACEMENT")
    print("EXECUTION_ALLOWED: true")
    print(f"ALGORITHM_RESULT: {decision['RESULT']}")
    print(f"SYMBOL: {order_ticket['symbol']}")
    print(f"SIDE: {order_ticket['side']}")
    print(f"TYPE: {order_ticket['type']}")
    print(f"TICKET_ID: {ticket_id}")
    print(f"USER_ALGORITHM_ID: {USER_ALGORITHM_ID}")
    if ticket_amount is not None:
        print(f"DOLLAR_AMOUNT: {ticket_amount:.2f}")
    if has_quantity_mode:
        print(f"QUANTITY_MODE: {order_ticket['quantity_mode']}")
        print(f"MIN_QUANTITY: {order_ticket.get('min_quantity', '0.00000001')}")
        if order_ticket.get("max_quantity") is not None:
            print(f"MAX_QUANTITY: {order_ticket['max_quantity']}")
    if asset_class == "CRYPTO":
        print("NEXT_ALLOWED_STEP: preview Blue Chip Stocks crypto order, then place only that previewed order if the runtime permits it")
    else:
        print("NEXT_ALLOWED_STEP: review Blue Chip Stocks equity order, then place only that reviewed order if the runtime permits it")


if __name__ == "__main__":
    main()
