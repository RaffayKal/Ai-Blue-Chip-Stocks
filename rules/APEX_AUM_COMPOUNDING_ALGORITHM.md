# APEX_SKYSCRAPER_AUM_ENGINE_V7 — MORPHOLOGY, METHODOLOGY + JURISPRUDENCE

Algorithm ID: `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING`

## APEX MICRO-CAPITAL SKYSCRAPER — GOVERNING SPECIFICATION

The user-supplied **APEX MICRO-CAPITAL SKYSCRAPER: NON-INTEREST AUM
COMPOUNDING SPECIFICATION** is the governing specification for this engine.
Its controlling invariants are:

- `q = $0.00000007` is ledger precision only; broker minimums, asset precision,
  tick size, and settled cash control executable orders.
- Deployable capital is settled cash less protected reserve, tax reserve, and
  pending orders; unrealized P/L never raises a confirmed floor.
- A floor is credited only after a closed position, settled proceeds, positive
  net realized P/L after all costs, and reconciliation.
- Use Decimal or integer nano-dollar accounting; never binary floating-point
  rounding for ledger quanta.
- Size from loss-first risk cash, invalidation distance, liquidity, position
  caps, and deployable capital.
- Require fresh quorum, no source conflict, broker/account verification,
  settled cash, numeric notional, positive after-cost edge, risk pass,
  duplicate-order clearance, and exact preview/review before execution.
- The state machine is `SCAN -> VALIDATE -> FORECAST -> SIZE -> GATE -> REVIEW
  -> EXECUTE -> RECONCILE`.
- Any failed, stale, contradictory, or missing condition yields `NO ACTION`;
  scanning and forecasting continue.

The quantum-inspired probability layer is an uncertainty model only. It never
creates certainty, capital, broker authority, or an execution exception.

V5 is primarily a medium-scanner control layer. Scanners classify and rank
evidence; they never create broker authority, submit previews, place orders, or
credit AUM.

V6 remains primarily for medium-scanner understanding and governance. Interest,
guaranteed profit, forecast-as-capital, imagination-as-evidence, options, margin,
leverage, and short selling are excluded. Legally transferred family funds are
permitted capital when the broker confirms ownership, availability, and account
eligibility; broker margin and leverage remain excluded.

V7 is primarily a medium-scanner operating method. It does not grant scanners
live authority; broker and final APEX gates remain mandatory.

Fresh-data ownership: ChatGPT medium-scanner workers running under the RunPod
runtime refresh configured market-source snapshots continuously and upload
timestamped candidate-lane artifacts. The scanner layer may publish a candidate
without a precomputed order amount. APEX/Codex calculates exact notional from
fresh broker buying power, risk, entry, invalidation, liquidity, and allocation
inputs; missing sizing inputs block execution, not source ingestion.

Mode: realized-net-profit compounding. Interest, broker-borrowed capital,

Capital freshness ceiling: verified deployable cash, trading capital, and
liquidated proceeds may not remain stale for more than 7 days. Before that
ceiling, refresh authoritative broker state, reconcile the AUM ledger,
recalculate permitted allocation, and evaluate current candidates. If no
candidate passes the APEX gates, preserve the capital and return `NO ACTION`.

Scanner source-of-truth priority: `projection.aum_compounding.compounding_score`
is the primary medium-scanner ranking field. It ranks verified realized
history when available and otherwise uses only the explicitly labeled
after-cost opportunity proxy. It never creates AUM or authorizes execution.
`UNKNOWN_REALIZED_LEDGER` is valid startup state when no completed transaction
exists; it must not be converted into profit or synthetic buying power.

Medium scanners may publish candidates without a precomputed notional. Exact
notional remains a downstream APEX/Codex calculation from fresh broker capital,
risk, entry, invalidation, liquidity, allocation, and friction inputs.
leverage, options, margin, short selling, guaranteed profit, unrealized profit,
and projected profit are excluded from compounding. Legally transferred family
capital is included after broker confirmation.

## Wait / grow / harvest pacing doctrine

