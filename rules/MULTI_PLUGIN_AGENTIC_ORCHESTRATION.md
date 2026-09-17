# MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md

This file defines the mandatory multi-plugin agentic orchestration order for Apex investing operations.

## ChatGPT/Plugin Scanner Boundary

ChatGPT/plugins may run continuous scanning, calculations, projections, and candidate qualification. They do not execute trades and do not wake Codex directly by assertion.

Their maximum authority is a qualified candidate envelope with:

- `created_by = CHATGPT_PLUGIN_SCANNER`
- `scanner_viable = true`
- `requested_codex_activation = true`
- `plugins_execute_trades = false`
- `broker_order_submitted = false`
- at least two fresh provenance records
- a `market_input` payload that passes local APEX validation

Codex starts from `FULL_AGENT = OFF`. It independently validates the envelope through `algorithms/candidate_envelope_gate.py`.

If validation prints `VIABLE: false`, Codex stays dormant and the scanner continues. If validation prints `VIABLE: true` and `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS`, Codex may run the existing autonomous agentic buy/sell workflow, then return to sleep.

## Default Operating State

```text
FULL_AGENT = OFF
LIGHTWEIGHT_WATCHER = ON
```

The lightweight watcher monitors for investment potential. The full agent wakes only when market movement, appreciation potential, and execution economics produce a viable positive expected net-profit trade value. After any action, blocked action, or synthesis, the full agent returns to off.

## Mandatory Plugin Order

Every Apex multi-plugin operation must preserve this order:

1. Superpowers
2. Longbridge
3. Notion
4. Carta CRM
5. TradingCursor
6. Precise Special Functions
7. Stocktwits
8. Finances
9. Apex Synthesis
10. Ace Knowledge Graph
11. Sleep / Return to Watcher

Ace Knowledge Graph is always last before sleep/return-to-watcher.

## 1. Superpowers — Operational Control Layer

Start every operation with Superpowers when available.

Function:

- inspect current objective
- preserve commanded trading architecture
- identify required analysis path
- validate workflow before execution
- prevent uncontrolled modification of rules

Input:

- market trigger
- current portfolio state
- targeted asset
- prior trade state
- current compounding rules

Output: `AUTHORIZED_ANALYTICAL_WORKFLOW`, then pass to Longbridge.

## 2. Longbridge — Primary Market Intelligence

Use Longbridge as the primary securities-data engine when connected and available.

Collect:

- live quote
- price change
- candlesticks
- volume
- liquidity
- spread or order-book context where available
- volatility
- capital flow
- anomalies
- market temperature
- company fundamentals
- analyst consensus
- valuation
- news
- filings
- catalysts
- IPO calendar/status
- portfolio or position information where connected

Target universe:

- Anthropic, once publicly listed and executable
- OpenAI, once publicly listed and executable
- NVDA
- AAPL
- GOOGL / GOOG
- MSFT
- META
- AMD
- additional qualifying major technology assets
- crypto where supported

Output: `MARKET_STATE`, then pass to Notion.

## 3. Notion — Operational Memory / Documentation

Use Notion as operational memory and documentation when connected and available.

Store or update:

- algorithm version
- asset watch universe
- trade hypotheses
- trigger conditions
- executed analytical decisions
- compounding state
- 75% / 25% harvest decisions
- retained-position growth
- no separate compounding-percentage ceiling
- IPO monitoring state
- post-operation reviews

Notion does not replace live market data. Notion records are documentation, not market-price authority.

Output: `CURRENT_OPERATION_CONTEXT`, then pass to Carta CRM.

## 4. Carta CRM — Structured Relationship / Entity Context

Use Carta CRM wherever available capabilities materially apply.

Function:

- organize applicable company or entity context
- preserve relevant structured records
- connect company-level information to the workflow

If Carta CRM has no applicable capability for the current market event, record `NO_APPLICABLE_ACTION` and continue. Do not fabricate a CRM result to force usage.

Output: `ENTITY_CONTEXT`, then pass to TradingCursor.

