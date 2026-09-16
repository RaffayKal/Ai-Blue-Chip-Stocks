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
