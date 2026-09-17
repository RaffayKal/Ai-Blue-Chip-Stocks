# APEX_SKYSCRAPER_AUM_ENGINE_V7.md

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

Morphology + methodology + jurisprudence layer, pasted directly by the user
as a full operations upgrade. Note: `APEX_AUM_COMPOUNDING_ALGORITHM.md`'s
title already read "APEX_SKYSCRAPER_AUM_ENGINE_V7 — MORPHOLOGY, METHODOLOGY +
JURISPRUDENCE" from an earlier session, but its body is the AUM-ledger/
family-funds-resolution content edited earlier in this session, not this
text. This file is the actual full V7 spec, kept separate so the earlier
file's load-bearing edits (family funds as capital, AUM compounding score
wiring) are not overwritten. No borrowed-capital conflict in this document;
the family-funds-as-capital resolution stands unmodified.

```
APEX_SKYSCRAPER_AUM_ENGINE_V7
MORPHOLOGY + METHODOLOGY + JURISPRUDENCE

INTEREST                  = 0
REALIZED_PROFIT_ONLY      = TRUE
UNREALIZED_PROFIT         = EXCLUDED
FORECAST_PROFIT           = EXCLUDED
OPTIONS                   = BLOCKED
MARGIN                    = BLOCKED
LEVERAGE                  = BLOCKED
SHORT_SELLING             = BLOCKED
GUARANTEE                 = FALSE
DEFAULT_DECISION          = NO_ACTION

============================================================
I. MORPHOLOGY — THE ANATOMY OF THE SYSTEM
============================================================

Every operation is divided into six morphological organs:

1. SENSOR

    receives market observations
    records source
    records timestamp
    records symbol
    records asset class
    records bid, ask, last, volume

2. INTERPRETER

    calculates spread
    calculates volatility
    calculates trend
    calculates liquidity
    compares historical behavior
    constructs scenarios

3. SKEPTIC

    searches for contradiction
    tests stale data
    tests duplicate evidence
    tests hidden assumptions
    tests adverse outcomes

4. GOVERNOR

    enforces allocation limits
    enforces daily loss limits
    enforces prohibited-asset rules
    enforces account and position limits

5. EXECUTION AUTHORITY

    refreshes broker state
    validates buying power
    validates position state
    previews the request
    hands off only through the existing authorized broker path

6. ARCHIVIST

    records packet hash
    records idempotency key
    records decision
    records rejection reason
    records broker response
    reconciles realized result into AUM

No organ may impersonate another.

The sensor cannot execute.
The interpreter cannot authorize.
The governor cannot invent data.
The archivist cannot rewrite history.

============================================================
II. MORPHOLOGICAL TRANSFORMATION
============================================================

A candidate changes form only through verified transitions:

    RAW_DATA
        -> NORMALIZED_DATA
        -> VERIFIED_MARKET_FACTS
        -> CANDIDATE_HYPOTHESIS
        -> FALSIFIED_OR_VALIDATED_SETUP
        -> BROKER_REVALIDATED_REQUEST
        -> WOULD_EXECUTE or NO_ACTION
        -> BROKER_CONFIRMED_EXECUTED
        -> REALIZED_RESULT
        -> RECONCILED_AUM

Forbidden transformation:

    RAW_DATA -> ORDER

Forbidden transformation:

    FORECAST -> AUM

Forbidden transformation:

    SENTIMENT -> EXECUTION

Forbidden transformation:

    SUCCESSFUL_PRIOR_TRADE -> LARGER_AUTHORITY

============================================================
III. AUM MORPHOLOGY
============================================================

AUM has three separate forms:

A. EXISTING AUM

    broker-confirmed cash
    broker-confirmed positions
    verified account value

B. DEPLOYABLE AUM

    existing AUM
    minus unavailable funds
    minus reserved obligations
    minus restricted funds
    minus required protection buffer

C. COMPOUNDING AUM

    prior reconciled AUM
    plus realized net profit
    minus realized net loss
    minus fees and costs
    plus verified external deposits
    minus verified withdrawals

Only C may serve as the base for future
realized-profit compounding.

============================================================
IV. METHODOLOGY — THE REPEATABLE METHOD
============================================================

The system must use the same method on every candidate.

STEP_01 — OBSERVE

    collect current facts
    collect historical context
    collect independent sources

STEP_02 — NORMALIZE

    standardize symbol
    standardize asset class
    standardize venue
    standardize currency
    standardize timestamp and timezone

STEP_03 — CROSS-CHECK

    compare source values
    identify copied sources
    identify missing values
    identify contradictions

STEP_04 — HYPOTHESIZE

    state exactly why the candidate may qualify

STEP_05 — ATTACK

    search for evidence that disproves the hypothesis

STEP_06 — PRICE FRICTION

    calculate:

        spread
      + fees
      + expected slippage
      + execution delay
      + liquidity impact
      + tax reserve

STEP_07 — CALCULATE SCENARIOS

    adverse
    flat
    expected
    favorable
    extreme favorable

STEP_08 — SIZE DYNAMICALLY

    use only runtime broker-confirmed buying power

STEP_09 — REVALIDATE

    refresh market and broker state immediately before handoff

STEP_10 — DECIDE

    NO_ACTION
    WATCHLIST_ONLY
    VALIDATED_SETUP
    WOULD_EXECUTE
    EXECUTED

STEP_11 — RECONCILE

    update AUM only after the broker confirms
    a completed economic result

============================================================
V. JURISPRUDENCE — THE LAW OF THE SYSTEM
============================================================

Treat every trade candidate as a case.

The candidate is not guilty of being viable
until the evidence proves it satisfies every required element.

------------------------------------------------------------
ELEMENTS OF A QUALIFIED ACTION
------------------------------------------------------------

ELEMENT_01:
    identity of instrument proven

ELEMENT_02:
    asset class proven

ELEMENT_03:
    venue proven

ELEMENT_04:
    market session proven

ELEMENT_05:
    current price proven

ELEMENT_06:
    spread proven

ELEMENT_07:
    liquidity proven

ELEMENT_08:
    quote freshness proven

ELEMENT_09:
    buying power proven by broker

ELEMENT_10:
    position state proven by broker

ELEMENT_11:
    duplicate state proven clear

ELEMENT_12:
    downside calculated

ELEMENT_13:
    total friction calculated

ELEMENT_14:
    APEX viability proven true

ELEMENT_15:
    execution eligibility proven true

If one required element is not proven:

    CASE_STATUS = DISMISSED
    DECISION = NO_ACTION

============================================================
VI. BURDEN OF PROOF
============================================================

The burden of proof belongs to the candidate.

The system must not ask:

    "Can we find a reason to execute?"

It must ask:

    "Has every required condition been proven?"

Evidence hierarchy:

    BROKER_CONFIRMATION
        highest authority for account and order state

    DIRECT_LIVE_MARKET_SOURCE
        high authority for current market facts

    INDEPENDENT_CROSS_CHECK
        confirms or challenges live data

    HISTORICAL_DATA
        context only

    MODEL_FORECAST
        hypothesis only

    HUMAN_NARRATIVE
        non-authoritative context

A lower-level source cannot override
a higher-level contradictory source.

============================================================
VII. RULES OF EVIDENCE
============================================================

Admissible evidence must be:

    timestamped
    attributable
    reproducible
    relevant
    internally consistent
    current for the decision

Inadmissible as sole execution authority:

    screenshot without timestamp
    old packet
    copied quote
    unsupported forecast
    social-media claim
    unverified account value
    imagined future price
    prior success
    user confidence
    model confidence

Chain of custody:

    source
        -> normalized record
        -> packet hash
        -> consumer pickup
        -> Codex validation
        -> broker refresh
        -> decision record
        -> broker response
        -> ledger entry

If chain of custody breaks:

    NO_ACTION("evidence_chain_broken")

============================================================
VIII. DUE PROCESS FOR EVERY CANDIDATE
============================================================

Every candidate receives:

1. NOTICE

    What instrument?
    What side?
    What data?
    What timestamp?
    What proposed notional?

2. CHANCE TO BE HEARD

    What supports the candidate?
    What contradicts it?
    What could invalidate it?

3. INDEPENDENT REVIEW

    Codex rechecks the candidate independently.

4. REASONED DECISION

    record every pass and failure.

5. APPEAL

    if data changes, the candidate may be resubmitted
    only as a new validation event.

A rejected candidate is not silently revived
by repeating the same filesystem event.

============================================================
IX. PRECEDENT AND MODEL DRIFT
============================================================

A prior successful trade is precedent,
not binding law.

A prior rejected trade is warning evidence,
not permanent proof that the asset is invalid.

Every new decision must evaluate:

    current market regime
    current liquidity
    current spread
    current volatility
    current broker state
    current source freshness

The system must detect precedent abuse:

    "It worked before, so execute again."

Result:

    NO_ACTION("prior_success_is_not_current_proof")

============================================================
X. PROPORTIONALITY
============================================================

The proposed notional must be proportionate to:

    verified buying power
    quantified downside
    configured allocation cap
    liquidity
    total friction
    current portfolio exposure
    remaining daily loss capacity

Define:

    PERMITTED_NOTIONAL =
        MIN(
            broker_buying_power * configured_cap,
            risk_budget / downside_per_unit,
            liquidity_capacity,
            broker_limit,
            remaining_daily_loss_capacity
        )

If the proposed amount exceeds permitted notional:

    reduce to permitted notional

If permitted notional is uneconomic after friction:

    NO_ACTION

A strong signal does not justify disproportionate exposure.

============================================================
XI. GOVERNANCE COURT
============================================================

The governance layer reviews:

    AUTHORITY
    EVIDENCE
    PROCEDURE
    PROPORTIONALITY
    CONSISTENCY
    AUDITABILITY

A decision is valid only if:

    authority_valid
    AND evidence_valid
    AND procedure_valid
    AND proportionality_valid
    AND consistency_valid
    AND auditability_valid

Otherwise:

    decision = NO_ACTION

------------------------------------------------------------
SEPARATION OF POWERS
------------------------------------------------------------

RUNPOD:

    keeps infrastructure and scanners running

CHATGPT SCANNERS:

    interpret data and construct candidates

CODEX:

    validates packet and applies APEX rules

ROBINHOOD MCP:

    confirms account state and authorized broker operations

LEDGER:

    records realized results

No scanner may grant broker authority.
No forecast may grant capital.
No packet may grant itself execution permission.

============================================================
XII. AUM COMPOUNDING UNDER JURISPRUDENCE
============================================================

AUM_NEXT =
    VERIFIED_AUM_CURRENT
  + VERIFIED_EXTERNAL_DEPOSITS
  + REALIZED_NET_PROFIT
  - REALIZED_NET_LOSS
  - BROKER_FEES
  - SPREAD_COST
  - SLIPPAGE_COST
  - EXECUTION_COST
  - TAX_RESERVE
  - VERIFIED_WITHDRAWALS

    INTEREST_INCOME = 0

A realized net profit is admissible
only when the following record exists:

    broker_order_id
    broker_completion_status
    entry_value
    exit_value
    all_costs
    timestamp
    account_identity
    internal_ledger_match

If any record is missing:

    profit_status = UNPROVEN
    AUM_CHANGE = 0

============================================================
XIII. THE SKYSCRAPER COURT ORDER
============================================================

FLOOR_01:
    capital exists

FLOOR_02:
    capital belongs to the verified account

FLOOR_03:
    capital is deployable

FLOOR_04:
    market evidence is current

FLOOR_05:
    hypothesis survives disconfirmation

FLOOR_06:
    costs do not consume the edge

FLOOR_07:
    downside is bounded

FLOOR_08:
    allocation is proportionate

FLOOR_09:
    broker state is refreshed

FLOOR_10:
    duplicate state is clear

FLOOR_11:
    final APEX viability is true

FLOOR_12:
    authorized handoff is available

FLOOR_13:
    broker confirms completion

FLOOR_14:
    realized result is reconciled

Only Floor 14 creates a new compounding base.

============================================================
XIV. COMPLETE V7 ALGORITHM
============================================================

function apex_v7(candidate):

    morphology = classify_candidate_stage(candidate)
    method = run_standard_validation_method(candidate)
    evidence = evaluate_chain_of_custody(candidate)
    jurisdiction = evaluate_authority_and_procedure(candidate)
    broker = refresh_authoritative_broker_state()

    if morphology.invalid_transition:
        return NO_ACTION("invalid_state_transition")

    if evidence.chain_broken:
        return NO_ACTION("evidence_chain_broken")

    if jurisdiction.authority_invalid:
        return NO_ACTION("authority_invalid")

    if method.required_fact_missing:
        return NO_ACTION("burden_of_proof_not_met")

    if candidate.stale:
        return NO_ACTION("stale_candidate")

    if candidate.sources_conflict:
        return NO_ACTION("contradictory_evidence")

    if candidate.asset_class in PROHIBITED_CLASSES:
        return NO_ACTION("prohibited_asset_class")

    if candidate.margin_or_leverage:
        return NO_ACTION("margin_or_leverage_blocked")

    if candidate.short_sale:
        return NO_ACTION("short_selling_blocked")

    if broker.buying_power_unavailable:
        return NO_ACTION("buying_power_unverified")

    if broker.position_state_unknown:
        return NO_ACTION("position_state_unverified")

    if candidate.downside_unknown:
        return NO_ACTION("downside_unproven")

    if candidate.total_friction >= candidate.expected_net_result:
        return NO_ACTION("economic_case_not_proven")

    if duplicate_or_pending_order_exists(candidate):
        return NO_ACTION("duplicate_or_pending_execution")

    notional = calculate_proportionate_notional(
        verified_buying_power=broker.buying_power,
        downside=candidate.downside,
        liquidity=candidate.liquidity,
        configured_cap=APEX_ALLOCATION_CAP
    )

    if notional <= 0:
        return NO_ACTION("no_proportionate_allocation")

    final_refresh = refresh_authoritative_broker_state()

    if final_refresh.changed:
        return RESTART_CASE_FROM_STEP_01

    if SHADOW_MODE:
        return WOULD_EXECUTE(
            case_status=VALIDATED_BUT_NOT_SUBMITTED,
            notional=notional,
            live_order_submitted=false,
            AUM_change=0,
            realized_profit=0
        )

    return EXISTING_AUTHORIZED_ROBINHOOD_HANDOFF(
        candidate=candidate,
        notional=notional,
        case_status=EXECUTION_AUTHORIZED
    )

============================================================
XV. APPEAL AND HALT RULES
============================================================

A decision may be reconsidered only when:

    new evidence arrives
    broker state changes
    quote refreshes
    packet is newly generated
    source conflict is resolved
    required data becomes available

A decision may not be reconsidered merely because:

    the user is impatient
    the model is confident
    the asset is moving
    a prior trade succeeded
    the forecast looks attractive
    the account has more money

Immediate halt conditions:

    unknown broker state
    duplicate execution signal
    corrupted packet hash
    stale account data
    contradictory position data
    unexplained AUM change
    unauthorized execution path
    repeated failed reconciliation

============================================================
FINAL RULE
============================================================

Morphology asks:

    "What is this thing and what stage is it in?"

Methodology asks:

    "Was the same valid process applied?"

Jurisprudence asks:

    "Was the action authorized, proven, proportionate,
     reasoned, auditable, and procedurally valid?"

Only when all three agree:

    the candidate may advance.

AUM compounds without interest only through:

    verified capital
    verified evidence
    proportionate allocation
    authorized execution
    realized net result
    reconciled ledger entry

Otherwise:

    NO_ACTION
```
