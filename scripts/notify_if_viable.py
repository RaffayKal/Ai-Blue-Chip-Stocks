#!/usr/bin/env python3
"""Read-only viability check for the 24/7 notify-and-confirm pipeline.

Runs the existing envelope + capital-engine gates against the current
candidate envelope and prints a plain-language summary. This script never
calls a broker API and never places an order. It exists only to tell a human
(or the calling agent) whether a ticket is ready for manual review.
"""
import json
import subprocess
import sys
from pathlib import Path

from project_root import ROOT

ENVELOPE_PATH = ROOT / "data" / "current_candidate_envelope.json"
GATE_SCRIPT = ROOT / "algorithms" / "candidate_envelope_gate.py"


def main() -> None:
    if Path.cwd() != ROOT:
        print("NOTIFY_STATE: SKIPPED")
        print("REASON: must run from repo root")
        raise SystemExit(0)

    if not ENVELOPE_PATH.exists():
        print("NOTIFY_STATE: SKIPPED")
        print("REASON: no current_candidate_envelope.json")
        raise SystemExit(0)

    result = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), str(ENVELOPE_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    gate_output = result.stdout.strip()
    print(gate_output)

    if "VIABLE: true" not in gate_output:
        print("NOTIFY_STATE: NOT_VIABLE_NO_NOTIFICATION")
        raise SystemExit(0)

    envelope = json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))
    market_input = envelope.get("market_input", {})

    print("NOTIFY_STATE: VIABLE_TICKET_READY_FOR_HUMAN_REVIEW")
    print(f"SYMBOL: {market_input.get('symbol')}")
    print(f"ASSET_CLASS: {market_input.get('asset_class')}")
    print(f"BID: {market_input.get('bid')}")
    print(f"ASK: {market_input.get('ask')}")
    print(f"LAST: {market_input.get('last')}")
    print(f"CANDIDATE_DECISION: {envelope.get('candidate_decision')}")
    print(f"ENVELOPE_ID: {envelope.get('envelope_id')}")
    print(f"IDEMPOTENCY_KEY: {envelope.get('idempotency_key')}")
    print("NEXT_ALLOWED_STEP: surface this ticket to the user for explicit approval; do not place any order automatically")


if __name__ == "__main__":
    main()
