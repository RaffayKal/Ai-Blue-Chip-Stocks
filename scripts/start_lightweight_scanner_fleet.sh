#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-7}"
SCANNER_LANES="${RUNPOD_SCANNER_LANES:-auto}"
MIN_MEDIUM_WEIGHT_LANES="${RUNPOD_MIN_MEDIUM_WEIGHT_LANES:-${RUNPOD_MIN_LIGHTWEIGHT_LANES:-7}}"
MAX_MEDIUM_WEIGHT_LANES="${RUNPOD_MAX_MEDIUM_WEIGHT_LANES:-${RUNPOD_MAX_LIGHTWEIGHT_LANES:-700}}"
SAFE_MEDIUM_WEIGHT_LANES="${RUNPOD_SAFE_MEDIUM_WEIGHT_LANES:-${RUNPOD_SAFE_LIGHTWEIGHT_LANES:-14}}"
ALLOW_HIGH_MEDIUM_WEIGHT_FANOUT="${RUNPOD_ALLOW_HIGH_MEDIUM_WEIGHT_FANOUT:-${RUNPOD_ALLOW_HIGH_LIGHTWEIGHT_FANOUT:-true}}"
PRESSURE_STATUS="${RUNPOD_SCANNER_PRESSURE_STATUS:-data/runpod_lightweight_scanner_status.json}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

mkdir -p logs

if [ "$SCANNER_LANES" = "auto" ]; then
  SCANNER_LANES="$MIN_MEDIUM_WEIGHT_LANES"
  if [ -f "$PRESSURE_STATUS" ]; then
    pressure="$(python3 - "$PRESSURE_STATUS" "$MIN_MEDIUM_WEIGHT_LANES" "$MAX_MEDIUM_WEIGHT_LANES" <<'PY'
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

if [ "$SCANNER_LANES" -lt "$MIN_MEDIUM_WEIGHT_LANES" ]; then
  SCANNER_LANES="$MIN_MEDIUM_WEIGHT_LANES"
fi

if [ "$ALLOW_HIGH_MEDIUM_WEIGHT_FANOUT" != "true" ] && [ "$SCANNER_LANES" -gt "$SAFE_MEDIUM_WEIGHT_LANES" ]; then
  echo "MEDIUM_WEIGHT_SCANNER_FANOUT_CAPPED: true"
  echo "SAFE_MEDIUM_WEIGHT_LANES: $SAFE_MEDIUM_WEIGHT_LANES"
  echo "REASON: high fanout requires confirmed no-heavy-usage condition"
  echo "HEAVY_ACTION: NO ACTION"
  SCANNER_LANES="$SAFE_MEDIUM_WEIGHT_LANES"
fi

if [ "$SCANNER_LANES" -gt "$MAX_MEDIUM_WEIGHT_LANES" ]; then
  echo "MEDIUM_WEIGHT_SCANNER_EXPANSION: ${SCANNER_LANES}_LANES"
  echo "MAX_MEDIUM_WEIGHT_LANES: $MAX_MEDIUM_WEIGHT_LANES"
  echo "HEAVY_ACTION: NO ACTION"
  SCANNER_LANES="$MAX_MEDIUM_WEIGHT_LANES"
fi

echo "MEDIUM_WEIGHT_SCANNER_LANE_RANGE: ${MIN_MEDIUM_WEIGHT_LANES}-${MAX_MEDIUM_WEIGHT_LANES}+"
echo "MEDIUM_WEIGHT_SCANNER_LANES_SELECTED: $SCANNER_LANES"
echo "HEAVY_ACTION: NO ACTION"

# Each lane used to be its own OS process (~20-25MB RSS just for the Python
# interpreter). At 700 lanes that is 15-20GB of RAM for work that is almost
# entirely file I/O and light JSON scoring. scan_once() has no shared mutable
# state keyed off process identity, so all lanes run as threads inside one
# interpreter instead: verified locally at 700 lanes / ~34MB RSS total.
POOL_LOG="logs/threaded_scanner_lane_pool.out.log"

start_pool() {
  python3 scripts/threaded_scanner_lane_pool.py \
    --lanes "$SCANNER_LANES" \
    --interval-seconds "$INTERVAL_SECONDS" \
    --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE" \
    >> "$POOL_LOG" 2>&1 &
  echo "$!"
}

pool_pid="$(start_pool)"
echo "STARTED_THREADED_SCANNER_LANE_POOL: lanes=$SCANNER_LANES pid=$pool_pid log=$POOL_LOG"

while true; do
  if ! kill -0 "$pool_pid" 2>/dev/null; then
    echo "RESTARTING_THREADED_SCANNER_LANE_POOL"
    pool_pid="$(start_pool)"
    echo "STARTED_THREADED_SCANNER_LANE_POOL: lanes=$SCANNER_LANES pid=$pool_pid log=$POOL_LOG"
  fi
  sleep 5
done
