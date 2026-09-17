# APEX_110_AUM_COMPOUNDING_NO_INTEREST.md

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

This is the canonical AUM/compounding ledger specification pasted directly by
the user, with one explicit resolution applied: the pasted text below excludes
"borrowed funds" and says "NO BORROWING" with no carve-out, which conflicted
with `rules/APEX_AUM_COMPOUNDING_ALGORITHM.md`'s "legally transferred family
funds are permitted capital" language added earlier in the same session. The
user resolved the conflict explicitly: **family funds still count as
capital.** Read every "borrowed funds" / "NO BORROWING" reference below as
scoped to broker margin, leverage, and short-term broker borrowing —
**not** to legally transferred family capital that the connected broker
confirms as available cash. Family capital is external deposit, not broker
borrowing, once broker-confirmed.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║              APEX CODEX AUM COMPOUNDING ALGORITHM — NO INTEREST              ║
║              APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING                           ║
╚══════════════════════════════════════════════════════════════════════════════╝


CORE OBJECTIVE
==============

Grow verified deployable AUM only through:

    1. external capital actually received
    2. realized net trading profit
    3. retained capital deliberately recycled into the next approved trade

EXCLUDE:

    interest income
    dividends unless explicitly included as verified realized income
    leverage
    margin
    borrowed funds (broker margin/leverage/short-term broker borrowing;
        legally transferred family capital that the broker confirms as
        available cash is external deposit, not borrowed funds)
    projected profits
    unrealized gains
    unverified balances
    paper appreciation
    guaranteed-return assumptions


AUM DEFINITIONS
===============

GROSS_AUM:

    verified cash
  + current market value of eligible holdings
  + verified unsettled or pending assets only when broker confirms availability

DEPLOYABLE_AUM:

    verified cash buying power
  + verified crypto buying power
  + verified sellable proceeds
  - reserved obligations
  - pending orders
  - required risk reserves

COMPOUNDING_AUM:

    beginning deployable AUM
  + verified external deposits
  + verified realized net profit
  - verified withdrawals
  - realized net losses
  - fees
  - spreads
  - slippage
  - execution friction
  - applicable tax reserve

UNREALIZED_PROFIT:

    tracked for information
    never credited as realized compounding capital
    never used to justify a larger order by itself


PRIMARY EQUATION
================

For each completed accounting period:

    AUM[t+1] =
        AUM[t]
      + NET_EXTERNAL_INFLOWS[t]
      + REALIZED_NET_PROFIT[t]
      - REALIZED_NET_LOSS[t]
      - WITHDRAWALS[t]
      - FEES[t]
      - EXECUTION_COSTS[t]
      - TAX_RESERVE[t]


TRADE-LEVEL NET PROFIT
======================

For a completed buy/sell cycle:

    GROSS_PROCEEDS
      - ORIGINAL_COST_BASIS
      - SPREAD_COST
      - BROKER_FEES
      - NETWORK_OR_TRANSACTION_FEES
      - SLIPPAGE
      - LIQUIDITY_IMPACT
      - EXECUTION_FRICTION
      - APPLICABLE_TAX_RESERVE
      = REALIZED_NET_PROFIT


NO-INTEREST RULE
================

    INTEREST_INCOME = 0

The algorithm must not create synthetic growth from:

    interest
    APR
    yield
    staking yield
    lending yield
    dividends
    projected appreciation
    forecasted appreciation

unless the user explicitly creates a separate verified income lane.

This AUM engine compounds trading results only.


CAPITAL-ALLOCATION LADDER
=========================

Every new cycle uses only verified current buying power.

    MAX_TRADE_AMOUNT =
        MIN(
            verified buying power,
            configured allocation cap,
            active ticket maximum,
            risk-allowed amount,
            liquidity-allowed amount
        )

Allocation operates inside the configured 3%–20% tactical band.

