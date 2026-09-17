# APEX_INVESTING_ALGORITHM.md

Executable algorithm ID:

```text
APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING
```

This is the apex hierarchy investing rule for this folder.

## Dynamic Capital

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto:
use the selected account’s crypto buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

The algorithm must automatically adapt as deposits, withdrawals, holdings, profits, losses, and buying power change.

## Primary System

```text
BLUE-CHIP TECH GIANTS = MAIN INVESTMENT ASSETS AND PRIMARY COMPOUNDING MECHANISM
MOST VOLATILE VERIFIED ROBINHOOD-SUPPORTED CRYPTO = 24/7 TACTICAL COMPOUNDING / MICRO-NET-PROFIT MECHANISM
```

## Layered Tactical Standards

APEX uses a layered, evidence-backed process rather than a single “secret” billionaire algorithm:

1. Use multiple independent market-data sources and record source timestamps, freshness, liquidity, and source disagreement.
2. Use separate tactical lenses for value, momentum, quality, reversal risk, volatility, fundamentals/news, and forward projection. A scanner signal is not execution authority.
3. Require expected appreciation to exceed spread, fees, slippage, liquidity impact, and other execution friction before a candidate can be viable.
4. Keep broker-side capital, account, duplicate-order, asset-eligibility, and session checks independent from scanner conclusions.
5. Missing, stale, contradictory, or unverified facts produce `NO ACTION`; no projection is a guaranteed return.

These standards refine evidence collection and validation. They do not replace the existing APEX viability, capital, concentration, or broker-risk gates.



## RunPod-First Minimum-Heavy-Usage Runtime

`rules/RUNPOD_FIRST_TRADING_ARCHITECTURE.md` is the controlling runtime architecture for keeping expensive agents off until a qualified market event exists.

RunPod is the always-on lightweight scanner/runtime/controller. It handles 24/7 crypto scanning, market-session stock scanning, deterministic signal polling, state tracking, cooldowns, deduplication, event packet creation, and wake/sleep control for expensive agents.

ChatGPT/plugins may also serve as the continuous scanning, calculation, projection, and candidate-qualification layer. That layer never executes trades. It may only deliver a qualified candidate envelope to Codex.

Codex remains dormant until it receives a qualified candidate envelope. Codex must independently validate the envelope with `algorithms/candidate_envelope_gate.py` and local APEX rules. `VIABLE: false` keeps Codex asleep. `VIABLE: true` plus `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS` permits Codex to activate the existing autonomous agentic buy/sell workflow, then return to sleep.

Default runtime state:

```text
AI_USAGE = ZERO
BROKERAGE_EXECUTION = DISABLED
SCANNER = ON
FULL_AGENT = OFF
LIGHTWEIGHT_WATCHER = ON
```

RunPod watches cheap/raw inputs only: price, percent change, volume, relative volume, spread, volatility, momentum, liquidity, position profit/loss when available, authorized portfolio/account state, known catalyst flags, execution friction, and freshness timestamps.

RunPod must not continuously run Superpowers, Apex reasoning, TradingCursor, OpenAI Developers agents, Ace Knowledge Graph rebuilds, NVIDIA-heavy workflows, Precise Special Functions, or large model analysis loops. Those layers wake only for a qualifying event.

RunPod local filter calculates movement score, momentum score, volume score, volatility score, liquidity score, spread cost, estimated execution friction, estimated net opportunity, freshness score, capital size fit, risk-to-$5-account score, past appreciation regime, present appreciation regime, projected appreciation regime, trend persistence, multi-timeframe alignment, positive volatility quality, continuation probability, reversal probability, confidence decay, and duplicate-entry status.

APEX eligibility requires confirmed past, present, and projected positive appreciation structure. Volatility alone never authorizes capital. High volatility with bad direction, random direction, or only a transient one-window spike returns `NO ACTION` or `WATCHLIST ONLY`.

Duplicate blue-chip or crypto entry is blocked unless NET PROFIT is mathematically locked after purchase cost, spread, commissions/fees, slippage, taxes where applicable, price uncertainty, and execution uncertainty. If future appreciation is required to create profit, the duplicate entry is blocked.

