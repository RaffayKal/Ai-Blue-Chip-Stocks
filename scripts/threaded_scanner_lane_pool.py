#!/usr/bin/env python3
"""Run many medium-weight scanner lanes as threads in a single process.

Running each lane as its own OS process (the previous model) costs one full
Python interpreter (~20-25MB RSS) per lane, which makes a 700-lane fanout
require 15-20GB of RAM for work that is almost entirely file I/O and light
JSON scoring. scan_once() in runpod_lightweight_scanner.py is a pure
function keyed only by lane name with no shared mutable state, so lanes can
run as threads instead: one interpreter, N lightweight workers.
"""
import argparse
import signal
import threading
import time
from pathlib import Path

from project_root import ROOT
import runpod_lightweight_scanner as scanner

STOP = threading.Event()


def lane_name_for(index):
    return "primary" if index == 1 else f"lane_{index}"


def run_lane(lane, codex_heavy_state, interval_seconds, once):
    lock = None
    if not once:
        lock_path = scanner.lane_paths(lane)[2]
        lock = scanner.acquire_lock(lock_path)
        if lock is None:
            print(f"LANE_DUPLICATE_BLOCKED: {lane}")
            return
    print(f"STARTED_MEDIUM_WEIGHT_SCANNER_LANE: {lane}")
    try:
        while not STOP.is_set():
            try:
                scanner.scan_once(codex_heavy_state, lane)
            except Exception as exc:  # noqa: BLE001 - keep the lane alive
                print(f"LANE_CYCLE_ERROR: lane={lane} error={exc!r}")
            if once:
                return
            STOP.wait(scanner.bounded_loop_interval(interval_seconds))
    finally:
        if lock is not None:
            lock.close()


def main():
    parser = argparse.ArgumentParser(description="Threaded medium-weight scanner lane pool.")
    parser.add_argument("--lanes", type=int, default=14)
    parser.add_argument("--interval-seconds", type=float, default=scanner.MAX_LOOP_INTERVAL_SECONDS)
    parser.add_argument("--codex-heavy-state", default="UNKNOWN_OR_FROZEN")
    parser.add_argument("--once", action="store_true", help="run a single cycle across all lanes and exit")
    args = parser.parse_args()

    if Path.cwd() != ROOT:
        print("RUNPOD_MEDIUM_WEIGHT_SCANNER: BLOCKED")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(1)

    lane_count = max(1, args.lanes)
    print(f"THREADED_LANE_POOL_SIZE: {lane_count}")

    def handle_signal(signum, frame):  # noqa: ARG001
        STOP.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    threads = []
    for index in range(1, lane_count + 1):
        lane = lane_name_for(index)
        thread = threading.Thread(
            target=run_lane,
            args=(lane, args.codex_heavy_state, args.interval_seconds, args.once),
            name=f"scanner-{lane}",
            daemon=True,
        )
        thread.start()
        threads.append(thread)
        # Stagger starts so lane_1..lane_N don't all hit the same files/APIs
        # in the same instant.
        time.sleep(0.02)

    if args.once:
        for thread in threads:
            thread.join()
        return

    try:
        while not STOP.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        STOP.set()
    for thread in threads:
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
