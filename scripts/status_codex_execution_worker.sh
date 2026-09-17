#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT/data/codex_packet_consumer_shadow.pid"
LIVE_PID_FILE="$ROOT/data/codex_packet_consumer_live.pid"
STATUS_FILE="$ROOT/data/codex_packet_consumer_status.json"
TASK_UID="$(id -u)"
if { launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker" >/dev/null 2>&1 || launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker-live" >/dev/null 2>&1 || { [ -f "$PID_FILE" ] && kill -0 "$(sed -n '1p' "$PID_FILE")" 2>/dev/null; } || { [ -f "$LIVE_PID_FILE" ] && kill -0 "$(sed -n '1p' "$LIVE_PID_FILE")" 2>/dev/null; }; }; then echo "CONSUMER: ACTIVE"; else echo "CONSUMER: INACTIVE"; fi
for name in INBOX PROCESSING PROCESSED REJECTED; do lower="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"; printf '%s_COUNT: %s\n' "$name" "$(find "$ROOT/data/codex_$lower" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"; done
if [ -f "$STATUS_FILE" ]; then
  python3 - "$STATUS_FILE" <<'PY'
import json, sys
data=json.load(open(sys.argv[1], encoding="utf-8"))
for key, label in (("last_packet","LAST_PACKET"),("last_decision","LAST_DECISION"),("last_error","LAST_ERROR"),("shadow_mode","SHADOW_MODE"),("robinhood_execution_path_available","ROBINHOOD_EXECUTION_PATH_AVAILABLE")):
    print(f"{label}: {data.get(key)}")
PY
else
  echo "LAST_PACKET: none"; echo "LAST_DECISION: none"; echo "LAST_ERROR: none"; echo "SHADOW_MODE: true"; echo "ROBINHOOD_EXECUTION_PATH_AVAILABLE: false"
fi
