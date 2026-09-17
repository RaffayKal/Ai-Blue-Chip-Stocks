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
import ssl
import urllib.error
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "candidate_lanes"
FALLBACK_INPUT = ROOT / "data" / "current_candidate_envelope.json"
OUTPUT_DIR = ROOT / "data" / "chatgpt_medium_scanner_observations"
AGGREGATE = ROOT / "data" / "chatgpt_medium_scanner_fleet.json"


def load_local_environment() -> None:
    """Load non-printed local configuration when the launcher did not export it."""
    if os.environ.get("OPENAI_API_KEY"):
        return
    path = ROOT / ".env.local"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == "OPENAI_API_KEY" and value.strip():
                os.environ["OPENAI_API_KEY"] = value.strip().strip('"').strip("'")
                return
    except OSError:
        return

ROLES = (
    ("blue_chip_momentum", "Analyze blue-chip momentum and continuation across supplied lanes."),
    ("blue_chip_reversal", "Analyze blue-chip reversal risk and invalidation conditions."),
    ("crypto_momentum", "Analyze crypto momentum and 24/7 continuation across supplied lanes."),
    ("crypto_reversal", "Analyze crypto volatility and reversal risk across supplied lanes."),
    ("fundamentals_news", "Evaluate supplied fundamentals and news context only; do not invent missing facts."),
    ("multi_source_quality", "Check source freshness, agreement, spread, liquidity, and missing fields."),
    ("forward_projection", "Produce bounded future-window projections and explicit uncertainty."),
)