This engine is not optimized for fast money or high-frequency cycling. A
position is realized (harvested) only after it clears both a minimum hold
duration and the next configured floor's required percentage gain -- not on
every favorable tick. A stop-loss or confirmed setup invalidation always
overrides patience; capital preservation beats waiting. Absent that, holding
toward the next floor and harvesting there is the default, not an exception.
`economically superior waiting` (see V4/V5 pause gates above) is the normal
operating mode, not a fallback.

## Controlling objective

Verified deployable AUM may grow only through external capital actually received,
realized net trading profit, and deliberately recycled realized capital. Interest,
broker-borrowed funds, leverage, margin, projected profits, unrealized gains,
paper appreciation, and unverified balances are excluded. Verified family
transfers are external capital, not broker borrowing.

## AUM accounting

`GROSS_AUM` is verified cash plus eligible holdings at current verified market
value plus broker-confirmed available unsettled assets.

`DEPLOYABLE_AUM` is Robinhood-confirmed spendable buying power (equity and crypto
kept separate), less reserved obligations, pending orders, and risk reserves.
Sale proceeds are included only when Robinhood's refreshed buying-power/availability
reports them spendable; never add the same proceeds a second time.

Capital-source clarification: broker-confirmed sellable holdings are a
liquidation path, not current cash buying power. A SELL gate may use exact fresh
sellable quantity without requiring positive cash buying power. It must not use
estimated holding value as buy capital. After a sale, refresh Robinhood
buying-power/availability and reconcile the ledger; count the proceeds once,
through the refreshed broker capital field, before sizing any next BUY.

`COMPOUNDING_AUM` changes only by verified deposits, realized net profit, realized
net loss, withdrawals, fees, execution costs, and applicable tax reserve.

Unrealized profit is informational only and never increases order size by itself.

For each period:

```text
AUM[t+1] = AUM[t]
        + external_inflows
        + realized_net_profit
        - realized_net_loss
        - withdrawals
        - fees
        - execution_costs
        - tax_reserve
```

Trade-level realized net profit deducts original cost basis, spread, broker and
transaction fees, slippage, liquidity impact, execution friction, and tax reserve.
Deposits are never labeled profit.

## No-interest rule

`INTEREST_INCOME = 0`. APR, yield, staking, lending, dividends, and forecasted
appreciation are excluded unless explicitly enabled as a separate verified income
lane. This engine compounds trading results only.

## Allocation and risk

Every cycle uses fresh verified broker state. The trade amount is the minimum of
verified buying power, the configured 3%–20% tactical allocation band, active
ticket maximum, risk-allowed amount, and liquidity-allowed amount. No full-Kelly,
all-in, leverage, margin, options, or short-selling allocation is permitted.

Sizing is recalculated after every realized action, loss, withdrawal, deposit, or
material state change. A stronger forecast never overrides a failed gate.

Allocation is damped: a new allocation may not exceed the calculated permitted
amount, the prior verified allocation multiplied by the configured maximum-growth
multiplier, current verified buying power multiplied by the configured cap, or
the configured 3%-20% tactical band. Unexpected jumps require fresh validation,
a reason code, and broker-state confirmation.

The engine separately checks for FOMO, revenge trading, overconfidence,
confirmation bias, recency bias, sunk-cost behavior, loss-chasing, gambler's
fallacy, hot-hand behavior, narrative bias, and action bias. Emotional urgency or
unsupported confidence produces `NO ACTION`.

## Entry and exit

Entry requires fresh source quorum, confirmed instrument/venue/session, acceptable
historical/present/projected regimes, multi-timeframe alignment, volatility quality,
liquidity, spread, positive expected net opportunity, duplicate-position clearance,
verified AUM and buying power, valid ticket, and fresh idempotency.

Exit requires confirmed sellable quantity, viable exit economics, cost basis,
positive net proceeds after all costs, and an exact Robinhood preview match.
Unrealized appreciation is never credited as realized compounding capital.

## Reconciliation

At every cycle compare calculated ending AUM with broker-verified ending AUM. Any
non-reconciliation freezes new execution, preserves the ledger, requests fresh
broker state, and returns `NO ACTION`.

## Outputs

Valid states are `VALIDATED SETUP`, `WATCHLIST ONLY`, `HUMAN APPROVAL REQUIRED`,
`NO ACTION`, `WOULD_EXECUTE` (shadow mode only), and `EXECUTED` (all live gates pass).