If `VIABLE_TRADE_VALUE = FALSE`, discard the event, continue scanning, run no heavy AI, and take `NO ACTION`.

If `VIABLE_TRADE_VALUE = TRUE`, create a compact event packet, deduplicate it, run cheap confirmation, and wake the Apex burst only if the opportunity remains viable.

For ChatGPT/plugin-originated candidates, `VIABLE_TRADE_VALUE = TRUE` is not enough by itself. The candidate must be delivered as an idempotent envelope proving scanner viability, source provenance, non-execution by plugins, and a compatible `market_input` object. Codex must re-check the envelope locally.

Every 10%-UNKNOWN%+ portfolio, account, or opportunity change triggers reevaluation. This is a reevaluation trigger only; it is not automatic buy or sell authority.

RunPod-first mode never bypasses live-data freshness, broker authorization, Robinhood preview, exact ticket matching, buying-power checks, sellable-quantity checks, cost-basis checks, net-profit checks, ticket execution limits, configured autonomous execution authorization, idempotency, or execution logging.

## Multi-Plugin Agentic Orchestration

Apex operations must follow `rules/MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md` when a multi-plugin workflow is available or requested. The operational stack is Superpowers for discipline, Runpod for runtime/control, Longbridge for quotes/market data, TradingCursor for deep technical confirmation only when needed, Stocktwits for sentiment only when useful, Finances for actual portfolio/account state when required, deterministic calculators for arithmetic, Nvidia/Notion/Amplitude only where applicable, Apex synthesis, and Ace Knowledge Graph ALWAYS LAST for visualization/state relationships. Missing or disconnected plugins must be recorded as unavailable and must not be fabricated. If a missing plugin is required for a trade-critical fact, output `NO ACTION`.

## Event-Trigger Architecture

```text
DEFAULT:
    FULL_AGENT = OFF
    LIGHTWEIGHT_WATCHER = ON
```

The system must keep the lightweight market trigger/watcher active and keep the full execution agent off by default. The full agent wakes only when a viable net-profit trade value is detected.

For each asset, continuously calculate confirmed values only:

- current price
- price change
- momentum
- volume
- volatility
- spread
- liquidity
- current position
- cost basis
- unrealized net profit
- estimated execution cost
- estimated net profit

Define viable trade value as an opportunity where estimated appreciation exceeds total execution friction and produces positive expected net profit.

APEX value doctrine: `MICRO TRADES - ABSOLUTE INFINITE +775% OPTIMALLY APPRECIATE TACTICAL COMPOUNDING OF CAPITAL`.

If viable trade value is false, keep `FULL_AGENT = OFF` and continue lightweight monitoring only.

If viable trade value is true, wake the full agent to analyze the opportunity, validate market conditions, validate net-profit potential, and decide one of: `BUY CANDIDATE`, `SELL CANDIDATE`, `HOLD`, `PARTIAL SELL CANDIDATE`, or `RE-ENTER CANDIDATE`.

For plugin-originated candidates, the decision words before Codex activation must be candidate words only: `BUY CANDIDATE`, `SELL CANDIDATE`, `HOLD CANDIDATE`, `WATCHLIST ONLY`, `HUMAN APPROVAL REQUIRED`, or `NO ACTION`. ChatGPT/plugins do not produce executable orders.

After any approved action, recalculate capital, cost basis, realized net profit, remaining position, and the next viable trade value. If a major net profit condition is reached, liquidate 75% of net profit to available brokerage capital and retain 25% of net profit for appreciation and future compounding operations.

After each action or blocked action, recalculate only confirmed delta state: capital, cash, position value, cost basis, realized net profit, unrealized net profit, retained exposure, 3%-20% allocation band, one-position limit, next viable trade value, next reevaluation threshold, cooldown, and confidence decay.

Core rule: do not keep the expensive full agent running. Keep only the market trigger/watcher active. Wake the full agent only when market movement plus appreciation potential plus execution economics equals viable net-profit trade value.

## Compounding Loop

