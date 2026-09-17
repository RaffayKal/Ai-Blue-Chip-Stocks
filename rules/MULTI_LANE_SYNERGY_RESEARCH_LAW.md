# MULTI_LANE_SYNERGY_RESEARCH_LAW.md

This file is mandatory law. It governs how the medium-weight scanner's lane
capacity (currently up to 700 concurrent lanes, `RUNPOD_MAX_MEDIUM_WEIGHT_LANES`
in `scripts/start_lightweight_scanner_fleet.sh`) is used, and it is binding
on Apex the same way `MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md` and
`BLUE_CHIP_RULES.md` are.

## Purpose

A single lane running one generic scan against one symbol wastes the fleet's
real capacity. With hundreds of lanes available, multiple lanes must be
dedicated per blue-chip stock and per tracked crypto asset, each looking in a
different analytical direction, so their combined output is a synergized
appreciation/depreciation read on that asset -- not N copies of the same
read.

## Symbol Universe

Blue-chip stocks remain the primary focus (`BLUE_CHIP_RULES.md`). Crypto is
the always-on 24/7 side of the fleet, secondary to blue-chip. Every symbol
this law applies to:

- Every symbol listed in `data/blue_chip_watchlist.txt` (per
  `BLUE_CHIP_RULES.md`, an unlisted symbol is never silently treated as
  approved).
- Every symbol in `lane_synergy_engine.TRACKED_CRYPTO_SYMBOLS` -- currently
  BTC, ETH, SOL, XRP, BNB, ADA, DOGE, LTC, DOT, AVAX, LINK.

This crypto list is deliberately broader than, and kept separate from, the
tradable/executable crypto set
(`rank_volatile_crypto_candidates.ROBINHOOD_SUPPORTED_TRACKED_SYMBOLS` and
`runpod_lightweight_scanner.TRACKED_CRYPTO_SYMBOLS`), which stays limited to
what the broker can actually execute. Adding a coin to the synergy research
universe is read-only market awareness; it never grants that coin execution
eligibility, and it never touches the broker-tradable list on its own.

No other symbol is in scope. This law does not expand the tradable universe;
`BLUE_CHIP_RULES.md` and the broker-tradable crypto list remain the sole
source of truth for what counts as a blue-chip or executable-crypto asset.

## Lane Role Taxonomy

Every dedicated lane is assigned exactly one `(symbol, role)` pair. The four
roles are:

1. **MATH** -- pure quantitative calculation. Computes momentum and
   volatility from the symbol's own recorded price history. States
   `INSUFFICIENT_DATA` rather than inventing a number when the window is
   thin.
2. **HISTORY** -- reads the symbol's real recorded price window (recent
   low/high/range/trend). This is the only source of "past" data; it is
   never backfilled or invented.
3. **RESEARCH** -- news/media/web/sentiment layer. Uses whichever connected
   source actually covers the symbol (currently Stocktwits sentiment, where
   its scope matches). Per the Missing Plugin Rule in
   `MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md`, a symbol with no connected
   news/media/web source reports `PLUGIN_UNAVAILABLE` -- it is never
   fabricated to force a signal.
4. **TEMPORAL** -- assembles PAST (oldest point in the current recorded
   window) / PRESENT (latest live read) / FUTURE (a labeled linear
   extrapolation of MATH's own momentum, explicitly tagged
   `PROJECTION_NOT_GUARANTEE`) into one frame per symbol.

Reference implementation: `scripts/lane_synergy_engine.py`. Lane assignment
and execution: `scripts/threaded_scanner_lane_pool.py`.

## Lane Allocation

With 700+ lanes available, capping each symbol at exactly 4 lanes (one per
role) wastes most of the fleet. Any number of lanes may be assigned to the
same blue-chip/crypto symbol:

- One full pass over every `(symbol, role)` combo is always dedicated first,
  as soon as the configured lane count allows it.
- Beyond that, lane index `i` (1-based) wraps around
  (`combo_index = (i - 1) % combo_count`), deliberately piling additional
  concurrent lanes onto earlier combos. More lanes on the same
  `(symbol, role)` means the live feed is sampled at more distinct
  sub-second instants per interval -- finer-grained real-time tracking, not
  duplicate work. `lane_synergy_engine.append_history` is idempotent
  against the underlying price tick, so concurrent lanes writing the same
  not-yet-updated price never corrupt or duplicate the recorded window.
- The dedicated lane count is `max(combo_count, round(lane_count *
  SYNERGY_LANE_SHARE))`, capped at `lane_count`
  (`RUNPOD_SYNERGY_LANE_SHARE` env var, default `0.6`). The remainder
  continues running the pre-existing generic scan
  (`runpod_lightweight_scanner.scan_once`) unchanged -- this law is
  additive. It does not replace, gate, or slow down the existing candidate
  envelope, viability check, or fleet consensus signal that Apex already
  depends on for trade-candidate qualification.

## Synergy Combination

Per symbol, once per rollup cycle, the four role outputs are combined:

- Requires MATH, HISTORY, and TEMPORAL to each be fresh (age within the
  configured staleness window) and `status: OK`. RESEARCH is corroborating
  only, because it is frequently `PLUGIN_UNAVAILABLE` today -- its absence
  must never block a forecast, and its presence must never be treated as
  sole authority.
- Forecast label is one of: `APPRECIATION_LIKELY`, `DEPRECIATION_LIKELY`,
  `NEUTRAL`, or `INSUFFICIENT_SYNERGY_DATA`.
- Output: `data/lane_synergy/<symbol>/synergy.json` per symbol, and a
  fleet-wide rollup at `data/lane_synergy_status.json`.

## Authority Boundary (binding)

This law produces **research evidence only**. It carries the same authority
class as Longbridge market intelligence, TradingCursor technical signal, and
Stocktwits sentiment in `MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md`:

- It has no execution authority. It does not place, modify, or cancel
  orders.
- It does not change AUM, position, capital-exposure, or compounding state.
- It does not bypass, weaken, or substitute for the existing candidate
  envelope gate, broker gates, risk gates, or Codex activation workflow.
- A forecast of `APPRECIATION_LIKELY` or `DEPRECIATION_LIKELY` is
  corroborating input to Apex Synthesis, never sole trade authority, exactly
  like sentiment is never sole trade authority.
- `INSUFFICIENT_SYNERGY_DATA` must never be treated as a bullish or bearish
  signal -- it means exactly what it says: not enough fresh role data
  exists yet to synergize.

## Fail-Closed Rule

If a role's underlying real data source is missing, stale, or unmatched to
the symbol, that role reports its own honest unavailable/stale status. It
never fabricates a substitute reading. A symbol lacking enough fresh roles
correctly produces `INSUFFICIENT_SYNERGY_DATA`, not a forced call.

## Relationship to Other Rules

This law sits upstream of, and feeds into, Step 2 (Longbridge) and Step 5
(TradingCursor) evidence gathering in
`MULTI_PLUGIN_AGENTIC_ORCHESTRATION.md`. It is subordinate to
`BLUE_CHIP_RULES.md` for what counts as an eligible blue-chip asset, and it
is subordinate to every capital, risk, broker, and execution gate elsewhere
in `rules/`. Nothing in this file grants new execution authority.
