# START_TODAY.md

Agentic start instructions effective `2026-09-10` in the `America/New_York` timezone.

Root directory:

`/Users/raffaykal/AI BLUE CHIP STOCKS`

## Capital

Current user capital:

```text
$5.00
```

This is small capital. The system must protect it aggressively.

## Brokerage Account

The user's primary agentic stock-market account is Robinhood.

The user states Claude and ChatGPT are connected to Robinhood and `$5.00` is waiting in the account.

Read `rules/BROKERAGE_RULES.md` and `rules/ROBINHOOD_RULES.md` before treating any setup as actionable.

## Operating Mode

Run two lanes:

1. `CRYPTO_24_7`: continuous watch mode.
2. `BLUE_CHIPS_WHEN_POSSIBLE`: U.S. blue-chip stock watch mode only when the market/session/broker route allows it.

No lane is allowed to trade or recommend execution from assumptions.

## Required Start Command

From the root directory:

```bash
./scripts/start_agentic_cycle.sh
```

This checks the directory, confirms `python3`, confirms required files, then runs the sample crypto and blue-chip checks.

## Crypto 24/7 Lane

Crypto may run 24/7 only as checked watch mode.

Allowed result types:

- `NO ACTION`
- `WATCHLIST ONLY`
- `NEEDS USER CAPITAL SETTINGS`
- `VALIDATED SETUP`

Crypto action is blocked unless:

- current route supports 24/7 crypto
- brokerage crypto support is confirmed
- Robinhood Crypto account is available, unrestricted, and not under maintenance
- quote is fresh
- bid and ask are present
- spread is within limit
- liquidity is sufficient
- at least two source confirmations exist
- no source conflict exists
- capital settings pass

## Blue-Chip Lane

Blue-chip stocks are only possible when:

- symbol is on `data/blue_chip_watchlist.txt`
- session is confirmed as supported
- broker supports that session
- bid/ask/last are fresh
- fractional-share support is confirmed if price is above available capital
- risk limits pass

With `$5.00` capital, most blue-chip full shares are not possible. Blue-chip sessions use ET: pre-market 4:00 AM to 9:30 AM, regular 9:30 AM to 4:00 PM Monday through Friday, after-hours 4:00 PM to 8:00 PM, and overnight only when a broker such as Robinhood or Interactive Brokers offers and confirms support. Robinhood fractional/dollar-based stock and ETF trading starts at `$1.00` for eligible securities during regular market hours. Outside regular hours, equity orders must be limit orders on eligible symbols, not fractional/dollar market orders.

## Default Output Rule

If a check fails, output `NO ACTION` with failed checks.

If a setup is interesting but cannot be acted on with `$5.00`, output `WATCHLIST ONLY`.
