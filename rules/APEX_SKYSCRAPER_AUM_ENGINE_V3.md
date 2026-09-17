# APEX_SKYSCRAPER_AUM_ENGINE_V3.md

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

Reference/knowledge document pasted directly by the user (physics- and
psychology-based market controls, the skyscraper floor model, and final APEX
pseudocode). Same resolved conflict as `APEX_110_AUM_COMPOUNDING_NO_INTEREST.md`
applies here: FLOOR_01_CAPITAL below says to "exclude ... borrowed funds" —
read that as broker margin/leverage/short-term broker borrowing, not
broker-confirmed legally transferred family capital, which counts as
external deposit per the user's explicit resolution.

```
APEX_SKYSCRAPER_AUM_ENGINE_V3
MODE: REALIZED-NET-PROFIT COMPOUNDING
INTEREST: EXCLUDED
LEVERAGE: EXCLUDED
OPTIONS: EXCLUDED
MARGIN: EXCLUDED
SHORT_SELLING: EXCLUDED
GUARANTEED_PROFIT: FALSE

============================================================
I. THE CONSERVATION LAW OF CAPITAL
============================================================

Capital is not created by a forecast.

Only these events may change verified AUM:

AUM_NEXT =
    AUM_CURRENT
  + VERIFIED_EXTERNAL_DEPOSIT
  + REALIZED_NET_PROFIT
  - REALIZED_NET_LOSS
  - VERIFIED_WITHDRAWAL
  - BROKER_FEES
  - SPREAD_COST
  - SLIPPAGE_COST
  - EXECUTION_COST
  - TAX_RESERVE
  - OTHER_VERIFIED_COST

UNREALIZED_PROFIT:
    does not increase deployable AUM

PROJECTED_PROFIT:
    does not increase deployable AUM

PAPER_PROFIT:
    does not increase deployable AUM

FORECAST_CONFIDENCE:
    does not increase deployable AUM

If broker ledger and internal ledger disagree:

    AUM_STATUS = UNRECONCILED
    DECISION   = NO ACTION

============================================================
II. THE SKYSCRAPER MODEL
============================================================

Each floor must be completed before the next floor can use its output.

FLOOR_00_FOUNDATION:
    Confirm broker identity
    Confirm account
    Confirm asset class
    Confirm session
    Confirm current timestamp
    Confirm buying power

FLOOR_01_CAPITAL:
    Read authoritative broker buying power
    Exclude unsettled, unavailable, restricted, or borrowed funds
    Exclude unrealized gains
    Exclude projected gains

FLOOR_02_DATA:
    Collect independent live price sources
    Validate symbol and venue
    Validate bid, ask, last, volume, and timestamp
    Reject stale or contradictory records

FLOOR_03_PHYSICS:
    Calculate transaction friction:

    TOTAL_FRICTION =
        spread
      + expected_slippage
      + fees
      + liquidity_impact
      + execution_delay_cost

    If expected_edge <= TOTAL_FRICTION:

        DECISION = NO ACTION

FLOOR_04_SIGNAL:
    Separate:
        observed fact
        calculated value
        forecast
        assumption

    Assumptions cannot authorize an order.

FLOOR_05_PSYCHOLOGY:
    Detect and penalize:

        FOMO
        revenge trading
        overconfidence
        confirmation bias
        recency bias
        sunk-cost behavior
        loss-chasing
        gambler's fallacy
        fear-of-missing-out urgency
        attachment to an existing position

    If the decision depends on emotional urgency:

        DECISION = NO ACTION

FLOOR_06_EXPECTANCY:
    Estimate scenario-weighted net outcome:

    EXPECTED_NET_VALUE =
        SUM(
            probability_scenario[i]
            * net_outcome_after_costs[i]
        )

    Do not use a single optimistic forecast.

    Require downside scenarios to be explicitly modeled.

FLOOR_07_POSITION:
    Determine maximum legal notional from live broker data:

    MAX_NOTIONAL =
        MIN(
            broker_buying_power,
            configured_AUM_allocation_limit,
            configured_risk_limit,
            liquidity_limit,
            venue_limit,
            remaining_daily_loss_capacity
        )

    Never use a hard-coded account balance.

FLOOR_08_DUPLICATE_CONTROL:
    Reject if:

        same idempotency_key already consumed
        same symbol and side already active beyond allowed limit
        duplicate order is pending
        packet hash was already processed
        position state is unknown
        broker order state is unknown

FLOOR_09_APEX_DECISION:
    Permit only:

        VALIDATED_SETUP
        WATCHLIST_ONLY
        NO_ACTION
        WOULD_EXECUTE
        EXECUTED

    "VALIDATED_SETUP" is not an order.
    "WOULD_EXECUTE" is not an order.
    Only the authorized broker execution path may submit.

FLOOR_10_REALIZED_RESULT:
    After execution, update AUM only after broker confirmation.

    No broker-confirmed fill:
        no realized profit
        no AUM increase
        no compounding credit

============================================================
III. PHYSICS-BASED MARKET CONTROLS
============================================================

1. CONSERVATION OF CAPITAL

The engine cannot create capital from a forecast.

A forecast may rank opportunities.
It may not rewrite the account ledger.

2. FRICTION

Every transaction has resistance.

Treat the following as friction:

    spread
    commission or fee
    slippage
    latency
    partial fill risk
    market impact
    liquidity loss
    transfer delay
    tax reserve

If friction consumes the calculated edge:

    NO ACTION

3. MOMENTUM

Momentum is not proof of continuation.

Momentum may be used as an observed feature only when:

    timestamped
    measured across multiple intervals
    supported by volume or liquidity
    not contradicted by independent sources
    still valid after the final quote refresh

4. MEAN REVERSION

A decline is not automatically undervaluation.

A spike is not automatically a reversal.

The engine must distinguish:

    price movement
    liquidity shock
    news response
    structural trend
    temporary deviation
    data error

5. ENTROPY AND NOISE

The more uncertain the inputs, the less authority the signal receives.

Define an information-quality score:

    INFORMATION_QUALITY =
        source_agreement
      * timestamp_quality
      * symbol_identity_quality
      * liquidity_quality
      * market_state_quality

If information quality falls below threshold:

    WATCHLIST_ONLY or NO ACTION

6. FEEDBACK

Positive feedback can amplify both gains and losses.

Therefore:

    realized profits may expand future capacity
    realized losses reduce future capacity
    no forecast may expand capacity
    no single trade may recursively authorize unlimited growth

7. STABILITY

Use a damping rule:

    NEW_ALLOCATION =
        MIN(
            calculated_allocation,
            prior_verified_allocation
            * maximum_growth_multiplier,
            current_verified_buying_power
            * configured_cap
        )

If allocation jumps unexpectedly:

    require fresh validation
    require reason code
    require broker-state confirmation
    otherwise NO ACTION

============================================================
IV. PSYCHOLOGY-BASED FAILURE CONTROLS
============================================================

LOSS AVERSION:
    Do not hold a losing position merely to avoid admitting loss.

OVERCONFIDENCE:
    Reduce authority when forecast confidence is based only
    on the system's prior success.

RECENCY BIAS:
    Recent price movement cannot represent the entire historical
    distribution.

CONFIRMATION BIAS:
    Require disconfirming evidence before approval.

GAMBLER'S FALLACY:
    A prior loss does not make the next trade more likely to win.

HOT-HAND FALLACY:
    A prior win does not justify larger risk by itself.

FOMO:
    A rapidly moving asset receives stricter freshness and spread
    validation, not automatic approval.

SUNK COST:
    Existing exposure cannot justify additional exposure.

NARRATIVE BIAS:
    A compelling story cannot replace verified price, liquidity,
    risk, and broker data.

ACTION BIAS:
    No qualifying trade is itself a valid result.

============================================================
V. AUM COMPOUNDING LADDER
============================================================

LEVEL_0:
    Starting verified AUM

LEVEL_1:
    Add verified external capital only

LEVEL_2:
    Preserve capital after all costs

LEVEL_3:
    Produce realized net profit

LEVEL_4:
    Reconcile realized profit with broker ledger

LEVEL_5:
    Retain the verified profit inside the account

LEVEL_6:
    Recalculate buying power

LEVEL_7:
    Recalculate maximum permitted allocation

LEVEL_8:
    Revalidate every new candidate independently

LEVEL_9:
    Permit only the next qualified action

LEVEL_10:
    Repeat only after another verified realized result

A level cannot skip a lower level.

Projected success cannot move the system upward.
Only verified account state can do that.

============================================================
VI. NET PROFIT COMPOUNDING EQUATION
============================================================

For each completed trade:

REALIZED_NET_PROFIT =
    broker_confirmed_exit_value
  - broker_confirmed_entry_value
  - spread_cost
  - fees
  - slippage
  - execution_cost
  - tax_reserve

If the result is positive:

    COMPOUNDING_BASE =
        prior_verified_AUM
      + realized_net_profit

If the result is negative:

    COMPOUNDING_BASE =
        prior_verified_AUM
      - absolute(realized_net_loss)

Then:

    NEXT_TRADE_CAPACITY =
        COMPOUNDING_BASE
        * current_configured_allocation_limit

No interest is included anywhere.

============================================================
VII. "SKYSCRAPER ADDITION" ALLOCATION RULE
============================================================

The skyscraper grows vertically only when the foundation remains valid.

For each candidate:

    candidate_notional =
        MIN(
            verified_buying_power * allocation_percentage,
            permitted_risk_budget / downside_per_dollar,
            available_liquidity_capacity,
            broker_minimum,
            broker_maximum
        )

The allocation percentage must remain inside the project's
configured range.

If the user requests a larger amount but the risk engine permits less:

    use the lower permitted amount

If the user requests a smaller amount:

    use the smaller amount only if it remains economically viable
    after all friction

If the minimum order cannot overcome transaction friction:

    NO ACTION

A $1-to-$2 result is mathematically possible in some circumstances,
but it is never guaranteed. The engine must calculate the outcome
after spread, slippage, fees, liquidity, and adverse movement.

============================================================
VIII. HISTORICAL-READING LAYER
============================================================

Historical data is evidence, not prophecy.

For every candidate, calculate:

    long_window_behavior
    medium_window_behavior
    short_window_behavior
    volatility_regime
    drawdown_history
    recovery_history
    liquidity_history
    gap_or_jump_frequency
    correlation_to_related_assets
    reaction_to_major_events

Require separation between:

    historical observation
    current observation
    model projection

The projection may influence ranking.
It may not override current stale, contradictory, or missing data.

============================================================
IX. FINAL APEX PSEUDOCODE
============================================================

function evaluate_candidate(candidate):

    facts = collect_current_facts(candidate)

    if facts.missing_or_contradictory:
        return NO_ACTION("missing_or_contradictory_facts")

    if facts.asset_class in OPTIONS_OR_UNSUPPORTED_CLASSES:
        return NO_ACTION("unsupported_asset_class")

    if facts.uses_margin_or_leverage:
        return NO_ACTION("margin_or_leverage_blocked")

    if facts.side == SHORT:
        return NO_ACTION("short_selling_blocked")

    if facts.data_is_stale:
        return NO_ACTION("stale_market_data")

    if facts.spread > configured_spread_limit:
        return NO_ACTION("spread_limit_exceeded")

    if facts.buying_power_is_unavailable:
        return NO_ACTION("buying_power_unavailable")

    psychology = detect_behavioral_distortion(candidate)

    if psychology.requires_action_urgency:
        return NO_ACTION("psychological_distortion")

    physics = calculate_market_friction(facts)

    forecast = calculate_scenario_distribution(
        historical_data,
        current_data,
        volatility,
        liquidity,
        opposing_evidence
    )

    if forecast.expected_net_value <= physics.total_friction:
        return NO_ACTION("edge_does_not_exceed_friction")

    size = calculate_dynamic_notional(
        broker_buying_power=facts.buying_power,
        risk_budget=facts.risk_budget,
        liquidity=facts.liquidity,
        allocation_cap=configured_allocation_cap
    )

    if size <= 0:
        return NO_ACTION("zero_permitted_notional")

    if duplicate_or_pending_order_exists(candidate):
        return NO_ACTION("duplicate_or_pending_order")

    final_broker_state = refresh_broker_state()

    if final_broker_state.changed:
        return REVALIDATE_FROM_BEGINNING

    if SHADOW_MODE:
        return WOULD_EXECUTE(
            candidate=candidate,
            notional=size,
            expected_net_value=forecast.expected_net_value,
            friction=physics.total_friction,
            live_order_submitted=false
        )

    return handoff_to_existing_authorized_broker_path(
        candidate,
        size,
        all_final_gates=true
    )

============================================================
X. AUM LEDGER INVARIANTS
============================================================

The following must always be true:

    interest_income == 0

    unrealized_profit_excluded == true

    projected_profit_excluded == true

    external_cash_flows_separated == true

    realized_profit_reconciled == true

    broker_buying_power_is_runtime_value == true

    duplicate_execution_blocked == true

    all_in_single_asset_blocked == true

    options_blocked == true

    margin_blocked == true

    leverage_blocked == true

    short_selling_blocked == true

    stale_data_blocked == true

    contradictory_data_blocked == true

    no_trade_is_valid_outcome == true

============================================================
XI. OUTPUT STATES
============================================================

NO_ACTION:
    no execution

WATCHLIST_ONLY:
    monitor, no execution

VALIDATED_SETUP:
    qualified for further controlled review

WOULD_EXECUTE:
    exact request produced in shadow mode
    live_order_submitted = false

EXECUTED:
    only after authorized broker path confirms submission

REALIZED:
    only after broker-confirmed completion and ledger reconciliation
```
