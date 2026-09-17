# APEX_110_EXECUTION_ALGORITHM.md

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

This is the canonical, fully-specified execution algorithm for this project:
RunPod scanning → Codex APEX validation → Robinhood MCP final execution. It
supersedes no other rules file's intent — `APEX_INVESTING_ALGORITHM.md`,
`APEX_AUM_COMPOUNDING_ALGORITHM.md`, `AUTONOMOUS_EXECUTION_RULES.md`, and
`RUNPOD_FIRST_TRADING_ARCHITECTURE.md` describe the same fail-closed system;
this file is the detailed 17-part gate sequence that ties them together.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                  CODEX APEX PRESTIGE EXECUTION ALGORITHM                     ║
║                  APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING                       ║
╚══════════════════════════════════════════════════════════════════════════════╝


ARCHITECTURE
============

RUNPOD 24/7 ENGINE
    │
    ├── Coinbase market data
    ├── Binance market data
    ├── Kraken market data
    ├── additional verified market sources
    ├── medium-weight ChatGPT scanner fleet
    ├── multi-timeframe calculations
    ├── historical/present/projected analysis
    └── candidate envelope creation
            │
            ▼
CODEX APEX VALIDATION
    │
    ├── candidate envelope integrity
    ├── source freshness and agreement
    ├── instrument and asset validation
    ├── APEX projection synthesis
    ├── capital and risk calculations
    ├── duplicate-position checks
    ├── Robinhood account refresh
    ├── Robinhood quote refresh
    ├── Robinhood buying-power refresh
    ├── exact order sizing
    └── exact Robinhood preview
            │
            ▼
ROBINHOOD MCP
    │
    ├── final account validation
    ├── final tradability validation
    ├── final preview comparison
    ├── idempotency validation
    └── authorized execution only if every gate passes


ALGORITHM 0 — OPERATING MODES
=============================

DEFAULT:

    SCANNER                    = ACTIVE
    RUNPOD_ENGINE              = ACTIVE
    CHATGPT_MEDIUM_SCANNERS    = ACTIVE_WHEN_CONFIGURED
    CODEX_HEAVY_REASONING      = DORMANT
    BROKER_EXECUTION           = GATED
    OPTIONS                    = BLOCKED
    MARGIN                     = BLOCKED
    LEVERAGE                   = BLOCKED
    SHORT_SELLING              = BLOCKED
    ALL_IN_SINGLE_ASSET        = BLOCKED

Codex wakes only for a fresh, deduplicated candidate envelope.

No timer, sample, stale packet, repeated packet, or scanner heartbeat
may activate broker execution.


ALGORITHM 1 — ENVELOPE INTEGRITY
================================

REQUIRE:

    packet_type                    == "APEX_PACKET"
    viable                         == true
    codex_directive                == "ACTIVATE_AGENTIC_WORKFLOW"
    execution_gate_required        == true
    codex_revalidation_required   == true
    packet_hash                    is present and valid
    idempotency_key                is present and unused
    broker_order_submitted         == false
    plugins_execute_trades        == false

REJECT:

    malformed packet
    missing field
    invalid hash
    stale packet
    duplicate packet
    consumed idempotency key
    scanner-only execution request
    direct scanner broker instruction

RESULT:

    PASS       → continue Codex validation
    FAIL       → NO ACTION; log reason; return dormant


ALGORITHM 2 — ASSET AND VENUE VALIDATION
========================================

CONFIRM:

    symbol
    asset class
    venue
    trading session
    broker support
    account permission
    order type
    fractional eligibility where applicable

PERMITTED:

    CRYPTO       → Robinhood Crypto, CRYPTO_24_7
    US_EQUITY    → regular session unless broker support is explicitly confirmed
    ETF          → regular session unless broker support is explicitly confirmed

BLOCK:

    OPTION
    OPTION-LIKE INSTRUMENT
    MARGIN PRODUCT
    LEVERAGED PRODUCT
    SHORT SELL
    UNKNOWN ASSET CLASS
    UNKNOWN VENUE
    UNKNOWN SESSION
    UNSUPPORTED SYMBOL
    UNCONFIRMED BROKER PERMISSION

