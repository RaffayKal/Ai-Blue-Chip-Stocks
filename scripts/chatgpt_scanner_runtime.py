#!/usr/bin/env python3
"""RunPod-hosted ChatGPT scanner stage.

This process performs scanner-side projection/qualification only. It never
creates APEX packets, authorizes execution, calls Robinhood, or places orders.
The deterministic RunPod scanner remains the source of raw market artifacts;
this stage records the ChatGPT scanner result for the existing packet monitor.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "current_candidate_envelope.json"
OUTPUT = ROOT / "data" / "chatgpt_scanner_observation.json"
LOG = ROOT / "logs" / "chatgpt_scanner_runtime.jsonl"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def log(event: str, **fields: object) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": iso_now(), "event": event, **fields}, sort_keys=True) + "\n")


def stable_input(value: dict) -> str:
    market = value.get("market_input", {})
    selected = {k: market.get(k) for k in ("symbol", "asset_class", "venue", "bid", "ask", "last", "source_count", "data_status", "risk_status", "scanner_viable")}
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("agent result is not an object")
    return value


def text_values(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            found.extend(text_values(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(text_values(child))
    return found


def run_once(client: OpenAI, model: str) -> None:
    envelope = load(INPUT)
    if not envelope:
        atomic_write(OUTPUT, {"timestamp": iso_now(), "status": "NO_INPUT", "execution_authority": False})
        return
    fingerprint = stable_input(envelope)
    previous = load(OUTPUT)
    if previous.get("input_fingerprint") == fingerprint:
        return
    prompt = json.dumps({
        "candidate_envelope": envelope,
        "task": "Perform scanner-side projections and qualification only.",
        "required_result": {"scanner_viable": "boolean", "candidate_decision": "BUY CANDIDATE|SELL CANDIDATE|WATCHLIST ONLY|NO ACTION", "projection": "object", "reason": "string"},
    }, sort_keys=True)
    session = client.beta.agents.sessions.create(
        environment={"type": "none"},
        agent={
            "model": model,
            "instructions": "You are the ChatGPT scanner layer for AI BLUE CHIP STOCKS. Use only supplied data. Do not execute, preview, authorize, or request any trade. Never override deterministic gates. Return JSON only with scanner_viable, candidate_decision, projection, and reason.",
        },
        input=prompt,
    )
    items = client.beta.agents.sessions.items.list(session.id)
    texts: list[str] = []
    for item in items:
        dumped = item.model_dump() if hasattr(item, "model_dump") else {}
        texts.extend(text_values(dumped))
    if not texts:
        raise RuntimeError("Agents API returned no scanner result")
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
        raise RuntimeError("Agents API returned no parseable scanner JSON")
    if not isinstance(result.get("scanner_viable"), bool):
        raise ValueError("scanner_viable must be boolean")
    if result.get("candidate_decision") not in {"BUY CANDIDATE", "SELL CANDIDATE", "WATCHLIST ONLY", "NO ACTION"}:
        raise ValueError("invalid candidate_decision")
    atomic_write(OUTPUT, {"timestamp": iso_now(), "status": "OK", "execution_authority": False, "input_fingerprint": fingerprint, "model": model, **result})
    log("observation_written", decision=result["candidate_decision"], scanner_viable=result["scanner_viable"])


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("CHATGPT_SCANNER: OPENAI_API_KEY is unavailable")
    interval = max(30.0, float(os.environ.get("CHATGPT_SCANNER_INTERVAL_SECONDS", "60")))
    model = os.environ.get("CHATGPT_SCANNER_MODEL", "gpt-5.5")
    client = OpenAI()
    while True:
        try:
            run_once(client, model)
            print("CHATGPT_SCANNER: ACTIVE", flush=True)
        except Exception as exc:
            log("error", error=f"{type(exc).__name__}: {exc}")
            print(f"CHATGPT_SCANNER: ERROR: {type(exc).__name__}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
