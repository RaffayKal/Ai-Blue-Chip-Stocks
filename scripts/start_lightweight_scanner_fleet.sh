#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-1}"
SCANNER_LANES="${RUNPOD_SCANNER_LANES:-7}"
MAX_EXPECTED_LIGHTWEIGHT_LANES="${RUNPOD_MAX_EXPECTED_LIGHTWEIGHT_LANES:-70}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

mkdir -p logs

if [ "$SCANNER_LANES" -gt "$MAX_EXPECTED_LIGHTWEIGHT_LANES" ]; then
  echo "LIGHTWEIGHT_SCANNER_EXPANSION: ${SCANNER_LANES}_LANES"
  echo "MAX_EXPECTED_LIGHTWEIGHT_LANES: $MAX_EXPECTED_LIGHTWEIGHT_LANES"
  echo "HEAVY_ACTION: NO ACTION"
fi

lane=1
while [ "$lane" -le "$SCANNER_LANES" ]; do
  lane_name="lane_${lane}"
  if [ "$lane" -eq 1 ]; then
    lane_name="primary"
  fi
  python3 scripts/runpod_lightweight_scanner.py \
    --interval-seconds "$INTERVAL_SECONDS" \
    --lane "$lane_name" \
    --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE" \
    > "logs/runpod_lightweight_scanner_${lane_name}.out.log" 2>&1 &
  echo "STARTED_LIGHTWEIGHT_SCANNER_LANE: $lane_name"
  lane=$((lane + 1))
done

wait
