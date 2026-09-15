#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-1}"
SCANNER_LANES="${RUNPOD_SCANNER_LANES:-auto}"
MIN_LIGHTWEIGHT_LANES="${RUNPOD_MIN_LIGHTWEIGHT_LANES:-7}"
MAX_LIGHTWEIGHT_LANES="${RUNPOD_MAX_LIGHTWEIGHT_LANES:-700}"
SAFE_LIGHTWEIGHT_LANES="${RUNPOD_SAFE_LIGHTWEIGHT_LANES:-14}"
ALLOW_HIGH_LIGHTWEIGHT_FANOUT="${RUNPOD_ALLOW_HIGH_LIGHTWEIGHT_FANOUT:-false}"
PRESSURE_STATUS="${RUNPOD_SCANNER_PRESSURE_STATUS:-data/runpod_lightweight_scanner_status.json}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

mkdir -p logs

if [ "$SCANNER_LANES" = "auto" ]; then
  SCANNER_LANES="$MIN_LIGHTWEIGHT_LANES"
  if [ -f "$PRESSURE_STATUS" ]; then
    pressure="$(python3 - "$PRESSURE_STATUS" "$MIN_LIGHTWEIGHT_LANES" "$MAX_LIGHTWEIGHT_LANES" <<'PY'
import json
import sys

path, min_lanes, max_lanes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
try:
    status = json.load(open(path, encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    print(min_lanes)
    raise SystemExit

source_quality = status.get("source_quality") or {}
fresh_count = int(source_quality.get("fresh_source_count") or 0)
scanner_viable = status.get("scanner_viable") is True
trade_execution_allowed = status.get("trade_execution_allowed") is True

lanes = min_lanes
if fresh_count >= 4:
    lanes = max(lanes, 14)
if scanner_viable:
    lanes = max(lanes, 70)
if trade_execution_allowed:
    lanes = min_lanes
print(min(max(lanes, min_lanes), max_lanes))
PY
)"
    SCANNER_LANES="$pressure"
  fi
fi

if [ "$SCANNER_LANES" -lt "$MIN_LIGHTWEIGHT_LANES" ]; then
  SCANNER_LANES="$MIN_LIGHTWEIGHT_LANES"
fi

if [ "$ALLOW_HIGH_LIGHTWEIGHT_FANOUT" != "true" ] && [ "$SCANNER_LANES" -gt "$SAFE_LIGHTWEIGHT_LANES" ]; then
  echo "LIGHTWEIGHT_SCANNER_FANOUT_CAPPED: true"
  echo "SAFE_LIGHTWEIGHT_LANES: $SAFE_LIGHTWEIGHT_LANES"
  echo "REASON: high fanout requires confirmed no-heavy-usage condition"
  echo "HEAVY_ACTION: NO ACTION"
  SCANNER_LANES="$SAFE_LIGHTWEIGHT_LANES"
fi

if [ "$SCANNER_LANES" -gt "$MAX_LIGHTWEIGHT_LANES" ]; then
  echo "LIGHTWEIGHT_SCANNER_EXPANSION: ${SCANNER_LANES}_LANES"
  echo "MAX_LIGHTWEIGHT_LANES: $MAX_LIGHTWEIGHT_LANES"
  echo "HEAVY_ACTION: NO ACTION"
  SCANNER_LANES="$MAX_LIGHTWEIGHT_LANES"
fi

echo "LIGHTWEIGHT_SCANNER_LANE_RANGE: ${MIN_LIGHTWEIGHT_LANES}-${MAX_LIGHTWEIGHT_LANES}+"
echo "LIGHTWEIGHT_SCANNER_LANES_SELECTED: $SCANNER_LANES"
echo "HEAVY_ACTION: NO ACTION"

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