## 5. TradingCursor — Technical Confirmation

Request technical analysis for the active asset and appropriate timeframe when connected and available.

Check:

- trend
- momentum
- support and resistance
- technical continuation
- reversal conditions
- timeframe alignment

For stocks, use the appropriate listed exchange. For crypto, use the appropriate crypto venue or pair.

Output: `TECHNICAL_SIGNAL`, then pass to Precise Special Functions.

## 6. Precise Special Functions — Mathematical Verification When Applicable

Use only where an actual supported special-function calculation contributes to the analysis.

Supported calculations:

- Gamma
- Riemann zeta
- Bessel J/Y/I/K
- hypergeometric 2F1
- elliptic integrals

If the current operation does not require one, set `SPECIAL_FUNCTION_STATUS = NOT_APPLICABLE`. Do not invent a trading application merely to force the plugin into the decision.

Output: `MATHEMATICAL_VERIFICATION_STATUS`, then pass to Stocktwits.

## 7. Stocktwits — Retail Sentiment / Attention Layer

Check when connected and available:

- current sentiment
- sentiment history
- message-volume acceleration
- trending status
- watcher activity
- symbol pulse
- relevant market conversation

Use sentiment as corroborating evidence only. Sentiment is never sole trade authority.

Output: `SENTIMENT_STATE`, then pass to Finances.

## 8. Finances — Personal Capital / Portfolio Layer

Use connected financial data when available.

Check:

- linked investment accounts
- available capital
- current holdings
- position values
- cost basis
- investment transactions
- realized activity
- portfolio concentration
- capital already exposed

Calculate against user rules:

```text
STARTING CAPITAL = $5

MAJOR PROFIT RULE:
    75% OF NET PROFIT → liquid available brokerage capital
    25% OF NET PROFIT → retained compounding exposure

RETAINED 25%:
    monitor growth from 10% → UNKNOWN%+

HIGH-RISK / HIGH-REWARD BLUE-CHIP MODE:
    allow compounding exposure when justified by current verified gates
```

Verify that proposed action does not exceed commanded capital-exposure rules.

Output: `CAPITAL_STATE`, `POSITION_STATE`, and `COMPOUNDING_STATE`, then pass to Apex synthesis.

## Apex Synthesis

Combine the ordered inputs:

```text
SUPERPOWERS workflow validation
+ LONGBRIDGE market intelligence
+ NOTION operational context
+ CARTA CRM entity context
+ TRADINGCURSOR technical analysis
+ PRECISE SPECIAL FUNCTIONS verification status
+ STOCKTWITS sentiment
+ FINANCES personal-capital state
```

Calculate:

```text
VIABLE_TRADE_VALUE = expected appreciation - spread - fees - slippage - execution friction
```

Require expected net result greater than zero and market/technical evidence supporting action.

If not viable, keep `FULL_AGENT = OFF` and return to lightweight watcher.

If viable, wake full agent and decide one of:

- BUY CANDIDATE
- SELL CANDIDATE
- HOLD
- PARTIAL HARVEST CANDIDATE
- CONTINUE COMPOUNDING CANDIDATE

Candidate status is not trade execution authority. Live execution is allowed only after Codex activation and only through the existing autonomous broker authorization, order preview, exact ticket match, idempotency, execution logging, configured execution authorization, and fail-closed risk gates.

If major net profit is confirmed, apply the 75% / 25% rule.

If retained 25% growth is at least 10%, Apex reassesses continuation. If projections remain sufficiently strong, let winner run. If projections deteriorate, harvest grown percentage.

If high-conviction blue-chip appreciation remains viable, permit compounding exposure subject to the existing capital, position, liquidity, risk, broker, and execution gates.

After operation, update operational records where connected, update financial state where connected, and return full agent to off.

## 9. Ace Knowledge Graph — Final Synthesis Map

Always place Ace Knowledge Graph last when graph capability is connected and the operation requires a final synthesis map.

Build graph of:

