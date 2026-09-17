# ROBINHOOD_RULES.md

Primary agentic broker: Robinhood.

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
- Robinhood Crypto orders can start at `$1.00`.
- Robinhood Crypto is separate from Robinhood Financial.
- Autonomous allocation is dynamically bounded between 3% and 20% of verified buying power, with one open position maximum.
- Accepted spread target is 0.02%-0.07%; 0.07% is the hard ceiling.
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

- regular hours fractional/dollar order: market order only, `$1.00` minimum
- extended hours: limit order only, no fractional/dollar market order
- all-day/24-hour market: limit order only, no fractional/dollar market order
- unsupported fractional eligibility returns `WATCHLIST ONLY`

## Crypto Rules

For crypto:

- Robinhood Crypto account must exist and be agentic-enabled.
- Crypto can be checked 24/7.
- Scheduled maintenance blocks action.
- Account restrictions block action.
- Minimum order evaluation is `$1.00`.
- Crypto cannot be used as margin collateral for stock positions.
