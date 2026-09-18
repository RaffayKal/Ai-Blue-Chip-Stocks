# APEX AGENTIC TRADING ENGINE

This is the governing investing/trading code for every scanner, envelope,
capital, APEX, RunPod, Codex, and Robinhood workflow.

Fractional spot, micro-purchase, AUM, governance, and execution details are
defined by `rules/APEX_MICRO_CRYPTO_UNIT_LEDGER.md` and the user-supplied APEX
Fractional Spot Trading specification. Those controls are mandatory for every
micro-purchase candidate.

## Authority

Predictions, scores, simulations, forecasts, and projections are inputs only.
Only a fresh, reconciled, broker-valid APEX envelope can authorize execution.

## Required state machine

`OBSERVE -> NORMALIZE -> VALIDATE_FRESHNESS -> BUILD_FEATURES -> FORECAST_SCENARIOS -> CALCULATE_EDGE -> SIZE_BY_LOSS -> RUN_APEX_GATES -> CREATE_CANDIDATE_ENVELOPE -> HUMAN_OR_POLICY_REVIEW -> PREVIEW_ORDER -> PLACE_ONLY_IF_AUTHORIZED -> QUERY_ORDER_STATUS -> RECONCILE_FILL_AND_COST -> UPDATE_AUM_AND_FLOOR -> AUDIT_LOG`

## Governing controls

- WebSocket/live events are primary; REST is bounded fallback, reconciliation,
  account verification, quota/heartbeat, and recovery only.
- Validate symbol, source, bid, ask, last, trade size, event/receive time,
  sequence, session, and `LIVE|PAPER|SAMPLE|UNKNOWN` mode. Reject stale,
  duplicated, backward, unknown, sample, contradictory, or incompatible data.
- Use Decimal or integer fixed-point accounting. `q = $0.00000007` is ledger
  precision only; broker minimums, tick size, asset precision, settlement, and
  routing control executable orders.
- Deployable capital is settled equity less protected reserve, tax reserve, and
  pending reservations. Unrealized P/L, deposits, forecasts, and paper trades
  do not create performance or floors.
- Size from maximum tolerable loss, invalidation distance, liquidity, position
  caps, and deployable capital. Reject non-positive risk, invalid stops,
  insufficient notional, or edge that does not exceed total expected cost.
- `VIABLE` requires fresh quorum, no conflict, account reconciliation, settled
  cash, numeric notional, risk pass, duplicate clearance, daily-loss pass,
  broker permission, positive net edge, and broker minimum compliance.
- Any failed condition is `VIABLE = FALSE`, `NO_ACTION`, and `EXECUTION = DORMANT`.
- A floor advances only after a closed position, settled proceeds, positive
  realized net P/L after every cost, and reconciliation.
- Never claim a fill until the broker confirms order status; never call a
  strategy profitable without net realized results.

## Final law

`NO FRESH DATA = NO AUTHORITY; NO SOURCE QUORUM = NO AUTHORITY; NO NUMERIC NOTIONAL = NO ORDER; NO POSITIVE NET EDGE = NO TRADE; NO SETTLED PROFIT = NO NEW FLOOR; NO VERIFIED FILL = NO EXECUTION CLAIM; NO AUDIT TRAIL = NO PROMOTION.`
