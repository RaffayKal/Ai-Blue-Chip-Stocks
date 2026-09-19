#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-7}"
SCANNER_LANES="${RUNPOD_SCANNER_LANES:-auto}"
MIN_MEDIUM_WEIGHT_LANES="${RUNPOD_MIN_MEDIUM_WEIGHT_LANES:-${RUNPOD_MIN_LIGHTWEIGHT_LANES:-70}}"
MAX_MEDIUM_WEIGHT_LANES="${RUNPOD_MAX_MEDIUM_WEIGHT_LANES:-${RUNPOD_MAX_LIGHTWEIGHT_LANES:-70}}"
SAFE_MEDIUM_WEIGHT_LANES="${RUNPOD_SAFE_MEDIUM_WEIGHT_LANES:-${RUNPOD_SAFE_LIGHTWEIGHT_LANES:-70}}"
ALLOW_HIGH_MEDIUM_WEIGHT_FANOUT="${RUNPOD_ALLOW_HIGH_MEDIUM_WEIGHT_FANOUT:-${RUNPOD_ALLOW_HIGH_LIGHTWEIGHT_FANOUT:-true}}"
PRESSURE_STATUS="${RUNPOD_SCANNER_PRESSURE_STATUS:-data/runpod_lightweight_scanner_status.json}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

# This worker is CPU-only. Do not let a stale environment variable request
# thousands of asyncio lanes on a small pod: prior runs on 4 GB RAM were OOM
# killed with exit code 137. Derive a hard safety ceiling from actual memory.
TOTAL_MEMORY_GB="$(awk '/MemTotal:/ {printf "%d", ($2/1024/1024)+0.5; exit}' /proc/meminfo 2>/dev/null || printf '4')"
if [ "$TOTAL_MEMORY_GB" -le 6 ]; then
  RESOURCE_SAFE_LANES=70
elif [ "$TOTAL_MEMORY_GB" -le 16 ]; then
  RESOURCE_SAFE_LANES=70
else
  RESOURCE_SAFE_LANES=280
fi
if [ "$MAX_MEDIUM_WEIGHT_LANES" -gt "$RESOURCE_SAFE_LANES" ]; then
  MAX_MEDIUM_WEIGHT_LANES="$RESOURCE_SAFE_LANES"
fi
if [ "$SAFE_MEDIUM_WEIGHT_LANES" -gt "$RESOURCE_SAFE_LANES" ]; then
  SAFE_MEDIUM_WEIGHT_LANES="$RESOURCE_SAFE_LANES"
fi
echo "RESOURCE_MEMORY_GB: $TOTAL_MEMORY_GB"
echo "RESOURCE_SAFE_MEDIUM_WEIGHT_LANES: $RESOURCE_SAFE_LANES"
echo "RESOURCE_CPU_TARGET_PERCENT: 97-100 (advisory scheduler target; autonomous gates unchanged)"

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
# interpreter). At high lane counts that is 15-20GB of RAM for work that is almost
# entirely file I/O and light JSON scoring. scan_once() has no shared mutable
# state keyed off process identity, so all lanes run as threads inside one
# interpreter instead: asyncio tasks keep lane count decoupled from OS thread count.
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

# The per-lane pool's own stdout is redirected to $POOL_LOG above so high lane counts
# lanes' worth of per-cycle output doesn't flood the container log. That
# also meant nothing visible ever proved the scanner was actively deciding
# anything -- only infra-level price ticks (COINGECKO_QUOTE, etc.) reached
# the visible container log, which looked identical whether or not the
# scanner was actually running. This periodically surfaces real proof of
# active scanning (current decision, viability, fleet consensus) to the
# visible container log, reading the same JSON status files Codex/external
# checks already read.
print_scanning_proof() {
  python3 - "$PRESSURE_STATUS" "data/fleet_synergy_status.json" "data/volatile_crypto_candidates.json" <<'PY'
import json
import sys

scanner_path, synergy_path, candidates_path = sys.argv[1], sys.argv[2], sys.argv[3]

def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

scanner = load(scanner_path)
synergy = load(synergy_path)
candidates = load(candidates_path)

print(
    "SCANNING_PROOF: "
    f"active_symbol={candidates.get('active_symbol', 'UNKNOWN')} "
    f"candidate_decision={scanner.get('candidate_decision', 'UNKNOWN')} "
    f"scanner_viable={scanner.get('scanner_viable', 'UNKNOWN')} "
    f"last_status_timestamp={scanner.get('timestamp_utc', 'UNKNOWN')} "
    f"fleet_samples={synergy.get('sample_count', 'UNKNOWN')} "
    f"fleet_consensus={synergy.get('consensus_decision', 'UNKNOWN')} "
    f"fleet_agreement={synergy.get('agreement_ratio', 'UNKNOWN')} "
    f"fleet_ranked_at={synergy.get('timestamp_utc', 'UNKNOWN')}"
)
PY
}

heartbeat_ticks=0
while true; do
  if ! kill -0 "$pool_pid" 2>/dev/null; then
    echo "RESTARTING_THREADED_SCANNER_LANE_POOL"
    pool_pid="$(start_pool)"
    echo "STARTED_THREADED_SCANNER_LANE_POOL: lanes=$SCANNER_LANES pid=$pool_pid log=$POOL_LOG"
  fi
  heartbeat_ticks=$((heartbeat_ticks + 1))
  if [ "$heartbeat_ticks" -ge 3 ]; then
    print_scanning_proof
    heartbeat_ticks=0
  fi
  sleep 5
done
