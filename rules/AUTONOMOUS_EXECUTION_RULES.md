# AUTONOMOUS_EXECUTION_RULES.md

Autonomous execution is allowed only when every gate in this file passes.

## CONTROLLING VERBATIM PROCEDURE

```text
runpod 24/7 engine - >  codex/live source/robinhoon live market feeds +
  ChatGPT sources/prjections/math/calculations/forecatsing/etc.  → envelopes →
  Codex Robinhood MCP
    refresh → enriched envelope → viability gate → preview → execution only
  after
    confirmation
```

No subsystem may defer, reorder, or bypass this procedure. The user's blanket
autonomous buy/sell authorization satisfies the user-confirmation gate for
orders that pass every live gate; Robinhood preview, idempotency, and broker
reconciliation remain mandatory.

## Codex Robinhood MCP Freshness Authority

Codex has the direct Robinhood MCP connection and is the broker-data authority.
Robinhood data must be refreshed at every candidate-processing and final broker
revalidation step. The data is not considered permanently live merely because
the MCP is connected.

```text
fresh Codex Robinhood MCP refresh = required for each candidate
stale, missing, contradictory, or failed refresh = NO ACTION
RunPod/ChatGPT scanning = continues 24/7 while execution is blocked
```

RunPod does not need a direct Robinhood relay to scan. Codex performs the live
Robinhood refresh, enriches the envelope, and owns the viability gate. No
cached Robinhood quote, heartbeat, or prior account snapshot may authorize a
new preview or order.

## Reinforced APEX Candidate Sequence

```text
1. Refresh Robinhood MCP account and quote data.
2. Reject the refresh if stale, incomplete, contradictory, or failed.
3. Use the live executable ask as the spot-buy entry when no model entry exists.
4. Derive invalidation dynamically at the break-even boundary where verified
   execution friction makes projected net profit non-positive.
5. Run APEX loss-first sizing and accept the ledger result `SIZED CANDIDATE`
   when all failure checks are empty.
6. Require positive net edge, fresh quorum, broker validation, preview, and
   explicit confirmation before Robinhood placement.
```

`SIZED CANDIDATE` is not a fill or execution authorization. It is the handoff
state between APEX sizing and broker preview.


## RunPod-First Runtime Gate

`rules/RUNPOD_FIRST_TRADING_ARCHITECTURE.md` is the top runtime rule for heavy-agent usage. RunPod or any remote always-on worker may scan cheaply, track state, apply cooldowns, deduplicate market events, and create compact event packets.

Default state:

```text
AI_USAGE = ZERO
BROKERAGE_EXECUTION = DISABLED
SCANNER = ON
FULL_AGENT = OFF
LIGHTWEIGHT_WATCHER = ON
```

The always-on runtime must not keep Superpowers, Apex reasoning, TradingCursor, OpenAI Developers agents, Ace Knowledge Graph rebuilds, NVIDIA-heavy workflows, Precise Special Functions, or large model loops running continuously. It may wake those layers only after a deduplicated event remains viable through cheap confirmation.

Cheap confirmation may use Longbridge market confirmation, 2+2 Calculator arithmetic checks, Precise Special Functions only when actually relevant, and authorized stock/account data only when needed. If the event is no longer viable, return `NO ACTION` and resume scanning.

RunPod-first runtime does not authorize scanner/plugin brokerage execution by itself. After Codex validates a qualified envelope and prints `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS`, live autonomous order placement still requires the active ticket, validated Apex algorithm ID, exact Robinhood preview, buying-power or sellable-quantity confirmation, cost-basis and net-profit checks for sells, execution limit checks, configured autonomous execution authorization, idempotency, execution logging, and an authorized execution connector. If the authorized execution connector is unavailable or rejects preview, output `NO ACTION`.

## Multi-Plugin Workflow Gate

