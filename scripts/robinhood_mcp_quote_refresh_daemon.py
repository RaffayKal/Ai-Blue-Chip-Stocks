#!/usr/bin/env python3
"""Continuously refresh Robinhood market data on the authenticated host.

This process refreshes public routed quotes for the top-crypto and blue-chip
universe and host-side broker state.
It never places orders itself.  The execution-capable watchdog/worker performs
the account, APEX, preview, idempotency, broker-confirmation, placement and
fill-reconciliation steps.  Authentication material remains host-only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ingest_robinhood_crypto_quote_snapshot import normalize_many  # noqa: E402
from ingest_robinhood_execution_snapshot import normalize as normalize_execution  # noqa: E402

VOLATILE_CANDIDATES = ROOT / "data" / "volatile_crypto_candidates.json"
SYMBOL_POOL = ROOT / "data" / "robinhood_symbol_pool.json"
STATUS = ROOT / "data" / "robinhood_quote_refresh_status.json"
CAPITAL_SNAPSHOT = ROOT / "data" / "robinhood_crypto_capital_snapshot.json"
DEFAULT_INTERVAL_SECONDS = 240.0
DEFAULT_TIMEOUT_SECONDS = 150.0
MAX_SYMBOLS = 95
MAX_CRYPTO_SYMBOLS = 58


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def clean_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper().replace("-", "")
    if symbol.endswith("USD"):
        symbol = symbol[:-3]
    return symbol if symbol.isalnum() else ""


def tracked_symbols(limit: int = MAX_CRYPTO_SYMBOLS) -> list[str]:
    payload = json.loads(VOLATILE_CANDIDATES.read_text(encoding="utf-8"))
    ordered: list[str] = []

    def add(value: Any) -> None:
        symbol = clean_symbol(value)
        if symbol and symbol not in ordered and len(ordered) < limit:
            ordered.append(symbol)

    add(payload.get("active_symbol"))
    add(payload.get("fallback_symbol"))
    for row in payload.get("ranked_symbols", []):
        add(row.get("symbol") if isinstance(row, dict) else row)
    for value in payload.get("fresh_symbols", []):
        add(value)
    for value in payload.get("tracked_symbols", []):
        add(value)
    if SYMBOL_POOL.exists():
        catalog = json.loads(SYMBOL_POOL.read_text(encoding="utf-8"))
        for value in catalog.get("crypto_symbols", []):
            add(value)
    if not ordered:
        raise ValueError("volatile crypto candidate pool is empty")
    return ordered


def blue_chip_symbols(limit: int = MAX_SYMBOLS) -> list[str]:
    if not SYMBOL_POOL.exists():
        return []
    catalog = json.loads(SYMBOL_POOL.read_text(encoding="utf-8"))
    return [clean_symbol(value) for value in catalog.get("equity_symbols", []) if clean_symbol(value)][:limit]


def find_codex() -> str | None:
    configured = os.environ.get("CODEX_CLI_PATH")
    candidates = [configured] if configured else []
    candidates.extend(("/opt/homebrew/bin/codex", "/usr/local/bin/codex", "/usr/bin/codex"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("codex")


def quote_prompt(symbols: list[str]) -> str:
    requested = ", ".join(f"{symbol}-USD" for symbol in symbols)
    return f"""Use only the authenticated robinhood-trading MCP. This is a read-only public crypto quote refresh.
Do not access portfolio, buying power, positions, orders, previews, or any private account data, and do not place or mutate any order.
Call the public crypto quote tool exactly once in one bounded batch for these symbols: {requested}.
Preserve the broker-returned bid_price, ask_price, mark_price, updated_at, and routing for each actual result.
Return the tool result without changing symbols, values, timestamps, or routing. Do not fabricate missing results.
Do not include markdown or commentary. If the tool cannot provide quotes, respond exactly QUOTE_REFRESH_FAILED: followed by a short reason."""


def equity_quote_prompt(symbols: list[str]) -> str:
    requested = ", ".join(symbols)
    return f"""Use only the authenticated robinhood-trading MCP. This is a read-only public equity quote refresh.
Do not access portfolio, buying power, positions, orders, previews, or any private account data, and do not place or mutate any order.
Call the public equity quote tool exactly once in one bounded batch for these symbols: {requested}.
Preserve the broker-returned bid_price, ask_price, last_trade_price, last_non_reg_trade_price, venue timestamps, state, and has_traded for each actual result.
Return the tool result without changing symbols, values, timestamps, or absent fields. Do not fabricate missing routing; the equity quote tool does not return a routing field.
Do not include markdown or commentary. If the tool cannot provide quotes, respond exactly QUOTE_REFRESH_FAILED: followed by a short reason."""


def account_prompt() -> str:
    return """Use only the authenticated robinhood-trading MCP for a read-only host-side account refresh.