- asset
- market trigger
- Longbridge evidence
- technical signal
- sentiment signal
- capital exposure
- current position
- net-profit state
- 75% harvested capital
- 25% retained capital
- retained-growth percentage
- no separate compounding-percentage ceiling
- IPO catalysts
- final Apex decision

Relationships should show:

- why the agent activated
- what evidence supported activation
- how capital was allocated
- whether position was harvested or retained
- how profits feed the next compounding cycle

## Final Loop

```text
SUPERPOWERS
    ↓
LONGBRIDGE
    ↓
NOTION
    ↓
CARTA CRM
    ↓
TRADINGCURSOR
    ↓
PRECISE SPECIAL FUNCTIONS
    ↓
STOCKTWITS
    ↓
FINANCES
    ↓
APEX SYNTHESIS
    ↓
ACE KNOWLEDGE GRAPH
    ↓
SLEEP / RETURN TO WATCHER
    ↓
NEXT VIABLE TRADE EVENT
```

## Missing Plugin Rule

If a mandatory plugin is not connected or not callable in the current environment, record `PLUGIN_UNAVAILABLE` for that plugin and continue only if the missing plugin is not required for the specific decision. If the missing plugin is required to confirm a trade-critical fact, output `NO ACTION`.

Never fabricate plugin output. Never use stale documentation as live market authority.


## Multi-Lane Synergy Research Layer

Before Step 2 (Longbridge) is consulted, the scanner's own multi-lane
synergy research layer (`rules/MULTI_LANE_SYNERGY_RESEARCH_LAW.md`) has
already been running continuously in the background across every blue-chip
and tracked-crypto symbol, combining dedicated MATH, HISTORY, RESEARCH, and
TEMPORAL lanes into a per-symbol `APPRECIATION_LIKELY` / `DEPRECIATION_LIKELY`
/ `NEUTRAL` / `INSUFFICIENT_SYNERGY_DATA` forecast at
`data/lane_synergy/<symbol>/synergy.json`.

When available and fresh, Apex Synthesis treats this forecast as
corroborating evidence at the same authority level as sentiment: it may
support or weaken a candidate decision, but it is never sole trade
authority, never bypasses a gate, and `INSUFFICIENT_SYNERGY_DATA` is never
read as a directional call. See `rules/MULTI_LANE_SYNERGY_RESEARCH_LAW.md`
for the full binding definition.

## RunPod-first controller overlay

RunPod is the always-on scanner/runtime/controller. It performs cheap scanning, state tracking, cooldowns, deduplication, event packet creation, and wake/sleep control. The mandatory plugin order applies only after RunPod has confirmed a non-duplicate viable event that justifies waking the agentic burst.

RunPod must return expensive agents to sleep after synthesis, action, blocked action, or `NO ACTION`.

When ChatGPT/plugins are the continuous scanner, they replace only the cheap scanning/calculation/projection layer. They do not replace Codex validation, APEX risk controls, broker gates, execution logs, configured autonomous authorization, or fail-closed order handling.

## Concentration Check in Apex Synthesis

Apex Synthesis must include a single-stock concentration check before any stock candidate is considered. If the proposed stock action puts 100% of available capital into one stock, the decision is `NO ACTION`.

Finances and Apex Synthesis must prefer spread exposure across verified eligible blue-chip assets when stock execution is allowed. If spreading is impossible because the account is too small for broker minimums, the output is `WATCHLIST ONLY` or `NO ACTION`, not an all-in stock order.

## Crypto Concentration Check in Apex Synthesis

Apex Synthesis must include a single-crypto concentration check before any crypto candidate is considered. If the proposed crypto action puts 100% of available capital into one crypto asset, the decision is `NO ACTION`.

Finances and Apex Synthesis must prefer spread exposure across verified broker-supported crypto assets when crypto execution is allowed. If spreading is impossible because the account is too small for broker minimums, the output is `WATCHLIST ONLY`, `NO ACTION`, or a capped ticket inside the configured per-crypto limit.
