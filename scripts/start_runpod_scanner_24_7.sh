#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-7}"
SCANNER_LANES="${RUNPOD_SCANNER_LANES:-7}"
ONCE_ARG="${1:-}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

if [ "${ALPACA_ADAPTER_REST_PREFLIGHT:-false}" = "true" ]; then
  python3 scripts/alpaca_market_data_adapter.py --rest-once || exit 1
fi

if [ "${ALPACA_STREAM_MARKET_DATA:-true}" = "true" ]; then
  python3 scripts/stream_alpaca_market_data.py &
fi

if [ "${COINGECKO_STREAM_MARKET_DATA:-true}" = "true" ]; then
  python3 scripts/stream_coingecko_market_data.py &
fi

if [ "${ROBINHOOD_STREAM_MARKET_DATA:-false}" = "true" ]; then
  python3 scripts/stream_robinhood_market_data.py &
fi

if [ "${MEDIUM_SCANNER_ENABLED:-true}" = "true" ]; then
  SCAN_INTERVAL_SECONDS="${MEDIUM_SCANNER_INTERVAL_SECONDS:-7}" python3 scripts/medium_market_orchestrator.py &
fi

if [ "$ONCE_ARG" = "--once" ]; then
  exec python3 scripts/runpod_lightweight_scanner.py \
    --once \
    --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE"
fi

exec python3 scripts/runpod_lightweight_scanner.py \
  --interval-seconds "$INTERVAL_SECONDS" \
  --lane "primary" \
  --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE"
