# BLUE_CHIP_RULES.md

Rules for blue-chip stock handling.

## Definition

For this project, a blue-chip stock is not assumed from popularity. It must be explicitly listed in:

`data/blue_chip_watchlist.txt`

Agents may propose additions, but must not silently treat an unlisted symbol as approved.


## Blue-Chip Trading Hours

Blue-chip stock trading windows use Eastern Time:

- `PRE_MARKET`: generally 4:00 AM to 9:30 AM ET. Peak volume and liquidity usually concentrate closer to 8:00 AM ET.
- `REGULAR`: 9:30 AM to 4:00 PM ET, Monday through Friday.
- `AFTER_HOURS`: 4:00 PM to 8:00 PM ET, including late-day earnings and announcement reaction windows.
- `OVERNIGHT`: select-brokerage session covering remaining overnight gaps when offered by the broker, including Robinhood or Interactive Brokers where supported.

These hours define the session label only. Execution still requires live confirmation of broker support, symbol tradability, order type, bid, ask, spread, volume, liquidity, timestamp, source freshness, buying power, and risk limits.


## High-Risk / High-Reward Blue-Chip Mode

Blue chips are the main investment assets for this project. When a verified blue-chip position has high-conviction upside, Apex may let exposure continue compounding instead of harvesting early.

Maximum compounding capital exposure is 30% of max capital. The system must block any high-risk/high-reward blue-chip exposure above that cap.

A retained position with growth at or above 10% must be re-evaluated. If upside remains clear and viable, let it run within the 30% cap. If upside deteriorates, harvest the grown percentage only when the sale is expected to produce positive net profit after execution friction.

## Session Gate

Blue-chip stock checks are allowed only when the equity session is known:

- `REGULAR`: allowed if all data and risk checks pass.
- `PRE_MARKET`: watch or action only if broker support is confirmed.
- `AFTER_HOURS`: watch or action only if broker support is confirmed.
- `OVERNIGHT`: watch or action only if broker support is confirmed.
- `CLOSED`, `HOLIDAY`, `HALTED`, `UNKNOWN`: `NO ACTION`.

## Dynamic Capital Rule

Capital is dynamic and must be read from the connected broker at runtime.

For equities/options:
use the selected account’s authoritative buying power.

Never use a hard-coded capital amount or total portfolio value as spendable capital.

If live buying-power data is missing, stale, contradictory, or unavailable:
`NO ACTION`.

Full-share blue-chip positions are blocked when the ask price is above authoritative live buying power.

Fractional-share action is blocked unless all are confirmed:

- broker supports fractional shares
- asset is fractional eligible
- minimum order value is less than or equal to authoritative live buying power
- fees do not make the order irrational
- spread and liquidity checks pass

If fractional support is not confirmed, output `WATCHLIST ONLY`.

## Robinhood Rule

For Robinhood, fractional/dollar-based trading for eligible U.S. stocks and ETFs starts at `$1.00`. Fractional/dollar equity orders are regular-market-hours only through the agentic route. Outside regular hours, equity orders must be limit orders for eligible symbols, and fractional/dollar market orders must return `WATCHLIST ONLY` or `NO ACTION`.

## No 100% Single-Stock Allocation

Blue-chip assets are the main investment assets, but no single stock may receive 100% of available capital. All-in single-stock exposure is blocked.

When stock execution is allowed by a separate equity gate, the system must prefer a spread basket across verified eligible blue-chip assets. The basket must respect the Apex hierarchy, confirmed tradability, session status, buying power, fractional eligibility, liquidity, spread, and per-symbol exposure caps.

If available capital is too small to build a spread basket under broker minimums, the system must return `WATCHLIST ONLY` or `NO ACTION` unless a separate explicit reviewed-order approval authorizes one small fractional candidate within the per-symbol cap.