When full agent execution wakes, the agent must follow `rules/MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md` where tools are connected and applicable. The workflow order is Superpowers, Longbridge, Notion, Carta CRM, TradingCursor, Precise Special Functions, Stocktwits, Finances, Apex Synthesis, Ace Knowledge Graph, then return to watcher.

Unavailable plugin results must not be invented. If a plugin is unavailable and its data is required for a trade-critical fact, the only valid result is `NO ACTION`.

## Event-Trigger Operating Mode

Default operating state:

```text
FULL_AGENT = OFF
LIGHTWEIGHT_WATCHER = ON
```

The watcher may monitor and calculate market conditions. It must not place an order. It may wake the full agent only when confirmed market movement, appreciation potential, and execution economics produce viable positive expected net-profit trade value.

If viable trade value is false, the valid result is `NO ACTION`; keep the full agent off and continue lightweight monitoring.

When the full agent wakes, it must still pass every autonomous gate, Robinhood preview, account check, buying-power or sellable-quantity check, ticket execution limit, idempotency check, execution log check, and net-profit rule before placement. After the action or blocked action, return `FULL_AGENT = OFF`.

## Scope

Current autonomous scope:

- broker: Robinhood
- asset class: crypto
- account: verified agent-accessible account in `rules/brokerage_intake.json`
- capital: cash-backed only
- margin: blocked
- options: blocked
- equities: blocked until regular-market session and exact broker tradability are live-confirmed

## Required Files

Autonomous execution requires:

- `rules/user_settings.json`
- `rules/brokerage_intake.json`
- `data/autonomous_btc_market_buy_1usd.json`
- `data/autonomous_execution_log.json`
- a market input file that returns `VALIDATED SETUP` from `algorithms/capital_engine.py`

## Required Ticket Fields

The autonomous order ticket must contain:

```json
{
  "autonomous_execution": true,
  "user_algorithm_id": "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING",
  "symbol": "selected crypto",
  "asset_class": "CRYPTO",
  "venue": "Robinhood Crypto",
  "side": "buy",
  "type": "market",
  "dollar_amount": "1.00",
  "requires_preview": true,
  "requires_algorithm_result": "VALIDATED SETUP",
  "ticket_id": "btc_market_buy_1usd",
  "max_executions": 7
}
```

No range orders. No default amount. No margin. No order above verified buying power. No order above the configured asset allocation cap.

For dynamic buy sizing, use:

```json
"dollar_amount_mode": "AUTO_MAX_ALLOWED"
```

The gate must convert it into one exact `DOLLAR_AMOUNT` before any Robinhood preview. The calculated amount is:

```text
min(verified crypto buying power, available trading capital * crypto allocation cap, ticket max dollar amount)
```

If that calculated amount is below the broker minimum or below the ticket minimum, the result is `NO ACTION`.


## Retained Growth Re-Evaluation Gate

A retained 25% position that grows less than 10% remains in `HOLD / MONITOR` unless another hard exit rule is triggered.

A retained 25% position that grows at least 10% wakes Apex for re-evaluation only. It does not authorize automatic liquidation by itself.

The full agent may harvest the grown percentage only when all of these are confirmed:

- retained position source and cost basis
- current sellable quantity
- growth percentage at or above 10%
- projected upside is no longer sufficiently viable
- previewed order has positive expected net profit after fees, spread, slippage, and execution friction
- execution stays inside ticket limits and broker/account/risk gates

If projected upside remains clear and viable, the result is `HOLD / LET IT RUN`; return `FULL_AGENT = OFF` after logging the review state.

## Blue-Chip Capital Exposure Gate

High-risk / high-reward blue-chip mode may maintain compounding exposure within the configured 3%-20% tactical allocation band when high-conviction upside remains viable. Blue-chip execution remains blocked in this automation until a separate equity execution gate exists and approves the exact order.

## Autonomous Gate

Before any autonomous placement:

