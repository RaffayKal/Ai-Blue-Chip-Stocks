---
description: Check Blue Chip Stocks APEX PRESTIGE runtime status without placing trades.
---

Check runtime status only.

Rules:
- Do not place trades.
- Do not print secrets.
- Verify scanner/supervisor process state.
- Verify status JSON freshness.
- Verify candidate envelope freshness.
- Report ACTIVE / WATCH_ONLY / FROZEN / BROKEN.

Commands:

pgrep -af run_blue_chip_watcher || true
pgrep -af runpod_lightweight_scanner || true
cat data/runpod_lightweight_scanner_status.json 2>/dev/null || true
cat data/current_candidate_envelope.json 2>/dev/null || true
