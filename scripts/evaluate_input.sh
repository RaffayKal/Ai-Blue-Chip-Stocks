#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$(pwd)" != "$ROOT" ]; then
  echo "RESULT: NO ACTION"
  echo "FAILED_CHECKS: wrong working directory"
  exit 1
fi

SYMBOL="${1:-}"
ASSET_CLASS="${2:-UNKNOWN}"
SESSION="${3:-UNKNOWN}"
DATA_STATUS="${4:-missing}"
RISK_STATUS="${5:-needs settings}"

failed=()

if [ -z "$SYMBOL" ]; then
  failed+=("missing symbol")
fi

case "$ASSET_CLASS" in
  CRYPTO|US_EQUITY|ETF|OPTION|FUND) ;;
  *) failed+=("unknown asset class") ;;
esac

case "$SESSION" in
  PRE_MARKET|REGULAR|AFTER_HOURS|OVERNIGHT|HOLIDAY|HALTED|CLOSED|UNKNOWN|CRYPTO_24_7) ;;
  *) failed+=("invalid session label") ;;
esac

if [ "$SESSION" = "UNKNOWN" ] || [ "$SESSION" = "CLOSED" ] || [ "$SESSION" = "HALTED" ] || [ "$SESSION" = "HOLIDAY" ]; then
  failed+=("unsupported or inactive session")
fi

if [ "$DATA_STATUS" != "fresh" ]; then
  failed+=("data not fresh")
fi

if [ "$RISK_STATUS" != "pass" ]; then
  failed+=("risk not passed")
fi

if [ "${#failed[@]}" -gt 0 ]; then
  echo "RESULT: NO ACTION"
else
  echo "RESULT: VALIDATED SETUP"
fi

echo "SYMBOL: ${SYMBOL:-missing}"
echo "ASSET_CLASS: $ASSET_CLASS"
echo "SESSION: $SESSION"
echo "DATA_STATUS: $DATA_STATUS"
echo "RISK_STATUS: $RISK_STATUS"
echo "FAILED_CHECKS: ${failed[*]:-none}"
