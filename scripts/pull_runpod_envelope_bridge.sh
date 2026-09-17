#!/usr/bin/env bash
set -u

# Bridges the gap between "RunPod scans 24/7" and "the local Codex packet
# monitor sees it": RunPod and this local machine each run their own
# independent copy of the full scanner pipeline (same start_runpod_scanner_24_7.sh),
# each writing its own data/current_candidate_envelope.json. The local Codex
# packet monitor only ever reads the local file, so RunPod's remote scanning
# results never reached it -- two disconnected pipelines, not one chain.
#
# This periodically pulls RunPod's envelope over the existing read-only SSH
# path (same key/host used by report_runpod_runtime.sh) and promotes it into
# the local current_candidate_envelope.json only when it is genuinely fresher
# (by market_input.timestamp) than whatever is already there -- so whichever
# source (local Mac awake and scanning, or RunPod always-on) has the most
# current, already-ChatGPT-reinforced envelope is what Codex actually sees.
# Never mutates anything on the pod; read-only pull.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_ENVELOPE="$ROOT/data/current_candidate_envelope.json"
LOG="$ROOT/logs/pull_runpod_envelope_bridge.log"
KEY="${RUNPOD_SSH_KEY:-$HOME/runpod_codex_bridge}"
USER_HOST="${RUNPOD_SSH_USER_HOST:-e7iwfvficlyk6w-644117fc@ssh.runpod.io}"
REMOTE_ENVELOPE_PATH="${RUNPOD_REMOTE_ROOT:-/root/aibluechipstocks}/data/current_candidate_envelope.json"
POLL_INTERVAL_SECONDS="${RUNPOD_ENVELOPE_BRIDGE_INTERVAL_SECONDS:-15}"
BEGIN_MARKER="RUNPOD_ENVELOPE_BRIDGE_BEGIN"
END_MARKER="RUNPOD_ENVELOPE_BRIDGE_END"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  exit 1
fi

mkdir -p "$ROOT/data" "$ROOT/logs"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" | tee -a "$LOG"
}

pull_remote_envelope() {
  local remote_cmd
  remote_cmd="printf '%s\n' '$BEGIN_MARKER'; cat '$REMOTE_ENVELOPE_PATH' 2>/dev/null; printf '%s\n' '$END_MARKER'"
  printf '%s\nexit\n' "$remote_cmd" \
    | ssh -tt -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i "$KEY" "$USER_HOST" 2>/dev/null \
    | tr -d '\r' \
    | sed $'s/\033\\[[0-9;?]*[ -\/]*[@-~]//g' \
    | sed -n "/^${BEGIN_MARKER}\$/,/^${END_MARKER}\$/p" \
    | sed '1d;$d'
}

run_once() {
  if [ ! -r "$KEY" ]; then
    log "SKIP reason=ssh_key_unreadable"
    return
  fi
  local remote_tmp
  remote_tmp="$(mktemp "${TMPDIR:-/tmp}/runpod_envelope_bridge.XXXXXX")"
  pull_remote_envelope > "$remote_tmp"
  if [ ! -s "$remote_tmp" ]; then
    log "SKIP reason=empty_or_unreachable"
    rm -f "$remote_tmp"
    return
  fi
  python3 - "$LOCAL_ENVELOPE" "$remote_tmp" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

local_path, remote_path = sys.argv[1], sys.argv[2]
with open(remote_path, encoding="utf-8") as handle:
    remote_json = handle.read()
os.unlink(remote_path)

def parse_ts(value):
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

def envelope_timestamp(payload):
    if not isinstance(payload, dict):
        return None
    return parse_ts((payload.get("market_input") or {}).get("timestamp"))

try:
    remote = json.loads(remote_json)
except json.JSONDecodeError:
    print("SKIP reason=remote_json_invalid")
    raise SystemExit

try:
    local = json.loads(open(local_path, encoding="utf-8").read())
except (OSError, json.JSONDecodeError):
    local = None

remote_ts = envelope_timestamp(remote)
local_ts = envelope_timestamp(local)

if remote_ts is None:
    print("SKIP reason=remote_timestamp_missing")
    raise SystemExit

if local_ts is not None and local_ts >= remote_ts:
    print(f"SKIP reason=local_is_fresher_or_equal local={local_ts.isoformat()} remote={remote_ts.isoformat()}")
    raise SystemExit

tmp = local_path + f".{os.getpid()}.tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(remote, handle, indent=2, sort_keys=True)
    handle.write("\\n")
os.replace(tmp, local_path)
print(f"PROMOTED source=runpod remote={remote_ts.isoformat()} local_was={local_ts.isoformat() if local_ts else 'none'}")
PY
}

once="${1:-}"
while true; do
  result="$(run_once)"
  log "$result"
  if [ "$once" = "--once" ]; then
    exit 0
  fi
  sleep "$POLL_INTERVAL_SECONDS"
done
