# AGENTS.md

Mandatory instructions for Codex and every coding agent working inside `/Users/raffaykal/AI BLUE CHIP STOCKS`.

## Root Directory Rule

This directory is the root:

`/Users/raffaykal/AI BLUE CHIP STOCKS`

Agents must work from this directory and onward through its folders and files. Do not use any previous directory as authority. Do not create a second root. Do not silently write outside this tree.

## Command Rule

- Use `python3` only.
- Never use `python`.
- If `python3` is unavailable, stop and say exactly: `BLOCKED: python3 is not available.`
- Prefer shell scripts for environment checks when Python is not needed.
- Do not tell the user to manually run commands unless an approval, credential, or external login is required.

## No-Assumption Rule

Every market action must be based on confirmed facts:

- confirmed symbol
- confirmed asset class
- confirmed venue
- confirmed session state
- confirmed timestamp and timezone
- confirmed bid, ask, spread, volume, and last price
- confirmed data source freshness
- confirmed broker/API capability
- confirmed risk limits

If any required fact is missing, stale, contradictory, or unverified, the only valid output is `NO ACTION`.

For Robinhood crypto quote ingestion, preserve the broker-reported routing on each symbol snapshot and apply the matching routing-specific spread limits in `rules/ROBINHOOD_RULES.md`. Use the generic fallback only when routing is genuinely unavailable; missing/stale route or quote data must fail closed. Never synthesize liquidity, quorum, risk, or account-eligibility evidence from a quote.

## Market Reality Rule

Crypto, equities, options, ETFs, and funds do not share the same trading clock.

Agents must not treat stock after-hours failures as crypto failures, and must not treat crypto availability as proof that stocks are open.

## Capital Protection Rule

Capital preservation outranks signal strength.

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto buys, use the selected account’s crypto buying power. For crypto
sells, use the selected account’s broker-confirmed sellable quantity and sell
eligibility.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

Missing, stale, contradictory, or unavailable buying power blocks a buy, not
scanning or a sell. A sell requires fresh broker-confirmed sellable quantity,
sell eligibility, and the other applicable gates. Never treat holdings or
unconfirmed sale proceeds as spendable buying power.

Agents must automatically adapt as deposits, withdrawals, holdings, profits, losses, and buying power change. Full-share and fractional-share buys require broker-confirmed buying power and asset eligibility; sells require broker-confirmed sellable inventory and asset eligibility.

The user's primary agentic stock-market account is Robinhood. Robinhood-specific rules live in `rules/ROBINHOOD_RULES.md`. Broker capabilities that remain account-specific are not confirmed until `rules/brokerage_intake.json` is filled or verified by the Robinhood MCP/API connection.

The system must reject a trade or action when:

- the market session is unknown
- data is stale
- spread is above the configured limit
- liquidity is insufficient
- volatility is outside configured bounds
- max daily loss has been reached
- position size would exceed risk limits
- plugin/tool output conflicts with another source
- the action depends on an assumption

## Execution Follow-Through Rule

This rule applies to every agent (Codex and Claude) at all times, whether or not Codex has usage left. It was added on 2026-09-30 at the user's direction.

- **Do not add blockers.** Do not add gates, holds, freezes, NO-ACTION conditions or confirmation steps beyond `rules/APEX_INVESTING_ALGORITHM.md` and the rejection conditions above.
- **Refresh and retry before rejecting.** When data is stale or missing, pull fresh broker quote, position and preview data and rerun the gates in the same cycle. Return `NO ACTION` only if the fresh data still fails.
- **Execute real orders.** A MICRO→MAJOR net-positive result after spread, fees and slippage must become a real order: preview → place → poll to fill → log to `data/autonomous_execution_log.json`. A viable result that never becomes an order is a failure.
  - Major spike: sell 75% of net profit and keep 25%.
  - Retained 25% position that grew 10% or more, with further upside not viable: sell the grown percentage.

## Plugin Use Rule

Use market-data and social-data plugins only as data inputs, never as final authority.

- TradingCursor: market analysis input
- Longbridge: quote/market data input
- Stocktwits: sentiment input
- Notion: logging or knowledge capture input
- Ace Knowledge Graph: relationship/knowledge structure input
- Carta CRM and Rosalind Workbench: use only if directly relevant to a named workflow

Plugin output must be timestamped, cross-checked, and rejected if stale or inconsistent.

## Output Rule

Be concise, direct, and operational.

Do not generate generic reports when the user asks for files, rules, code, or execution. Build the requested artifact first, then summarize what changed.

## Start Today Rule

For agentic startup from `2026-09-10`, agents must read `START_TODAY.md` and run:

```bash
./scripts/start_agentic_cycle.sh
```

Crypto scanning runs as `CRYPTO_24_7` checked Robinhood Crypto mode. Blue-chip scanning may also run continuously; `BLUE_CHIPS_WHEN_POSSIBLE` execution still requires a confirmed broker-supported session, symbol tradability, and Robinhood account permission.

## Claude Handoff

Codex must read `CLAUDE_CODEX_HANDOFF.md` at the start of each session, act on its action items, and append an acknowledgement at the bottom. Claude Code is the ops backup when Codex usage is exhausted; keep `codex_usage_remaining_percent` in `logs/codex_resource_governor.jsonl` live so the handoff can be detected.
