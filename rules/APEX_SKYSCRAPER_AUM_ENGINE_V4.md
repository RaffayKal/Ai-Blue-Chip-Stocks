# APEX_SKYSCRAPER_AUM_ENGINE_V4.md

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

Philosophical + quantum-inspired control layer, pasted directly by the user
and marked as a full operations upgrade (not reference-only). Same resolved
conflict as the other `APEX_110`/`APEX_SKYSCRAPER` docs: this spec's
`BORROWED_CAPITAL = 0` header and AUM equation exclude borrowed funds with no
exception. Per the user's explicit resolution recorded in
`APEX_110_AUM_COMPOUNDING_NO_INTEREST.md`, read "borrowed funds" here as
broker margin/leverage/short-term broker credit — not broker-confirmed
legally transferred family capital, which counts as external deposit
(`VERIFIED_DEPOSIT` in the equation below).

```
APEX_SKYSCRAPER_AUM_ENGINE_V4
PHILOSOPHICAL + QUANTUM-INSPIRED CONTROL LAYER

INTEREST = 0
BORROWED_CAPITAL = 0
LEVERAGE = 0
OPTIONS = 0
SHORT_SELLING = 0
GUARANTEED_PROFIT = FALSE
UNREALIZED_PROFIT = NOT_COMPOUNDABLE
PROJECTED_PROFIT = NOT_COMPOUNDABLE

============================================================
I. PHILOSOPHICAL FOUNDATION
============================================================

PRINCIPLE_1 — EPISTEMIC HUMILITY

The system must separate:

    FACT
    CALCULATION
    ESTIMATE
    FORECAST
    UNKNOWN

Only FACT and reproducible CALCULATION may pass a hard gate.

Forecasts may rank candidates.
Forecasts may never create capital,
increase buying power,
or override a failed gate.

PRINCIPLE_2 — STOIC CONTROL

The system controls:

    data validation
    position sizing
    order eligibility
    execution timing
    loss limits
    ledger reconciliation

The system does not control:

    market direction
    liquidity disappearance
    slippage
    news
    broker outages
    future returns

When an uncontrollable factor is uncertain:

    NO ACTION

PRINCIPLE_3 — ARISTOTELIAN PROPORTIONALITY

Every allocation must be proportional to:

    verified capital
    measured opportunity
    downside exposure
    market liquidity
    execution quality

Signal strength alone cannot determine size.

PRINCIPLE_4 — MUNGER-STYLE INVERSION

Before asking:

    "Why should this trade happen?"

ask:

    "What would make this trade fail?"

List failure conditions:

    stale quote
    spread expansion
    thin liquidity
    wrong asset class
    contradictory sources
    position already open
    duplicate order
    insufficient buying power
    adverse volatility
    broken broker state
    forecast invalidated

If any decisive failure condition is present:

    NO ACTION

PRINCIPLE_5 — BUFFETT-STYLE CAPITAL ALLOCATION

Retain capital only when the next deployment is superior to waiting.

A qualified "do nothing" decision is better than
forcing capital into an inferior opportunity.

============================================================
II. QUANTUM-INSPIRED STATE MODEL
============================================================

This is a classical model inspired by quantum concepts.
It does not claim quantum speed or quantum prediction.

A candidate exists as a set of possible states:

    |CANDIDATE> =
        a0|NO_ACTION>
      + a1|WATCHLIST>
      + a2|VALIDATED_SETUP>
      + a3|WOULD_EXECUTE>
      + a4|EXECUTED>

The coefficients are confidence weights, not guarantees.

Required condition:

    SUM(probability_state[i]) = 1

Before final validation, several states may remain possible.

After measurement:

    exactly one operational state is selected

Measurement means:

    fresh data collection
    final gate evaluation
    broker-state refresh
    deterministic decision

The system must never treat the unmeasured
candidate state as executed capital.

============================================================
III. QUANTUM-INSPIRED FACTOR COMBINATION
============================================================

Each independent evidence lane produces a bounded score:

    q_price
    q_volume
    q_liquidity
    q_volatility
    q_historical
    q_current_trend
    q_cross_source
    q_broker
    q_risk
    q_execution

Each score must be normalized:

    0.0 <= q_i <= 1.0

Evidence is divided into:

    SUPPORTING_EVIDENCE
    NEUTRAL_EVIDENCE
    CONTRADICTING_EVIDENCE
    UNKNOWN_EVIDENCE

Contradicting evidence must reduce confidence.

Unknown evidence cannot be silently treated as support.

A classical confidence estimate may be calculated as:

    SUPPORT =
        weighted_mean(supporting_evidence)

    CONTRADICTION =
        weighted_mean(contradicting_evidence)

    DATA_QUALITY =
        source_agreement
      * timestamp_quality
      * identity_quality
      * liquidity_quality

    NET_EVIDENCE =
        SUPPORT
      - CONTRADICTION
      - uncertainty_penalty

If:

    DATA_QUALITY < minimum_quality
    OR NET_EVIDENCE <= 0
    OR required_fact_missing == true

then:

    NO_ACTION

============================================================
IV. SUPERPOSITION = SCENARIO SPACE
============================================================

Represent each candidate using multiple scenarios:

    S0 = adverse outcome
    S1 = flat outcome
    S2 = expected outcome
    S3 = favorable outcome
    S4 = extreme favorable outcome

Each scenario must include:

    probability estimate
    price range
    time horizon
    gross result
    spread
    fees
    slippage
    liquidity impact
    net result
    maximum loss

Calculate:

    EXPECTED_NET_RESULT =
        SUM(
            scenario_probability[i]
            * scenario_net_result[i]
        )

But expected value alone is insufficient.

Require:

    downside_is_bounded
    worst_case_is_known
    total_friction_is_known
    probability_assumptions_are_documented
    current_data_supports_the_scenarios

If the favorable scenario is the only profitable scenario:

    NO_ACTION

============================================================
V. ENTANGLEMENT = FACTOR DEPENDENCE
============================================================

Multiple indicators may not be independent.

Examples:

    price momentum and moving averages
    volume and liquidity
    sentiment and price reaction
    correlated stocks
    correlated crypto assets
    multiple feeds copying the same source

Do not count duplicated evidence as separate confirmation.

Define an effective evidence count:

    EFFECTIVE_EVIDENCE =
        raw_evidence_count
        - correlation_penalty
        - duplicated_source_penalty

If five sources repeat the same underlying feed:

    treat them as one source family,
    not five independent confirmations.

For correlated positions:

    PORTFOLIO_EXPOSURE =
        SUM(position_notional * correlation_weight)

If correlated exposure exceeds the configured limit:

    NO_ACTION or REDUCE_SIZE

============================================================
VI. INTERFERENCE = CONTRADICTION FILTER
============================================================

Positive evidence and negative evidence must be allowed
to cancel each other.

Example:

    strong momentum
    but deteriorating liquidity
    and widening spread

The momentum signal does not automatically win.

Define:

    SIGNAL_RESULT =
        positive_signal_strength
      - negative_signal_strength
      - friction_penalty
      - uncertainty_penalty

If:

    SIGNAL_RESULT <= minimum_required_edge

then:

    NO_ACTION

This prevents one attractive chart pattern
from overpowering operational risk.

============================================================
VII. MEASUREMENT = FINAL DECISION
============================================================

A candidate is "measured" only after:

    fresh timestamp obtained
    symbol confirmed
    asset class confirmed
    venue confirmed
    market session confirmed
    bid confirmed
    ask confirmed
    last price confirmed
    spread confirmed
    liquidity confirmed
    buying power refreshed
    position refreshed
    duplicate state checked
    APEX viability recalculated
    execution eligibility recalculated

Then select exactly one:

    NO_ACTION
    WATCHLIST_ONLY
    VALIDATED_SETUP
    WOULD_EXECUTE
    EXECUTED

No measurement:

    no order
    no AUM compounding
    no execution authority

============================================================
VIII. SKYSCRAPER AUM ADDITION
============================================================

The skyscraper grows only from verified ledger events.

AUM_NEXT =
    VERIFIED_AUM_CURRENT
  + VERIFIED_DEPOSIT
  + REALIZED_NET_PROFIT
  - REALIZED_NET_LOSS
  - FEES
  - SPREAD_COST
  - SLIPPAGE_COST
  - EXECUTION_COST
  - TAX_RESERVE
  - VERIFIED_WITHDRAWAL

Interest is never included.

    INTEREST_INCOME = 0

Do not add:

    forecast profit
    unrealized appreciation
    expected value
    confidence score
    projected compounding
    potential future deposits

============================================================
IX. CAPITAL RECURSION CONTROL
============================================================

A realized profit may increase the next capital base only after:

    broker confirms completion
    cash or buying power is updated
    internal ledger is reconciled
    no reversal or correction is pending
    tax reserve is accounted for

Then:

    VERIFIED_COMPOUNDING_BASE =
        reconciled_AUM
      + reconciled_realized_net_profit

Next allocation:

    NEXT_NOTIONAL =
        MIN(
            verified_buying_power * configured_cap,
            remaining_risk_budget,
            liquidity_capacity,
            broker_limit,
            account_limit
        )

A forecast cannot recursively increase its own allocation.

This prevents:

    forecast -> larger position
    larger position -> assumed profit
    assumed profit -> larger position
    larger position -> uncontrolled recursion

============================================================
X. PHILOSOPHICAL "PAUSE" GATES
============================================================

Pause when:

    truth is incomplete
    identity is uncertain
    evidence is duplicated
    data conflicts
    the broker state is unknown
    the expected result depends on a guarantee
    the model is being pressured to act
    recent success is being used as proof
    recent loss is being used as justification
    waiting is economically superior

Output:

    NO_ACTION(reason="epistemic_or_operational_uncertainty")

============================================================
XI. AUM SKYSCRAPER FLOORS
============================================================

FLOOR_1:
    verified starting AUM

FLOOR_2:
    verified external capital

FLOOR_3:
    current buying-power reconciliation

FLOOR_4:
    first qualified trade

FLOOR_5:
    broker-confirmed completion

FLOOR_6:
    realized net result

FLOOR_7:
    ledger reconciliation

FLOOR_8:
    retained realized profit

FLOOR_9:
    recalculated allocation capacity

FLOOR_10:
    independently qualified next action

FLOOR_11:
    portfolio-level correlation control

FLOOR_12:
    drawdown and loss-budget control

FLOOR_13:
    periodic model validation

FLOOR_14:
    audited AUM history

No floor may be built from an estimate.

============================================================
XII. COMPLETE DECISION ALGORITHM
============================================================

function compound_AUM(candidate):

    broker = refresh_authoritative_broker_state()
    market = collect_current_multi_source_data(candidate)
    history = load_historical_observations(candidate)

    if broker.invalid:
        return NO_ACTION("broker_state_invalid")

    if market.missing_or_contradictory:
        return NO_ACTION("market_state_invalid")

    if market.stale:
        return NO_ACTION("stale_data")

    if candidate.asset_class in OPTIONS_MARGIN_LEVERAGE_SHORT:
        return NO_ACTION("prohibited_asset_class_or_action")

    states = build_scenario_state_space(
        current_data=market,
        historical_data=history,
        broker_state=broker
    )

    states = remove_duplicated_evidence(states)
    states = apply_contradiction_interference(states)
    states = apply_uncertainty_penalty(states)

    if states.downside_unknown:
        return NO_ACTION("downside_unknown")

    net_result = calculate_after_costs(states)

    if net_result.expected <= total_friction:
        return NO_ACTION("edge_does_not_exceed_friction")

    if net_result.worst_case_exceeds_budget:
        return NO_ACTION("risk_budget_exceeded")

    notional = calculate_dynamic_notional(
        buying_power=broker.authoritative_buying_power,
        risk_budget=broker.remaining_risk_budget,
        liquidity=market.liquidity,
        configured_cap=APEX_ALLOCATION_CAP
    )

    if notional <= 0:
        return NO_ACTION("no_permitted_notional")

    if duplicate_or_pending_order_exists(candidate):
        return NO_ACTION("duplicate_or_pending_order")

    final_state = refresh_authoritative_broker_state()

    if final_state.changed:
        return RESTART_VALIDATION

    if SHADOW_MODE:
        return WOULD_EXECUTE(
            notional=notional,
            expected_net_result=net_result.expected,
            realized_AUM_change=0,
            live_order_submitted=false
        )

    return EXISTING_AUTHORIZED_BROKER_HANDOFF(
        candidate=candidate,
        notional=notional,
        all_gates=true
    )

============================================================
XIII. FINAL PRINCIPLE
============================================================

The purpose is not to force the skyscraper upward.

The purpose is to prevent a false floor from being built.

AUM grows only when:

    capital is verified
    evidence is current
    costs are included
    downside is bounded
    broker state is confirmed
    execution is authorized
    profit is realized
    the ledger is reconciled

Otherwise:

    NO_ACTION
```
