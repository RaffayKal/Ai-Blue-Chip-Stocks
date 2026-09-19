# RUNPOD_FIRST_TRADING_ARCHITECTURE.md

ABSOLUTE INFINITE +775%
TACTICAL APPRECIATION OPERATIONS COMPOUNDING

APEX PRESTIGE RUNPOD-FIRST MINIMUM-HEAVY-USAGE TRADING ARCHITECTURE

## CANONICAL FOREVER OPERATIONS PIPELINE

```text
runpod 24/7 engine - >  independent live market feeds +
  ChatGPT sources/prjections/math/calculations/forecatsing/etc.  → envelopes →
  Codex Robinhood MCP
    refresh → enriched envelope → viability gate → preview → execution only
  after
    confirmation
```

This verbatim procedure is controlling and must not be deferred, reordered, or replaced.

## FRONTLINE ROBINHOOD MCP RULE

For every active operation, status report, hourly check, candidate, and
execution decision, Codex must refresh Robinhood MCP first. Robinhood is the
frontline broker-data authority, not a passive background source. The fresh
account/quote result then enters the envelope, APEX calculations, and viability
gate. A stale, failed, missing, or contradictory refresh produces `NO ACTION`
and keeps 24/7 scanning active.

```text
RunPod MCP/live sources
    -> ChatGPT/RunPod fresh sources and independent live feeds,
       projections, forecasting, math, and calculations
    -> timestamped envelopes
    -> Codex Robinhood MCP market-data refresh only at final broker revalidation
    -> enriched envelope
    -> Codex viability gate
    -> Robinhood inspection and preview
    -> Robinhood explicit user confirmation
    -> Robinhood execution
    -> operations ledger and monitoring
    -> loop
```

This is the major tactical operating procedure. Envelopes may be produced
whenever their independent market-data quorum, freshness, symbol, venue,
spread, liquidity, risk, and calculation fields are present. Robinhood quote
and account usage is deferred until final Codex broker revalidation. The final
Robinhood refresh remains mandatory before preview or execution.
Envelope production never authorizes execution. Missing, stale, contradictory,
or unavailable facts produce `NO ACTION`. No forecast, projection, lane count,
or RunPod status is user confirmation.

This is the permanent operating mode: RunPod and ChatGPT produce lightweight
envelopes, Codex performs heavy work only at the viability gate, and Robinhood
MCP remains the broker-side authority for current quotes, buying power, account
state, inspection, preview, and execution. A lane, scanner, MCP connection, or
envelope never grants execution authority by itself.

The pipeline remains fail-closed. Missing, stale, contradictory, or unverified
broker data produces `NO ACTION`. Continuous operation is not a promise to
trade, a promise of profit, or a guarantee of capital growth.

CONTROL SPLIT

ChatGPT/plugins may perform continuous scanning, calculations, projections, catalyst review, sentiment review, quote comparison, and candidate qualification.

ChatGPT/plugins must never execute trades, submit broker orders, place previews as if approved, or claim brokerage authority. Their maximum output is a structured qualified candidate envelope.

Codex remains dormant until a qualified candidate envelope is delivered. Codex independently validates `viable=true` or `viable=false` using local APEX rules, source provenance, idempotency, capital controls, and fail-closed checks.

If Codex validates `viable=false`, Codex stays asleep and the scanner continues.

If Codex validates `viable=true`, Codex may activate the existing autonomous agentic buy/sell workflow. Any live brokerage action still remains blocked unless the active autonomous ticket, exact Robinhood preview match, broker authorization, idempotency, execution logging, sellable-quantity or buying-power checks, cost-basis/net-profit checks where applicable, and configured execution authorization all pass.

CORE CAPITAL RULES

Starting capital: $5.

Profit handling:
75% of NET PROFIT is harvested.
25% of NET PROFIT is retained inside the compounding engine.

Reevaluation rule:
Every 10%-UNKNOWN%+ portfolio/account/opportunity change triggers reevaluation.

Capital compounding:
Use the configured 3%-20% tactical allocation band from the APEX AUM Compounding Algorithm, subject to verified buying power, current data, liquidity, execution math, risk confirmation, and the maximum-open-position rule.

