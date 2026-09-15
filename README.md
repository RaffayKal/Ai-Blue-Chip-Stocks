# AI BLUE CHIP STOCKS

This is the main working directory for Claude, Codex, and trading-support agents.

The previous directory is abandoned. Agents must treat this folder as the new root and must not borrow rules, paths, assumptions, or outputs from any older project unless the user explicitly names the file to import.

## Required Start Order

1. Read `AGENTS.md`.
2. Read `CLAUDE.md` when running Claude.
3. Read `COMMANDS.md`.
4. Read `rules/MARKET_SESSION_RULES.md`.
5. Read `rules/CAPITAL_RULES.md`.
6. Read `algorithms/CAPITAL_ALGORITHM.md`.
7. Run `./scripts/verify_environment.sh`.
8. Run executable checks with `python3 algorithms/capital_engine.py <input.json>` when a structured market input exists.
9. For the current $5 start mode, read `START_TODAY.md` and run `./scripts/start_agentic_cycle.sh`.
10. Because the user's primary agentic stock-market account is Robinhood, read `rules/BROKERAGE_RULES.md` and `rules/ROBINHOOD_RULES.md`, then fill or verify `rules/brokerage_intake.json` before treating anything as actionable.

No reports, summaries, dashboards, alerts, trades, scans, or recommendations are valid until this start order is complete.

Autonomous execution, when enabled by the user, is gated by `rules/AUTONOMOUS_EXECUTION_RULES.md`, `algorithms/candidate_envelope_gate.py`, `scripts/run_autonomous_if_viable.sh`, and `algorithms/autonomous_order_gate.py`. Codex must stay dormant unless `data/current_candidate_envelope.json` validates `VIABLE: true` and `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS`. After activation, the autonomous buy/sell gates must use the current envelope's extracted `market_input`, not sample market files.

The active code must also pass `rules/algorithm_sources.json` through `scripts/verify_algorithm_sources.sh`. That manifest anchors the main folder to the rule and algorithm files in `rules/` and `algorithms/`; if any required source is missing or empty, autonomous execution returns `NO ACTION`.

The executable user algorithm is `APEX_110_BLUE_CHIP_CRYPTO_COMPOUNDING` in `rules/APEX_INVESTING_ALGORITHM.md`. Autonomous tickets must declare this exact `user_algorithm_id`, or the gate returns `NO ACTION`.

## Usage-Conserving Runtime Cadence

- Lightweight market watch runs continuously at a 1-second scanner cadence.
- Codex usage-refresh start: run one light health check to confirm operations are live.
- Codex usage exhaustion/end: run one light health check and freeze/report if usage is at or below 2%.
- Otherwise, a light operations-health check runs every 5 hours to confirm operations remain live.
- Night report: send one concise operations report after the day session showing smooth/not-smooth status and blockers.
- Codex/APEX heavy checks do not run on the heartbeat; they stay asleep unless a fresh viable event requires the gate workflow.
- Trading execution remains OFF unless every scanner, broker, Robinhood, risk, preview, idempotency, and APEX gate passes.

## Absolute Operating Truth

- Crypto can trade 24/7, subject to exchange, liquidity, maintenance, wallet, and API availability.
- U.S. stocks do not trade like crypto. Regular, pre-market, after-hours, overnight, holiday, halted, and closed sessions must be handled separately.
- If a session, data source, broker route, order type, or timestamp cannot be verified, execution returns `NO ACTION`; operations continue until Codex usage is less than or equal to `2%` or telemetry is unknown.
- Use `python3` only. Never use the `python` command.
- No agent may promise profit, certainty, or guaranteed optimality.

## First Code Check

```bash
python3 algorithms/capital_engine.py data/sample_crypto_input.json
```

The sample intentionally returns `NO ACTION` until source confirmations and capital settings are supplied.

## Start Today

```bash
./scripts/start_agentic_cycle.sh
```

This runs the crypto 24/7 check, the blue-chip-when-possible check, and the current-envelope activation bridge. With the default dormant envelope, it must not run buy/sell gates.
