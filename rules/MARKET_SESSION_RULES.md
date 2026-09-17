# MARKET_SESSION_RULES.md

Rules for handling market hours, after-hours, crypto availability, and stale data.

## Asset Classes

Every symbol must be classified before action:

- `CRYPTO`
- `US_EQUITY`
- `ETF`
- `OPTION`
- `FUND`
- `UNKNOWN`

`UNKNOWN` always returns `NO ACTION`.

## Apex Expansion Market Rule

Non-blue-chip / non-crypto symbols may be checked only when they are explicitly listed in `data/apex_expansion_watchlist.txt` and the market input declares `market_focus: APEX_EXPANSION`.

Expansion checks are viability discovery only. They do not inherit blue-chip approval and do not authorize order preview, order placement, broker mutation, or all-in allocation.

Expansion candidates must still confirm asset class, venue, session, bid, ask, last/mark, spread, volume or liquidity, timestamp, source freshness, broker/API capability, and risk limits. Missing or stale facts return `NO ACTION`.

## Crypto Session Rule

Crypto is normally a 24/7 market, but an action is valid only when all checks are true:

- exchange or broker route is online
- pair is supported
- deposits/withdrawals/trading route are not under maintenance
- bid and ask are present
- spread is within configured limit
- liquidity is sufficient
- quote timestamp is fresh
- order type is supported

If any check fails, output `NO ACTION`.

## U.S. Equity Session Rule

U.S. equities and blue-chip stocks must be separated by session in Eastern Time:

- `PRE_MARKET`: generally 4:00 AM to 9:30 AM ET. Peak volume and liquidity usually concentrate closer to 8:00 AM ET.
- `REGULAR`: 9:30 AM to 4:00 PM ET, Monday through Friday, excluding market holidays and halts.
- `AFTER_HOURS`: 4:00 PM to 8:00 PM ET. This can react to late-day earnings and announcements, but liquidity and spreads must be verified.
- `OVERNIGHT`: select-brokerage session covering remaining overnight gaps when offered by the broker, including Robinhood or Interactive Brokers where supported.
- `HOLIDAY`
- `HALTED`
- `CLOSED`
- `UNKNOWN`

Equity actions outside `REGULAR` require explicit support for the broker route, order type, symbol tradability, and session. If not confirmed, output `NO ACTION`.

## Blue-Chip Spread Limit (configured limit referenced above)

```text
midpoint       = (bid + ask) / 2
spread_decimal = (ask - bid) / midpoint
spread_percent = spread_decimal * 100
```

Typical observed ranges, for context only (not a gate by themselves):

- Regular session, very liquid mega-cap: 0.01%-0.05%
- Regular session, typical blue chip: 0.03%-0.10%
- Regular session, volatile/less liquid: 0.10%-0.25%
- Extended hours, typical range: 0.20%-1.00%+

Binding maximums:

- `REGULAR` session: `spread_percent` must not exceed `0.10`. Above that,
  `NO ACTION`.
- `PRE_MARKET`, `AFTER_HOURS`, `OVERNIGHT`: `spread_percent` must not exceed
  `0.25`. Above that, `NO ACTION`.

This is the numeric definition of "spread is within configured limit" in
the Crypto Session Rule above and the spread checks referenced throughout
`BLUE_CHIP_RULES.md` and `CAPITAL_RULES.md`.

## Fast-Market Rule

If volatility or spread expands materially within a session:

- shorten the trusted quote-age window for that symbol
- recalculate execution friction
- recalculate position sizing
- if any resulting gate check fails, output `NO ACTION`

## Freshness Timings

- Scanner refresh cadence: 4 seconds minimum
- Maximum packet age: 420 seconds
- Maximum quote age: 420 seconds
- Maximum provenance age: 420 seconds
- Packet emission interval: 4 seconds minimum

Any fact older than its maximum age above is stale under the Stale Data
Rule below and returns `NO ACTION`.

## Net Opportunity Rule

```text
expected net opportunity =
    expected appreciation
    - spread
    - slippage
    - fees
    - liquidity impact
    - execution friction
```

If expected net opportunity is less than or equal to zero, output
`NO ACTION`.

## Stale Data Rule

Data is stale when:

- timestamp is missing
- timezone is missing
- quote age exceeds configured max age
- source clock conflicts with local clock
- multiple sources disagree beyond configured tolerance

Stale data always returns `NO ACTION`.

## Cross-Source Rule

For a market action, at least two independent confirmations are required when available:

- broker/API quote
- exchange quote
- market-data plugin quote
- news or halt feed
- session calendar

If confirmations conflict, use the most restrictive interpretation and output `NO ACTION` unless the conflict is resolved.