The exact percentage is selected only after:

    current volatility
    liquidity
    spread
    downside risk
    drawdown profile
    source agreement
    broker buying power
    current position exposure
    daily loss state
    execution friction

A larger percentage is never justified by confidence language alone.


SKYSCRAPER AUM LADDER
=====================

Each floor is a verified capital state, not a prediction.

FLOOR 00 — BASE CAPITAL
    verified starting deployable AUM

FLOOR 01 — FIRST REALIZED NET PROFIT
    beginning AUM
    + realized net profit
    = new verified deployable capital

FLOOR 02 — REINVESTMENT
    next trade amount calculated from new verified AUM
    no automatic increase from unrealized gains

FLOOR 03 — CAPITAL PRESERVATION
    retain uncommitted cash
    preserve risk reserve
    prevent all-in exposure

FLOOR 04 — REPEATED NET PROFIT
    verified realized profit is added to AUM
    next sizing recalculated from live broker state

FLOOR 05 — LOSS CONTROL
    realized loss reduces AUM
    allocation cap recalculates downward
    cooldown or NO ACTION may activate

FLOOR 06 — POSITION GROWTH
    unrealized appreciation is monitored
    it is not treated as spendable profit

FLOOR 07 — PROFIT REALIZATION
    profit becomes compounding capital only after sale
    broker confirms settlement and proceeds

FLOOR 08 — RETAINED PROFIT
    retained capital remains exposed only if:
        position remains viable
        downside remains acceptable
        liquidity remains sufficient
        broker confirms the position

FLOOR 09 — CAPITAL RECYCLE
    realized net proceeds return to the compounding pool
    next trade uses a fresh APEX calculation

FLOOR 10 — SCALE
    position size increases only because verified AUM increased
    never because a forecast sounded stronger

FLOOR 11 — DRAWdown RESET
    after a material loss:
        reduce allocation
        reassess volatility
        reassess source agreement
        reassess liquidity
        reassess strategy performance
        block if risk limits fail

FLOOR 12 — AUM GOVERNANCE
    every dollar must have a source:
        deposited
        realized profit
        realized loss
        withdrawal
        fee
        reserve
        current position value

FLOOR 13 — VERIFIED COMPOUNDING
    AUM increases only when the ledger proves it

FLOOR 14 — NO-ACTION FLOOR
    missing broker data
    missing buying power
    stale quote
    source conflict
    invalid position state
    negative expected net opportunity
        → NO ACTION


GEOMETRIC COMPOUNDING
=====================

If a period produces a verified net return r[t]:

    AUM[t+1] = AUM[t] × (1 + r[t])

For multiple periods:

    AUM[n] =
        AUM[0]
        × (1 + r[1])
        × (1 + r[2])
        × ...
        × (1 + r[n])

But:

    r[t] must be realized net return
    r[t] must include losses and costs
    r[t] must exclude external deposits and withdrawals
    r[t] must not be a forecast
    r[t] must not be treated as guaranteed

If there is a loss:

    r[t] < 0

Losses compound downward just as gains compound upward.


CASH-FLOW-ADJUSTED AUM
======================

External deposits and withdrawals are not investment performance.

For each period:

    START_AUM
  + DEPOSITS
  - WITHDRAWALS
  = CAPITAL_BASE

    END_AUM
  - CAPITAL_BASE
  = PERIOD_NET_RESULT

For performance measurement:

    separate:
        capital contribution
        withdrawal
        realized trading profit
        realized trading loss
        unrealized position change
        fees
        taxes
        execution costs

Codex must never label a deposit as profit.


APEX ENTRY ALGORITHM
====================

A candidate may enter the compounding loop only if:

    fresh source quorum passes
    symbol is confirmed
    asset class is confirmed
    venue is confirmed
    session is confirmed
    historical regime is acceptable
    present regime is acceptable
    projected regime is acceptable
    trend persistence passes
    multi-timeframe alignment passes
    volatility quality passes
    liquidity passes
    spread passes
    expected net opportunity is positive
    duplicate-position check passes
    current AUM is verified
    buying power is verified
    risk limits pass
    ticket is valid
    idempotency is fresh

