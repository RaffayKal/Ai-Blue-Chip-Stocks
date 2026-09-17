#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_UID="$(id -u)"
if launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker" >/dev/null 2>&1; then
  launchctl bootout "gui/$TASK_UID/com.raffaykal.codex-execution-worker"
fi
if launchctl print "gui/$TASK_UID/com.raffaykal.codex-execution-worker-live" >/dev/null 2>&1; then
  launchctl bootout "gui/$TASK_UID/com.raffaykal.codex-execution-worker-live"
fi
for PID_FILE in "$ROOT/data/codex_packet_consumer_shadow.pid" "$ROOT/data/codex_packet_consumer_live.pid"; do
  if [ -f "$PID_FILE" ]; then
    PID="$(sed -n '1p' "$PID_FILE")"
    if kill -0 "$PID" 2>/dev/null; then kill -TERM "$PID" 2>/dev/null || true; fi
    rm -f "$PID_FILE"
  fi
done
echo "CONSUMER: INACTIVE"