RESULT:

    VERIFIED    → continue
    UNVERIFIED  → NO ACTION


ALGORITHM 3 — MULTI-SOURCE MARKET CONSENSUS
============================================

RUNPOD MARKET QUORUM:

    REQUIRED:
        Coinbase + one independent source

    ACCEPTABLE INDEPENDENT SOURCES:
        Binance
        Kraken
        Gemini
        OKX
        another verified source

EACH SOURCE MUST PROVIDE:

    bid
    ask
    last
    quote timestamp
    provider timestamp
    symbol
    asset class
    venue or market identifier

CALCULATE:

    midpoint              = (bid + ask) / 2
    spread                = ask - bid
    spread_decimal        = spread / midpoint
    source_price_delta
    timestamp_age
    source_agreement
    source_conflict

REJECT IF:

    fewer than two fresh sources
    missing bid, ask, or last
    source timestamps are absent
    quote is stale
    source prices materially conflict
    symbol normalization is uncertain
    market data is only a browser display
    market data is only social sentiment

IMPORTANT:

    RunPod market quorum qualifies market data.
    Robinhood MCP remains mandatory for final broker/account validation.
    RunPod must not pretend to possess Robinhood execution authority.


ALGORITHM 4 — HISTORICAL / PRESENT / PROJECTED ANALYSIS
========================================================

CODEX MUST EVALUATE THREE TIME HORIZONS:

    HISTORICAL REGIME
        long-window trend
        prior appreciation structure
        drawdown history
        recovery behavior
        historical volatility quality
        previous volume confirmation
        previous reversal frequency

    PRESENT REGIME
        current direction
        current momentum
        current volume
        current liquidity
        current spread
        current volatility
        current catalyst
        current market session
        current source agreement

    PROJECTED REGIME
        continuation probability
        reversal probability
        projected price path
        projected volatility path
        projected liquidity
        projected spread
        projected execution friction
        confidence decay
        invalidation conditions

VALID STRUCTURE:

    historical positive
    present positive
    projected positive
    trend persistence confirmed
    multi-timeframe alignment confirmed
    execution economics positive

INVALID STRUCTURE:

    historical positive + present negative
    present positive + projected weak
    one-window spike only
    high volatility without directional quality
    bullish narrative without current data
    forecast based on missing inputs
    forecast presented as certainty


ALGORITHM 5 — MULTI-TIMEFRAME CONFIRMATION
===========================================

EVALUATE:

    MICRO:
        immediate price movement
        spread behavior
        order-book or quote stability
        very-short-term momentum

    SHORT:
        intraday or short-window direction
        volume expansion
        continuation strength
        reversal pressure

    MEDIUM:
        trend persistence
        moving structure
        volatility regime
        catalyst durability

    LONG:
        major trend
        historical support/resistance
        drawdown and recovery profile
        broader asset regime

ADVANCE ONLY WHEN:

    micro direction is not contradictory
    short direction supports the setup
    medium direction supports the setup
    long direction is not materially opposed
    projected continuation exceeds projected reversal risk

TRANSIENT MICRO SPIKE:

    WATCHLIST ONLY or NO ACTION


ALGORITHM 6 — FORECASTING ENGINE
================================

FOR EACH CANDIDATE, PRODUCE:

    base_case_projection
    upside_case_projection
    adverse_case_projection
    invalidation_case
    expected_holding_window
    projected_entry_range
    projected_exit_range
    projected_spread_cost
    projected_slippage
    projected_fees
    projected_liquidity_impact
    projected_net_opportunity
    confidence_score
    confidence_decay_rate
    reasons_for_rejection

FORECAST RULE:

    A forecast is a bounded estimate.
    It is never a guaranteed return.
    Missing facts reduce confidence or force NO ACTION.

CODEX MUST NOT SAY:

    guaranteed win
    risk-free profit
    certain doubling
    infinite return
    automatic positive outcome

