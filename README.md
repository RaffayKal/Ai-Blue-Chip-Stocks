# AI BLUE CHIP STOCKS

This is the main working directory for Codex and trading-support operations.

The previous directory is abandoned. Agents must treat this folder as the new root and must not borrow rules, paths, assumptions, or outputs from any older project unless the user explicitly names the file to import.

## Required Start Order

1. Read `AGENTS.md`.
2. Read `COMMANDS.md`.
4. Read `rules/MARKET_SESSION_RULES.md`.
5. Read `rules/CAPITAL_RULES.md`.
6. Read `algorithms/CAPITAL_ALGORITHM.md`.
7. Run `./scripts/verify_environment.sh`.
8. Run executable checks with `python3 algorithms/capital_engine.py <input.json>` when a structured market input exists.
9. Read `START_TODAY.md` and run `./scripts/start_agentic_cycle.sh`.
10. Because the user's primary agentic stock-market account is Robinhood, read `rules/BROKERAGE_RULES.md` and `rules/ROBINHOOD_RULES.md`, then fill or verify `rules/brokerage_intake.json` before treating anything as actionable.

No reports, summaries, dashboards, alerts, trades, scans, or recommendations are valid until this start order is complete.

Autonomous execution, when enabled by the user, is gated by `rules/AUTONOMOUS_EXECUTION_RULES.md`, `algorithms/candidate_envelope_gate.py`, `scripts/run_autonomous_if_viable.sh`, and `algorithms/autonomous_order_gate.py`. Codex must stay dormant unless `data/current_candidate_envelope.json` validates `VIABLE: true` and `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS`. After activation, the autonomous buy/sell gates must use the current envelope's extracted `market_input`, not sample market files.

The active code must also pass `rules/algorithm_sources.json` through `scripts/verify_algorithm_sources.sh`. That manifest anchors the main folder to the rule and algorithm files in `rules/` and `algorithms/`; if any required source is missing or empty, autonomous execution returns `NO ACTION`.

The executable user algorithm is `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING` in `rules/APEX_INVESTING_ALGORITHM.md`, with AUM accounting controlled by `rules/APEX_AUM_COMPOUNDING_ALGORITHM.md`. Autonomous tickets must declare this exact `user_algorithm_id`, or the gate returns `NO ACTION`.

## Usage-Conserving Runtime Cadence

- Medium-weight market watch runs continuously with scanner loop intervals bounded to `4` through `420` seconds. Heartbeat cadences stay as configured below.
- Medium-weight scanner fleet runs as `7-700+` adaptive lanes as optimally needed, only while lanes remain medium-weight and do not run Codex/APEX heavy execution checks.
- Medium-weight scanners run forward projections/forecasting: continuation probability, reversal risk, stale penalty, spread quality, and net-opportunity scoring for crypto 24/7 and blue-chip market-hours lanes. Forecasts are scanner context, not execution authority.
- Medium-weight scanners refresh quota/snapshot context tactically from Alpaca, Robinhood, CoinGecko, and connected plugin artifacts such as Longbridge, Stocktwits, and TradingCursor. Websocket/live-feed artifacts drive freshness; REST snapshots are bounded fallback/cross-check inputs.
- Scanner lanes read online market/media/report context from machine-readable fresh source artifacts, including Longbridge, Stocktwits, and TradingCursor snapshots when connected. Missing or stale online context is reported and never fabricated.
- Fanout above the safe medium-weight cap is explicitly allowed for medium-weight scanner lanes when needed, up to the configured `7-700+` range. This does not authorize heavy Codex/APEX analysis, order preview, order placement, or broker mutation.
- Codex usage-refresh start: run one light health check to confirm operations are live. Usage remaining is live fluctuating telemetry; `rules/user_settings.json` is only a stale/manual fallback, not the source of truth.
- Codex usage exhaustion/end: run one light health check and freeze/report if usage is at or below 2%.
- Otherwise, a light operations-health check runs every 5 hours to confirm operations remain live.
- Night report: send one concise operations report after the day session showing smooth/not-smooth status and blockers.
- Codex/APEX heavy checks do not run on the heartbeat; they stay asleep unless a fresh viable event requires the gate workflow.
- Trading execution remains OFF unless every scanner, broker, Robinhood, risk, preview, idempotency, and APEX gate passes.
- Major tactical operations follow the explicit loop: RunPod 24/7 engine -> Codex Robinhood live feed plus ChatGPT/RunPod fresh sources and calculations -> timestamped envelopes -> Codex Robinhood MCP refresh -> enriched envelope -> Codex viability gate -> Robinhood inspection/preview -> explicit user confirmation -> Robinhood execution -> operations loop. Missing or stale facts produce `NO ACTION`.

