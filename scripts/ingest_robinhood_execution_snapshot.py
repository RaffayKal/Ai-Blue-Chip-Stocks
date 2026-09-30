#!/usr/bin/env python3
"""Normalize private Robinhood capital and position reads for host-only gates.

This snapshot is intentionally separate from public quote snapshots.  It must
never be copied to RunPod by the quote-sync path.
"""

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from project_root import ROOT

SNAPSHOT = ROOT / "data" / "robinhood_crypto_execution_snapshot.json"


def decimal_value(value, name):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise SystemExit(f"BLOCKED: invalid {name}")
    if parsed < 0:
        raise SystemExit(f"BLOCKED: negative {name}")
    return parsed


def normalize(payload):
    if not isinstance(payload, dict):
        raise SystemExit("BLOCKED: input must be an object")
    retrieved_at = payload.get("retrieved_at")
    try:
        stamp = datetime.fromisoformat(str(retrieved_at).replace("Z", "+00:00"))
    except ValueError:
        raise SystemExit("BLOCKED: invalid retrieved_at")
    if stamp.tzinfo is None:
        raise SystemExit("BLOCKED: retrieved_at must include timezone")
    if payload.get("account_match_confirmed") is not True:
        raise SystemExit("BLOCKED: broker account match not confirmed")
    if payload.get("crypto_account_confirmed") is not True:
        raise SystemExit("BLOCKED: Robinhood Crypto account not confirmed")

    portfolio = payload.get("portfolio", {}).get("data")
    positions = payload.get("positions", {}).get("data", {}).get("results")
    if not isinstance(portfolio, dict) or not isinstance(positions, list):
        raise SystemExit("BLOCKED: Robinhood portfolio or position data missing")
    buying_power = decimal_value(
        (portfolio.get("crypto_buying_power") or {}).get("buying_power"),
        "crypto buying power",
    )

    normalized_positions = []
    for row in positions:
        if not isinstance(row, dict):
            continue
        symbol = str((row.get("currency") or {}).get("code") or "").strip().upper()
        if not symbol:
            continue
        transferable = decimal_value(row.get("quantity_transferable"), f"{symbol} quantity_transferable")
        held_for_sell = decimal_value(row.get("quantity_held_for_sell", "0"), f"{symbol} quantity_held_for_sell")
        direct_quantity = Decimal("0")
        direct_cost_basis = Decimal("0")
        for basis in row.get("cost_bases") or []:
            if not isinstance(basis, dict):
                continue
            direct_quantity += decimal_value(basis.get("direct_quantity", "0"), f"{symbol} direct_quantity")
            direct_cost_basis += decimal_value(basis.get("direct_cost_basis", "0"), f"{symbol} direct_cost_basis")
        normalized_position = {
            "symbol": symbol,
            "quantity_transferable": float(transferable),
            "quantity_held_for_sell": float(held_for_sell),
            "direct_quantity": float(direct_quantity),
            "direct_cost_basis_usd": float(direct_cost_basis),
            "cost_basis_complete": direct_quantity >= transferable,
            "position_status": "fresh",
            "position_source": "Robinhood.get_crypto_positions",
            "position_timestamp": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "position_account_matches_verified_account": True,
            # This is deliberately opt-in.  A positive unrealized/net amount
            # is only a review trigger; APEX must separately confirm that the
            # wait/grow/harvest rule is satisfied before a sell can proceed.
            "apex_harvest_gate_passed": row.get("apex_harvest_gate_passed") is True,
        }
        if isinstance(row.get("apex_harvest_reason"), str):
            normalized_position["apex_harvest_reason"] = row["apex_harvest_reason"]
        normalized_positions.append(normalized_position)

    return {
        "retrieved_at": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "Robinhood.get_portfolio+get_crypto_positions",
        "account_match_confirmed": True,
        "crypto_account_confirmed": True,
        "crypto_buying_power_usd": float(buying_power),
        "positions": normalized_positions,
    }


def write_snapshot(path, snapshot):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    snapshot = normalize(json.load(sys.stdin))
    write_snapshot(SNAPSHOT, snapshot)
    print(f"ROBINHOOD_EXECUTION_SNAPSHOT: {len(snapshot['positions'])} position(s) written host-only")


if __name__ == "__main__":
    main()