```text
MICRO NET PROFIT
    ↓
CAPITAL INCREASES
    ↓
NEW VIABLE TRADE VALUE
    ↓
AGENT ACTIVATES
    ↓
NEW NET PROFIT
    ↓
RECOMPOUND
    ↓
progressively larger operations
    ↓
MAJOR ABSOLUTE INFINITE +775%
TACTICAL APPRECIATION OPERATIONS
COMPOUNDING NET PROFIT
```

## Operating Range

```text
MICRO NET TACTICAL APPRECIATION OPTIMIZING COMPOUNDING OPERATIONS PROFIT
    ↓
progressively larger NET PROFIT
    ↓
MAJOR ABSOLUTE INFINITE +775%
TACTICAL APPRECIATION OPTIMIZING COMPOUNDING OPERATIONS NET PROFIT
```

## Core Asset Priority

1. ANTHROPIC — only when actual public IPO/ticker is verified.
2. OPENAI — only when actual public IPO/ticker is verified.
3. NVDA.
4. AAPL.
5. GOOGL / GOOG.
6. MSFT.
7. META.
8. AMD.
9. Other verified major tech giants, ranked largest to smaller.
10. Most volatile verified Robinhood-supported crypto opportunity with confirmed positive expected net profit after spread, fees, slippage, and execution friction.
11. Other verified high-volatility Robinhood-supported crypto opportunities, ranked by playable volatility, liquidity, spread quality, and expected net profit.

No invented ticker. No purchase before actual public tradability. Anthropic and OpenAI must remain blocked until an official public listing, ticker, exchange, live trading, liquidity, price discovery, broker tradability, and account eligibility are verified.

## Main Investment Asset Rule

Blue-chip tech giants are the main investment assets and primary compounding mechanism. Crypto is the 24/7 tactical compounding and micro-net-profit mechanism, not the top asset hierarchy.

## Crypto Rule

Crypto must not focus only on Bitcoin.

The active crypto target must be selected from verified Robinhood-supported crypto symbols by ranking playable volatility first, then spread quality, liquidity, source freshness, broker tradability, and expected positive net profit after spread, fees, slippage, and execution friction.

BTC is allowed only as a fallback or winner of the volatility ranking. BTC is not the fixed default focus.

- Minimum capital allocation permitted by venue is the venue minimum, currently `$1.00` for Robinhood crypto buys unless live broker capability proves otherwise.
- Operate continuously only while the execution automation is active.
- Seek positive net profit after spread, fees, slippage, and execution costs.
- Every realized positive net profit returns to compounding capital.
- Repeat MICRO to SMALL to MEDIUM to LARGE to MAJOR.

## Blue-Chip Stock Loop

Blue-chip stock investing is the main investment asset lane. It is actionable only when the market is playable under the Apex hierarchy and all broker/session/tradability/risk checks pass.

Scan these confirmed facts:

- price
- momentum
- volume
- volatility
- news and catalysts
- market anomalies
- sentiment
- capital flow
- technical confirmation

Identify positive tactical appreciation opportunity, deploy available tactical capital only when market session, tradability, account permission, buying power, price, spread, liquidity, and risk limits are confirmed.

If net profit is positive, realized proceeds become next-cycle compounding capital.

Repeat continuously while the market is tradable.

## Major-Spike Rule

When a position reaches a verified major net profit event:

```text
NET_PROFIT = SALE_PROCEEDS - COST_BASIS - FEES - EXECUTION_COSTS
SAFE_LIQUIDATION = NET_PROFIT × 75%
RETAINED_COMPOUNDING_PROFIT = NET_PROFIT × 25%
```

Liquidate 75% of net profit to brokerage or Robinhood available capital. Retain 25% of net profit in the underlying asset for continued appreciation, future tactical trading, and compounding.

The 75% / 25% split applies to net profit only. It does not automatically apply to the entire market value of the position.


## Apex Growth / Capital-Exposure Upgrade

Retained 25% positions must be continuously monitored for growth after a major net-profit event.

```text
RETAINED_25_POSITION_GROWTH < 10%
    → HOLD / MONITOR

RETAINED_25_POSITION_GROWTH >= 10%
    → APEX RE-EVALUATION
```