1. Run `algorithms/capital_engine.py` on the matching market input.
2. Continue only if the result is exactly `VALIDATED SETUP`.
3. Confirm the order ticket symbol matches the market input symbol.
4. Confirm the ticket asset class matches the market input asset class.
5. Confirm the ticket side is explicit.
6. Confirm the ticket order type is supported for the asset class.
7. Confirm the ticket amount is a single numeric value.
8. Confirm the ticket amount is at least the broker minimum.
9. Confirm the ticket amount is at or below verified buying power.
10. Confirm the ticket amount is at or below the configured allocation cap.
11. Confirm the ticket has not reached its execution limit in `data/autonomous_execution_log.json`.
12. Preview the Robinhood order.
13. Place only the previewed order.

Any failed check returns `NO ACTION`.

## Dynamic Capital Boundary

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto:
use the selected account’s crypto buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

The autonomous selected crypto order cap is calculated at runtime from verified crypto buying power and configured allocation limits.

## Unlimited Sell Ticket Generation

Unlimited sell mode means generating a fresh one-shot sell ticket after the previous sell ticket reaches `max_executions`. Do not reuse an exhausted ticket. Do not set `max_executions` to a string.

Each generated sell ticket must keep:

```json
{
  "autonomous_execution": true,
  "user_algorithm_id": "APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING",
  "symbol": "selected crypto",
  "asset_class": "CRYPTO",
  "venue": "Robinhood Crypto",
  "side": "sell",
  "type": "market",
  "quantity_mode": "AUTO_SELLABLE_POSITION",
  "min_quantity": "0.00000001",
  "requires_preview": true,
  "requires_algorithm_result": "VALIDATED SETUP",
  "ticket_id": "btc_market_sell_position_auto_<sequence>",
  "max_executions": 7
}
```

Sell sizing must come from the live Robinhood crypto position only. The executable quantity is `quantity_transferable`, after confirming symbol `selected crypto`, account `rhs_account_number 411926553`, and crypto account ending `5533`. If live sellable selected crypto is below `min_quantity`, the result is `NO ACTION`.

## Unlimited Buy/Sell Reload Engine

Unlimited mode is implemented by `scripts/reload_autonomous_tickets.py`. The automation must run this script before running buy or sell gates.

The script maintains these active 7-shot ticket files:

- `data/autonomous_crypto_market_buy_auto_max_active.json`
- `data/autonomous_crypto_market_sell_position_auto_active.json`

If an active ticket reaches `max_executions: 7` in `data/autonomous_execution_log.json`, the script writes the next sequence ticket with `max_executions: 7`, `reload_mode: UNLIMITED_7_SHOT_RELOAD`, and `user_algorithm_id: APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`. A ticket that appears fewer than 7 times in the log remains current.

The gate must still approve each ticket. Reloading a ticket does not bypass the apex algorithm, broker preview, account check, capital check, sellable quantity check, or execution log check.

## Single-Crypto Concentration Gate

Autonomous crypto execution must never allocate 100% of available capital into one crypto asset. BTC or any other crypto may be selected only inside the configured allocation cap and active ticket limits.

If a proposed crypto ticket would use all available capital on one crypto asset, the gate must return `NO ACTION`. If broker minimums prevent spreading across multiple crypto assets, the automation may use only a smaller capped ticket that remains inside the configured per-crypto limit and passes preview, buying-power, ticket, and net-profit checks.

## Usage-Reset Resume / Minimum-Heavy-Usage Rule

Only Codex usage remaining less than or equal to `2%`, or unknown usage telemetry, may freeze operations. In that case, `SYSTEM_STATE = FROZEN`. This pauses Runpod market scanning, APEX qualification, candidate generation, connector-driven market analysis, trade analysis, execution requests, compounding actions, and queued execution. The first action after freezing is an atomic snapshot. While frozen, autonomous buy/sell is disabled and the only valid market result is `NO ACTION`.

