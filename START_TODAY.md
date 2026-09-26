# START_TODAY.md

Agentic start instructions effective `2026-09-10` in the `America/New_York` timezone.

Root directory:

`/Users/raffaykal/AI BLUE CHIP STOCKS`

## Capital

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

For crypto:
use the selected account’s crypto buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

The system must automatically adapt as deposits, withdrawals, holdings, profits, losses, and buying power change. Capital preservation outranks signal strength.

## Brokerage Account

The user's primary agentic stock-market account is Robinhood.

The user's selected broker account and live buying power must be verified at runtime before treating any setup as actionable.

Read `rules/BROKERAGE_RULES.md` and `rules/ROBINHOOD_RULES.md` before treating any setup as actionable.

## Operating Mode

Current conditional operations policy: use 4:00 AM America/New_York as the
daily operations start/resume and retain a 10-minute monitor. Two consecutive
fresh Robinhood reads must confirm positive spendable crypto buying power before
24/7 scanning is enabled. Until then, run watch/scanner operations only during
actual U.S. trading days from 4:00 AM through 8:00 PM ET, including early,
regular and late sessions; outside that window RunPod, Codex, ChatGPT and Claude
heavy/scanner layers are dormant or paused. Equity buying power, total portfolio
value, unsold holdings, projected profit and promised funding do not unlock
24/7 mode. Asset-specific sessions, actual broker buying power, execution
permissions and all existing trade gates remain unchanged. Read
`RUNPOD_OPERATIONS.md` for the state-transition procedure and proof limits.

Off-market pausing is provider-capability dependent. RunPod currently exposes
`stop`, `restart` and `terminate` for the named pod, not a safe reversible
`pause` with guaranteed autonomous resume. Do not use `stop` merely to save
usage because this pod has ephemeral container storage; leave it untouched when
no safe pause exists and keep the monitor/heavy-agent layers paused.

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

- LOOKING — fresh, viable watch/scanner state; no executable ticket yet.

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
- live broker buying-power checks pass

LOOKING does not authorize a buy or sell. It replaces the ambiguous watch-only
NO ACTION label when scanner and quote gates are healthy but capital or sizing
gates are still pending. NO ACTION remains the fail-closed execution result
for missing, stale, contradictory, or failed required facts.

## Blue-Chip Lane

Blue-chip stocks are only possible when:

- symbol is on `data/blue_chip_watchlist.txt`
- session is confirmed as supported
- broker supports that session
- bid/ask/last are fresh
- fractional-share support is confirmed if price is above authoritative live buying power
- risk limits pass

Blue-chip sessions use ET: pre-market 4:00 AM to 9:30 AM, regular 9:30 AM to 4:00 PM Monday through Friday, after-hours 4:00 PM to 8:00 PM, and overnight only when a broker such as Robinhood or Interactive Brokers offers and confirms support. Robinhood fractional/dollar-based stock and ETF trading starts at the broker minimum for eligible securities during regular market hours. Outside regular hours, equity orders must be limit orders on eligible symbols, not fractional/dollar market orders.

## Default Output Rule

If a check fails, output `NO ACTION` with failed checks.

If a setup is interesting but cannot be acted on because live buying power, broker support, source freshness, or risk facts are incomplete, output `WATCHLIST ONLY` or `NO ACTION` as the local gate requires.
