#!/usr/bin/env python3
"""Keep the existing scanner service alive alongside vLLM on the named pod.

No broker orders are submitted by this supervisor. Deployment survives SSH
disconnects; the bootstrap image must restore it after a container reset.
"""

import fcntl
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "data" / "pod_scanner_supervisor_status.json"


def main():
    os.chdir(ROOT)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    lock = (ROOT / "data" / "pod_scanner_supervisor.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("SCANNER_SUPERVISOR_ALREADY_RUNNING", flush=True)
        return
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    env = os.environ.copy()
    # RunPod PID 1 owns container secrets; SSH shells need not inherit them.
    for item in Path("/proc/1/environ").read_bytes().split(b"\0"):
        name, sep, value = item.partition(b"=")
        if sep and name.decode() in {"OPENAI_API_KEY", "OPEN AI API KEY", "FINNHUB_API_KEY"}:
            target = "OPENAI_API_KEY" if name == b"OPEN AI API KEY" else name.decode()
            if value and not value.startswith(b"{{"):
                env.setdefault(target, value.decode())
    env.update({"RUNPOD_MEMORY_GB": "4", "RUNPOD_SCANNER_LANES": "70",
                "RUNPOD_MIN_MEDIUM_WEIGHT_LANES": "70", "RUNPOD_MAX_MEDIUM_WEIGHT_LANES": "70",
                "RUNPOD_SAFE_MEDIUM_WEIGHT_LANES": "70", "PYTHONUNBUFFERED": "1"})
    restarts = 0
    while not stopping:
        log_path = ROOT / "logs" / "pod_scanner_service.log"
        if log_path.exists() and log_path.stat().st_size > 10_000_000:
            log_path.replace(log_path.with_suffix(".previous.log"))
        with log_path.open("a") as log:
            process = subprocess.Popen(["bash", "scripts/start_runpod_scanner_24_7.sh"],
                                       env=env, stdout=log, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                while not stopping and process.poll() is None:
                    state = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                             "status": "RUNNING", "supervisor_pid": os.getpid(),
                             "scanner_pid": process.pid, "configured_lanes": 70,
                             "restart_count": restarts, "execution_authority": False}
                    temporary = STATUS.with_suffix(".tmp")
                    temporary.write_text(json.dumps(state, indent=2) + "\n")
                    temporary.replace(STATUS)
                    time.sleep(5)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        restarts += 1
        if not stopping:
            time.sleep(5)


if __name__ == "__main__":
    main()
