#!/usr/bin/env python3
import json
import shutil
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

SETTINGS = ROOT / "rules" / "user_settings.json"
SNAPSHOT_DIR = ROOT / "data" / "atomic_snapshots"
STATE_LOG = ROOT / "logs" / "codex_resource_governor.jsonl"
RUNTIME_STATE = ROOT / "data" / "apex_prestige_runtime_state.json"
LIVE_USAGE_STATUS = ROOT / "data" / "codex_usage_status.json"
STALE_SIGNAL_DIR = ROOT / "data" / "stale_signals"
FREEZE_THRESHOLD_PERCENT = 2.0
LIVE_USAGE_MAX_AGE_SECONDS = 600
ARCHITECTURE_NAME = "ABSOLUTE INFINITE +775% TACTICAL APPRECIATION OPERATIONS COMPOUNDING — APEX PRESTIGE ARCHITECTURE"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value):
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def age_seconds(value):
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds()


def emit(line):
    print(line)


def write_log(record):
    STATE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with STATE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def read_usage(settings):
    operations = settings.get("operations", {})
    env_verified = os.environ.get("CODEX_USAGE_VERIFIED")
    env_remaining = os.environ.get("CODEX_USAGE_REMAINING_PERCENT")
    if env_verified is not None or env_remaining is not None:
        verified = str(env_verified or "").strip().lower() in {"1", "true", "yes", "verified"}
        remaining = env_remaining
        source = "environment"
    elif LIVE_USAGE_STATUS.exists():
        try:
            usage = load_json(LIVE_USAGE_STATUS)
        except (OSError, json.JSONDecodeError):
            usage = {}
        timestamp = usage.get("timestamp_utc")
        usage_age = age_seconds(timestamp)
        if usage_age is not None and 0 <= usage_age <= LIVE_USAGE_MAX_AGE_SECONDS:
            verified = usage.get("codex_usage_verified") is True
            remaining = usage.get("codex_usage_remaining_percent")
            source = "data/codex_usage_status.json"
        else:
            verified = operations.get("codex_usage_verified")
            remaining = operations.get("codex_usage_remaining_percent")
            source = "rules/user_settings.json_stale_fallback"
    else:
        verified = operations.get("codex_usage_verified")
        remaining = operations.get("codex_usage_remaining_percent")
        source = "rules/user_settings.json_stale_fallback"
    return verified, remaining, source


def runtime_state():
    if not RUNTIME_STATE.exists():
        return {}
    try:
        return load_json(RUNTIME_STATE)
    except (OSError, json.JSONDecodeError):
        return {}


