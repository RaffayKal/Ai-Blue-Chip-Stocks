# CAPITAL_ALGORITHM.md

Deterministic capital algorithm for Claude and Codex.

This is a rules engine, not a promise of profit.

## Required Inputs

Each evaluation requires:

- symbol
- asset class
- venue or broker route
- session state
- current timestamp and timezone
- quote timestamp and timezone
- bid
- ask
- last price
- spread
- recent volume or liquidity proxy
- user capital available for this system
- max risk per action
- max daily loss
- current open positions
- current open orders
- data source names

Missing input returns `NO ACTION`.

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto:
use the selected account’s crypto buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

## Algorithm

1. Confirm working directory is `/Users/raffaykal/AI BLUE CHIP STOCKS`.
2. Confirm `python3` exists if Python execution is required.
3. Classify the symbol into an asset class.
4. Confirm market session using `rules/MARKET_SESSION_RULES.md`.
5. Reject unknown, closed, unsupported, halted, or unconfirmed sessions.
6. Confirm quote freshness.
7. Confirm bid, ask, spread, and liquidity.
8. Cross-check data sources.
9. Confirm broker/API route supports the asset, session, and order type.
10. Apply hard stops from `rules/CAPITAL_RULES.md`.
11. For blue-chip stocks, apply `rules/BLUE_CHIP_RULES.md`.
12. Calculate risk dollars.
13. Calculate position size.
14. Reject the action if size, notional, liquidity, spread, or open risk violates limits.
15. Output one of:
    - `NO ACTION`
    - `NEEDS USER CAPITAL SETTINGS`
    - `WATCHLIST ONLY`
    - `VALIDATED SETUP`

## Output Format

```text
RESULT: <NO ACTION | NEEDS USER CAPITAL SETTINGS | WATCHLIST ONLY | VALIDATED SETUP>
SYMBOL: <symbol>
ASSET_CLASS: <asset class>
SESSION: <session>
DATA_STATUS: <fresh | stale | conflicting | missing>
RISK_STATUS: <pass | fail | needs settings>
FAILED_CHECKS: <comma-separated list or none>
NEXT_ALLOWED_STEP: <plain action>
```

## Forbidden Outputs

Agents must not output:

- guaranteed profit claims
- certainty claims
- unverified buy/sell commands
- recommendations based only on sentiment
- crypto assumptions applied to stocks
- stock-session assumptions applied to crypto
- position sizing without user capital settings
