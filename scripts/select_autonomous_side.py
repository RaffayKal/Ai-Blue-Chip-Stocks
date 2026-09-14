#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
USER_SETTINGS = ROOT / "rules" / "user_settings.json"


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        print(f"AUTONOMOUS_SIDE: NONE")
        print(f"FAILED_CHECKS: missing {path}")
        raise SystemExit(0)
    except json.JSONDecodeError as exc:
        print("AUTONOMOUS_SIDE: NONE")
        print(f"FAILED_CHECKS: invalid json: {exc}")
        raise SystemExit(0)
    if not isinstance(payload, dict):
        print("AUTONOMOUS_SIDE: NONE")
        print("FAILED_CHECKS: json must be an object")
        raise SystemExit(0)
    return payload


def main() -> None:
    if Path.cwd() != ROOT:
        print("AUTONOMOUS_SIDE: NONE")
        print("FAILED_CHECKS: command is not running inside AI BLUE CHIP STOCKS")
        raise SystemExit(0)
    if len(sys.argv) != 2:
        print("AUTONOMOUS_SIDE: NONE")
        print("FAILED_CHECKS: usage: python3 scripts/select_autonomous_side.py <candidate_envelope.json>")
        raise SystemExit(0)

    envelope = load_json(Path(sys.argv[1]))
    settings = load_json(USER_SETTINGS)
    decision = str(envelope.get("candidate_decision") or "").strip().upper()
    operations = settings.get("operations") if isinstance(settings.get("operations"), dict) else {}

    if decision == "BUY CANDIDATE":
        if operations.get("all_buys_paused") is True:
            print("AUTONOMOUS_SIDE: NONE")
            print("FAILED_CHECKS: buys paused by current operations mode")
            raise SystemExit(0)
        print("AUTONOMOUS_SIDE: BUY")
        raise SystemExit(0)

    if decision == "SELL CANDIDATE":
        print("AUTONOMOUS_SIDE: SELL")
        raise SystemExit(0)

    print("AUTONOMOUS_SIDE: NONE")
    print(f"FAILED_CHECKS: candidate_decision {decision or 'missing'} does not authorize buy/sell gate")


if __name__ == "__main__":
    main()