Execution rule:
No live brokerage execution unless an actually authorized execution surface is available.
If no authorized execution connector exists, output is WATCHLIST ONLY / NO ACTION / HUMAN APPROVAL REQUIRED.

════════════════════════════════════
STATE 0 — RUNPOD 24/7 LIGHTWEIGHT RUNTIME
════════════════════════════════════

Runpod is the 24/7 primary runtime and always-on process.

Runpod handles:
STOCK_UNIVERSE_STATE
CRYPTO_UNIVERSE_STATE
ACTIVE_POSITION_STATE
CAPITAL_STATE
MARKET_REGIME_STATE
VOLATILITY_STATE
CATALYST_STATE
DUPLICATE_TRANSACTION_STATE
EXECUTION_FRICTION_STATE
LAST_APEX_DECISION_STATE
COOLDOWN_STATE
PROFIT_RECYCLING_STATE
24/7 crypto scanning
market-session stock scanning
cheap deterministic signal polling
state tracking
cooldowns
deduplication
event packet creation
wake/sleep control for expensive agents
qualified candidate envelope handoff to Codex

Runpod does NOT continuously run:
Superpowers
APEX reasoning
TradingCursor
OpenAI Developers agents
Ace Knowledge Graph rebuilds
NVIDIA-heavy workflows
Precise Special Functions
large model analysis loops

Runpod watches only cheap/raw inputs:
price
percent change
volume
relative volume
spread
volatility
momentum
liquidity
position P/L when available
portfolio/account state when authorized
known catalyst flags
execution friction
freshness timestamps

Default state:
AI usage = ZERO
brokerage execution = DISABLED
scanner = ON

Scan loop:

```text
ingest raw market data
normalize symbol state
update multi-timeframe history
recompute regime metrics
recompute volatility quality
recompute liquidity/spread
recompute trend persistence
recompute catalyst score
recompute estimated net-profit envelope
evaluate existing-position conflicts
evaluate duplicate-entry prohibition
emit event ONLY if material state change occurs
```

No material change means continue scanning and keep the heavy agent OFF.

════════════════════════════════════
STATE 1 — RUNPOD LOCAL FILTER
════════════════════════════════════

Runpod calculates locally:

movement_score
momentum_score
volume_score
volatility_score
liquidity_score
spread_cost
estimated_execution_friction
estimated_net_opportunity
freshness_score
capital_size_fit
risk_to_$5_account_score
past_appreciation_regime
present_appreciation_regime
projected_appreciation_regime
trend_persistence
multi_timeframe_alignment
positive_volatility_quality
continuation_probability
reversal_probability
confidence_decay_rate
duplicate_entry_status

Asset eligibility is not created by volatility alone. `APEX_ELIGIBLE(asset)` requires confirmed past, present, and projected positive appreciation regimes plus acceptable trend persistence, momentum alignment, multi-timeframe alignment, volume confirmation, liquidity, spread, slippage estimate, drawdown profile, recovery profile, catalyst score, reversal risk, expected net profit, and capital efficiency.

Positive volatility means upside-dominant volatility inside a persistent positive appreciation regime. Random movement, high amplitude alone, one-session spikes, and unconfirmed momentum are rejected.

Multi-timeframe consistency must evaluate micro, short, medium, and long trend states. Past positive with present negative means WATCH / REJECT. Past and present positive with weak projection means WATCH. Micro positive with medium/long negative means REJECT TRANSIENT SPIKE. Micro + short + medium + long positive with projected continuation may advance.

Volatility quality must consider upside volatility ratio, downside volatility ratio, positive return frequency, positive return magnitude, negative return magnitude, recovery speed, drawdown depth, trend stability, momentum decay, and volume confirmation. High volatility with bad or random direction is rejected.

Decision:

VIABLE_TRADE_VALUE = FALSE
→ discard
→ continue scanning
→ no heavy AI

VIABLE_TRADE_VALUE = TRUE
→ create compact EVENT_PACKET / qualified candidate envelope
→ continue to deduplication

════════════════════════════════════
STATE 2 — RUNPOD EVENT DEDUPLICATION
════════════════════════════════════

Before waking expensive agents, Runpod checks:

Has price materially changed?
Has volume/liquidity materially changed?
Has spread/execution friction changed?
Has signal strength changed?
Has catalyst changed?
Has account/position state changed?
Is cooldown complete?
Does this cross the 10%-UNKNOWN%+ reevaluation threshold?

If NO:
discard duplicate
continue scanning

If YES:
advance to cheap confirmation and candidate-envelope preparation

════════════════════════════════════
STATE 3 — CHEAP CONFIRMATION LAYER
════════════════════════════════════

Runpod calls only the minimum connected stack needed.

Longbridge:
market data
quotes
price/volume confirmation
basic instrument context

2+2 Calculator:
cheap arithmetic checks
percentage change
capital sizing
profit split
risk math

Precise Special Functions:
only if specialized math is actually needed

Stock/account source:
only if portfolio state is actually needed and authorized

Still viable?

NO:
NO ACTION
return to Runpod scanning

YES:
deliver qualified candidate envelope to dormant Codex

════════════════════════════════════
STATE 3A — CHATGPT/PLUGIN CANDIDATE ENVELOPE
════════════════════════════════════

ChatGPT/plugins may keep scanning and calculating continuously outside Codex, but their handoff must be compact, idempotent, and non-executing.

Envelope must include:
envelope_id
idempotency_key
created_by = CHATGPT_PLUGIN_SCANNER
user_algorithm_id = APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING
scanner_viable = true
requested_codex_activation = true
plugins_execute_trades = false
broker_order_submitted = false
candidate_decision
data_provenance with at least two fresh source records
market_input object compatible with the local capital engine
asset
timestamp
current price
existing position state
cost basis if relevant
trend state
volatility quality
volume state
spread
liquidity
catalyst state
continuation estimate
reversal estimate
expected net profit
duplicate-entry status
capital required
capital-at-risk
trigger reason
material change since prior state

Missing, stale, conflicting, non-idempotent, or trade-executing envelopes are invalid. Invalid envelope = `viable=false`, `CODEX_STATE=DORMANT`, `NO ACTION`.

Codex validation entrypoint:

```text
python3 algorithms/candidate_envelope_gate.py data/current_candidate_envelope.json
```

Only `CODEX_STATE=ACTIVATE_AGENTIC_WORKFLOW`, `VIABLE=true`, and `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS` may wake the existing autonomous agentic buy/sell workflow.

════════════════════════════════════
STATE 4 — AUTONOMOUS AGENTIC BURST ONLY ON QUALIFYING EVENTS
════════════════════════════════════

Codex, not ChatGPT/plugins, controls this state after envelope validation. This is the state where the project may run autonomous buy/sell handling, but only through the existing local autonomous gate.

Superpowers:
high-level tactical judgment only after event qualifies

OpenAI Developers:
agent/tool design, API orchestration, structured decision workflows

TradingCursor:
deeper technical confirmation only when needed

Ace Knowledge Graph:
ALWAYS LAST visualization of architecture/state relationships. It is not trade authority.

NVIDIA Skills:
GPU/model/runtime optimization only when infrastructure or accelerated inference matters

Amplitude:
event analytics, scanner performance, trigger quality, false-positive rate, wake-cost tracking

Carta CRM:
relationship/entity/customer/investor context only if relevant to the trading workflow

Notion:
decision logs, watchlists, post-trade notes, human review queue

Runpod remains the controller:
Runpod wakes agents.
Runpod receives their outputs.
Runpod stores compact state.
Runpod returns to scanning.
Codex returns to dormant state after synthesis, blocked action, approved non-executing workflow output, or completed autonomous workflow.

════════════════════════════════════
STATE 5 — APEX DECISION
════════════════════════════════════

APEX output must be one of:

NO ACTION
WATCHLIST ONLY
HOLD
BUY CANDIDATE
SELL CANDIDATE
PARTIAL SELL CANDIDATE
RE-ENTER CANDIDATE
HUMAN APPROVAL REQUIRED

Required checks before any BUY/SELL candidate:

fresh data
two-source confirmation when practical
spread acceptable
liquidity acceptable
capital sizing valid for $5 start
fractional eligibility confirmed if equity
crypto action status confirmed if crypto
risk does not exceed approved limits
3%-20% verified-buying-power allocation band respected
75% net-profit harvest / 25% retained rule preserved
10%-UNKNOWN%+ reevaluation rule applied
duplicate-position rule applied
projected appreciation remains positive
expected NET opportunity remains positive

