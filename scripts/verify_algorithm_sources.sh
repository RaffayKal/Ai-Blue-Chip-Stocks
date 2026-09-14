#!/usr/bin/env bash
set -u

ROOT="/Users/raffaykal/AI BLUE CHIP STOCKS"
MANIFEST="rules/algorithm_sources.json"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

python3 -m json.tool "$MANIFEST" >/dev/null || exit 1

python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
root = Path(manifest["root"])
failed = []

for relative_path in manifest.get("required_algorithm_files", []):
    path = root / relative_path
    if not path.is_file():
        failed.append(f"missing {relative_path}")
        continue
    if path.stat().st_size == 0:
        failed.append(f"empty {relative_path}")

if failed:
    print("ALGORITHM_SOURCES: NO ACTION")
    print("FAILED_CHECKS: " + ", ".join(failed))
else:
    print("ALGORITHM_SOURCES: VERIFIED")
    print(f"COUNT: {len(manifest.get('required_algorithm_files', []))}")
PY