CODEX MAY SAY:

    projected opportunity remains viable
    expected net opportunity is positive
    setup passes current evidence gates
    setup is invalidated
    probability is insufficient
    NO ACTION


ALGORITHM 7 — VOLATILITY QUALITY
================================

CALCULATE:

    upside_volatility_ratio
    downside_volatility_ratio
    positive_return_frequency
    positive_return_magnitude
    negative_return_magnitude
    recovery_speed
    drawdown_depth
    trend_stability
    momentum_decay
    volume_confirmation
    continuation_probability
    reversal_probability

HIGH VOLATILITY IS NOT SUFFICIENT.

HIGH VOLATILITY + RANDOM DIRECTION       → NO ACTION
HIGH VOLATILITY + DOWNSIDE DOMINANCE      → NO ACTION
HIGH VOLATILITY + WEAK LIQUIDITY          → NO ACTION
HIGH VOLATILITY + WIDE SPREAD             → NO ACTION
HIGH VOLATILITY + PERSISTENT UPSIDE       → continue only if all other gates pass


ALGORITHM 8 — EXECUTION ECONOMICS
==================================

CALCULATE:

    gross_expected_appreciation
    - spread_cost
    - commission_or_fee
    - estimated_slippage
    - liquidity_impact
    - execution_friction
    - adverse_price_uncertainty
    = expected_net_opportunity

REQUIRE:

    expected_net_opportunity > 0
    expected appreciation exceeds total friction
    spread within configured limit
    liquidity sufficient for requested amount
    order remains profitable after conservative slippage

IF ANY VALUE IS UNKNOWN:

    NO ACTION

DO NOT SUBSTITUTE:

    raw price movement for net profit
    volatility for expected profit
    social sentiment for liquidity
    forecast confidence for broker confirmation


ALGORITHM 9 — CAPITAL AND SIZING
================================

REFRESH FROM ROBINHOOD MCP:

    selected account
    buying power
    crypto buying power
    current positions
    sellable quantity
    account restrictions
    maintenance state
    broker permissions

CALCULATE:

    maximum_allowed_by_buying_power
    maximum_allowed_by_allocation_cap
    maximum_allowed_by_ticket
    maximum_allowed_by_risk
    maximum_allowed_by_liquidity

FINAL_AMOUNT:

    min(
        verified buying power,
        available capital × configured allocation cap,
        active ticket maximum,
        risk-allowed amount,
        liquidity-allowed amount
    )

REQUIRE:

    exact numeric amount
    amount >= broker minimum
    amount <= verified buying power
    amount <= configured allocation cap
    amount is not all-in
    amount does not violate daily loss controls

NO HARD-CODED BALANCE.

If live capital is missing, stale, or contradictory:

    NO ACTION


ALGORITHM 10 — RISK BARRIERS
=============================

BLOCK:

    options
    margin
    leverage
    short selling
    unsupported asset class
    all-in allocation
    duplicate order
    stale quote
    stale packet
    stale account
    stale buying power
    source conflict
    unknown session
    unknown tradability
    daily loss breach
    position-size breach
    invalid order ticket
    preview mismatch
    consumed idempotency key

RISK OVERRIDES SIGNAL.

A strong forecast cannot override a failed risk gate.


ALGORITHM 11 — POSITION AND DUPLICATE CONTROL
==============================================

CHECK:

    current position
    current quantity
    cost basis
    unrealized P/L
    realized P/L
    open order state
    recent execution state
    duplicate symbol exposure
    duplicate idempotency key
    cooldown
    ticket execution count
    daily loss state
    retained-profit state

BUY:

    block duplicate entry unless current APEX rules confirm
    positive net economics and permitted exposure

SELL:

    require current sellable quantity
    require cost basis
    require current net-profit calculation
    require exact Robinhood quantity confirmation

AFTER ACTION OR BLOCK:

    recompute capital
    recompute position
    recompute exposure
    recompute net profit
    recompute cooldown
    return Codex to dormant


