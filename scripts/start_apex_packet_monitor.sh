#!/usr/bin/env bash
set -u

ROOT="/Users/raffaykal/AI BLUE CHIP STOCKS"
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
