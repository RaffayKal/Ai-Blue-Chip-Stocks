#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${RUNPOD_SCANNER_INTERVAL_SECONDS:-1}"
SCANNER_LANES="${RUNPOD_SCANNER_LANES:-7}"
ONCE_ARG="${1:-}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

if [ "$ONCE_ARG" = "--once" ]; then
  exec python3 scripts/runpod_lightweight_scanner.py \
    --once \
    --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE"
fi

exec python3 scripts/runpod_lightweight_scanner.py \
  --interval-seconds "$INTERVAL_SECONDS" \
  --lane "primary" \
  --codex-heavy-state "FROZEN_UNTIL_VERIFIED_USAGE_AND_VIABILITY_GATES_TRUE"
