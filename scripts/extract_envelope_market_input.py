#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")


def fail(message: str) -> None:
    print("CODEX_STATE: DORMANT")
    print("VIABLE: false")
    print(f"FAILED_CHECKS: {message}")
    raise SystemExit(0)


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        fail(f"candidate envelope missing: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid candidate envelope json: {exc}")
    if not isinstance(payload, dict):
        fail("candidate envelope must be an object")
    return payload


def main() -> None:
    if Path.cwd() != ROOT:
        fail("command is not running inside AI BLUE CHIP STOCKS")
    if len(sys.argv) != 3:
        fail("usage: python3 scripts/extract_envelope_market_input.py <candidate_envelope.json> <output_market_input.json>")

    envelope_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    if ".." in output_path.parts:
        fail("output market input path must not contain parent traversal")
    if output_path.is_absolute() and not str(output_path).startswith("/private/tmp/"):
        fail("absolute output market input path must be under /private/tmp")

    envelope = load_json(envelope_path)
    market_input = envelope.get("market_input")
    if not isinstance(market_input, dict) or not market_input:
        fail("candidate envelope market_input missing")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(market_input, indent=2) + "\n", encoding="utf-8")
    print(f"ENVELOPE_MARKET_INPUT: {output_path}")


if __name__ == "__main__":
    main()