Use get_accounts only to select the verified account where accessible_to_this_agent is true. Then call get_portfolio and get_crypto_positions for that same verified agentic account.
Do not access orders, previews, quotes, or any other market-data tool. Do not place or mutate any order. Do not return account identifiers in your final response.
The host adapter will extract the structured results from the two MCP calls and write them locally; do not summarize or alter their values.
If either required call fails, respond exactly ACCOUNT_REFRESH_FAILED: followed by a short reason."""


def extract_quote_payload(output: str) -> dict[str, Any] | None:
    """Extract structured MCP output, then support the explicit JSON fallback."""
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict):
            continue
        result = item.get("result")
        if not isinstance(result, dict):
            continue
        structured = result.get("structured_content")
        if isinstance(structured, dict) and isinstance(structured.get("data"), dict):
            if isinstance(structured["data"].get("results"), list):
                return structured
        for content in result.get("content", []):
            if not isinstance(content, dict) or content.get("type") != "text":
                continue
            try:
                payload = json.loads(content.get("text", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("results"), list):
                return payload

    marker = "QUOTE_SNAPSHOT_JSON:"
    if marker in output:
        candidate = output.split(marker, 1)[1].strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("results"), list):
            return payload
    return None


def extract_tool_payloads(output: str) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or not isinstance(item.get("tool"), str):
            continue
        result = item.get("result")
        if not isinstance(result, dict):
            continue
        structured = result.get("structured_content")
        if isinstance(structured, dict):
            payloads[item["tool"]] = structured
            continue
        for content in result.get("content", []):
            if not isinstance(content, dict) or content.get("type") != "text":
                continue
            try:
                payload = json.loads(content.get("text", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                payloads[item["tool"]] = payload
    return payloads


def codex_command(prompt: str, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    codex = find_codex()
    if not codex:
        raise RuntimeError("Codex CLI unavailable for authenticated Robinhood MCP refresh")
    command = [
        codex,
        "exec",
        "--ephemeral",
        "--json",
        "--ignore-user-config",
        "--model",
        os.environ.get("CODEX_EXECUTION_MODEL", "gpt-5.6-luna"),
        "--cd",
        str(ROOT),
        "--sandbox",
        "read-only",
        "-c",
        'mcp_servers.robinhood-trading.url="https://agent.robinhood.com/mcp/trading"',
        prompt,
    ]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=timeout_seconds)


def refresh_once(symbols: list[str], timeout_seconds: float) -> tuple[bool, str, int]:
    result = codex_command(quote_prompt(symbols), timeout_seconds)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(f"Robinhood MCP refresh exited {result.returncode}: {output[-600:]}")
    payload = extract_quote_payload(result.stdout)
    if payload is None:
        raise RuntimeError(f"Robinhood MCP refresh returned no quote payload: {output[-600:]}")

    returned = payload["data"]["results"]
    requested = set(symbols)
    filtered = [row for row in returned if isinstance(row, dict) and clean_symbol(row.get("symbol")) in requested]
    if not filtered:
        raise RuntimeError("Robinhood MCP refresh returned no requested symbols")
    normalized = normalize_many({"data": {"results": filtered}})
    ingest = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ingest_robinhood_crypto_quote_snapshot.py")],
        cwd=ROOT,
        input=json.dumps({"data": {"results": filtered}}),
        capture_output=True,
        text=True,
        check=False,
    )
    if ingest.returncode != 0:
        raise RuntimeError(f"quote ingestion failed: {ingest.stdout[-400:]}{ingest.stderr[-400:]}")
    atomic_write(
        STATUS,
        {
            "timestamp": iso_now(),
            "status": "REFRESHED",
            "source": "authenticated Robinhood MCP public quotes",
            "quote_count": len(normalized),
            "symbols": [row["symbol"] for row in normalized],
            "original_quote_timestamps": {row["symbol"]: row["quote_timestamp"] for row in normalized},
            "runpod_private_data_transferred": False,
            "execution_authority": "Robinhood MCP host-only",
        },
    )
    return True, ingest.stdout.strip(), len(normalized)


def refresh_equity_once(symbols: list[str], timeout_seconds: float) -> int:
    result = codex_command(equity_quote_prompt(symbols), timeout_seconds)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(f"Robinhood equity MCP refresh exited {result.returncode}: {output[-600:]}")
    payload = extract_quote_payload(result.stdout)
    if payload is None:
        raise RuntimeError(f"Robinhood equity MCP refresh returned no quote payload: {output[-600:]}")
    requested = set(symbols)
    returned = payload["data"]["results"]
    filtered = [
        row for row in returned
        if isinstance(row, dict)
        and isinstance(row.get("quote"), dict)
        and str(row["quote"].get("symbol") or "").upper() in requested
    ]
    if not filtered:
        raise RuntimeError("Robinhood equity MCP refresh returned no requested symbols")
    ingest = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ingest_robinhood_equity_quote_snapshot.py")],
        cwd=ROOT,
        input=json.dumps({"data": {"results": filtered}}),
        capture_output=True,
        text=True,
        check=False,
    )
    if ingest.returncode != 0:
        raise RuntimeError(f"equity quote ingestion failed: {ingest.stdout[-400:]}{ingest.stderr[-400:]}")
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    status.update(
        {
            "equity_quote_count": len(filtered),
            "equity_symbols": [row["quote"]["symbol"] for row in filtered],
            "equity_original_quote_timestamps": {
                row["quote"]["symbol"]: max(
                    (value for value in (
                        row["quote"].get("venue_bid_time"),
                        row["quote"].get("venue_ask_time"),
                        row["quote"].get("venue_last_trade_time"),
                        row["quote"].get("venue_last_non_reg_trade_time"),
                    ) if value),
                    default=None,
                )
                for row in filtered
            },
            "equity_quote_source": "authenticated Robinhood MCP public quotes",
            "equity_routing_returned": False,
        }
    )
    atomic_write(STATUS, status)
    return len(filtered)


def refresh_account_once(timeout_seconds: float) -> tuple[str, int]:
    result = codex_command(account_prompt(), timeout_seconds)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(f"Robinhood account refresh exited {result.returncode}: {output[-600:]}")
    payloads = extract_tool_payloads(result.stdout)
    portfolio = payloads.get("get_portfolio")
    positions = payloads.get("get_crypto_positions")
    if not isinstance(portfolio, dict) or not isinstance(positions, dict):
        raise RuntimeError(f"Robinhood account refresh returned incomplete host-only results: {output[-600:]}")
    payload = {
        "retrieved_at": iso_now(),
        "account_match_confirmed": True,
        "crypto_account_confirmed": True,
        "portfolio": portfolio,
        "positions": positions,
    }
    normalized = normalize_execution(payload)
    ingest = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ingest_robinhood_execution_snapshot.py")],
        cwd=ROOT,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if ingest.returncode != 0:
        raise RuntimeError(f"account snapshot ingestion failed: {ingest.stdout[-400:]}{ingest.stderr[-400:]}")
    atomic_write(
        CAPITAL_SNAPSHOT,
        {
            "retrieved_at": normalized["retrieved_at"],
            "crypto_buying_power_usd": normalized["crypto_buying_power_usd"],
            "crypto_capital_source": "robinhood.get_portfolio.crypto_buying_power.buying_power",
            "crypto_capital_retrieved_at": normalized["retrieved_at"],
            "host_only": True,
            "runpod_private_data_transferred": False,
        },
    )
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    status.update(
        {
            "private_account_refresh": "REFRESHED_HOST_ONLY",
            "private_account_retrieved_at": normalized["retrieved_at"],
            "private_position_count": len(normalized["positions"]),
            "runpod_private_data_transferred": False,
        }
    )
    atomic_write(STATUS, status)
    return ingest.stdout.strip(), len(normalized["positions"])


def main() -> int:
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()
    interval = max(60.0, min(420.0, args.interval_seconds))
    while True:
        started = time.monotonic()
        try:
            symbols = tracked_symbols()
            ok, message, count = refresh_once(symbols, args.timeout_seconds)
            equity_count = refresh_equity_once(blue_chip_symbols(), args.timeout_seconds)
            account_message, position_count = refresh_account_once(args.timeout_seconds)
            print(f"ROBINHOOD_QUOTE_REFRESH: {count} crypto + {equity_count} blue-chip quote(s) written; account refresh: {position_count} position(s)", flush=True)
            exit_code = 0 if ok else 1
        except Exception as exc:  # keep the 24/7 liveness loop alive; gates remain fail-closed
            atomic_write(STATUS, {"timestamp": iso_now(), "status": "RETRYING", "error": str(exc), "runpod_private_data_transferred": False})
            print(f"ROBINHOOD_QUOTE_REFRESH_RETRY: {type(exc).__name__}: {exc}", flush=True)
            exit_code = 1
        if args.once:
            return exit_code
        time.sleep(max(1.0, interval - (time.monotonic() - started)))


if __name__ == "__main__":
    raise SystemExit(main())
