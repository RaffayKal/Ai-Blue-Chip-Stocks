# CAPITAL_RULES.md

Capital rules for the user's capital algorithm.

## Priority Order

1. Protect capital.
2. Avoid invalid market sessions.
3. Avoid stale or contradictory data.
4. Avoid oversized positions.
5. Avoid low-liquidity execution.
6. Only then evaluate signal quality.

Signal strength never overrides risk failure.

## Current Allocation and Market-Quality Bounds

- Allocation: dynamically 3%-20% of verified buying power.
- Maximum open positions: 1.
- Liquidity: require confirmed positive liquidity sufficient for the positive net-profit calculation; no invented fixed dollar threshold.
- Equity spread: 0.00%-0.07%. Crypto spread is routing-aware: market-maker up to 2.00%, smart-exchange up to 0.70%. There is no minimum spread requirement; preview and positive after-cost-profit checks still control execution.
- Quote freshness: use available live sources within the configured 0.0007-second-to-7-minute operating range; stale or contradictory data returns `NO ACTION`.

## Dynamic Capital Rule

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto:
use the selected account’s crypto buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

BUY and SELL capital checks are distinct. A SELL may be evaluated against fresh,
broker-confirmed sellable quantity for the exact held position even when cash
buying power is zero. The quote/position record must identify a fresh Robinhood
position source and the requested quantity must not exceed its sellable quantity.
That position record must also be tied to the currently verified agentic account.
Unsold market value is not deployable cash. After broker-confirmed sale, fresh
Robinhood availability/buying-power refresh, and ledger reconciliation, sale
proceeds may fund a subsequent BUY. If Robinhood already reports the proceeds
spendable, do not impose an extra settlement wait; use that refreshed buying-
power field and never add the same proceeds a second time.

The system must automatically adapt as deposits, withdrawals, holdings, profits, losses, and buying power change.

## Hard Stops

Return `NO ACTION` when any item is true:

- symbol is unknown
- asset class is unknown
- session state is unknown
- data is stale
- bid or ask is missing
- spread is too wide
- liquidity is below threshold
- max daily loss is hit
- open risk exceeds limit
- trade route is unavailable
- order type is unsupported
- plugin/tool results conflict
- live buying power is unknown for a sizing calculation


## Retained Growth and Exposure Rules

Retained 25% major-profit exposure is monitored after a major net-profit event. Growth below 10% is `HOLD / MONITOR`. Growth at or above 10% triggers Apex re-evaluation, not automatic liquidation.

If upside remains clear and viable, retain the exposure and reassess dynamically. If upside deteriorates, harvest the grown percentage only after confirming positive net profit after execution friction.

Blue-chip allocation is dynamically bounded between 3% and 20% of verified buying power. The 20% cap is hard, and maximum open positions is 1.

## Position Sizing Formula

Variables:

- `C`: available trading capital
- `R`: allowed risk per action as a decimal
- `D`: distance from entry to invalidation/stop
- `P`: entry price
- `Q`: position quantity

Formula:

```text
risk_dollars = C * R
Q = floor(risk_dollars / D)
notional = Q * P
```

Reject the position when:

- `D <= 0`
- `P <= 0`
- `Q <= 0`
- `notional` exceeds available capital
- `notional` exceeds max allocation for the asset class

## Default Risk Posture

Until the user defines exact numeric risk settings, all sizing outputs must be `NEEDS USER CAPITAL SETTINGS`, not a trade instruction.

## Single-Stock Concentration Block

Never put 100% of capital into one stock. Any proposed stock order or stock portfolio state that would concentrate all available capital in a single stock is blocked.

For U.S. equities and blue-chip stocks, capital must be spread across eligible verified positions whenever execution is allowed. If the account is too small to meet broker minimums across multiple symbols, the system must prefer `WATCHLIST ONLY` or `NO ACTION` instead of forcing a one-stock all-in order.

A single stock must stay inside the configured 3%-20% per-symbol allocation band, available buying power, session rules, broker tradability, liquidity, spread, and risk checks. The 20% ceiling is not all-in permission.

## Single-Crypto Concentration Block

Never put 100% of capital into one crypto asset. Any proposed crypto order or crypto portfolio state that would concentrate all available capital in a single crypto asset is blocked.

For crypto, capital must be spread across verified broker-supported crypto assets whenever execution is allowed and broker minimums permit it. If the account is too small to meet broker minimums across multiple crypto symbols, the system must prefer `WATCHLIST ONLY`, `NO ACTION`, or a smaller capped ticket instead of forcing one-crypto all-in exposure.

A single crypto asset must stay inside the configured per-symbol/per-asset allocation cap, buying power, liquidity, spread, volatility, and net-profit checks.
