#!/usr/bin/env python3
import json

from project_root import ROOT


SCANNER_STATUS = ROOT / "data" / "runpod_lightweight_scanner_status.json"
SUPERVISOR_STATUS = ROOT / "data" / "apex_prestige_supervisor_status.json"
CANDIDATE = ROOT / "data" / "current_candidate_envelope.json"


def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def yes_no(value):
    return "true" if value is True else "false"


def main():
    scanner = load_json(SCANNER_STATUS)
    supervisor = load_json(SUPERVISOR_STATUS)
    candidate = load_json(CANDIDATE)

    scanner_active = scanner.get("scanner_active") is True
    quote_stream = scanner.get("scanner_quote_stream") or {}
    execution_allowed = scanner.get("trade_execution_allowed") is True
    viable = candidate.get("scanner_viable") is True and candidate.get("requested_codex_activation") is True
    smooth = scanner_active and not execution_allowed

    print("NIGHT_OPERATIONS_REPORT")
    print(f"OPERATIONS_SMOOTH: {yes_no(smooth)}")
    print(f"SCANNER_ACTIVE: {yes_no(scanner_active)}")
    print(f"SCANNER_TIMESTAMP_UTC: {scanner.get('timestamp_utc', 'missing')}")
    print(f"MEDIUM_SCANNER_QUOTE_STREAM_ACTIVE: {yes_no(quote_stream.get('active') is True)}")
    print(f"MEDIUM_SCANNER_QUOTE_SOURCE_FRESH: {yes_no(quote_stream.get('source_fresh') is True)}")
    print(f"MEDIUM_SCANNER_QUOTE_SOURCE_COUNT: {quote_stream.get('quote_source_count', 'missing')}")
    print(f"MEDIUM_SCANNER_FRESH_QUOTE_SOURCE_COUNT: {quote_stream.get('fresh_quote_source_count', 'missing')}")
    print(f"MEDIUM_SCANNER_QUOTE_SOURCE_CONFLICT: {yes_no(quote_stream.get('source_conflict') is True)}")
    print(f"SUPERVISOR_STATE: {supervisor.get('supervisor_state', 'missing')}")
    print(f"HEALTH_CHECK_ONLY: {yes_no(supervisor.get('health_check_only') is True)}")
    print("HEAVY_ACTION: NO ACTION")
    print(f"TRADE_EXECUTION_ALLOWED: {yes_no(execution_allowed)}")
    print(f"CANDIDATE_DECISION: {candidate.get('candidate_decision', 'missing')}")
    print(f"SCANNER_VIABLE: {yes_no(viable)}")
    failed = candidate.get("failed_checks") or []
    if failed:
        print("BLOCKERS: " + "; ".join(str(item) for item in failed))
    else:
        print("BLOCKERS: none")
    print("NEXT_SAFE_ACTION: keep lightweight market watch running; do not execute unless every live gate passes")


if __name__ == "__main__":
    main()
