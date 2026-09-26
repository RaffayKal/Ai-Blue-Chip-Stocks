#!/usr/bin/env python3
import sys
from pathlib import Path

from capital_engine import evaluate, load_json
from project_root import ROOT

USER_ALGORITHM_ID = "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING"
ALLOWED_SCANNER_DECISIONS = {
    "LOOKING",
    "NO ACTION",
    "WATCHLIST ONLY",
    "HOLD CANDIDATE",
    "BUY CANDIDATE",
    "SELL CANDIDATE",
}
ACTIVATING_RESULTS = {"VALIDATED SETUP"}


def main() -> None:
    if Path.cwd() != ROOT:
        print("CODEX_STATE: DORMANT")
        print("VIABLE: false")
        print("FAILED_CHECKS: wrong working directory")
        raise SystemExit(0)
    if len(sys.argv) != 2:
        print("CODEX_STATE: DORMANT")
        print("VIABLE: false")
        print("FAILED_CHECKS: usage: python3 algorithms/candidate_envelope_gate.py <candidate_envelope.json>")
        raise SystemExit(0)

    envelope = load_json(Path(sys.argv[1]))
    failed = []

    if envelope.get("user_algorithm_id") != USER_ALGORITHM_ID:
        failed.append(f"user algorithm is not {USER_ALGORITHM_ID}")
    if not envelope.get("envelope_id"):
        failed.append("envelope_id missing")
    if not envelope.get("idempotency_key"):
        failed.append("idempotency_key missing")
    if envelope.get("created_by") != "CHATGPT_PLUGIN_SCANNER":
        failed.append("created_by must be CHATGPT_PLUGIN_SCANNER")
    if envelope.get("scanner_viable") is not True:
        failed.append("scanner_viable is not true")
    if envelope.get("requested_codex_activation") is not True:
        failed.append("requested_codex_activation is not true")
    if envelope.get("plugins_execute_trades") is not False:
        failed.append("plugins_execute_trades must be false")
    if envelope.get("broker_order_submitted") is not False:
        failed.append("broker_order_submitted must be false")
    if envelope.get("candidate_decision") not in ALLOWED_SCANNER_DECISIONS:
        failed.append("candidate_decision is not allowed")

    # Robinhood is the sole hard-required market-data authority. A persisted
    # envelope that names a peer feed as required is stale legacy state and
    # must never reach the autonomous workflow.
    required_sources = envelope.get("required_sources") or []
    required_source_names = {
        str(item.get("source") or "")
        for item in required_sources
        if isinstance(item, dict)
    }
    if any("Coinbase" in name or "Binance" in name or "Kraken" in name for name in required_source_names):
        failed.append("legacy peer-feed requirement detected; Robinhood must be the only required market-data source")
    if not any("Robinhood" in name for name in required_source_names):
        failed.append("Robinhood required market-data source missing")

    provenance = envelope.get("data_provenance")
    if not isinstance(provenance, list) or len(provenance) < 2:
        failed.append("data_provenance must contain at least two source records")
    else:
        source_names = []
        for index, source in enumerate(provenance, start=1):
            if not isinstance(source, dict):
                failed.append(f"data_provenance[{index}] must be an object")
                continue
            source_name = source.get("source")
            if not source_name:
                failed.append(f"data_provenance[{index}] source missing")
            else:
                source_names.append(str(source_name))
            if not source.get("timestamp"):
                failed.append(f"data_provenance[{index}] timestamp missing")
            if source.get("status") != "fresh":
                failed.append(f"data_provenance[{index}] status is not fresh")
        if len(source_names) != len(set(source_names)):
            failed.append("data_provenance must contain unique independent sources")

    market_input = envelope.get("market_input")
    if not isinstance(market_input, dict):
        failed.append("market_input must be an object")
        market_decision = {
            "RESULT": "NO ACTION",
            "FAILED_CHECKS": "market_input missing",
            "NEXT_ALLOWED_STEP": "none",
        }
    else:
        market_decision = evaluate(market_input)
        if market_decision["RESULT"] not in ACTIVATING_RESULTS:
            failed.append(f"capital engine result is {market_decision['RESULT']}")

    if failed:
        print("CODEX_STATE: DORMANT")
        print("VIABLE: false")
        print(f"CAPITAL_ENGINE_RESULT: {market_decision['RESULT']}")
        print(f"FAILED_CHECKS: {', '.join(failed)}")
        print("NEXT_ALLOWED_STEP: keep ChatGPT/plugins scanning; do not wake Codex agentic workflow")
        raise SystemExit(0)

    print("CODEX_STATE: ACTIVATE_AGENTIC_WORKFLOW")
    print("VIABLE: true")
    print("AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS")
    print(f"CAPITAL_ENGINE_RESULT: {market_decision['RESULT']}")
    print(f"SYMBOL: {market_decision['SYMBOL']}")
    print(f"ASSET_CLASS: {market_decision['ASSET_CLASS']}")
    print("NEXT_ALLOWED_STEP: run existing autonomous agentic workflow; place only preview-matched orders that pass active ticket, broker, risk, idempotency, and logging gates")


if __name__ == "__main__":
    main()
