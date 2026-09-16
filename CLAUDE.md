# CLAUDE.md

Mandatory Claude instructions for `/Users/raffaykal/AI BLUE CHIP STOCKS`.

Claude must follow `AGENTS.md` first. This file adds Claude-specific behavior.

## Start Protocol

Before changing or analyzing anything, Claude must read:

1. `AGENTS.md`
2. `COMMANDS.md`
3. `rules/MARKET_SESSION_RULES.md`
4. `rules/CAPITAL_RULES.md`
5. `algorithms/CAPITAL_ALGORITHM.md`
6. `START_TODAY.md`

Claude must not use memories, older folders, prior generated reports, or inferred objectives as authority over these files.

## Execution Protocol

- Build files when asked to build files.
- Fix code when asked to fix code.
- Do not replace execution with a restated objective.
- Use exact filenames and paths.
- Use `python3` only.
- If a rule blocks an action, say the exact blocked reason.

## Trading Safety Protocol

Claude must not issue buy/sell instructions unless the user explicitly requests trading execution support and all configured risk, session, data, and broker checks pass.

When checks do not pass, Claude must output `NO ACTION` and list the failed checks.

## Today's Mode

Claude must treat capital as dynamic and read spendable buying power from the connected broker at runtime. For equities/options, use the selected account’s authoritative buying power. For crypto, use the selected account’s crypto buying power. Never use a hard-coded capital amount or total portfolio value as spendable capital. If live buying-power data is missing, stale, contradictory, or unavailable, return `NO ACTION`.

Crypto is monitored as a Robinhood Crypto 24/7 checked lane. Blue-chip stocks are monitored only when possible under `rules/BLUE_CHIP_RULES.md` and `rules/ROBINHOOD_RULES.md`.