Otherwise:

    NO ACTION


APEX EXIT / PROFIT-REALIZATION ALGORITHM
========================================

A position is not sold merely because it is profitable.

Codex must evaluate:

    current price
    current spread
    current liquidity
    current position
    original cost basis
    realized and unrealized P/L
    projected continuation
    reversal probability
    downside risk
    exit friction
    net proceeds

Sell only if:

    sellable quantity is confirmed
    exit remains viable
    net proceeds are positive after all costs
    the action does not violate risk controls
    Robinhood preview matches the exact request

After a confirmed sale:

    realized_net_profit =
        proceeds
      - cost_basis
      - all confirmed costs

    add only realized_net_profit to compounding AUM


AUM LEDGER
==========

Every cycle writes:

    cycle_id
    timestamp_utc
    broker
    account
    symbol
    asset_class
    starting_deployable_aum
    verified_buying_power
    order_amount
    cost_basis
    sale_proceeds
    realized_gross_profit
    spread_cost
    fees
    slippage
    execution_friction
    tax_reserve
    realized_net_profit
    realized_net_loss
    unrealized_profit
    external_deposit
    withdrawal
    ending_deployable_aum
    next_allocation_cap
    source_freshness
    source_count
    source_conflict
    apex_result
    execution_result
    idempotency_key


RECONCILIATION RULE
===================

At every cycle:

    CALCULATED_END_AUM =
        START_AUM
      + DEPOSITS
      + REALIZED_NET_PROFIT
      - REALIZED_NET_LOSS
      - WITHDRAWALS
      - FEES
      - EXECUTION_COSTS
      - TAX_RESERVE

Compare:

    CALCULATED_END_AUM
    versus
    BROKER_VERIFIED_END_AUM

If they do not reconcile:

    freeze new execution
    preserve the ledger
    request fresh broker state
    return NO ACTION


RISK-OF-RUIN RULE
=================

The objective is not maximum trade frequency.

The objective is survival plus verified compounding.

If the next loss could materially impair the operating capital:

    reduce allocation
    require stronger liquidity
    require stronger source agreement
    require lower spread
    require higher expected net opportunity
    or return NO ACTION

No full-Kelly or all-in sizing.

Use a conservative fraction of the mathematically allowable amount,
subject to the existing project allocation and risk limits.


CODEX DECISION OUTPUT
=====================

VALIDATED SETUP:

    all market, AUM, risk, broker, and execution gates pass

WATCHLIST ONLY:

    candidate is interesting but not executable

HUMAN APPROVAL REQUIRED:

    project configuration requires explicit approval

NO ACTION:

    any required AUM, market, broker, or risk fact is missing,
    stale, contradictory, or unverified

WOULD_EXECUTE:

    shadow mode only
    exact request recorded
    zero live broker mutation

EXECUTED:

    only after exact Robinhood preview and every authorization gate passes


FINAL PRINCIPLE
===============

    AUM does not grow because the algorithm predicts growth.

    AUM grows only when the ledger and broker verify:

        capital entered
        net profit was realized
        costs were deducted
        losses were recorded
        risk remained controlled
        proceeds became available
        the next allocation was recalculated

    NO INTEREST.
    NO GUARANTEES.
    NO BROKER BORROWING (margin/leverage/short-term broker credit; broker-
        confirmed legally transferred family capital is external deposit,
        not borrowing).
    NO LEVERAGE.
    NO ALL-IN TRADES.
    NO COMPOUNDING OF UNREALIZED PROFITS.

    SCAN BROADLY.
    READ DEEPLY.
    CALCULATE CONSERVATIVELY.
    REALIZE NET PROFIT.
    RECYCLE VERIFIED CAPITAL.
    PRESERVE THE AUM.
```
