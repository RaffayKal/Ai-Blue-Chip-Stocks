#!/usr/bin/env bash
set -u
export RUNPOD_MARKET_QUORUM=external

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-7}"
export RUNPOD_SCANNER_LANES="${RUNPOD_SCANNER_LANES:-14}"
ONCE_ARG="${1:-}"
PYTHON3_BIN="${PYTHON3_BIN:-}"

mkdir -p "$ROOT/logs" "$ROOT/data"

if [ -z "$PYTHON3_BIN" ] && [ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" ]; then
  PYTHON3_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
fi

if [ -z "$PYTHON3_BIN" ]; then
  PYTHON3_BIN="$(command -v python3 || true)"
fi

if [ -z "$PYTHON3_BIN" ] || [ ! -x "$PYTHON3_BIN" ]; then
  echo "BLOCKED: python3 is not available."
  exit 1
fi

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

ALPACA_KEY="${ALPACA_API_KEY_ID:-${APCA_API_KEY_ID:-${ALPACA_API_KEY:-}}}"
ALPACA_SECRET="${ALPACA_API_SECRET_KEY:-${APCA_API_SECRET_KEY:-${ALPACA_SECRET_KEY:-}}}"
ALPACA_CREDENTIALS_AVAILABLE=false
if [ -n "$ALPACA_KEY" ] && [ -n "$ALPACA_SECRET" ]; then
  ALPACA_CREDENTIALS_AVAILABLE=true
fi

if [ "${ALPACA_ADAPTER_REST_PREFLIGHT:-false}" = "true" ]; then
  if [ "$ALPACA_CREDENTIALS_AVAILABLE" = "true" ]; then
    "$PYTHON3_BIN" scripts/alpaca_market_data_adapter.py --rest-once || exit 1
  else
    echo "ALPACA_REST_PREFLIGHT: SKIPPED (Alpaca credentials unavailable; optional source)"
  fi
fi

if [ "${ALPACA_STREAM_MARKET_DATA:-false}" = "true" ]; then
  if [ "$ALPACA_CREDENTIALS_AVAILABLE" = "true" ]; then
    "$PYTHON3_BIN" scripts/stream_alpaca_market_data.py &
  else
    echo "ALPACA_STREAM: DISABLED (Alpaca credentials unavailable; optional source)"
  fi
fi

if [ "${COINGECKO_STREAM_MARKET_DATA:-true}" = "true" ]; then
  "$PYTHON3_BIN" scripts/stream_coingecko_market_data.py &
fi

if [ "${COINBASE_STREAM_MARKET_DATA:-true}" = "true" ]; then
  "$PYTHON3_BIN" scripts/stream_coinbase_crypto_market_data.py &
fi

if [ "${INDEPENDENT_CRYPTO_STREAMS:-true}" = "true" ]; then
  "$PYTHON3_BIN" scripts/stream_independent_crypto_market_data.py &
fi

if [ "${ROBINHOOD_STREAM_MARKET_DATA:-false}" = "true" ]; then
  mkdir -p "$ROOT/data"
  PROJECT_ROOT="$ROOT" "$PYTHON3_BIN" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

path = Path(os.environ["PROJECT_ROOT"]) / "data" / "robinhood_stream_status.json"
payload = {
    "status": "MCP_ONLY",
    "reason": "Robinhood feed requires robinhood-trading MCP relay; direct ROBINHOOD_USERNAME/ROBINHOOD_PASSWORD pod login is disabled",
    "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "execution_authority": False,
    "trade_execution_allowed": False,
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"ROBINHOOD_STREAM_STATUS: {payload['status']} - {payload['reason']}")
PY
else
  mkdir -p "$ROOT/data"
  PROJECT_ROOT="$ROOT" "$PYTHON3_BIN" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

path = Path(os.environ["PROJECT_ROOT"]) / "data" / "robinhood_stream_status.json"
payload = {
    "status": "DISABLED",
    "reason": "ROBINHOOD_STREAM_MARKET_DATA is not true",
    "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"ROBINHOOD_STREAM_STATUS: {payload['status']} - {payload['reason']}")
PY
fi

# Robinhood MCP is owned by the authenticated Codex host. No remote broker
# relay is part of the RunPod scanner runtime.

if [ "${MEDIUM_WEIGHT_FLEET_ENABLED:-true}" = "true" ]; then
  echo "MEDIUM_WEIGHT_FLEET: ENABLED (multi-source scanner lanes)"
else
  echo "MEDIUM_WEIGHT_FLEET: DISABLED by explicit configuration"
fi

if [ "$ONCE_ARG" = "--once" ]; then
  exec "$PYTHON3_BIN" scripts/runpod_lightweight_scanner.py \
    --once \
    --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE"
fi

if [ "${CHATGPT_SCANNER_ENABLED:-true}" = "true" ]; then
  (
    while true; do
      "$PYTHON3_BIN" scripts/chatgpt_medium_scanner_fleet.py >> logs/chatgpt_medium_scanner_fleet.out.log 2>&1
      sleep 5
    done
  ) &
  echo "CHATGPT_MEDIUM_SCANNER_FLEET: STARTED"
fi

if [ "${MEDIUM_WEIGHT_FLEET_ENABLED:-true}" = "true" ]; then
  exec ./scripts/start_lightweight_scanner_fleet.sh
fi

exec "$PYTHON3_BIN" scripts/runpod_lightweight_scanner.py \
  --interval-seconds "$INTERVAL_SECONDS" \
  --lane "primary" \
  --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE"
