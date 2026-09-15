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

exec ./scripts/start_apex_packet_monitor.sh "$CONFIG" "$ONCE_ARG"
