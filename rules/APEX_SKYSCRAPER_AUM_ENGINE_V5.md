# APEX_SKYSCRAPER_AUM_ENGINE_V5.md

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

Metaphysical + epistemological + ethical + logical layer, pasted directly by
the user as a full operations upgrade. No borrowed-capital conflict in this
document (it does not exclude borrowed/family funds specifically) — the
resolution in `APEX_110_AUM_COMPOUNDING_NO_INTEREST.md` (family funds count
as capital once broker-confirmed) still stands and is not contradicted here.

```
APEX_SKYSCRAPER_AUM_ENGINE_V5
METAPHYSICAL + EPISTEMOLOGICAL + ETHICAL + LOGICAL LAYER

INTEREST                         = 0
GUARANTEED_PROFIT                = FALSE
UNREALIZED_PROFIT_COMPOUNDABLE   = FALSE
FORECAST_PROFIT_COMPOUNDABLE     = FALSE
OPTIONS                          = BLOCKED
MARGIN                           = BLOCKED
LEVERAGE                         = BLOCKED
SHORT_SELLING                    = BLOCKED
ALL_IN_ALLOCATION                = BLOCKED

============================================================
I. METAPHYSICS — WHAT ACTUALLY EXISTS?
============================================================

The system must distinguish four different realities:

1. ACCOUNT REALITY

    broker-confirmed cash
    broker-confirmed buying power
    broker-confirmed positions
    broker-confirmed orders
    broker-confirmed fills

2. MARKET REALITY

    confirmed symbol
    confirmed asset class
    confirmed venue
    confirmed session
    confirmed bid
    confirmed ask
    confirmed last price
    confirmed volume
    confirmed timestamp
    confirmed source freshness

3. MODEL REALITY

    calculated spread
    calculated volatility
    scenario probabilities
    historical statistics
    forecast values
    ranking scores

4. NARRATIVE REALITY

    opinions
    stories
    hopes
    fears
    "this must go up"
    "I knew it would spike"
    "it cannot lose"
    "the model guarantees it"

Only account reality and verified market reality
can authorize an action.

Model reality can support analysis.

Narrative reality can never authorize execution.

------------------------------------------------------------
METAPHYSICAL AXIOM
------------------------------------------------------------

A forecast is not a possession.

A projected gain is not capital.

A model score is not buying power.

An intention is not an order.

An order request is not a fill.

A fill is not realized profit until broker records reconcile it.

Therefore:

    PROJECTED_AUM != VERIFIED_AUM

    UNREALIZED_PROFIT != REALIZED_NET_PROFIT

    WOULD_EXECUTE != EXECUTED

    EXECUTED != REALIZED

============================================================
II. THE IDENTITY OF AUM
============================================================

Define:

    GROSS_AUM =
        market_value_of_all_holdings
        + available_cash

    VERIFIED_AUM =
        broker-confirmed account value at timestamp T

    DEPLOYABLE_CAPITAL =
        broker-confirmed buying power
        minus reserved obligations
        minus required buffers

    COMPOUNDING_AUM =
        prior verified AUM
        plus realized net profits
        minus realized net losses
        minus verified withdrawals
        minus verified costs

Only COMPOUNDING_AUM may affect
future compounding calculations.

------------------------------------------------------------
AUM LAW
------------------------------------------------------------

AUM_NEXT =
    AUM_CURRENT
  + VERIFIED_DEPOSITS
  + REALIZED_NET_PROFIT
  - REALIZED_NET_LOSS
  - VERIFIED_WITHDRAWALS
  - BROKER_FEES
  - SPREAD_COST
  - SLIPPAGE_COST
  - EXECUTION_COST
  - TAX_RESERVE

    INTEREST_INCOME = 0

No other variable may increase AUM.

============================================================
III. EPISTEMOLOGY — WHAT COUNTS AS KNOWLEDGE?
============================================================

Every input receives an epistemic classification:

    K0 = UNKNOWN
    K1 = CLAIMED
    K2 = OBSERVED
    K3 = CALCULATED
    K4 = CROSS-CHECKED
    K5 = BROKER-CONFIRMED

Execution requires:

    symbol              >= K4
    asset_class         >= K4
    venue               >= K4
    market_session      >= K4
    quote               >= K4
    spread              >= K4
    liquidity           >= K4
    buying_power        >= K5
    position_state      >= K5
    duplicate_state     >= K5
    final_eligibility   >= K5

If any required value is K0, K1, K2, or K3:

    NO_ACTION

A calculation can be correct while its input is false.
Therefore calculated precision does not cure bad evidence.

------------------------------------------------------------
EPISTEMIC RULE
------------------------------------------------------------

The system must never claim:

    "the trade will win"

It may only state:

    "under these verified inputs and assumptions,
     this scenario has this calculated distribution of outcomes"

Historical data gives evidence about prior behavior.
It does not establish future certainty.

The SEC states that investments carry risk and that past performance
does not guarantee future results. [SEC investor guidance](https://www.sec.gov/about/reports-publications/investorpubsinwshtm)

============================================================
IV. HUME'S PROBLEM OF INDUCTION
============================================================

The fact that:

    pattern P appeared before

does not logically prove:

    pattern P must appear again

Therefore historical patterns may be used for:

    context
    probability estimation
    regime detection
    scenario construction
    candidate ranking

They may not override:

    stale data
    contradictory data
    broken liquidity
    broker restrictions
    loss limits
    execution friction

Historical success never grants permanent authority.

============================================================
V. POPPER-STYLE FALSIFICATION
============================================================

For every candidate, create a disconfirmation test.

The system must ask:

    What evidence would prove this candidate invalid?

Examples:

    spread widens above limit
    price falls through invalidation level
    liquidity disappears
    source disagreement appears
    volume fails confirmation
    volatility enters prohibited regime
    broker buying power changes
    another order already exists
    expected edge falls below total friction

If invalidating evidence appears:

    candidate_status = INVALIDATED
    action = NO_ACTION

A candidate that cannot be falsified is not a properly specified
market hypothesis.

============================================================
VI. LOGIC — VALID INFERENCE ONLY
============================================================

Use this implication:

    IF all required facts are verified
    AND all prohibited actions are absent
    AND total costs are covered
    AND downside is within limits
    AND duplicate state is clear
    AND final broker validation passes
    THEN the candidate may enter WOULD_EXECUTE or execution handoff.

Do not reverse the implication.

Invalid reverse logic:

    "It looks profitable, therefore the facts must be valid."

Invalid reverse logic:

    "The scanner found it, therefore the broker can execute it."

Invalid reverse logic:

    "The last trade worked, therefore the next trade will work."

Invalid reverse logic:

    "The system is autonomous, therefore the system is authorized."

------------------------------------------------------------
LOGICAL CONSISTENCY CHECK
------------------------------------------------------------

If the system contains both:

    viable = true

and:

    required_fact_missing = true

then the final result must be:

    NO_ACTION

The stronger safety predicate wins.

If:

    source_A says BUY
    source_B says NO_DATA
    broker_state is unknown

then:

    NO_ACTION

Contradiction is not permission to choose the favorable source.

============================================================
VII. ETHICS — WHAT MAY BE DONE?
============================================================

The ethical objective is not "maximize activity."

The ethical objective is:

    preserve agency
    preserve capital
    disclose uncertainty
    avoid deception
    avoid unauthorized risk
    avoid hidden escalation
    maintain auditability

Use a duty-first rule:

    A profitable outcome does not justify
    an unauthorized or prohibited action.

This means:

    no order from an unverified quote
    no order from missing buying power
    no order from a forecast alone
    no order from an emotional command
    no order from contradictory data
    no order that bypasses the broker gate

The system must not treat the possibility of profit
as moral permission to ignore the controls.

Aristotle's concept of practical wisdom is relevant here: technical skill is not sufficient unless the action is directed toward a sound end and fitted to the particular facts. [Stanford Encyclopedia of Philosophy: Aristotle's Ethics](https://plato.stanford.edu/entries/aristotle-ethics/)

============================================================
VIII. THE ETHICAL AUM SKYSCRAPER
============================================================

FLOOR_01 — EXISTENCE

    Does the capital actually exist in the broker account?

FLOOR_02 — OWNERSHIP

    Is the capital available to this authorized account?

FLOOR_03 — ACCESS

    Is it legally and technically deployable?

FLOOR_04 — KNOWLEDGE

    Are the market facts current and cross-checked?

FLOOR_05 — PROPORTIONALITY

    Is the proposed notional proportionate to verified capital
    and measured downside?

FLOOR_06 — NON-DECEPTION

    Are projected gains excluded from AUM?

FLOOR_07 — NON-COERCION

    Is the action free from urgency, pressure, or revenge behavior?

FLOOR_08 — REVERSIBILITY

    Can the action be stopped, reconciled, and audited?

FLOOR_09 — ACCOUNTABILITY

    Is there an idempotency key, packet hash, decision reason,
    and broker reference?

FLOOR_10 — REALIZATION

    Has the result actually been confirmed and reconciled?

Only Floor 10 can produce realized compounding credit.

============================================================
IX. QUANTUM-INSPIRED POSSIBILITY SPACE
============================================================

This is a classical probability model,
not a claim of quantum market prediction.

Represent candidate states as:

    C =
        p0(NO_ACTION)
      + p1(WATCHLIST)
      + p2(VALIDATED_SETUP)
      + p3(WOULD_EXECUTE)
      + p4(EXECUTED)

Where:

    p0 + p1 + p2 + p3 + p4 = 1

The system must not "collapse" into EXECUTED
until execution is actually confirmed by the broker.

Before final validation:

    multiple outcomes remain possible

After final validation:

    one operational decision is selected

After broker confirmation:

    only then can the ledger record execution

After completed settlement:

    only then can realized net profit affect AUM

------------------------------------------------------------
QUANTUM-INSPIRED UNCERTAINTY
------------------------------------------------------------

Define:

    UNCERTAINTY =
        missing_data
      + source_disagreement
      + forecast_variance
      + liquidity_uncertainty
      + execution_uncertainty
      + broker_uncertainty

Then:

    AUTHORITY =
        VERIFIED_EVIDENCE
        - UNCERTAINTY_PENALTY

If authority is below threshold:

    WATCHLIST_ONLY or NO_ACTION

Uncertainty reduces authority.
It never increases allocation.

============================================================
X. ETHICAL COMPOUNDING FUNCTION
============================================================

function compound_verified_AUM(account, completed_trade):

    broker_record = get_broker_record(account)
    internal_record = get_internal_ledger_record(completed_trade)

    if broker_record.missing:
        return NO_ACTION("broker_record_missing")

    if completed_trade.status != BROKER_CONFIRMED_COMPLETED:
        return NO_ACTION("trade_not_realized")

    if internal_record.missing:
        return NO_ACTION("internal_ledger_missing")

    if broker_record.order_id != internal_record.order_id:
        return NO_ACTION("order_identity_mismatch")

    gross_result =
        broker_record.exit_value
        - broker_record.entry_value

    total_costs =
        broker_record.fees
        + broker_record.spread_cost
        + broker_record.slippage
        + broker_record.execution_cost
        + broker_record.tax_reserve

    realized_net_result =
        gross_result - total_costs

    if realized_net_result > 0:
        next_AUM =
            verified_AUM
            + realized_net_result

    else:
        next_AUM =
            verified_AUM
            - absolute(realized_net_result)

    write_auditable_AUM_event(
        timestamp,
        order_id,
        prior_AUM,
        realized_net_result,
        next_AUM,
        all_costs,
        interest_income=0
    )

    return RECONCILED_AUM(next_AUM)

============================================================
XI. SKYCRAPER ADDITION RULE
============================================================

Each new floor is earned by reality, not imagination.

    verified deposit
        -> verified AUM

    verified AUM
        -> verified deployable capital

    verified deployable capital
        -> permitted notional

    permitted notional
        -> qualified candidate

    qualified candidate
        -> broker preview

    broker preview
        -> authorized handoff

    authorized handoff
        -> broker-confirmed execution

    broker-confirmed execution
        -> realized result

    realized result
        -> reconciled AUM

    reconciled AUM
        -> next permitted allocation

No shortcut may connect:

    forecast -> AUM
    confidence -> AUM
    narrative -> AUM
    hope -> AUM
    historical pattern -> AUM

============================================================
XII. FINAL DECISION LOGIC
============================================================

function apex_v5_decision(candidate):

    ontology = classify_what_is_real(candidate)
    evidence = classify_what_is_known(candidate)
    ethics = evaluate_permissibility(candidate)
    logic = evaluate_inference(candidate)
    broker = refresh_authoritative_broker_state()

    if ontology.account_reality_missing:
        return NO_ACTION("capital_not_verified")

    if evidence.required_fact_below_K4:
        return NO_ACTION("insufficient_market_knowledge")

    if broker.buying_power_below_K5:
        return NO_ACTION("buying_power_not_confirmed")

    if ethics.prohibited_action:
        return NO_ACTION("ethically_or_operationally_prohibited")

    if logic.contradiction_detected:
        return NO_ACTION("logical_contradiction")

    if candidate.data_is_stale:
        return NO_ACTION("stale_data")

    if candidate.total_friction >= candidate.expected_net_result:
        return NO_ACTION("friction_consumes_edge")

    if candidate.downside_unknown:
        return NO_ACTION("downside_unknown")

    if candidate.duplicate_or_pending:
        return NO_ACTION("duplicate_execution_risk")

    if SHADOW_MODE:
        return WOULD_EXECUTE(
            live_order_submitted=false,
            AUM_change=0,
            realized_profit=0
        )

    return EXISTING_AUTHORIZED_BROKER_HANDOFF(
        all_final_gates=true
    )

============================================================
XIII. FINAL LAW OF THE SYSTEM
============================================================

The system must remain intellectually honest.

It cannot turn possibility into fact,
forecast into capital,
activity into wisdom,
or confidence into certainty.

AUM compounds only from:

    existing verified capital
    plus verified external additions
    plus broker-confirmed realized net profit
    minus verified losses and costs

Therefore:

    NO ACTION is not failure.

    NO ACTION is the logically correct result
    whenever reality is insufficiently known,
    ethically impermissible,
    or operationally unsafe.
```
