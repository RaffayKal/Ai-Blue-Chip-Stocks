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
import statistics
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from project_root import ROOT
import lane_synergy_engine as synergy_engine
import runpod_lightweight_scanner as scanner

SYNERGY_STATUS_PATH = ROOT / "data" / "fleet_synergy_status.json"
LANE_MANIFEST_PATH = ROOT / "data" / "fleet_lane_manifest.json"
SHARED_INPUT_CHANNELS = (
    "Robinhood_MCP_quote",
    "Alpaca_quote",
    "Coinbase_quote",
    "Binance_quote",
    "Kraken_quote",
    "CoinGecko_quote",
    "Polygon_Massive_equity_quote",
    "Twelve_Data_equity_quote",
    "Nasdaq_Data_Link_equity_quote",
    "ChatGPT_scanner_envelopes",
)


def lane_name_for(index):
    return "primary" if index == 1 else f"lane_{index}"


def worker_pool_size():
    # Real parallel work here is I/O-bound (small JSON reads/writes), so a
    # modest fixed pool services an arbitrary number of lanes without one
    # OS thread per lane.
    return min(64, max(8, (os.cpu_count() or 2) * 8))


def extract_net_opportunity(status):
    try:
        return status["projection"]["crypto"]["projection_scores"]["net_opportunity_score"]
    except (KeyError, TypeError):
        return None


async def run_lane(lane, codex_heavy_state, interval_seconds, once, executor, loop, stop_event, recent_results):
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
                status = await loop.run_in_executor(executor, scanner.scan_once, codex_heavy_state, lane)
                recent_results.append(
                    {
                        "lane": lane,
                        "timestamp_utc": status.get("timestamp_utc"),
                        "candidate_decision": status.get("candidate_decision"),
                        "scanner_viable": bool(status.get("scanner_viable")),
                        "net_opportunity_score": extract_net_opportunity(status),
                    }
                )
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


async def run_role_lane(symbol, role, lane_label, codex_heavy_state, interval_seconds, once, executor, loop, stop_event, recent_results):
    """Dedicated MATH/HISTORY/RESEARCH/TEMPORAL lane for one symbol, per
    rules/MULTI_LANE_SYNERGY_RESEARCH_LAW.md.

    Unlike the legacy generic lane, this is unlocked on purpose: with 700+
    lanes available, any number of lanes may be assigned to the same
    (symbol, role) pair (see lane_synergy_engine.role_assignment's
    wrap-around), running concurrently to sample the live feed at many
    distinct sub-second instants per interval. That is safe because
    lane_synergy_engine.append_history is idempotent against the
    underlying live price tick: concurrent lanes reading the same not-yet-
    updated price simply re-derive and re-write the same window, they
    never corrupt or duplicate it."""
    print(f"STARTED_SYNERGY_LANE: {lane_label} symbol={symbol} role={role}")
    while not stop_event.is_set():
        try:
            # Every lane runs the common scanner/micro-math cycle. The role
            # calculation is additive; it never replaces envelope production.
            status = await loop.run_in_executor(
                executor, scanner.scan_once, codex_heavy_state, lane_label
            )
            recent_results.append(
                {
                    "lane": lane_label,
                    "timestamp_utc": status.get("timestamp_utc"),
                    "candidate_decision": status.get("candidate_decision"),
                    "scanner_viable": bool(status.get("scanner_viable")),
                    "net_opportunity_score": extract_net_opportunity(status),
                }
            )
            await loop.run_in_executor(executor, synergy_engine.run_role, symbol, role)
        except Exception as exc:  # noqa: BLE001 - keep the lane alive
            print(f"SYNERGY_LANE_CYCLE_ERROR: lane={lane_label} symbol={symbol} role={role} error={exc!r}")
        if once:
            return
        wait_seconds = scanner.bounded_loop_interval(interval_seconds)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
        except asyncio.TimeoutError:
            pass


