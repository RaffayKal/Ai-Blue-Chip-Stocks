#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "BLOCKED: command is not running inside AI BLUE CHIP STOCKS."
  echo "CURRENT_DIRECTORY: $(pwd)"
  exit 1
fi

echo "OK: running inside AI BLUE CHIP STOCKS"

if ! command -v python3 >/dev/null 2>&1; then
  echo "BLOCKED: python3 is not available."
  exit 1
fi

echo "OK: python3 command found"

required_files=(
  "AGENTS.md"
  "COMMANDS.md"
  "rules/MARKET_SESSION_RULES.md"
  "rules/CAPITAL_RULES.md"
  "rules/BROKERAGE_RULES.md"
  "rules/ROBINHOOD_RULES.md"
  "rules/AUTONOMOUS_EXECUTION_RULES.md"
  "rules/algorithm_sources.json"
  "rules/plugin_runtime_stack.json"
  "algorithms/CAPITAL_ALGORITHM.md"
  "scripts/extract_envelope_market_input.py"
  "scripts/select_autonomous_side.py"
  "scripts/codex_resource_governor.py"
  "scripts/apex_prestige_supervisor.py"
  "scripts/nightly_operations_report.py"
  "scripts/runpod_lightweight_scanner.py"
  "scripts/start_lightweight_scanner_fleet.sh"
  "scripts/start_runpod_scanner_24_7.sh"
  "algorithms/candidate_envelope_gate.py"
  "algorithms/autonomous_order_gate.py"
  "data/sample_qualified_candidate_envelope.json"
  "START_TODAY.md"
)

for file in "${required_files[@]}"; do
  if [ ! -f "$file" ]; then
    echo "BLOCKED: required file missing: $file"
    exit 1
  fi
done

echo "OK: required control files found"

# Legacy envelope bridges are forbidden: they create a second writer and can
# reintroduce stale broker requirements after deployment.
for forbidden in \
  "com.raffaykal.runpod-envelope-bridge.plist" \
  "scripts/pull_runpod_envelope_bridge.sh"; do
  if [ -e "$forbidden" ]; then
    echo "BLOCKED: deleted legacy envelope bridge is present: $forbidden"
    exit 1
  fi
done

required_provider_pattern='REQUIRED_CRYPTO_QUOTE_PROVIDERS[[:space:]]*=[[:space:]]*\(ROBINHOOD_FRONTLINE_PROVIDER,\)'
if command -v rg >/dev/null 2>&1; then
  provider_check=(rg -q "$required_provider_pattern" scripts/runpod_lightweight_scanner.py)
else
  provider_check=(grep -Eq "$required_provider_pattern" scripts/runpod_lightweight_scanner.py)
fi
if ! "${provider_check[@]}"; then
  echo "BLOCKED: Robinhood is not the sole required crypto quote provider."
  exit 1
fi

echo "OK: legacy envelope bridge absent; Robinhood is sole required crypto quote provider"

./scripts/verify_algorithm_sources.sh || exit 1