If any required field is missing, stale, unsupported, or conflicting:
NO ACTION.

Before any BUY, duplicate-position status is an absolute hard gate.

```text
IF existing_position(asset) == FALSE:
    evaluate normal entry

IF existing_position(asset) == TRUE:
    DUPLICATE_ENTRY = TRUE
    DEFAULT = BLOCK DUPLICATE ENTRY
```

Only structurally locked NET PROFIT after purchase cost, spread, commissions/fees, slippage, taxes where applicable, price uncertainty, and execution uncertainty may override the duplicate block. If future appreciation is required to create profit, the profit is not guaranteed and the duplicate entry is blocked. 95%, 99%, and 99.99% confidence are not 100%.

════════════════════════════════════
STATE 6 — EXECUTION GATE
════════════════════════════════════

No scanner/plugin trades.

ChatGPT/plugins must never place live orders.

After Codex validates a qualified envelope and activates, live autonomous order placement is permitted only when all are true:

authorized brokerage execution surface exists
account status is confirmed
instrument eligibility is confirmed
order preview is available
preview exactly matches the active autonomous ticket
idempotency key has not already been consumed
execution log confirms the ticket is under limit
exact order details are shown
configured autonomous execution authorization is true

Without that:
WATCHLIST ONLY or HUMAN APPROVAL REQUIRED.

════════════════════════════════════
STATE 7 — PROFIT COMPOUNDING LOOP
════════════════════════════════════

When profit exists and is confirmed as NET PROFIT:

75% harvested out of the active compounding pool
25% retained for compounding

If APEX supports increased exposure:
capital allocation may rise up to 20% max

If APEX does not support increased exposure:
retain current size
or reduce size
or NO ACTION

Every 10%-UNKNOWN%+ change:
rerun reevaluation
rerun risk math
rerun capital allocation logic

After each action, recalculate capital, cash, position value, cost basis, realized net profit, unrealized net profit, retained exposure, 3%-20% allocation band, one-position limit, duplicate-entry state, next viable trade value, next reevaluation threshold, cooldown, and confidence decay. Write only delta state. Notion may record decision/state change. Amplitude may record runtime event metrics. Runpod updates live machine state.

Block transaction if any of these exist:

```text
DATA_STALE
DATA_CONFLICT
SPREAD_TOO_HIGH
LIQUIDITY_INSUFFICIENT
REVERSAL_RISK_TOO_HIGH
EXPECTED_NET_PROFIT <= 0
POSITIVE_VOLATILITY_NOT_CONSISTENT
PROJECTED_APPRECIATION_FAIL
DUPLICATE_POSITION_BLOCKED
CAPITAL_EXPOSURE_LIMIT
EXECUTION_STATE_UNKNOWN
```

Result: NO TRADE, return to watcher.

════════════════════════════════════
CONNECTED STACK ROLES
════════════════════════════════════

Runpod:
24/7 scanner/runtime/controller

Superpowers:
high-level agentic tactical burst

OpenAI Developers:
agent/API/workflow build layer

Precise Special Functions:
specialized math only when needed

NVIDIA Skills:
accelerated compute/runtime optimization only when needed

2+2 Calculator:
cheap arithmetic and percentage verification

TradingCursor:
technical market analysis confirmation

Carta CRM:
relationship/entity/customer context when relevant

Notion:
logs, review queue, watchlists, documentation

Longbridge:
market data and quote confirmation

Amplitude:
signal analytics and wake-cost optimization

Ace Knowledge Graph:
ALWAYS LAST visualization of architecture/state relationships

FINAL OPERATING PRINCIPLE

Runpod stays awake.
Everything expensive sleeps.

Runpod scans deterministically 24/7.
Runpod wakes agents only when there is a qualifying event.
Runpod does not execute trades without a real authorized execution surface and explicit reviewed-order approval.

Final system law:

```text
NO CAPITAL CHASES RANDOM VOLATILITY.
NO DUPLICATE BLUE CHIP / CRYPTO ENTRY WITHOUT MATHEMATICALLY LOCKED NET PROFIT.
NO HEAVY AGENT USAGE WITHOUT A QUALIFIED EVENT.
NO EVENT QUALIFIES WITHOUT CONSISTENT PAST + PRESENT + PROJECTED POSITIVE APPRECIATION STRUCTURE.
ACE KNOWLEDGE GRAPH = LAST.
```

