#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:-rules/apex_packet_monitor.template.json}"
ONCE_ARG="${2:-}"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

./scripts/verify_environment.sh || exit 1

if [ "$ONCE_ARG" = "--once" ]; then
  exec python3 scripts/apex_prestige_supervisor.py --config "$CONFIG" --once
fi

exec python3 scripts/apex_prestige_supervisor.py --config "$CONFIG"