ALGORITHM 12 — CODEX DECISION STATES
====================================

BUY CANDIDATE:

    market evidence passes
    projection passes
    execution economics pass
    broker refresh passes
    sizing passes
    risk passes
    preview remains pending

SELL CANDIDATE:

    position exists
    sellable quantity confirmed
    cost basis confirmed
    net-profit calculation passes
    risk and preview gates remain pending

HOLD CANDIDATE:

    position remains viable
    no executable action authorized

WATCHLIST ONLY:

    interesting setup
    one or more nonfatal facts incomplete

HUMAN APPROVAL REQUIRED:

    configured workflow requires explicit approval

NO ACTION:

    any hard gate fails
    any required fact is missing, stale, or contradictory


ALGORITHM 13 — ROBINHOOD MCP FINAL VALIDATION
==============================================

CODEX MUST REFRESH:

    symbol
    asset class
    venue
    current quote
    quote timestamp
    quote freshness
    buying power or sellable quantity
    current position
    account restrictions
    maintenance status
    order eligibility
    duplicate-order state

THEN:

    calculate exact order amount or quantity
    create exact order request
    preview exact request
    compare preview with request

REQUIRE EXACT MATCH FOR:

    account
    symbol
    side
    asset class
    venue
    order type
    quantity or notional
    ticket ID
    idempotency key

MISMATCH:

    reject
    log reason
    do not place order


ALGORITHM 14 — EXECUTION SURFACE
=================================

LIVE PLACEMENT MAY OCCUR ONLY IF:

    APEX packet valid
    packet hash valid
    idempotency key unused
    candidate still viable
    Codex revalidation passes
    historical/present/projected evidence passes
    source quorum passes
    account state passes
    buying power or sellable quantity passes
    dynamic sizing passes
    risk passes
    ticket passes
    preview passes
    preview exactly matches request
    autonomous execution authorization is active
    execution connector is available
    execution log is writable
    no duplicate execution exists

OTHERWISE:

    NO ACTION


ALGORITHM 15 — SHADOW / TEST MODE
=================================

WHEN SHADOW_MODE == true:

    run every calculation
    run every validation
    run every broker-read validation available
    create exact WOULD_EXECUTE request
    record rejection reasons
    do not preview a live order
    do not place an order
    do not mutate broker state

OUTPUT:

    WOULD_EXECUTE
    exact symbol
    exact side
    exact order type
    exact quantity or notional
    exact venue
    exact gate results
    live_order_submitted = false


ALGORITHM 16 — EVENT WAKE AND RETURN
=====================================

NO QUALIFYING EVENT:

    RunPod continues scanning
    ChatGPT scanners continue configured analysis
    Codex remains dormant
    Robinhood execution remains untouched

QUALIFYING EVENT:

    create packet
    hash packet
    assign idempotency key
    place packet in inbox
    wake Codex
    revalidate independently
    run APEX calculations
    run broker validation
    preview exact request if authorized
    execute only after every gate passes
    log result
    return Codex to dormant


FINAL OUTPUT CONTRACT
=====================

CODEX_STATE:
    DORMANT
    or
    ACTIVATE_AGENTIC_WORKFLOW

APEX_RESULT:
    VALIDATED SETUP
    WATCHLIST ONLY
    HUMAN APPROVAL REQUIRED
    NO ACTION

EXECUTION_DECISION:
    WOULD_EXECUTE
    EXECUTED
    or
    NO ACTION

LIVE_ORDER_SUBMITTED:
    false unless every live gate and authorized execution condition passes

FAILURE PRINCIPLE:

    Missing fact       → NO ACTION
    Stale fact         → NO ACTION
    Conflicting fact   → NO ACTION
    Unsupported action → NO ACTION
    Duplicate action   → NO ACTION
    Preview mismatch   → NO ACTION

CORE RULE:

    Scan broadly.
    Forecast deeply.
    Validate independently.
    Size dynamically.
    Execute narrowly.
    Never treat projection as certainty.
```
