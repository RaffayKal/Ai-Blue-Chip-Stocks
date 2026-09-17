#!/usr/bin/env python3
"""Regular-ChatGPT medium-weight scanner fleet.

This is analysis only. Workers inspect scanner-produced candidate lanes from
different tactical perspectives and write separate timestamped observations.
They cannot authorize, preview, or place broker orders.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "candidate_lanes"
FALLBACK_INPUT = ROOT / "data" / "current_candidate_envelope.json"
OUTPUT_DIR = ROOT / "data" / "chatgpt_medium_scanner_observations"
AGGREGATE = ROOT / "data" / "chatgpt_medium_scanner_fleet.json"

ROLES = (
    ("blue_chip_momentum", "Analyze blue-chip momentum and continuation across supplied lanes."),
    ("blue_chip_reversal", "Analyze blue-chip reversal risk and invalidation conditions."),
    ("crypto_momentum", "Analyze crypto momentum and 24/7 continuation across supplied lanes."),
    ("crypto_reversal", "Analyze crypto volatility and reversal risk across supplied lanes."),
    ("fundamentals_news", "Evaluate supplied fundamentals and news context only; do not invent missing facts."),
    ("multi_source_quality", "Check source freshness, agreement, spread, liquidity, and missing fields."),
    ("forward_projection", "Produce bounded future-window projections and explicit uncertainty."),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def inputs() -> list[dict]:
    paths = sorted(INPUT_DIR.glob("*.json"))
    values = [load(path) for path in paths]
    values = [value for value in values if value]
    if not values:
        value = load(FALLBACK_INPUT)
        values = [value] if value else []
    return values


def fingerprint(values: list[dict]) -> str:
    body = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("scanner result is not an object")
    return value


def text_values(value: object) -> list[str]:
    """Collect textual fields from SDK response objects without assuming a shape."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values: list[str] = []
        for child in value.values():
            values.extend(text_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(text_values(child))
        return values
    return []


def scan_once(client: OpenAI, model: str, role: str, instruction: str, lanes: list[dict], fp: str) -> dict:
    prompt = json.dumps({
        "role": role,
        "instruction": instruction,
        "candidate_lanes": lanes,
        "required_result": {
            "scanner_viable": "boolean",
            "candidate_decision": "BUY CANDIDATE|SELL CANDIDATE|WATCHLIST ONLY|NO ACTION",
            "projection": "object",
            "reason": "string",
            "missing_facts": "array",
        },
    }, sort_keys=True)
    session = client.beta.agents.sessions.create(
        environment={"type": "none"},
        agent={
            "model": model,
            "instructions": (
                "You are one regular ChatGPT medium-weight scanner in a market-analysis fleet. "
                "Use only supplied data. Do not invent quotes, timestamps, liquidity, or forecasts. "
                "Do not execute, preview, authorize, or request a trade. Never override deterministic gates. "
                "Return JSON only. scanner_viable must be false if required facts are missing, stale, or conflicting."
            ),
        },
        input=prompt,
    )
    items = client.beta.agents.sessions.items.list(session.id)
    texts = []
    for item in items:
        dumped = item.model_dump() if hasattr(item, "model_dump") else {}
        texts.extend(text_values(dumped))
    result = None
    for text in reversed(texts):
        if "scanner_viable" not in text:
            continue
        try:
            result = extract_json(text)
            break
        except (ValueError, json.JSONDecodeError):
            continue
    if result is None:
        raise RuntimeError("no parseable scanner JSON")
    if not isinstance(result.get("scanner_viable"), bool):
        raise ValueError("scanner_viable must be boolean")
    if result.get("candidate_decision") not in {"BUY CANDIDATE", "SELL CANDIDATE", "WATCHLIST ONLY", "NO ACTION"}:
        raise ValueError("invalid candidate_decision")
    return {
        "timestamp": now(),
        "role": role,
        "input_fingerprint": fp,
        "status": "OK",
        "execution_authority": False,
        **result,
    }


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("CHATGPT_MEDIUM_SCANNER_FLEET: OPENAI_API_KEY is unavailable")
    interval = max(30.0, float(os.environ.get("CHATGPT_MEDIUM_SCANNER_INTERVAL_SECONDS", "60")))
    model = os.environ.get("CHATGPT_MEDIUM_SCANNER_MODEL", "gpt-5.5")
    client = OpenAI()
    previous = ""
    while True:
        lanes = inputs()
        fp = fingerprint(lanes)
        if lanes and fp != previous:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            results = []
            with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
                futures = [pool.submit(scan_once, client, model, role, instruction, lanes, fp) for role, instruction in ROLES]
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = {"timestamp": now(), "status": "ERROR", "execution_authority": False, "error": type(exc).__name__}
                    results.append(result)
                    if result.get("role"):
                        atomic_write(OUTPUT_DIR / f"{result['role']}.json", result)
            atomic_write(AGGREGATE, {
                "timestamp": now(),
                "status": "OK" if results and all(item.get("status") == "OK" for item in results) else "PARTIAL_OR_ERROR",
                "worker_count": len(ROLES),
                "input_fingerprint": fp,
                "execution_authority": False,
                "workers": sorted(results, key=lambda item: item.get("role", "")),
            })
            previous = fp
        print("CHATGPT_MEDIUM_SCANNER_FLEET: ACTIVE", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
