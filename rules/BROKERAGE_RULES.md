# BROKERAGE_RULES.md

The user's primary agentic stock-market account is Robinhood.

This confirms account existence only. It does not confirm broker capabilities, live data, order routing, fractional shares, crypto access, after-hours access, API access, or execution permission.

## Required Broker Facts

Before any action can move beyond watch mode, agents must confirm:

- broker name
- account type
- supported asset classes
- crypto trading support
- U.S. stock regular-hours support
- U.S. stock pre-market support
- U.S. stock after-hours support
- U.S. stock overnight support
- fractional-share support
- minimum order size
- supported order types
- whether API or plugin execution is connected
- whether live quotes are available
- whether user has explicitly authorized the specific action
- whether the Robinhood account is `agentic_allowed=true`
- whether the Robinhood Crypto account is available and unrestricted when crypto is involved
- whether margin is approved and portfolio value meets Robinhood margin requirements when margin is involved

## Status Before Confirmation

Until the required facts are known:

- crypto may run as checked watch mode only
- blue chips may run as watchlist mode only
- no execution instruction is valid
- no agent may assume fractional shares are supported
- no agent may assume crypto is supported by the broker
- no agent may assume after-hours stock trading is supported
- no agent may assume margin is available

## Robinhood Routing

Read `rules/ROBINHOOD_RULES.md` after this file.

## Broker Intake Prompt

The broker name is Robinhood.

Then ask only for missing facts that cannot be verified from the broker/plugin/API.
