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

## Market Reality Rule

Crypto, equities, options, ETFs, and funds do not share the same trading clock.

Agents must not treat stock after-hours failures as crypto failures, and must not treat crypto availability as proof that stocks are open.

## Capital Protection Rule

Capital preservation outranks signal strength.

Current user capital is `$5.00` unless the user updates `rules/user_settings.json`.

With `$5.00`, agents must prefer watchlist mode and must block full-share blue-chip purchases above available capital. Fractional-share blue-chip action requires broker and asset eligibility confirmation.

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

Crypto runs as `CRYPTO_24_7` checked Robinhood Crypto mode. Blue chips run as `BLUE_CHIPS_WHEN_POSSIBLE` only when session, symbol tradability, and Robinhood account permission are confirmed.