## Absolute Operating Truth

- Crypto can trade 24/7, subject to exchange, liquidity, maintenance, wallet, and API availability.
- U.S. stocks do not trade like crypto. Regular, pre-market, after-hours, overnight, holiday, halted, and closed sessions must be handled separately.
- Capital is dynamic and must be read from the connected broker at runtime. Equities/options use the selected account’s authoritative buying power. Crypto uses the selected account’s crypto buying power. Never use a hard-coded capital amount or total portfolio value as spendable capital. Missing, stale, contradictory, or unavailable live buying-power data returns `NO ACTION`.
- If a session, data source, broker route, order type, or timestamp cannot be verified, execution returns `NO ACTION`; operations continue until Codex usage is less than or equal to `2%` or telemetry is unknown.
- Use `python3` only. Never use the `python` command.
- No agent may promise profit, certainty, or guaranteed optimality.

## First Code Check

```bash
python3 algorithms/capital_engine.py data/sample_crypto_input.json
```

The sample intentionally returns `NO ACTION` until source confirmations and capital settings are supplied.

## Alpaca Market Data Stream

```bash
python3 scripts/stream_alpaca_market_data.py
```

This optional 24/7 feed reads `ALPACA_API_KEY_ID`/`ALPACA_API_SECRET_KEY` or `APCA_API_KEY_ID`/`APCA_API_SECRET_KEY` from `.env`, plus `ALPACA_STOCK_FEED`, `ALPACA_BLUE_CHIPS`, and `ALPACA_CRYPTO_PAIRS`. It writes non-executing stock/crypto stream artifacts under `data/alpaca_stream/` and a latest crypto quote artifact at `data/alpaca_crypto_quote_snapshot.json`. Freshness is driven by Alpaca websocket quote/trade event timestamps, not REST snapshot polling. It does not preview, place, or authorize trades.

```bash
python3 scripts/verify_alpaca_market_access.py --stock-feed iex --limit 5
python3 scripts/scan_apex_expansion_viability.py
```

The verifier checks Alpaca paper account status plus latest blue-chip, crypto, and Apex expansion quotes without order mutation. The expansion scanner evaluates non-blue-chip / non-crypto candidates from `data/apex_expansion_watchlist.txt` and records whether Apex viability is true or false under the same fail-closed capital rules.

## Alpaca Read-Only Adapter

```bash
python3 scripts/alpaca_market_data_adapter.py --rest-once
python3 scripts/alpaca_market_data_adapter.py --serve
```

This adapter reads credentials from `ALPACA_API_KEY_ID`/`ALPACA_API_SECRET_KEY` or the Alpaca-native `APCA_API_KEY_ID`/`APCA_API_SECRET_KEY`, which can be injected as environment variables or RunPod secrets. It normalizes stock and crypto quotes as `provider`, `symbol`, `asset_class`, `bid`, `ask`, `last`, and `timestamp`; rejects stale quotes using `QUOTE_MAX_AGE_SECONDS`; and keeps `scanner_viable` separate from `execution_allowed`. `--rest-once` is a preflight/fallback heartbeat only; fresh scanning should use `--stream`.

The Cloudflare-facing read-only interface is authenticated with `CLOUDFLARE_SCAN_TOKEN` or `SCAN_INTERFACE_TOKEN` and exposes:

- `GET /health`
- `GET /scan?mode=medium`

It returns JSON with `last_event_at`, `symbols_ok`, `stale_count`, `scanner_viable`, `execution_allowed`, and `capital_status`. It does not place orders or change Robinhood execution authority.

## Start Today

```bash
./scripts/start_agentic_cycle.sh
```

This runs the crypto 24/7 check, the blue-chip-when-possible check, and the current-envelope activation bridge. With the default dormant envelope, it must not run buy/sell gates.
