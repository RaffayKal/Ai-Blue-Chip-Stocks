#!/usr/bin/env bash
set -u

ROOT="/Users/raffaykal/AI BLUE CHIP STOCKS"
ENVELOPE="${1:-data/current_candidate_envelope.json}"
ENVELOPE_MARKET_INPUT="/private/tmp/apex_current_envelope_market_input.json"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "CODEX_STATE: DORMANT"
  echo "VIABLE: false"
  echo "FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS"
  exit 0
fi

if [ ! -f "$ENVELOPE" ]; then
  echo "CODEX_STATE: DORMANT"
  echo "VIABLE: false"
  echo "FAILED_CHECKS: current candidate envelope missing"
  echo "NEXT_ALLOWED_STEP: keep watcher scanning; do not run buy/sell gates"
  exit 0
fi

GOVERNOR_OUTPUT="$(python3 scripts/codex_resource_governor.py)"
echo "$GOVERNOR_OUTPUT"
if printf '%s
' "$GOVERNOR_OUTPUT" | grep -qx 'SYSTEM_STATE: FROZEN'; then
  echo "CODEX_STATE: DORMANT"
  echo "VIABLE: false"
  echo "AUTONOMOUS_BUY_SELL: DISABLED_WHILE_FROZEN"
  exit 0
fi

GATE_OUTPUT="$(python3 algorithms/candidate_envelope_gate.py "$ENVELOPE")"
echo "$GATE_OUTPUT"

if ! printf '%s
' "$GATE_OUTPUT" | grep -qx 'VIABLE: true'; then
  echo "AUTONOMOUS_BUY_SELL: DISABLED_UNTIL_VIABLE_TRUE"
  echo "SYSTEM_STATE: ACTIVE"
  echo "OPERATIONS: CONTINUE_UNTIL_USAGE_LESS_THAN_OR_EQUAL_2_PERCENT"
  echo "NEXT_ALLOWED_STEP: keep operations active; block execution only until a fresh viable envelope passes"
  exit 0
fi

if ! printf '%s
' "$GATE_OUTPUT" | grep -qx 'AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS'; then
  echo "AUTONOMOUS_BUY_SELL: DISABLED_UNTIL_GATE_PASS"
  echo "SYSTEM_STATE: ACTIVE"
  echo "OPERATIONS: CONTINUE_UNTIL_USAGE_LESS_THAN_OR_EQUAL_2_PERCENT"
  echo "NEXT_ALLOWED_STEP: keep operations active; block execution only until every gate passes"
  exit 0
fi

echo "--- AUTONOMOUS_TICKET_RELOAD ---"
python3 scripts/reload_autonomous_tickets.py || exit 1

echo "--- ENVELOPE_MARKET_INPUT_EXTRACT ---"
python3 scripts/extract_envelope_market_input.py "$ENVELOPE" "$ENVELOPE_MARKET_INPUT" || exit 1

echo "--- AUTONOMOUS_SIDE_SELECT ---"
SIDE_OUTPUT="$(python3 scripts/select_autonomous_side.py "$ENVELOPE")"
echo "$SIDE_OUTPUT"

if printf '%s
' "$SIDE_OUTPUT" | grep -qx 'AUTONOMOUS_SIDE: BUY'; then
  echo "--- AUTONOMOUS_VOLATILE_CRYPTO_MARKET_BUY_GATE ---"
  python3 algorithms/autonomous_order_gate.py "$ENVELOPE_MARKET_INPUT" data/autonomous_crypto_market_buy_auto_max_active.json || exit 1
  exit 0
fi

if printf '%s
' "$SIDE_OUTPUT" | grep -qx 'AUTONOMOUS_SIDE: SELL'; then
  echo "--- AUTONOMOUS_VOLATILE_CRYPTO_MARKET_SELL_GATE ---"
  python3 algorithms/autonomous_order_gate.py "$ENVELOPE_MARKET_INPUT" data/autonomous_crypto_market_sell_position_auto_active.json || exit 1
  exit 0
fi

echo "AUTONOMOUS_BUY_SELL: NO_SIDE_AUTHORIZED"
echo "NEXT_ALLOWED_STEP: return Codex to dormant state"
