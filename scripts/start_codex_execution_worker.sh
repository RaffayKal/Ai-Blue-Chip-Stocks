#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKER_MODE="${WORKER_MODE:-shadow}"
if [ "$WORKER_MODE" != "shadow" ] && [ "$WORKER_MODE" != "live" ]; then echo "BLOCKED: WORKER_MODE must be shadow or live"; exit 1; fi
PID_FILE="$ROOT/data/codex_packet_consumer_$WORKER_MODE.pid"
LOG_FILE="$ROOT/logs/codex_packet_consumer_$WORKER_MODE.log"
PLIST="$ROOT/com.raffaykal.codex-execution-worker.plist"
LIVE_PLIST="$ROOT/com.raffaykal.codex-execution-worker-live.plist"
PYTHON3_BIN="${PYTHON3_BIN:-$(command -v python3 || true)}"

if [ "$(pwd)" != "$ROOT" ]; then echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."; exit 1; fi
if [ -z "$PYTHON3_BIN" ] || [ ! -x "$PYTHON3_BIN" ]; then echo "BLOCKED: python3 is not available."; exit 1; fi
for directory in data/codex_inbox data/codex_processing data/codex_processed data/codex_rejected logs; do mkdir -p "$ROOT/$directory"; done
TASK_UID="$(id -u)"
SHADOW_MODE="${SHADOW_MODE:-true}"
if [ "$WORKER_MODE" = "live" ]; then
  if [ "${AUTONOMOUS_LIVE_EXECUTION_ENABLED:-false}" != "true" ]; then echo "BLOCKED: set AUTONOMOUS_LIVE_EXECUTION_ENABLED=true explicitly"; exit 1; fi
  if [ "$SHADOW_MODE" = "true" ]; then echo "BLOCKED: live worker requires SHADOW_MODE=false"; exit 1; fi
else
  if [ "$SHADOW_MODE" != "true" ]; then echo "BLOCKED: shadow worker requires SHADOW_MODE=true"; exit 1; fi
fi
if [ "$WORKER_MODE" = "shadow" ] && launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker" >/dev/null 2>&1; then echo "CONSUMER: ACTIVE"; exit 0; fi
if [ -f "$PID_FILE" ] && kill -0 "$(sed -n '1p' "$PID_FILE")" 2>/dev/null; then echo "CONSUMER: ACTIVE"; exit 0; fi
if [ -f "$PID_FILE" ]; then rm -f "$PID_FILE"; fi

if [ ! -f "$PLIST" ]; then echo "BLOCKED: LaunchAgent plist is missing"; exit 1; fi
if [ "$WORKER_MODE" = "shadow" ]; then
  launchctl bootstrap "gui/$TASK_UID" "$PLIST"
  PID="$(launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker" | awk '/^[[:space:]]*pid = / {print $3; exit}')"
else
  if [ ! -f "$LIVE_PLIST" ]; then echo "BLOCKED: live LaunchAgent plist is missing"; exit 1; fi
  launchctl bootstrap "gui/$TASK_UID" "$LIVE_PLIST"
  PID="$(launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker-live" | awk '/^[[:space:]]*pid = / {print $3; exit}')"
fi
echo "CONSUMER: ACTIVE"
echo "PID: $PID"
echo "SHADOW_MODE: $([ "$WORKER_MODE" = "shadow" ] && echo true || echo false)"