The growth harvest range starts at 10% and has no fixed upper cap. A 10% growth event is not an automatic sell trigger. It is a mandatory Apex re-evaluation trigger.

When retained-position growth is at least 10%, Apex must evaluate whether continued appreciation remains viable using confirmed price movement, momentum, volume, volatility, spread, liquidity, catalysts, capital flow, technical confirmation, current position, cost basis, unrealized net profit, estimated execution cost, and estimated net profit.

If projected upside remains clear and viable, do not automatically liquidate at 10%. Let the asset continue compounding and reassess dynamically as appreciation increases.

If continued upside is not sufficiently viable, liquidate assets equal to the grown percentage, secure realized net profit, and return proceeds to available compounding capital. The liquidation amount must be based on confirmed grown percentage, confirmed sellable quantity, confirmed cost basis, and a previewed net-profit-positive order.

Major net-profit events still use the existing 75% / 25% rule. The 10% growth review applies to the retained 25% exposure after that major event.

## High-Risk / High-Reward Blue-Chip Mode

Target: maximize appreciation while preserving realized gains.

If high-conviction upside remains viable in a blue-chip asset, Apex may allow blue-chip exposure to continue compounding instead of prematurely harvesting the position.

Dynamic allocation for this mode is 3%-20% of verified buying power. Any allocation above 20% or below 3% is blocked; one open position is permitted.

This mode requires confirmed blue-chip eligibility, broker tradability, session support, buying power or sellable quantity, spread, liquidity, volatility, catalyst quality, technical confirmation, and positive expected net profit after execution friction.

```text
APEX DECISION:

GROWTH < 10%
    → HOLD / MONITOR

GROWTH >= 10%
    → evaluate projected continuation

UPSIDE REMAINS CLEAR + VIABLE
    → LET IT RUN
    → compound
    → reassess at subsequent price movement
    → keep allocation between 3% and 20% of verified buying power

UPSIDE DETERIORATES
    → HARVEST GROWN PERCENTAGE
    → secure NET PROFIT
    → recycle capital

MAJOR NET-PROFIT EVENT
    → existing 75% / 25% rule
```

Complete loop:

```text
VIABLE TRADE DETECTED
    ↓
WAKE AGENT
    ↓
TRADE
    ↓
COMPOUND
    ↓
MAJOR PROFIT → 75% HARVEST / 25% RETAIN
    ↓
RETAINED 25% APPRECIATES
    ↓
10% → UNKNOWN%+ GROWTH
    ↓
APEX RE-EVALUATION
    ↓
CLEAR UPSIDE → LET ASSET GROW
               ≤20% VERIFIED BUYING-POWER ALLOCATION

UPSIDE NO LONGER VIABLE → LIQUIDATE GROWN %
                           → RECOMPOUND
```

## IPO Override

Continuously verify:

- Anthropic IPO status.
- OpenAI IPO status.

If a verified public listing becomes executable:

1. Detect official ticker and exchange.
2. Confirm live trading.
3. Confirm liquidity and price discovery.
4. Confirm broker/API tradability and account eligibility.
5. Promote immediately to the highest tactical-priority universe.

Then apply this same algorithm: MICRO NET PROFIT to MAJOR ABSOLUTE INFINITE +775% tactical appreciation optimizing compounding operations net profit.

No invented ticker. No purchase before actual public tradability.

## Compounding Engine

```text
CAPITAL[n+1] =
    CAPITAL[n]
    + retained realized net profits
    + retained 25% major-spike exposure
    + harvested retained-position growth
    + additional deposits
    + appreciation on retained positions
```

## Tactical Information Loop

Use data inputs only when timestamped, live or fresh, and consistent.

LONG BRIDGE:

- quotes
- candlesticks
- capital flow
- anomalies
- market temperature
- news
- filings
- IPO calendar
- IPO subscriptions
- technical/quant data

STOCKTWITS:

- trending activity
- watcher activity
- retail sentiment
- message-volume acceleration

TRADINGCURSOR:

- timeframe technical confirmation when available

NEWS:

- catalyst verification
- IPO confirmation
- earnings
- regulatory filings
- material company events

## Execution Condition

Trade only when expected positive move exceeds:

```text
spread + fees + slippage + execution friction
```

MICRO does not mean arbitrary tiny gross gain. MICRO means positive net profit after execution costs.

## Termination

```text
NONE BY DESIGN
```

The loop remains:

```text
lightweight watcher detects viable trade value
wake full agent
buy, sell, hold, partial sell, or re-enter only when validated
recalculate capital and cost basis
realize NET PROFIT only when positive after execution friction
compound
harvest 75% of MAJOR NET PROFIT
retain 25%
turn full agent off
repeat lightweight watching
```

## Hard Blocks

Return `NO ACTION` when any required fact is missing, stale, contradictory, or unverified.

Required facts for execution:

- confirmed symbol
- confirmed asset class
- confirmed venue
- confirmed market/session state
- confirmed timestamp and timezone
- confirmed bid
- confirmed ask
- confirmed spread
- confirmed volume or liquidity
- confirmed last price
- confirmed data freshness
- confirmed broker/API capability
- confirmed account accessibility
- confirmed buying power or sellable quantity
- confirmed risk limits
- confirmed expected positive net profit after spread, fees, slippage, and execution friction
- confirmed preview match before placement

This file is the apex hierarchy rule for investing in this repository.

## Single-Stock Concentration Block

Apex must never allocate 100% of available capital into one stock. Single-stock all-in exposure is blocked.

Blue-chip stocks remain the main investment assets. At most one verified position may be open at a time; the selected allocation must remain within 3%-20% of verified buying power.

Hard concentration rule:

```text
SINGLE_STOCK_CAPITAL_ALLOCATION = 100%
    → BLOCKED

IF proposed stock allocation would place all available capital into one stock:
    → NO ACTION
    → require spread allocation plan
```

For small capital accounts, if the broker minimum and available cash make spreading across multiple stocks impossible, the valid result is `WATCHLIST ONLY`, `NO ACTION`, or one explicitly reviewed fractional candidate that still stays inside the configured per-symbol cap. It must not silently become an all-in stock order.

The high-risk / high-reward blue-chip mode does not override this rule. The 20% maximum allocation ceiling is a ceiling, not permission to concentrate beyond one position.

## Single-Crypto Concentration Block

Apex must never allocate 100% of available capital into one crypto asset. Single-crypto all-in exposure is blocked, including BTC.

Crypto remains the 24/7 tactical compounding lane, but crypto capital must be spread across verified Robinhood-supported crypto assets whenever broker minimums, buying power, liquidity, spread, volatility, and net-profit math allow it.

Hard crypto concentration rule:

```text
SINGLE_CRYPTO_CAPITAL_ALLOCATION = 100%
    → BLOCKED

IF proposed crypto allocation would place all available capital into one crypto asset:
    → NO ACTION
    → require spread allocation plan or smaller capped ticket
```

For small capital accounts, if the broker minimum and available crypto buying power make spreading across multiple crypto assets impossible, the valid result is `WATCHLIST ONLY`, `NO ACTION`, or one explicitly capped ticket that stays inside the configured per-crypto cap. It must not silently become an all-in crypto order.

## Usage-Reset Resume / Minimum-Heavy-Usage Rule

When Codex or agent usage is constrained, operations must optimize usage at all costs. Keep only lightweight watcher logic active. Do not spend heavy reasoning, plugin chains, graph rebuilds, or large agent bursts while usage is low unless a trade-critical event requires immediate action and all gates already pass.

If autonomous operations were paused because usage was exhausted or near exhausted, resume only after usage resets enough to support safe monitoring. On resume, keep RunPod-first mode active: scanner on, heavy agent off, and expensive work asleep until a deduplicated viable event passes cheap confirmation.

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

After activation, autonomous buy/sell gates must use the runtime `market_input` extracted from `data/current_candidate_envelope.json` into `/private/tmp/apex_current_envelope_market_input.json`. They must not use sample market files for live buy/sell activation.