SCANNER_INSTRUCTIONS = (
    "You are one regular ChatGPT medium-weight scanner in a market-analysis fleet. "
    "Use only supplied data. Do not invent quotes, timestamps, liquidity, or forecasts. "
    "Evaluate factor-diverse evidence including value, momentum, quality, liquidity, "
    "spread, slippage, and fees where supplied. Treat source disagreement, missing data, "
    "and uncertain execution economics as reasons for WATCHLIST ONLY or NO ACTION. "
    "Do not claim guaranteed returns. Do not execute, preview, authorize, or request a trade. "
    "Never override deterministic gates. Return JSON only. scanner_viable must be false "
    "if required facts are missing, stale, or conflicting."
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


def call_responses_api(model: str, instructions: str, prompt: str) -> dict:
    api_key = os.environ["OPENAI_API_KEY"].strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is empty after trimming")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/responses",
        data=json.dumps({"model": model, "instructions": instructions, "input": prompt}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        context = ssl.create_default_context(cafile=certifi.where()) if certifi is not None else None
        with urllib.request.urlopen(request, timeout=45, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"OpenAI transport error: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("OpenAI response was not a JSON object")
    return payload


def scan_once(model: str, role: str, instruction: str, lanes: list[dict], fp: str) -> dict:
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
    response = call_responses_api(
        model,
        instructions=SCANNER_INSTRUCTIONS,
        prompt=prompt,
    )
    texts = text_values(response)
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


def deterministic_role_result(role: str, lanes: list[dict], fp: str, openai_error: str | None = None) -> dict:
    """Have RunPod's own already-computed deterministic scoring stand in for a
    ChatGPT role when the OpenAI API is unavailable (missing key, exhausted
    credits, transport error). RunPod's scanner already computes the medium8
    forward-projection (continuation/reversal/net-opportunity) for every
    candidate lane; most roles here are just a labeled view of numbers that
    already exist. This never invents data ChatGPT would have supplied that
    RunPod does not actually have (fundamentals/news narrative), and it is
    always labeled OK_DETERMINISTIC_FALLBACK, never "OK", so it is never
    mistaken for a real ChatGPT analysis.
    """
    lane = lanes[0] if lanes else {}
    projection = lane.get("projection") or {}
    crypto = projection.get("crypto") or {}
    blue_chips = projection.get("blue_chips") or {}
    crypto_scores = crypto.get("projection_scores") or {}
    blue_chip_scores = blue_chips.get("projection_scores") or {}
    scanner_viable = bool(lane.get("scanner_viable"))
    candidate_decision = lane.get("candidate_decision") or "NO ACTION"
    missing_facts: list[str] = []
    if not lane:
        missing_facts.append("no_candidate_lane_available")

    if role == "blue_chip_momentum":
        projection_out = {
            "continuation_probability": blue_chip_scores.get("continuation_probability"),
            "net_opportunity_score": blue_chip_scores.get("net_opportunity_score"),
        }
        reason = "RunPod deterministic fallback: blue-chip continuation/net-opportunity score from the scanner's own medium8 projection."
    elif role == "blue_chip_reversal":
        projection_out = {
            "reversal_risk_score": blue_chips.get("reversal_risk_score"),
            "stale_penalty_score": blue_chips.get("stale_penalty_score"),
        }
        reason = "RunPod deterministic fallback: blue-chip reversal-risk score from the scanner's own medium8 projection."
    elif role == "crypto_momentum":
        projection_out = {
            "continuation_probability": crypto_scores.get("continuation_probability"),
            "net_opportunity_score": crypto_scores.get("net_opportunity_score"),
        }
        reason = "RunPod deterministic fallback: crypto continuation/net-opportunity score from the scanner's own medium8 projection."
    elif role == "crypto_reversal":
        projection_out = {
            "reversal_risk_score": crypto.get("reversal_risk_score"),
            "stale_penalty_score": crypto.get("stale_penalty_score"),
        }
        reason = "RunPod deterministic fallback: crypto reversal-risk score from the scanner's own medium8 projection."
    elif role == "multi_source_quality":
        source_records = lane.get("required_sources") or []
        fresh_count = sum(1 for item in source_records if item.get("status") == "fresh")
        projection_out = {
            "fresh_source_count": fresh_count,
            "total_source_count": len(source_records),
            "source_conflict": (lane.get("market_input") or {}).get("source_conflict"),
        }
        reason = "RunPod deterministic fallback: source freshness/conflict read directly from the scanner's own quote quorum."
        if fresh_count == 0:
            scanner_viable = False
    elif role == "forward_projection":
        projection_out = {"crypto": crypto_scores, "blue_chips": blue_chip_scores}
        reason = "RunPod deterministic fallback: identical medium8 forward-projection math the scanner already computes every cycle."
    elif role == "fundamentals_news":
        projection_out = {}
        candidate_decision = "NO ACTION"
        scanner_viable = False
        missing_facts.append("fundamentals_and_news_narrative_unavailable_without_chatgpt")
        reason = (
            "RunPod has no fundamentals/news data source. This role cannot be "
            "deterministically substituted; reporting it honestly as unavailable "
            "rather than fabricating a narrative."
        )
    else:
        projection_out = {}
        scanner_viable = False
        missing_facts.append("no_deterministic_mapping_for_role")
        reason = "RunPod deterministic fallback: no mapping defined for this role."

    result = {
        "timestamp": now(),
        "role": role,
        "input_fingerprint": fp,
        "status": "OK_DETERMINISTIC_FALLBACK",
        "execution_authority": False,
        "scanner_viable": scanner_viable,
        "candidate_decision": candidate_decision,
        "projection": projection_out,
        "reason": reason,
        "missing_facts": missing_facts,
        "fallback_source": "RUNPOD_MEDIUM_WEIGHT_SCANNER_DETERMINISTIC",
    }
    if openai_error:
        result["openai_error"] = openai_error
    return result


def run_role(model: str, role: str, instruction: str, lanes: list[dict], fp: str, openai_available: bool) -> dict:
    if not openai_available:
        return deterministic_role_result(role, lanes, fp, openai_error="OPENAI_API_KEY unavailable")
    try:
        return scan_once(model, role, instruction, lanes, fp)
    except Exception as exc:
        detail = str(exc)
        configured_key = os.environ.get("OPENAI_API_KEY", "")
        if configured_key:
            detail = detail.replace(configured_key, "[REDACTED]")
            detail = detail.replace(configured_key.strip(), "[REDACTED]")
        return deterministic_role_result(role, lanes, fp, openai_error=f"{type(exc).__name__}: {detail[:500]}")


def main() -> None:
    # RunPod does the medium-scanner's job itself whenever ChatGPT is down
    # (missing key, exhausted credits, transport failure) rather than the
    # whole fleet process exiting or every role going to ERROR. Re-check the
    # key each cycle so the fleet automatically resumes real ChatGPT analysis
    # once billing/credits are restored, with no restart required.
    interval = max(30.0, float(os.environ.get("CHATGPT_MEDIUM_SCANNER_INTERVAL_SECONDS", "60")))
    model = os.environ.get("CHATGPT_MEDIUM_SCANNER_MODEL", "gpt-5.5")
    previous = ""
    while True:
        load_local_environment()
        openai_available = bool(os.environ.get("OPENAI_API_KEY"))
        lanes = inputs()
        fp = fingerprint(lanes)
        if lanes and fp != previous:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            results = []
            with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
                futures = {
                    pool.submit(run_role, model, role, instruction, lanes, fp, openai_available): role
                    for role, instruction in ROLES
                }
                for future in as_completed(futures):
                    role = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:  # noqa: BLE001 - keep the fleet alive
                        result = deterministic_role_result(role, lanes, fp, openai_error=f"{type(exc).__name__}: {exc}")
                    results.append(result)
                    if result.get("role"):
                        atomic_write(OUTPUT_DIR / f"{result['role']}.json", result)
            statuses = {item.get("status") for item in results}
            if statuses and statuses <= {"OK"}:
                overall_status = "OK"
            elif statuses and statuses <= {"OK", "OK_DETERMINISTIC_FALLBACK"}:
                overall_status = "OK_DETERMINISTIC_FALLBACK"
            else:
                overall_status = "PARTIAL_OR_ERROR"
            atomic_write(AGGREGATE, {
                "timestamp": now(),
                "status": overall_status,
                "openai_available": openai_available,
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