Market, broker, candidate, APEX, risk, preview, source-provenance, or viability gates may block execution, candidates, previews, or buy/sell actions. They must not freeze or stop operations while verified Codex usage remains above `2%`. In that state, operations continue in active/watch mode and wait for a fresh qualifying envelope.

If autonomous operations were paused because usage was exhausted or near exhausted, resume only after usage resets enough to support safe monitoring. On resume, restore state only from a current atomic snapshot, refresh live market data, destroy stale signals, rebuild candidates, rerun every APEX gate, and reject/watch unless `VIABLE = TRUE`.

Resume after usage reset does not bypass capital rules. It must still enforce no 100% concentration into one stock, no 100% concentration into one crypto, per-symbol exposure caps, ticket limits, Robinhood preview, buying power, sellable quantity, and net-profit gates.

## Recovery Lockdown / BTC Sell-Only Exception

User command active: pause all operations except selling BTC to recover capital or realize net profit.

While this mode is active:

- all buy orders are disabled, including BTC, other crypto, and equities
- autonomous resume/rebuy logic is disabled
- the only permitted live brokerage action is `BTC` `CRYPTO` `sell` on `Robinhood Crypto` from rhs account `411926553` / crypto account ending `5533`
- sell sizing must come from live sellable BTC quantity only
- a Robinhood preview is mandatory before placement
- placement is allowed only if the preview proves the sale recovers capital or produces positive net profit after spread, fees, slippage, and execution friction
- if the preview is below recovery threshold, stale, rejected, or mismatched, the result is `NO ACTION`
- after any sell placement, check the order by id and append the result to `data/autonomous_execution_log.json`
- after any action or blocked action, return `FULL_AGENT = OFF` and keep only lightweight monitoring active

This recovery exception does not authorize any buy, equity trade, margin use, invented symbol, changed amount, or stale-data action.

## Current Envelope Required Before Buy/Sell Activation

Autonomous buy/sell mode may not run from sample data. The full buy/sell workflow activates only when `data/current_candidate_envelope.json` exists and `python3 algorithms/candidate_envelope_gate.py data/current_candidate_envelope.json` prints both:

```text
VIABLE: true
AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS
```

If the current envelope is missing, stale, sample-only, `scanner_viable: false`, lacks two fresh source records, lacks idempotency, or fails capital-engine validation, the system must keep `FULL_AGENT = OFF`, skip buy/sell gates, place no orders, and return `NO ACTION`.

`data/sample_qualified_candidate_envelope.json` is test data only and must never be used as the live autonomous activation source.

## Event-Trigger Only / No Codex Timer Watcher

Codex must not run a 24/7 watcher and must not wake every minute just to check the market. Autonomous buy/sell is event-trigger only.

Allowed activation path:

1. An external scanner or broker-side/current-project trigger updates `data/current_candidate_envelope.json` with fresh confirmed data.
2. Codex is invoked only after that event exists.
3. Codex validates the envelope locally.
4. Codex may run buy/sell workflow only if validation prints both exact lines:

```text
VIABLE: true
AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS
```

If those lines are absent, Codex stays dormant. No timer wake, no order preview, no order placement.

The old every-minute Codex heartbeat/watch loop is disabled by rule.

After activation, autonomous buy/sell gates must use the runtime `market_input` extracted from `data/current_candidate_envelope.json` into `/private/tmp/apex_current_envelope_market_input.json`. They must not use `data/sample_robinhood_volatile_crypto_input.json`, `data/sample_robinhood_crypto_input.json`, or any other sample market file for live buy/sell activation.

After activation, Codex must run only the side authorized by `candidate_decision`. `BUY CANDIDATE` may run the buy gate only when buys are not paused by current operations mode. `SELL CANDIDATE` may run the sell gate. `HOLD CANDIDATE`, `WATCHLIST ONLY`, `HUMAN APPROVAL REQUIRED`, and `NO ACTION` must run no buy/sell gate.
