#!/usr/bin/env python3
import json
import subprocess
import sys

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


def apex_gate_passed():
    if not CANDIDATE.exists():
        return False
    result = subprocess.run(
        [sys.executable, str(ROOT / "algorithms" / "candidate_envelope_gate.py"), str(CANDIDATE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and "VIABLE: true" in result.stdout.splitlines()


def main():
    scanner = load_json(SCANNER_STATUS)
    supervisor = load_json(SUPERVISOR_STATUS)
    candidate = load_json(CANDIDATE)

    scanner_active = scanner.get("scanner_active") is True
    quote_stream = scanner.get("scanner_quote_stream") or {}
    online_coverage = scanner.get("online_market_media_reports_coverage") or {}
    projection = scanner.get("projection") or {}
    crypto_projection = projection.get("crypto") or {}
    blue_projection = projection.get("blue_chips") or {}
    crypto_scores = crypto_projection.get("projection_scores") or {}
    blue_scores = blue_projection.get("projection_scores") or {}
    execution_allowed = scanner.get("trade_execution_allowed") is True
    viable = candidate.get("scanner_viable") is True and candidate.get("requested_codex_activation") is True
    smooth = scanner_active and not execution_allowed
    execution_search_state = (
        scanner.get("apex_execution_search_state")
        or scanner.get("execution_search_state")
        or candidate.get("apex_execution_search_state")
        or "LOOKING FOR EXECUTION"
    )
    # Keep the operational search state separate from the candidate-level
    # fail-safe.  ORDER_ELIGIBILITY describes what the worker is doing now;
    # APEX_FAIL_SAFE_RESULT below describes whether this specific envelope
    # may proceed to ticket/preview/placement.
    apex_fail_safe_result = "PASSED" if apex_gate_passed() else "NO ACTION"

    print("NIGHT_OPERATIONS_REPORT")
    print(f"OPERATIONS_SMOOTH: {yes_no(smooth)}")
    print(f"SCANNER_ACTIVE: {yes_no(scanner_active)}")
    print(f"SCANNER_TIMESTAMP_UTC: {scanner.get('timestamp_utc', 'missing')}")
    print(f"MEDIUM_SCANNER_QUOTE_STREAM_ACTIVE: {yes_no(quote_stream.get('active') is True)}")
    print(f"MEDIUM_SCANNER_QUOTE_SOURCE_FRESH: {yes_no(quote_stream.get('source_fresh') is True)}")
    print(f"MEDIUM_SCANNER_QUOTE_SOURCE_COUNT: {quote_stream.get('quote_source_count', 'missing')}")
    print(f"MEDIUM_SCANNER_FRESH_QUOTE_SOURCE_COUNT: {quote_stream.get('fresh_quote_source_count', 'missing')}")
    print(f"MEDIUM_SCANNER_QUOTE_SOURCE_CONFLICT: {yes_no(quote_stream.get('source_conflict') is True)}")
    print(f"ONLINE_MARKET_MEDIA_REPORTS_ALL_FRESH: {yes_no(online_coverage.get('all_online_sources_fresh') is True)}")
    print(f"ONLINE_MARKET_MEDIA_REPORTS_FRESH_COUNT: {online_coverage.get('fresh_online_source_count', 'missing')}")
    print(f"ONLINE_MARKET_MEDIA_REPORTS_SOURCE_COUNT: {online_coverage.get('online_source_count', 'missing')}")
    print(f"FORECASTING_ENABLED: {yes_no(projection.get('forecasting_enabled') is True)}")
    print(f"FORECASTING_MODE: {projection.get('mode', 'missing')}")
    print(f"CRYPTO_CONTINUATION_PROBABILITY: {crypto_scores.get('continuation_probability', 'missing')}")
    print(f"CRYPTO_NET_OPPORTUNITY_SCORE: {crypto_scores.get('net_opportunity_score', 'missing')}")
    print(f"CRYPTO_REVERSAL_RISK_SCORE: {crypto_projection.get('reversal_risk_score', 'missing')}")
    print(f"BLUE_CHIP_CONTINUATION_PROBABILITY: {blue_scores.get('continuation_probability', 'missing')}")
    print(f"BLUE_CHIP_NET_OPPORTUNITY_SCORE: {blue_scores.get('net_opportunity_score', 'missing')}")
    print(f"BLUE_CHIP_REVERSAL_RISK_SCORE: {blue_projection.get('reversal_risk_score', 'missing')}")
    print(f"SUPERVISOR_STATE: {supervisor.get('supervisor_state', 'missing')}")
    print(f"HEALTH_CHECK_ONLY: {yes_no(supervisor.get('health_check_only') is True)}")
    print("DISCOVERY_STATE: SCANNING FOR VIABLE CANDIDATE/ENVELOPE")
    print(f"EXECUTION_SEARCH_STATE: {execution_search_state}")
    print("OPERATIONAL_STATE: LOOKING FOR EXECUTION")
    print("ORDER_ELIGIBILITY: LOOKING FOR EXECUTION")
    print(f"APEX_FAIL_SAFE_RESULT: {apex_fail_safe_result}")
    print(f"EXECUTION_TICKET_ELIGIBILITY: {apex_fail_safe_result}")
    print(f"TRADE_EXECUTION_ALLOWED: {yes_no(execution_allowed)}")
    print(f"CANDIDATE_DECISION: {candidate.get('candidate_decision', 'missing')}")
    print(f"SCANNER_VIABLE: {yes_no(viable)}")
    failed = candidate.get("failed_checks") or []
    if failed:
        print("BLOCKERS: " + "; ".join(str(item) for item in failed))
    else:
        print("BLOCKERS: none")
    print("NEXT_SAFE_ACTION: keep medium-weight market watch running; do not execute unless every live gate passes")


if __name__ == "__main__":
    main()
