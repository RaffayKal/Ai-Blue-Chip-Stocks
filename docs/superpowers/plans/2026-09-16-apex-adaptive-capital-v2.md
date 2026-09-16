# APEX Adaptive Capital Engine v2 Implementation Plan

**Goal:** Replace brittle all-or-nothing opportunity qualification with an adaptive, regime-aware, multi-source NetEdge pipeline while preserving downstream capital/risk controls and permanently blocking options execution.

**Architecture:** Normalize independent market sources into source-level freshness/confidence records, classify market regime, score multi-horizon evidence and expected net edge, then map candidates through REJECT/WATCH/QUALIFIED/APEX. Missing auxiliary providers reduce confidence rather than automatically killing a candidate when sufficient authoritative evidence remains. Existing capital, broker, preview, idempotency, allocation and execution gates remain downstream hard constraints.

**Tech Stack:** Python 3, existing test suite and market/runtime adapters.

## Global constraints
- OPTION must never be executable or produce an executable APEX envelope.
- Missing one auxiliary provider must not force viable=false when minimum authoritative evidence is satisfied.
- Stale/conflicting sources are penalized individually; contradictory authoritative price data remains a hard stop.
- NetEdge = p_profit*expected_gain - p_loss*expected_loss - spread - slippage - fees - uncertainty_penalty.
- +775% remains an optimization label/target, not a guaranteed-return predicate.
- Buying power, allocation caps, margin prohibition, preview/review, idempotency and execution logging remain hard controls.
- Main laptop directory `/Users/raffaykal/AI BLUE CHIP STOCKS` is the canonical runtime target; GitHub is the synchronization path.

## Task 1 — Adaptive scoring core
Create `algorithms/apex_adaptive_engine.py` and `tests/test_apex_adaptive_engine.py`.

- [ ] RED: tests for regime classification, provider substitution, stale-source penalties, authoritative conflicts, NetEdge and tier boundaries.
- [ ] GREEN: implement deterministic `classify_regime`, `score_sources`, `calculate_net_edge`, `qualify_candidate`.
- [ ] Require sufficient independent evidence without requiring a named auxiliary provider.
- [ ] Run focused tests; commit `feat: add adaptive apex scoring core`.

## Task 2 — Capital-engine integration + options firewall
Modify `algorithms/capital_engine.py`; create `tests/test_capital_engine_adaptive.py`.

- [ ] RED: OPTION => NO ACTION; auxiliary outage alone does not reject; stale auxiliary data lowers confidence; contradictory authoritative quotes reject.
- [ ] GREEN: explicitly block OPTION before scoring.
- [ ] Replace aggregate freshness/raw source-count choke points with adaptive source assessment while retaining session/quote/buying-power hard stops.
- [ ] Preserve legacy result keys and append APEX_TIER, NET_EDGE, REGIME, SOURCE_CONFIDENCE.
- [ ] Run focused + existing tests; commit.

## Task 3 — Candidate-envelope semantics
Modify `algorithms/candidate_envelope_gate.py`; create `tests/test_candidate_envelope_adaptive.py`.

- [ ] RED: REJECT/WATCH/QUALIFIED keep Codex dormant; APEX wakes only after VALIDATED SETUP; OPTION always dormant.
- [ ] GREEN: gate activation on APEX plus existing capital validation without named-provider dependency.
- [ ] Preserve plugins_execute_trades=false and broker_order_submitted=false requirements.
- [ ] Run tests; commit.

## Task 4 — Execution defense in depth
Modify `algorithms/autonomous_order_gate.py`; create `tests/test_autonomous_order_options_firewall.py`.

- [ ] RED: attempt OPTION through every ticket path and assert execution denied.
- [ ] GREEN: explicit option-firewall reason while preserving executable classes CRYPTO/US_EQUITY/ETF and all risk controls.
- [ ] Run tests; commit.

## Task 5 — Runtime source substitution
Modify `algorithms/apex_packet_monitor.py`, the existing RunPod/orchestrator module identified from imports, `tests/test_apex_packet_monitor.py`, and `tests/test_runpod_lightweight_scanner_capital.py`.

- [ ] RED: Alpaca/Robinhood/Longbridge substitution, auxiliary outage, mixed freshness, authoritative quote disagreement.
- [ ] GREEN: normalize provenance records with source/timestamp/status/role/confidence; never convert one auxiliary outage into global stale state.
- [ ] Feed regime/scoring inputs into adaptive engine and preserve raw provenance for audit.
- [ ] Run tests; commit.

## Task 6 — Verification + laptop deployment handoff
Modify `algorithms/CAPITAL_ALGORITHM.md` and README runtime documentation where applicable.

- [ ] Run `python3 -m pytest tests -q`; require zero failures.
- [ ] Run `python3 -m py_compile` on modified Python modules.
- [ ] Document adaptive tiers, NetEdge, source substitution and options prohibition.
- [ ] Confirm no credentials/secrets are committed.
- [ ] Synchronize approved code through GitHub, then fast-forward/pull it into `/Users/raffaykal/AI BLUE CHIP STOCKS` on the main laptop and rerun the complete test suite there before runtime restart.