## Enforcement in this folder

RunPod-first mode is the top runtime architecture for heavy-agent usage. It controls when expensive agents wake, but it does not bypass `rules/AUTONOMOUS_EXECUTION_RULES.md`, `rules/ROBINHOOD_RULES.md`, `rules/BROKERAGE_RULES.md`, or any live broker preview/placement requirement.

For the currently authorized Robinhood crypto automation, Codex may use the verified agent-accessible Robinhood crypto execution surface only under the exact active autonomous ticket, preview, buying-power, sellable-quantity, cost-basis, idempotency, logging, and net-profit gates already defined in this folder. If that authorized execution surface is unavailable or rejects the preview, the result is `NO ACTION`.

Blue-chip stocks remain the main investment assets, but this crypto automation must not place equity orders unless a separate equity execution gate exists and approves the exact order.

## Single-Stock Concentration Guard

RunPod must flag and block any event packet that would place 100% of available capital into one stock. The lightweight scanner may rank stock opportunities, but it must request a spread allocation plan for stock execution instead of waking an all-in single-stock order.

If the account size cannot support a spread basket because of broker minimums, RunPod returns `WATCHLIST ONLY` or `NO ACTION` for stock execution. Crypto execution remains governed by the separate crypto ticket, preview, buying-power, and net-profit gates.

## Single-Crypto Concentration Guard

RunPod must flag and block any event packet that would place 100% of available capital into one crypto asset. The lightweight scanner may rank crypto opportunities by volatility and net-profit potential, but it must not wake or execute an all-in single-crypto order.

If the account size cannot support a spread crypto basket because of broker minimums, RunPod returns `WATCHLIST ONLY`, `NO ACTION`, or uses only a capped ticket that remains inside the configured single-crypto cap.

## Usage-Reset Resume / Minimum-Heavy-Usage Rule

Only Codex usage remaining less than or equal to `2%`, or unknown Codex usage telemetry, may freeze Codex-heavy operations. In that case, `SYSTEM_STATE = FROZEN` for Codex-heavy wakeups only. Runpod 24/7 lightweight market scanning, watching, deterministic calculations, projections, cooldowns, deduplication, health logging, and candidate-readiness bookkeeping stay active. Connector-driven heavy market analysis, Codex trade analysis, execution requests, compounding actions, queued execution, order preview, and order placement are paused. The first heavy-freeze action is an atomic snapshot and stale Codex activation invalidation. While Codex-heavy operations are frozen, the only valid heavy/action result is `NO ACTION`, but Runpod scanning continues.

Market, broker, candidate, APEX, risk, preview, source-provenance, or viability gates may block execution, candidates, previews, or buy/sell actions. They must not freeze or stop operations while verified Codex usage remains above `2%`. In that state, operations continue in active/watch mode and wait for a fresh qualifying envelope.

When Codex or agent usage is constrained above the hard-freeze threshold, operations must optimize usage at all costs. Keep only lightweight watcher logic active. Do not spend heavy reasoning, plugin chains, graph rebuilds, or large agent bursts while usage is low unless a trade-critical event requires immediate action and all gates already pass.

If Codex-heavy operations were paused because usage was exhausted, unknown, or near exhausted, resume Codex-heavy wakeups only after usage resets enough to support safe validation. Runpod scanning does not stop. On resume, restore state only from a current atomic snapshot, refresh live market data from Runpod or connected market sources, destroy stale Codex activation signals, rebuild candidates, rerun every APEX gate, and reject/watch unless `VIABLE = TRUE`.

Resume after usage reset does not bypass capital rules. It must still enforce no 100% concentration into one stock, no 100% concentration into one crypto, per-symbol exposure caps, ticket limits, Robinhood preview, buying power, sellable quantity, and net-profit gates.

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

After activation, autonomous buy/sell gates must use the runtime `market_input` extracted from `data/current_candidate_envelope.json` into `/private/tmp/apex_current_envelope_market_input.json`. They must not use sample market files for live buy/sell activation.
