#!/usr/bin/env python3
import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from project_root import ROOT

CONFIG = ROOT / "rules" / "apex_packet_monitor.template.json"
LOCK = ROOT / "data" / "apex_prestige_supervisor.lock"
STATUS = ROOT / "data" / "apex_prestige_supervisor_status.json"
LOG = ROOT / "logs" / "apex_prestige_supervisor.jsonl"
ARCHITECTURE_NAME = "ABSOLUTE INFINITE +775% TACTICAL APPRECIATION OPERATIONS COMPOUNDING — APEX PRESTIGE ARCHITECTURE"


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def log(event, **fields):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp_utc": iso_now(), "architecture": ARCHITECTURE_NAME, "event": event, **fields}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def run_command(args):
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return result.returncode, result.stdout


def load_interval(config_path):
    config = read_json(config_path)
    return float(config.get("loop", {}).get("interval_seconds", 300))


def acquire_lock():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open("w", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(str(__import__("os").getpid()))
    handle.flush()
    return handle


def supervisor_once(config_path):
    gov_code, gov_output = run_command([sys.executable, "scripts/codex_resource_governor.py"])
    frozen = "SYSTEM_STATE: FROZEN" in gov_output.splitlines()
    if frozen:
        scan_code, scan_output = run_command([
            sys.executable,
            "scripts/runpod_lightweight_scanner.py",
            "--once",
            "--codex-heavy-state",
            "FROZEN",
        ])
        status = {
            "timestamp_utc": iso_now(),
            "architecture": ARCHITECTURE_NAME,
            "supervisor_state": "RUNPOD_SCANNER_ACTIVE_CODEX_HEAVY_FROZEN",
            "operations_active": True,
            "runpod_lightweight_scanner_active": True,
            "codex_heavy_operations_active": False,
            "zero_market_operations": False,
            "zero_trade_execution": True,
            "pre_pause_execution_survives": False,
            "last_governor_exit": gov_code,
            "last_scanner_exit": scan_code,
        }
        write_json(STATUS, status)
        log("codex_heavy_frozen_scanner_active", governor_exit=gov_code, scanner_exit=scan_code, governor_output=gov_output, scanner_output=scan_output)
        print(gov_output, end="")
        print(scan_output, end="")
        print("APEX_PRESTIGE_SUPERVISOR: RUNPOD_SCANNER_ACTIVE_CODEX_HEAVY_FROZEN")
        print("HEAVY_ACTION: NO ACTION")
        return "RUNPOD_SCANNER_ACTIVE_CODEX_HEAVY_FROZEN"

    scan_code, scan_output = run_command([
        sys.executable,
        "scripts/runpod_lightweight_scanner.py",
        "--once",
        "--codex-heavy-state",
        "ASLEEP_HEALTH_CHECK_ONLY",
    ])
    status = {
        "timestamp_utc": iso_now(),
        "architecture": ARCHITECTURE_NAME,
        "supervisor_state": "LIGHT_HEALTH_CHECK_ONLY",
        "operations_active": True,
        "runpod_lightweight_scanner_active": True,
        "codex_heavy_operations_active": False,
        "apex_heavy_monitor_active": False,
        "health_check_only": True,
        "health_check_cadence": "EVERY_SUPERVISOR_LOOP_AND_AT_LEAST_HOURLY",
        "hourly_check_requirement": "SATISFIED_BY_4_SECOND_SUPERVISOR_LOOP",
        "repair_policy": "RERUN_GATES_AND_RESTART_SCANNER_ON_FAILURE; NEVER_GRANT_EXECUTION_FROM_HEALTH_CHECK",
        "hourly_operations_report": "ACTIVE",
        "hourly_operations_actions": ["REPORT", "CHECK", "FIX_SAFE_RUNTIME_FAILURES", "REINFORCE_GATES", "CONTINUE_24_7"],
        "night_report_required": True,
        "zero_market_operations": False,
        "monitor_interval_seconds": load_interval(config_path),
        "wrapper_restart_interval_seconds": None,
        "pre_pause_execution_survives": False,
        "live_market_data_refresh_required_before_viable": True,
        "all_apex_gates_rerun_before_resume": True,
        "last_governor_exit": gov_code,
        "last_scanner_exit": scan_code,
        "last_monitor_exit": None,
    }
    write_json(STATUS, status)
    log("light_health_check_only", governor_exit=gov_code, scanner_exit=scan_code, scanner_output=scan_output)
    print(gov_output, end="")
    print(scan_output, end="")
    print("APEX_PRESTIGE_SUPERVISOR: LIGHT_HEALTH_CHECK_ONLY")
    print("HEAVY_ACTION: NO ACTION")
    return "LIGHT_HEALTH_CHECK_ONLY"


def main():
    parser = argparse.ArgumentParser(description=ARCHITECTURE_NAME)
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if Path.cwd() != ROOT:
        print("APEX_PRESTIGE_SUPERVISOR: BLOCKED")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(1)

    lock = acquire_lock()
    if lock is None:
        print("APEX_PRESTIGE_SUPERVISOR: DUPLICATE_BLOCKED")
        print(f"LOCK_FILE: {LOCK}")
        raise SystemExit(0)

    config_path = Path(args.config)
    interval = load_interval(config_path)
    log("started", config=str(config_path), interval_seconds=interval, once=args.once)
    if args.once:
        supervisor_once(config_path)
        return

    while True:
        supervisor_once(config_path)
        time.sleep(interval)


if __name__ == "__main__":
    main()