async def synergy_rollup_loop(symbols, interval_seconds, once, stop_event, executor, loop):
    """Periodically combine each symbol's four role outputs into one
    appreciation/depreciation forecast, then publish the fleet-wide
    rollup. Runs independently of individual role lane timing."""
    rollup_interval = min(max(interval_seconds * 2, 5.0), 60.0)
    while True:
        for symbol in symbols:
            await loop.run_in_executor(executor, synergy_engine.run_synergy, symbol)
        rollup = await loop.run_in_executor(executor, synergy_engine.run_rollup, symbols)
        print(
            "LANE_SYNERGY_ROLLUP: "
            f"symbols={rollup['symbols_tracked']} with_output={rollup['symbols_with_synergy_output']}"
        )
        if once:
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=rollup_interval)
        except asyncio.TimeoutError:
            pass


async def synergy_aggregator(recent_results, lane_count, interval_seconds, once, stop_event):
    """Publish one fleet-level consensus signal instead of N duplicate lane outputs.

    Every lane already computes the same 8-part forecast (continuation
    probability, reversal risk, net-opportunity score, etc.) from
    scan_once(); the actual redundancy problem was that 700 identical
    lanes reading the same shared snapshot never talked to each other.
    Because lanes are staggered ~1ms apart in one process, they sample the
    live incoming price stream at many distinct sub-second instants per
    interval. This turns that into a real signal: decision agreement
    across the fleet, how many lanes see a currently-viable setup, and the
    spread of the net-opportunity forecast across samples. Read-only —
    changes no gate, sizing input, or AUM value.
    """
    aggregate_interval = min(max(interval_seconds, 2.0), 30.0)
    while True:
        window = list(recent_results)
        if window:
            decisions = Counter(item["candidate_decision"] for item in window)
            execution_gate_decision, consensus_count = decisions.most_common(1)[0]
            viable_count = sum(1 for item in window if item["scanner_viable"])
            # A fleet with no currently viable lane is still actively
            # searching. Keep the old majority execution result separately so
            # reporting cannot turn a fail-closed execution outcome into a
            # false claim that discovery stopped.
            consensus_decision = (
                "LOOKING"
                if viable_count == 0
                else execution_gate_decision
            )
            discovery_state = (
                "LOOKING_FOR_VIABLE_CANDIDATES"
                if viable_count == 0
                else "VIABLE_CANDIDATE_PRESENT"
            )
            execution_consensus_decision = consensus_decision
            execution_gate_decision = consensus_decision
            execution_search_state = (
                "SCANNING_FOR_VIABLE_BUY_SELL_CANDIDATES"
                if viable_count == 0
                else "VIABLE_BUY_SELL_CANDIDATE_PRESENT"
            )
            scores = [item["net_opportunity_score"] for item in window if isinstance(item["net_opportunity_score"], (int, float))]
            payload = {
                "timestamp_utc": scanner.iso_now(),
                "fleet_size_configured": lane_count,
                "sample_count": len(window),
                "distinct_lanes_represented": len({item["lane"] for item in window}),
                "consensus_decision": consensus_decision,
                "execution_consensus_decision": execution_consensus_decision,
                "execution_gate_decision": execution_gate_decision,
                "execution_search_state": execution_search_state,
                "discovery_state": discovery_state,
                "agreement_ratio": round(consensus_count / len(window), 4),
                "viable_ratio": round(viable_count / len(window), 4),
                "net_opportunity_score_avg": round(statistics.fmean(scores), 3) if scores else None,
                "net_opportunity_score_min": round(min(scores), 3) if scores else None,
                "net_opportunity_score_max": round(max(scores), 3) if scores else None,
                "note": (
                    "Read-only fleet consensus/confirmation signal aggregated across "
                    "staggered lane samples. Not an execution authority; does not "
                    "change sizing, gates, or AUM."
                ),
            }
            scanner.write_json(SYNERGY_STATUS_PATH, payload)
            print(
                f"FLEET_SYNERGY: lanes={lane_count} samples={payload['sample_count']} "
                f"consensus={consensus_decision} execution={execution_consensus_decision} "
                f"gate={execution_gate_decision} "
                f"search={execution_search_state} "
                f"agreement={payload['agreement_ratio'] * 100:.1f}% "
                f"viable_ratio={payload['viable_ratio'] * 100:.1f}% "
                f"net_opportunity_avg={payload['net_opportunity_score_avg']}"
            )
        if once:
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=aggregate_interval)
        except asyncio.TimeoutError:
            pass


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

    recent_results = deque(maxlen=min(5000, max(200, lane_count * 3)))

    synergy_symbols = synergy_engine.synergy_symbols()
    # Reserve lane 1 for the primary scanner. It writes the global candidate
    # envelope/status consumed by Codex; assigning it to a role lane leaves
    # the fleet calculating while the status surface reports UNKNOWN.
    dedicated_synergy_lanes = min(
        max(0, lane_count - 1),
        synergy_engine.dedicated_role_lane_count(lane_count, synergy_symbols),
    )
    lane_manifest = {
        "timestamp_utc": scanner.iso_now(),
        "fleet_size_configured": lane_count,
        "lanes": [lane_name_for(index) for index in range(1, lane_count + 1)],
        "shared_input_channels": list(SHARED_INPUT_CHANNELS),
        "envelope_output": "data/current_candidate_envelope.json",
        "consensus_output": str(SYNERGY_STATUS_PATH.relative_to(ROOT)),
        "codex_viability_gate": "algorithms/candidate_envelope_gate.py",
        "robinhood_inspection": "Robinhood MCP only",
        "execution_authority": False,
        "note": "Every lane reads shared source artifacts and emits analysis only; Codex is the single viability gate.",
    }
    scanner.write_json(LANE_MANIFEST_PATH, lane_manifest)
    print(
        "FLEET_LANE_MANIFEST: "
        f"lanes={lane_count} channels={len(SHARED_INPUT_CHANNELS)} "
        "envelope_only=true execution_authority=false"
    )
    if dedicated_synergy_lanes:
        print(
            "MULTI_LANE_SYNERGY_RESEARCH_LAW: "
            f"dedicated_lanes={dedicated_synergy_lanes} symbols={len(synergy_symbols)} "
            f"roles={len(synergy_engine.ROLES)}"
        )

    tasks = []
    for index in range(1, lane_count + 1):
        lane = lane_name_for(index)
        assignment = None
        if index > 1 and index - 1 <= dedicated_synergy_lanes:
            assignment = synergy_engine.role_assignment(index - 1, synergy_symbols)
        if assignment is not None:
            symbol, role = assignment
            tasks.append(
                asyncio.create_task(
                    run_role_lane(
                        symbol,
                        role,
                        lane,
                        args.codex_heavy_state,
                        args.interval_seconds,
                        args.once,
                        executor,
                        loop,
                        stop_event,
                        recent_results,
                    )
                )
            )
        else:
            tasks.append(
                asyncio.create_task(
                    run_lane(
                        lane,
                        args.codex_heavy_state,
                        args.interval_seconds,
                        args.once,
                        executor,
                        loop,
                        stop_event,
                        recent_results,
                    )
                )
            )
        # Small stagger so lane_1..lane_N don't all queue file I/O in the
        # same instant against the fixed worker pool.
        await asyncio.sleep(0.001)

    if args.once:
        await asyncio.gather(*tasks)
        await synergy_aggregator(recent_results, lane_count, args.interval_seconds, True, stop_event)
        if dedicated_synergy_lanes:
            await synergy_rollup_loop(synergy_symbols, args.interval_seconds, True, stop_event, executor, loop)
        return

    aggregator_task = asyncio.create_task(
        synergy_aggregator(recent_results, lane_count, args.interval_seconds, False, stop_event)
    )
    background_tasks = [aggregator_task]
    if dedicated_synergy_lanes:
        background_tasks.append(
            asyncio.create_task(
                synergy_rollup_loop(synergy_symbols, args.interval_seconds, False, stop_event, executor, loop)
            )
        )
    await asyncio.gather(*tasks, *background_tasks)


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
