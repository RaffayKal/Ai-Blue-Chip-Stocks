#!/usr/bin/env python3
"""Run many medium-weight scanner lanes concurrently in a single process.

History of this file's approach, and why it changed twice:

1. One OS process per lane (the original design). Each lane is a full Python
   interpreter (~20-25MB RSS), so 700 lanes needs 15-20GB RAM. This OOM-killed
   the RunPod pod repeatedly at just 14 lanes on its 4GB allocation.

2. One OS thread per lane in a single process. scan_once() has no shared
   mutable state keyed on process identity, so this is safe, and 700 lanes
   measured ~34MB RSS total. But OS thread counts have a hard ceiling
   independent of RAM (observed: `RuntimeError: can't start new thread` at
   ~2048 threads on this machine) — so this does not scale past a few
   thousand lanes no matter how much memory is available.

3. This version: asyncio tasks (no OS thread per lane; a Task is a few KB of
   Python object, not an OS resource) driving a small, fixed-size
   ThreadPoolExecutor that actually performs the synchronous file I/O in
   scan_once(). Lane count and OS thread count are now decoupled, so lane
   count scales to tens of thousands limited only by memory and how much
   real work the CPU can get through, not by an OS ceiling.
"""
import argparse
import asyncio
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from project_root import ROOT
import runpod_lightweight_scanner as scanner


def lane_name_for(index):
    return "primary" if index == 1 else f"lane_{index}"


def worker_pool_size():
    # Real parallel work here is I/O-bound (small JSON reads/writes), so a
    # modest fixed pool services an arbitrary number of lanes without one
    # OS thread per lane.
    return min(64, max(8, (os.cpu_count() or 2) * 8))


async def run_lane(lane, codex_heavy_state, interval_seconds, once, executor, loop, stop_event):
    lock = None
    if not once:
        lock_path = scanner.lane_paths(lane)[2]
        lock = await loop.run_in_executor(executor, scanner.acquire_lock, lock_path)
        if lock is None:
            print(f"LANE_DUPLICATE_BLOCKED: {lane}")
            return
    print(f"STARTED_MEDIUM_WEIGHT_SCANNER_LANE: {lane}")
    try:
        while not stop_event.is_set():
            try:
                await loop.run_in_executor(executor, scanner.scan_once, codex_heavy_state, lane)
            except Exception as exc:  # noqa: BLE001 - keep the lane alive
                print(f"LANE_CYCLE_ERROR: lane={lane} error={exc!r}")
            if once:
                return
            wait_seconds = scanner.bounded_loop_interval(interval_seconds)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
            except asyncio.TimeoutError:
                pass
    finally:
        if lock is not None:
            lock.close()


async def async_main(args, executor):
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass  # signal handlers in the event loop require Unix

    lane_count = max(1, args.lanes)
    print(f"THREADED_LANE_POOL_SIZE: {lane_count}")

    tasks = []
    for index in range(1, lane_count + 1):
        lane = lane_name_for(index)
        tasks.append(
            asyncio.create_task(
                run_lane(lane, args.codex_heavy_state, args.interval_seconds, args.once, executor, loop, stop_event)
            )
        )
        # Small stagger so lane_1..lane_N don't all queue file I/O in the
        # same instant against the fixed worker pool.
        await asyncio.sleep(0.001)

    await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(description="Async medium-weight scanner lane pool.")
    parser.add_argument("--lanes", type=int, default=14)
    parser.add_argument("--interval-seconds", type=float, default=scanner.MAX_LOOP_INTERVAL_SECONDS)
    parser.add_argument("--codex-heavy-state", default="UNKNOWN_OR_FROZEN")
    parser.add_argument("--once", action="store_true", help="run a single cycle across all lanes and exit")
    args = parser.parse_args()

    if Path.cwd() != ROOT:
        print("RUNPOD_MEDIUM_WEIGHT_SCANNER: BLOCKED")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(1)

    executor = ThreadPoolExecutor(max_workers=worker_pool_size(), thread_name_prefix="scan")
    try:
        asyncio.run(async_main(args, executor))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