def snapshot(reason, settings):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = SNAPSHOT_DIR / f"{timestamp}_frozen_snapshot"
    target.mkdir(parents=True, exist_ok=True)

    for rel in (
        "rules/user_settings.json",
        "data/current_candidate_envelope.json",
        "data/apex_packet_monitor_health.json",
        "data/autonomous_execution_log.json",
    ):
        src = ROOT / rel
        if src.exists() and src.is_file():
            dst = target / rel.replace("/", "__")
            shutil.copy2(src, dst)

    manifest = {
        "architecture": ARCHITECTURE_NAME,
        "timestamp_utc": iso_now(),
        "system_state": "FROZEN",
        "reason": reason,
        "codex_usage_remaining_percent": settings.get("operations", {}).get("codex_usage_remaining_percent"),
        "codex_usage_verified": settings.get("operations", {}).get("codex_usage_verified"),
        "zero_heavy_market_operations": True,
        "runpod_medium_weight_scanner_active": True,
        "resume_requires": [
            "verified usage reset above 2 percent",
            "restore state from snapshot only if still current",
            "refresh live market data",
            "destroy stale signals",
            "rebuild candidates",
            "rerun every APEX gate",
            "reject or watch unless viable is true",
        ],
    }
    (target / "snapshot_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def invalidate_stale_signals(reason):
    stale = []
    STALE_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for rel in (
        "data/current_candidate_envelope.json",
        "data/apex_packet_monitor_state.json",
    ):
        src = ROOT / rel
        if src.exists() and src.is_file():
            dst = STALE_SIGNAL_DIR / f"{timestamp}_{rel.replace('/', '__')}"
            shutil.copy2(src, dst)
            stale.append({"from": str(src), "to": str(dst)})
            if rel == "data/current_candidate_envelope.json":
                write_json(src, {
                    "invalidated_at": iso_now(),
                    "invalidated_by": "CODEX_RESOURCE_GOVERNOR",
                    "reason": reason,
                    "scanner_viable": False,
                    "requested_codex_activation": False,
                    "plugins_execute_trades": False,
                    "broker_order_submitted": False,
                    "candidate_decision": "NO ACTION",
                    "viable": False,
                    "stale_signal_destroyed": True,
                    "architecture": ARCHITECTURE_NAME,
                })
            else:
                write_json(src, {
                    "emitted_idempotency_keys": [],
                    "last_emit_at": None,
                    "consecutive_transport_failures": 0,
                    "circuit_open_until": None,
                    "stale_signal_destroyed_at": iso_now(),
                })
    return stale


def freeze(reason, settings):
    snap = snapshot(reason, settings)
    stale = invalidate_stale_signals(reason)
    record = {
        "timestamp_utc": iso_now(),
        "architecture": ARCHITECTURE_NAME,
        "system_state": "FROZEN",
        "reason": reason,
        "snapshot": str(snap),
        "stale_signals_destroyed": stale,
        "zero_heavy_market_operations": True,
        "runpod_medium_weight_scanner_active": True,
    }
    write_json(RUNTIME_STATE, record)
    write_log(record)
    emit(f"ARCHITECTURE: {ARCHITECTURE_NAME}")
    emit("SYSTEM_STATE: FROZEN")
    emit("CODEX_RESOURCE_GOVERNOR: BLOCKED")
    emit(f"FAILED_CHECKS: {reason}")
    emit(f"ATOMIC_SNAPSHOT: {snap}")
    emit("STALE_SIGNALS_DESTROYED: true")
    emit("ZERO_HEAVY_MARKET_OPERATIONS: true")
    emit("RUNPOD_MEDIUM_WEIGHT_MARKET_OPERATIONS: ACTIVE")
    emit("RUNPOD_MARKET_SCANNING: ACTIVE_MEDIUM_WEIGHT_24_7")
    emit("RUNPOD_CALCULATIONS: ACTIVE_MEDIUM_WEIGHT_24_7")
    emit("RUNPOD_PROJECTIONS: ACTIVE_MEDIUM_WEIGHT_24_7")
    emit("APEX_QUALIFICATION: MEDIUM_WEIGHT_ONLY")
    emit("CANDIDATE_GENERATION: MEDIUM_WEIGHT_ONLY")
    emit("CONNECTOR_MARKET_ANALYSIS: PAUSED")
    emit("TRADE_ANALYSIS: PAUSED")
    emit("EXECUTION_REQUESTS: PAUSED")
    emit("COMPOUNDING_ACTIONS: PAUSED")
    emit("QUEUED_EXECUTION: PAUSED")
    emit("CODEX_HEAVY_OPERATIONS: FROZEN")
    emit("NEXT_ALLOWED_STEP: keep Runpod medium-weight scanner alive; wait for verified reset above 2 percent before Codex-heavy wakeups; refresh live market data; destroy stale signals; rebuild candidates; rerun every APEX gate")
    return 0


def main():
    if Path.cwd() != ROOT:
        emit("SYSTEM_STATE: FROZEN")
        emit("CODEX_RESOURCE_GOVERNOR: BLOCKED")
        emit("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        emit("ZERO_HEAVY_MARKET_OPERATIONS: true")
        emit("RUNPOD_MEDIUM_WEIGHT_MARKET_OPERATIONS: ACTIVE")
        return 0

    if not SETTINGS.exists():
        emit("SYSTEM_STATE: FROZEN")
        emit("CODEX_RESOURCE_GOVERNOR: BLOCKED")
        emit("FAILED_CHECKS: user_settings.json missing; telemetry unknown")
        emit("ZERO_HEAVY_MARKET_OPERATIONS: true")
        emit("RUNPOD_MEDIUM_WEIGHT_MARKET_OPERATIONS: ACTIVE")
        return 0

    settings = load_json(SETTINGS)
    operations = settings.get("operations", {})
    verified, remaining, usage_source = read_usage(settings)
    paused = operations.get("pause_all_operations") is True
    mode = str(operations.get("mode") or "").upper()
    state = str(operations.get("system_state") or "").upper()

    if paused or mode == "FROZEN" or state == "FROZEN":
        return freeze("operations configured frozen", settings)

    if verified is not True or remaining is None:
        return freeze("telemetry unknown", settings)

    try:
        remaining_float = float(remaining)
    except (TypeError, ValueError):
        return freeze("codex usage remaining is not numeric", settings)

    if remaining_float <= FREEZE_THRESHOLD_PERCENT:
        return freeze("codex usage remaining less than or equal to 2 percent", settings)

    prior = runtime_state()
    resumed_after_freeze = prior.get("system_state") == "FROZEN"
    record = {
        "timestamp_utc": iso_now(),
        "architecture": ARCHITECTURE_NAME,
        "system_state": "ACTIVE",
        "codex_usage_remaining_percent": remaining_float,
        "codex_usage_verified": True,
        "codex_usage_source": usage_source,
        "resumed_after_freeze": resumed_after_freeze,
        "resume_requirements_enforced": [
            "stale Codex activation signals destroyed",
            "live market data must be refreshed by Runpod scanner before viable envelope",
            "candidates must be rebuilt",
            "all APEX gates must rerun",
            "pre-pause execution is invalid",
        ],
    }
    write_json(RUNTIME_STATE, record)
    write_log(record)
    emit(f"ARCHITECTURE: {ARCHITECTURE_NAME}")
    emit("SYSTEM_STATE: ACTIVE")
    emit("CODEX_RESOURCE_GOVERNOR: PASS")
    emit(f"CODEX_USAGE_REMAINING_PERCENT: {remaining_float}")
    emit(f"CODEX_USAGE_SOURCE: {usage_source}")
    emit("PRE_PAUSE_EXECUTION_SURVIVES: false")
    emit("RUNPOD_MARKET_SCANNING: ACTIVE_MEDIUM_WEIGHT_24_7")
    emit("RESUME_REQUIRES_FRESH_MARKET_DATA_AND_ALL_APEX_GATES: true")
    emit("NEXT_ALLOWED_STEP: continue only through live-data and APEX gates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
