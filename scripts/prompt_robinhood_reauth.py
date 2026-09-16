#!/usr/bin/env python3
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

QUOTE_SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"
STREAM_STATUS = ROOT / "data" / "robinhood_stream_status.json"
PROMPT_STATUS = ROOT / "data" / "robinhood_mcp_reauth_prompt_status.json"
DEFAULT_MAX_AGE_SECONDS = 90.0


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {"json_error": "invalid_json"}


def file_age(path):
    if not path.exists():
        return None
    return time.time() - path.stat().st_mtime


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_status(max_age_seconds):
    quote = read_json(QUOTE_SNAPSHOT)
    stream = read_json(STREAM_STATUS)
    quote_age = file_age(QUOTE_SNAPSHOT)
    stream_age = file_age(STREAM_STATUS)
    quote_fresh = quote_age is not None and 0 <= quote_age <= max_age_seconds
    stream_status = stream.get("status", "MISSING")
    stream_ok = stream_status == "MCP_ONLY"
    needs_reauth = not quote_fresh
    needs_persistent_stream = stream_status not in {"MCP_ONLY"} or not quote_fresh
    return {
        "timestamp_utc": iso_now(),
        "quote_snapshot": str(QUOTE_SNAPSHOT),
        "quote_age_seconds": quote_age,
        "quote_fresh": quote_fresh,
        "quote_timestamp": quote.get("quote_timestamp"),
        "quote_source": quote.get("source"),
        "stream_status_path": str(STREAM_STATUS),
        "stream_status_age_seconds": stream_age,
        "stream_status": stream_status,
        "stream_reason": stream.get("reason"),
        "stream_ok": stream_ok,
        "max_age_seconds": max_age_seconds,
        "needs_robinhood_mcp_reauth": needs_reauth,
        "needs_robinhood_persistent_stream": needs_persistent_stream,
        "execution_authority": False,
        "trade_execution_allowed": False,
    }


def print_status(status):
    print("ROBINHOOD_MCP_FEED_CHECK")
    print(f"QUOTE_FRESH: {str(status['quote_fresh']).lower()}")
    print(f"QUOTE_AGE_SECONDS: {status['quote_age_seconds']}")
    print(f"QUOTE_TIMESTAMP: {status['quote_timestamp']}")
    print(f"QUOTE_SOURCE: {status['quote_source']}")
    print(f"STREAM_STATUS: {status['stream_status']}")
    print(f"STREAM_REASON: {status['stream_reason']}")
    print(f"NEEDS_ROBINHOOD_MCP_REAUTH: {str(status['needs_robinhood_mcp_reauth']).lower()}")
    print(f"NEEDS_ROBINHOOD_PERSISTENT_STREAM: {str(status['needs_robinhood_persistent_stream']).lower()}")
    print("TRADE_EXECUTION_ALLOWED: false")
    if status["needs_robinhood_mcp_reauth"]:
        print("")
        print("PROMPT_USER_REAUTHENTICATE_ROBINHOOD_TRADING_MCP:")
        print("Open Codex MCP selector with /mcp.")
        print("Select robinhood-trading.")
        print("Choose Re-authenticate.")
        print("Complete Robinhood login/approval in the app/browser prompt.")
        print("Then tell me: reauthenticated.")
    elif status["needs_robinhood_persistent_stream"]:
        print("")
        print("ROBINHOOD_MCP_AUTH: LIVE")
        print("PERSISTENT_STREAM_STATUS: MCP_ONLY_RELAY_REQUIRED")
        print("NEXT: RunPod cannot use Robinhood username/password feed; keep refreshing via robinhood-trading MCP relay artifacts.")


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")
    parser = argparse.ArgumentParser(description="Check Robinhood MCP-fed scanner freshness and print the re-auth prompt when needed.")
    parser.add_argument("--max-age-seconds", type=float, default=DEFAULT_MAX_AGE_SECONDS)
    args = parser.parse_args()
    status = build_status(args.max_age_seconds)
    write_json(PROMPT_STATUS, status)
    print_status(status)


if __name__ == "__main__":
    main()