Missing, stale, contradictory, unsupported, or unverified facts always produce
`NO ACTION`.

## V4 control layer

Classify every input as `FACT`, `CALCULATION`, `ESTIMATE`, `FORECAST`, or
`UNKNOWN`. Only facts and reproducible calculations may pass hard gates. Forecasts
may rank candidates but cannot create capital, buying power, or authority.

Use adverse, flat, expected, favorable, and extreme-favorable scenarios. Record
probability, horizon, gross result, all costs, net result, and maximum loss. If
downside or total friction is unknown, or only the favorable scenario is
profitable, return `NO ACTION`.

Treat correlated or copied feeds as one source family. Apply correlation,
duplication, contradiction, and uncertainty penalties before combining evidence.
Momentum never overrides deteriorating liquidity or spread.

Measure a candidate only after refreshing timestamp, identity, venue, session,
bid, ask, last, spread, liquidity, buying power, position, duplicate state, APEX
viability, and execution eligibility. Before measurement there is no order,
compounding credit, or execution authority.

Pause for incomplete truth, uncertain identity, duplicated evidence, conflicts,
unknown broker state, guarantee-dependent outcomes, action pressure, recent-win
overconfidence, loss-chasing, or economically superior waiting. Return
`NO_ACTION` with the reason.

Realized profit may increase future capacity only after broker-confirmed completion,
updated buying power, ledger reconciliation, no pending correction, and tax-reserve
accounting. Forecasts cannot recursively increase allocation.

V4 invariants: `interest_income == 0`; unrealized and projected profit are not
compoundable; external cash flows remain separate; realized results reconcile;
prohibited actions, stale or contradictory data, duplicate execution, and all-in
single-asset exposure remain blocked.

## V6 scanner controls

Possibility is not reality: `POSSIBLE_TRADE`, `PROJECTED_PROFIT`, and
`WOULD_EXECUTE` never become account events without broker confirmation. Candidate
state probabilities are classical modeling labels only and must sum to 1; they
cannot create authority, AUM, or realized profit.

Track noise from delayed or copied quotes, missing timestamps, source conflict,
liquidity changes, spread expansion, broker delay, model error, forecast variance,
and execution latency. Effective confidence is raw evidence less the noise
penalty. More scanners, words, computation, or complexity cannot convert noise
into confidence.

Medium scanners may perform neutral process rehearsal: observe facts, identify
missing facts, test adverse/flat/favorable scenarios, calculate friction, recheck
required downstream facts, and accept `NO_ACTION`. Outcome imagination, urgency,
recent-win confidence, or loss-chasing receives no authority or capital credit.

Use two-clock validation: packet age, quote age, decision age, and execution age.
Fast markets require shorter permitted ages. Require event ordering from source
timestamp through packet, validation, broker refresh, preview, submission,
confirmation, and reconciliation. Missing, reversed, or inconsistent timestamps
produce `NO_ACTION` with `clock_integrity_failure`.

Governance is separation of duties: RunPod collects and transports; medium
scanners project, construct scenarios, rank, and label uncertainty; Codex/APEX
revalidates and sizes; Robinhood MCP confirms account state, preview, submission,
and order status; the ledger records realized results and reconciliation. No
component may grant itself authority.

V6 status distinctions are explicit: `SCANNING`, `CANDIDATE_DETECTED`,
`VALIDATION_REQUIRED`, `WATCHLIST_ONLY`, `WOULD_EXECUTE`, `EXECUTED`, `REALIZED`,
`RECONCILED`, and `HALTED`. AUM changes only at broker-confirmed realized and
reconciled events.

## V7 morphological organs

Every candidate passes through separate organs: `SENSOR` receives attributable
timestamped market observations; `INTERPRETER` normalizes and calculates;
`SKEPTIC` searches for contradiction, stale data, copied evidence, assumptions,
and adverse outcomes; `GOVERNOR` applies allocation, loss, asset, account, and
position limits; `EXECUTION_AUTHORITY` remains downstream; and `ARCHIVIST`
records hashes, idempotency, decisions, broker responses, and reconciliation.
No organ may impersonate another.

