#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$ROOT/data/runpod_runtime_report.json"
LOG="$ROOT/logs/runpod_runtime_report.log"
KEY="${RUNPOD_SSH_KEY:-$HOME/.ssh/runpod_ops}"
USER_HOST="${RUNPOD_SSH_USER_HOST:-e7iwfvficlyk6w-644117fc@ssh.runpod.io}"

mkdir -p "$ROOT/data" "$ROOT/logs"
timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ ! -r "$KEY" ]; then
  printf '{"timestamp":"%s","ssh":"UNAVAILABLE","reason":"SSH key not readable","execution_authority":false}\n' "$timestamp" > "$REPORT"
  exit 0
fi

remote='ROOT=/root/aibluechipstocks; printf "GIT_REV="; git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || true; printf "SCANNER="; pgrep -af "runpod_lightweight_scanner.py" >/dev/null && echo ACTIVE || echo INACTIVE; printf "CHATGPT_SCANNER="; pgrep -af "chatgpt_scanner_runtime.py" >/dev/null && echo ACTIVE || echo INACTIVE; printf "OPENAI_SDK="; python3 -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec(\"openai\") else 1)" >/dev/null 2>&1 && echo PRESENT || echo ABSENT; printf "OPENAI_KEY="; [ -n "${OPENAI_API_KEY:-}" ] && echo PRESENT || echo ABSENT; printf "SCANNER_VIABLE="; python3 - <<"PY"
import json
from pathlib import Path
try:
    value = json.loads((Path("/root/aibluechipstocks") / "data" / "runpod_lightweight_scanner_status.json").read_text())
    print(value.get("scanner_viable"))
except Exception:
    print("UNKNOWN")
PY'
output="$(ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i "$KEY" "$USER_HOST" "$remote" 2>&1)"
rc=$?
if [ "$rc" -ne 0 ]; then
  printf '{"timestamp":"%s","ssh":"FAILED","reason":"connection or authentication failed","execution_authority":false}\n' "$timestamp" > "$REPORT"
  printf '%s SSH_FAILED\n' "$timestamp" >> "$LOG"
  exit 0
fi

rev="$(printf '%s\n' "$output" | sed -n 's/^GIT_REV=//p' | head -1)"
scanner="$(printf '%s\n' "$output" | sed -n 's/^SCANNER=//p' | head -1)"
chatgpt="$(printf '%s\n' "$output" | sed -n 's/^CHATGPT_SCANNER=//p' | head -1)"
sdk="$(printf '%s\n' "$output" | sed -n 's/^OPENAI_SDK=//p' | head -1)"
key="$(printf '%s\n' "$output" | sed -n 's/^OPENAI_KEY=//p' | head -1)"
viable="$(printf '%s\n' "$output" | sed -n 's/^SCANNER_VIABLE=//p' | head -1)"
printf '{"timestamp":"%s","ssh":"PASS","git_revision":"%s","scanner":"%s","chatgpt_scanner":"%s","openai_sdk":"%s","openai_key":"%s","scanner_viable":"%s","execution_authority":false}\n' "$timestamp" "$rev" "$scanner" "$chatgpt" "$sdk" "$key" "$viable" > "$REPORT"
printf '%s SSH_PASS revision=%s scanner=%s chatgpt=%s viable=%s\n' "$timestamp" "$rev" "$scanner" "$chatgpt" "$viable" >> "$LOG"
