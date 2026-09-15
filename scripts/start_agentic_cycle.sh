#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

GOVERNOR_OUTPUT="$(python3 scripts/codex_resource_governor.py)"
echo "$GOVERNOR_OUTPUT"
if printf '%s
' "$GOVERNOR_OUTPUT" | grep -qx 'SYSTEM_STATE: FROZEN'; then
  echo "AUTONOMOUS_BUY_SELL: DISABLED_WHILE_FROZEN"
  echo "NO ACTION"
  exit 0
fi

echo "--- CRYPTO_24_7 CHECK ---"
python3 algorithms/capital_engine.py data/sample_crypto_input.json || exit 1

echo "--- BLUE_CHIPS_WHEN_POSSIBLE CHECK ---"
python3 algorithms/capital_engine.py data/sample_blue_chip_input.json || exit 1

echo "--- ROBINHOOD_FRACTIONAL_BLUE_CHIP_CHECK ---"
python3 algorithms/capital_engine.py data/sample_robinhood_fractional_blue_chip_input.json || exit 1

echo "--- ROBINHOOD_CRYPTO_24_7_CHECK ---"
python3 algorithms/capital_engine.py data/sample_robinhood_crypto_input.json || exit 1

echo "--- CURRENT_CANDIDATE_ENVELOPE_GATE ---"
./scripts/run_autonomous_if_viable.sh data/current_candidate_envelope.json || exit 1