Allowed transitions are `RAW_DATA` to `NORMALIZED_DATA` to
`VERIFIED_MARKET_FACTS` to `CANDIDATE_HYPOTHESIS` to `FALSIFIED_OR_VALIDATED_SETUP`
to broker revalidation and then a terminal operational state. Direct
`RAW_DATA` to order, forecast to AUM, sentiment to execution, and prior success
to larger authority are forbidden.

## V7 repeatable method

For every candidate: observe, normalize identity/asset/venue/currency/time,
cross-check independent sources, state the hypothesis, attack it with
disconfirming evidence, price all friction, calculate adverse/flat/expected/
favorable/extreme scenarios, size only from runtime broker buying power,
revalidate immediately before handoff, decide, and reconcile only after broker
confirmed completion.

The candidate bears the burden of proof. Admissible evidence is timestamped,
attributable, reproducible, relevant, current, and internally consistent.
Screenshots without timestamps, old packets, copied quotes, social claims,
unsupported forecasts, unverified account values, and prior success are not sole
execution authority.

## V7 jurisprudence and proportionality

Treat each candidate as a case. Instrument identity, asset class, venue, session,
price, spread, liquidity, freshness, broker buying power, broker position state,
duplicate clearance, downside, friction, APEX viability, and execution eligibility
must all be proven. One unproven element dismisses the case as `NO_ACTION`.

Maintain chain of custody from source through normalization, packet hash, consumer
pickup, Codex validation, broker refresh, decision, broker response, and ledger.
If the chain breaks, return `NO_ACTION` with `evidence_chain_broken`.

Prior success is precedent, not current proof. Reconsideration requires new
evidence, a broker change, a quote refresh, a new packet, or resolved conflict;
impatience, confidence, price movement, or prior success is insufficient.

Permitted notional is the minimum of broker buying power times configured cap,
risk budget divided by downside per unit, liquidity capacity, broker limit, and
remaining daily-loss capacity. Uneconomic or disproportionate size returns
`NO_ACTION`.

Immediate halt conditions include unknown broker state, duplicate execution,
corrupt packet hash, stale account data, contradictory position data, unexplained
AUM change, unauthorized execution path, and repeated reconciliation failure.

## V5 scanner controls

Keep account reality, verified market reality, model reality, and narrative
reality separate. Only the first two can support downstream authority. A forecast
is not capital, a score is not buying power, an order request is not a fill, and
a fill is not realized profit until broker records reconcile.

Classify evidence as `K0 UNKNOWN`, `K1 CLAIMED`, `K2 OBSERVED`, `K3 CALCULATED`,
`K4 CROSS-CHECKED`, or `K5 BROKER-CONFIRMED`. Medium scanners must reach K4 for
symbol, asset class, venue, session, quote, spread, and liquidity. Buying power,
position, duplicate state, and final eligibility remain K5 broker checks.

Every candidate receives a falsification test. Invalidate on stale quotes,
spread expansion, liquidity loss, source conflict, failed volume confirmation,
prohibited volatility, broker-state change, duplicate order, or edge falling
below friction. Invalidated candidates return `NO ACTION`.

Correlated or copied feeds count as one source family. Unknown evidence is not
support. Contradictory evidence reduces authority; `viable = true` cannot survive
a missing required fact. Scanner uncertainty never increases allocation.

Candidate states are classical probability labels only: `NO_ACTION`, `WATCHLIST`,
`VALIDATED_SETUP`, `WOULD_EXECUTE`, and `EXECUTED`. Probabilities must sum to 1,
but no candidate becomes `EXECUTED` without broker confirmation and no result
becomes `REALIZED` before completed settlement and ledger reconciliation.

Ethical pause gates include incomplete truth, uncertain identity, duplicated
evidence, broker uncertainty, guarantee-dependent outcomes, action pressure,
recent-win overconfidence, loss-chasing, and economically superior waiting.
Return `NO_ACTION` with the reason.

## Skyscraper invariants

`interest_income == 0`; unrealized and projected profit are excluded; verified
family transfers are recorded as external capital; external cash flows remain
separate; realized profit is broker-reconciled; broker buying
power is a runtime value; duplicate execution, options, margin, leverage, short
selling, stale data, contradictory data, and all-in single-asset exposure are
blocked. No trade is a valid outcome.
