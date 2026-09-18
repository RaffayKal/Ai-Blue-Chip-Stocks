# APEX_MICRO_CRYPTO_UNIT_LEDGER.md

## Governing Micro-Purchase Code

The user-supplied **APEX FRACTIONAL SPOT TRADING — MICRO-PURCHASES / AUM /
GOVERNANCE / EXECUTION** specification governs this ledger and every
fractional-spot candidate. It is subordinate only to live broker capability
and account facts, and it never treats ledger precision as executable order
precision.

Required controls are: streaming-first freshness, independent source quorum,
Decimal/integer fixed-point accounting, settled deployable capital, realized
net-profit-only floor advancement, loss-first sizing, after-cost expected edge,
idempotency, exact order review, broker-status reconciliation, immutable audit
events, and automatic demotion to `NO_ACTION` when any required fact is stale,
missing, contradictory, or unverified.

The governing state machine is:

`OBSERVE -> NORMALIZE -> VALIDATE -> UPDATE_FEATURES -> FORECAST_SCENARIOS -> CALCULATE_EXPECTANCY -> SIZE_BY_RISK -> RUN_APEX_GATES -> CREATE_CANDIDATE_ENVELOPE -> CHECK_IDEMPOTENCY -> PREVIEW_OR_REVIEW -> EXECUTE_IF_AUTHORIZED -> QUERY_BROKER_STATUS -> RECONCILE_FILL -> CALCULATE_REALIZED_NET_PNL -> UPDATE_AUM -> UPDATE_FLOOR_IF_SETTLED -> WRITE_AUDIT_RECORD`

Specification for the 24/7 micro-crypto trading unit ledger and risk sizing.

Reference implementation: `algorithms/apex_micro_crypto_ledger.py` (tested
in `tests/test_apex_micro_crypto_ledger.py`). It calculates and gates only
-- `evaluate()` returns `NO ACTION` or a sized `ORDER_NOTIONAL`, the same
authority level as `algorithms/capital_engine.py`. It does not itself place,
preview, or authorize a broker order, and it does not replace any existing
gate (duplicate-position, session, spread, broker authorization,
idempotency, etc. -- see `rules/RUNPOD_FIRST_TRADING_ARCHITECTURE.md` and
`rules/APEX_AUM_COMPOUNDING_ALGORITHM.md`). Wiring its output into the live
autonomous order-placement trigger chain is a separate, not-yet-made
change.

## Unit Denomination Ladder

Base unit of account for 24/7 micro-crypto trading. Each level is exactly
10x the previous in both dollar value and APEX units.

| Level | Dollar value | APEX units | Growth |
|---|---:|---:|---:|
| Atomic | `$0.00000007` | 1 | Base unit |
| Grain | `$0.00000070` | 10 | ×10 |
| Chip | `$0.00000700` | 100 | ×10 |
| Micro | `$0.00007000` | 1,000 | ×10 |
| Stack | `$0.00070000` | 10,000 | ×10 |
| Block | `$0.00700000` | 100,000 | ×10 |
| Floor | `$0.07000000` | 1,000,000 | ×10 |
| Tower | `$0.70000000` | 10,000,000 | ×10 |
| Capital | `$7.00000000` | 100,000,000 | ×10 |
| AUM | `$25.00000000` | 357,142,857 whole units plus `$0.00000001` | -- |

`atomic_unit = $0.00000007`. `ledger_units = floor(current_aum / atomic_unit)`.

## AUM Ledger and Risk Sizing Spec

```text
INPUT:
    current_aum
    settled_cash
    realized_pnl
    unrealized_pnl
    fees_and_slippage
    tax_reserve
    broker_minimum
    stop_distance_pct
    apex_viable
    source_freshness
    risk_gates_passed

CALCULATE:
    atomic_unit = 0.00000007
    ledger_units = floor(current_aum / atomic_unit)

    net_realized = realized_pnl - fees_and_slippage
    deployable_aum =
        settled_cash
        + max(net_realized, 0)
        - tax_reserve
        - protected_reserve

GATE:
    executable =
        apex_viable == true
        AND source_freshness == true
        AND risk_gates_passed == true
        AND deployable_aum >= broker_minimum

RISK:
    risk_budget = current_aum * risk_fraction
    candidate_notional = risk_budget / stop_distance_pct
    order_notional = min(
        candidate_notional,
        deployable_aum,
        position_cap
    )

    reject if order_notional < broker_minimum
    reject if expected_edge <= expected_cost
    reject if projected_drawdown > drawdown_limit

AFTER CLOSED TRADE:
    net_trade_pnl =
        sale_proceeds
        - cost_basis
        - fees
        - slippage
        - tax_allocation

    current_aum += net_trade_pnl

    if current_aum reaches next_floor:
        lock reserve_fraction of gains
        raise protected_floor
        calculate next_floor from confirmed current AUM
```

## Wait / Grow / Harvest Decision

Sizing a candidate (above) and deciding whether an already-open position may
be realized are separate questions. This gate answers the second one, and it
is deliberately biased against fast cycling: a position must clear a minimum
hold duration *and* reach the next floor's required percentage gain before
harvest is allowed, unless a stop-loss or setup invalidation fires first.

```text
INPUT:
    current_aum
    unrealized_gain_pct
    held_seconds
    min_hold_seconds
    stop_loss_triggered
    invalidation_triggered

DECIDE:
    if stop_loss_triggered or invalidation_triggered:
        HARVEST_NOW  # capital preservation overrides patience

    if held_seconds < min_hold_seconds:
        KEEP_GROWING  # too soon; let the position develop

    next_floor = next_floor_above(current_aum)
    required_gain_pct = (next_floor - current_aum) / current_aum

    if unrealized_gain_pct < required_gain_pct:
        KEEP_GROWING  # hasn't earned the next floor yet

    HARVEST_NOW  # both hold time and floor target are satisfied
```

Reference implementation: `apex_micro_crypto_ledger.should_harvest()`. This
is a decision helper, not an order gate -- it never places, previews, or
authorizes a broker order, and its output is one more input the existing
autonomous order gate may consult before an exit.

## Implementation Notes

- `deployable_aum` must never be treated as spendable unless its inputs
  (`settled_cash`, `realized_pnl`, etc.) were read from authoritative live
  broker state, per the Dynamic Capital Rule in `rules/CAPITAL_RULES.md`.
  `algorithms/apex_micro_crypto_ledger.py` computes the formula only; it
  does not fetch or verify broker freshness itself.
- `executable` is a necessary, not sufficient, gate: passing it does not
  override duplicate-position blocking, session rules, spread limits
  (`rules/MARKET_SESSION_RULES.md`), or any other existing APEX/broker gate.
- `next_floor_above()` walks the Unit Denomination Ladder above (Atomic
  through AUM), then continues by the same x10 rule past AUM -- it never
  invents a floor value ad hoc per trade.
- Wiring this module's `SIZED CANDIDATE` / `ORDER_NOTIONAL` output into the
  live autonomous order-placement trigger chain (e.g. as an additional
  required input alongside `algorithms/candidate_envelope_gate.py`) is a
  separate change, not made here.
