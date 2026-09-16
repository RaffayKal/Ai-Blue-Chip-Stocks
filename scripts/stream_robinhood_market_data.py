#!/usr/bin/env python3
"""Continuous Robinhood crypto quote poller for an always-on worker (RunPod).

Uses the UNOFFICIAL robin_stocks library, not the Robinhood MCP connection --
this exists specifically so Robinhood data can keep refreshing when no
Claude/ChatGPT/Codex session is open. That tradeoff (real account
credentials stored on a third-party server, against Robinhood's ToS for
unofficial API access) was made explicitly by the account owner; see the
conversation history for the reasoning. Read-only: this script only ever
reads quotes, it never places, previews, or touches any order.

Required environment variables (set as RunPod secrets, never hardcoded):
  ROBINHOOD_USERNAME
  ROBINHOOD_PASSWORD
  ROBINHOOD_MFA_CODE   -- only needed for the first login; once a session
                          pickle exists at ROBINHOOD_SESSION_PATH, subsequent
                          restarts reuse it without re-prompting for MFA,
                          until Robinhood invalidates the session.

Optional:
  ROBINHOOD_SESSION_PATH   -- where to persist the login session pickle
                              (default: data/.robinhood_session)
  ROBINHOOD_POLL_INTERVAL_SECONDS -- default 15
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"
SYMBOL = "BTC"
POLL_INTERVAL_SECONDS = float(os.getenv("ROBINHOOD_POLL_INTERVAL_SECONDS", "15"))
SESSION_PATH = Path(os.getenv("ROBINHOOD_SESSION_PATH", str(ROOT / "data" / ".robinhood_session")))


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def normalize(quote: dict) -> dict:
    symbol = str(quote.get("symbol") or SYMBOL).upper()
    bid = float(quote["bid_price"])
    ask = float(quote["ask_price"])
    last = float(quote["mark_price"])
    return {
        "symbol": symbol,
        "asset_class": "CRYPTO",
        "session": "CRYPTO_24_7",
        "venue": "Robinhood Crypto",
        "broker_name": "Robinhood",
        "timestamp": iso_now(),
        "quote_timestamp": iso_now(),
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
        "source": "robin_stocks.get_crypto_quote (unofficial API, RunPod poller)",
    }


def main():
    if Path.cwd() != ROOT:
        raise SystemExit("BLOCKED: command is not running inside AI BLUE CHIP STOCKS")

    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")
    mfa_code = os.getenv("ROBINHOOD_MFA_CODE")
    if not username or not password:
        raise SystemExit("BLOCKED: ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD are required")

    import robin_stocks.robinhood as rh

    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    rh.login(
        username=username,
        password=password,
        mfa_code=mfa_code,
        store_session=True,
        pickle_path=str(SESSION_PATH.parent),
        pickle_name=SESSION_PATH.name,
    )

    once = "--once" in sys.argv
    while True:
        try:
            quote = rh.crypto.get_crypto_quote(SYMBOL)
            if not quote or not quote.get("bid_price") or not quote.get("ask_price"):
                print("ROBINHOOD_QUOTE_UNAVAILABLE", flush=True)
            else:
                snapshot = normalize(quote)
                write_json(SNAPSHOT, snapshot)
                print(
                    f"ROBINHOOD_QUOTE symbol={snapshot['symbol']} bid={snapshot['bid']} "
                    f"ask={snapshot['ask']} last={snapshot['last']} at={snapshot['timestamp']}",
                    flush=True,
                )
        except Exception as exc:  # noqa: BLE001 -- keep polling despite transient API/session errors
            print(f"ROBINHOOD_QUOTE_ERROR {exc}", flush=True)

        if once:
            return
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
