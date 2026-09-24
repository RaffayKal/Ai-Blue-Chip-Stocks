# ROBINHOOD_RULES.md

Primary agentic broker: Robinhood.

Execution routing is fixed: Robinhood MCP is the sole primary order-placement
authority. RunPod may scan and provide backup data continuity; Claude and other
systems may orchestrate or validate. No alternate system may place orders.

Effective date: `2026-09-10`.

Configured local MCP route:

```text
robinhood-trading
https://agent.robinhood.com/mcp/trading
```

Robinhood buying power must be verified from the connected broker at runtime.

## Confirmed Robinhood Facts

- Robinhood supports fractional shares for eligible stocks and ETFs.
- Robinhood fractional stock/ETF orders must be valued at `$1.00` or more.
- Robinhood fractional stock/ETF orders are regular-market-hours only.
- Robinhood fractional equity orders require market orders in the agentic tool route.
- Robinhood extended-hours and 24 Hour Market equity orders require limit orders, not market orders.
- Robinhood Crypto can trade 24/7, except scheduled maintenance and account restrictions.
- Robinhood Crypto fractional spot orders can start at `$0.01` with market-maker routing or `$0.03` with smart-exchange routing, subject to live account, asset, routing, and preview validation.
- Robinhood Crypto is separate from Robinhood Financial.
- Autonomous allocation is dynamically bounded between 3% and 20% of verified buying power, with one open position maximum.
- Crypto spread is routing-aware: market-maker quotes may pass up to 2.00% because Robinhood live market-maker quotes can be materially wider; smart-exchange quotes remain capped at 0.70%. There is no minimum spread requirement. The live Robinhood preview and positive after-cost-profit check remain authoritative.
- Quotes must come from available live sources within the configured 0.0007-second-to-7-minute operating range.
- Robinhood margin access is not automatic.
- Robinhood margin requires eligibility and at least `$2,000` portfolio value.

## Dynamic Capital

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto:
use the selected account’s crypto buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

## Trillion-Scale Rule

The user's range "fractions of a dollar to trillions if the margins allow for it" means the algorithm must be scalable, not reckless.

At runtime:

- minimum live order evaluation must satisfy the broker minimum
- maximum cash-backed order evaluation is the selected account’s authoritative live buying power
- margin is blocked unless verified margin approval and margin buying power are live-confirmed
- trillion-scale notional is `NO ACTION` unless verified margin buying power, maintenance requirements, liquidity, risk limits, and explicit user authorization all support it

Only when a future account has verified margin approval, verified margin buying power, verified maintenance requirements, verified liquidity, and explicit user authorization may larger notional sizes be evaluated.

## Agentic Order Gate

Before any Robinhood real-money action:

1. Get accounts.
2. Use only an account with `agentic_allowed=true`.
3. Use the exact account number from the verified account.
4. Check tradability for equities.
5. Preview or review the order.
6. Present the result to the user.
7. Wait for explicit user confirmation for that exact order.
8. Place only the reviewed order.

No default order amount. No default ticker. No default account.


## Robinhood Equity Session Hours

For U.S. blue-chip stocks on Robinhood, classify sessions in Eastern Time:

- `PRE_MARKET`: generally 4:00 AM to 9:30 AM ET.
- `REGULAR`: 9:30 AM to 4:00 PM ET, Monday through Friday.
- `AFTER_HOURS`: 4:00 PM to 8:00 PM ET.
- `OVERNIGHT`: Robinhood 24 Hour Market only for eligible symbols and only when live broker tradability confirms support.

Regular-hours fractional/dollar stock orders use market orders. Pre-market, after-hours, and overnight equity execution require eligible symbols, live broker confirmation, and limit orders.

## Equity Rules

For blue-chip stocks and ETFs:

- crypto fractional spot order: routing-aware minimum of `$0.01` market-maker or `$0.03` smart-exchange; equity fractional minimum remains separate.
- extended hours: limit order only, no fractional/dollar market order
- all-day/24-hour market: limit order only, no fractional/dollar market order
- unsupported fractional eligibility returns `WATCHLIST ONLY`

## Crypto Rules

For crypto:

- Robinhood Crypto account must exist and be agentic-enabled.
- Crypto can be checked 24/7.
- Scheduled maintenance blocks action.
- Account restrictions block action.
- Minimum crypto order evaluation is routing-aware: `$0.01` market-maker or `$0.03` smart-exchange. The live Robinhood preview remains authoritative.
- Crypto cannot be used as margin collateral for stock positions.
