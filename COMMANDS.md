# COMMANDS.md

Strict command policy for this directory.

## Allowed Python Command

Use:

```bash
python3
```

Never use:

```bash
python
```

## Required Environment Check

Run from the root directory:

```bash
./scripts/verify_environment.sh
```

This also verifies the rule and algorithm manifest:

```bash
./scripts/verify_algorithm_sources.sh
```

Expected result:

```text
OK: running inside AI BLUE CHIP STOCKS
OK: python3 command found
OK: required control files found
```

If `python3` is missing, the system must stop and print:

```text
BLOCKED: python3 is not available.
```

## Required Algorithm Command

Use this form only:

```bash
python3 algorithms/capital_engine.py data/sample_crypto_input.json
```

Do not use `python algorithms/capital_engine.py`.

## Start Today's Agentic Cycle

Use:

```bash
./scripts/start_agentic_cycle.sh
```

This is the first command for the current `$5.00` crypto 24/7 and blue-chip-when-possible mode.

The live autonomous activation bridge is:

```bash
./scripts/run_autonomous_if_viable.sh data/current_candidate_envelope.json
```

That bridge must keep Codex dormant unless the current envelope validates `VIABLE: true` and `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS`. After activation, it must feed the extracted current-envelope `market_input` from `/private/tmp/apex_current_envelope_market_input.json` into the autonomous buy/sell gates, not sample market files.

## Robinhood Route

The active agentic route is:

```text
robinhood-trading
```

Before real-money order placement, activated Codex must use Robinhood review/preview tools and place only the exact preview-matched active autonomous ticket when configured autonomous execution authorization is true. ChatGPT/plugins must not place orders.

Live autonomous mode must first pass the current-envelope bridge:

```bash
./scripts/run_autonomous_if_viable.sh data/current_candidate_envelope.json
```

Direct `algorithms/autonomous_order_gate.py` calls with sample market files are test-only. They are not the live autonomous activation path.

If the bridge does not print `VIABLE: true` and `AUTONOMOUS_BUY_SELL: ENABLED_AFTER_GATE_PASS`, the only valid result is `NO ACTION`.

## Working Directory Rule

Every command must run from:

```text
/Users/raffaykal/AI BLUE CHIP STOCKS
```

If a command runs from a different directory, its result is invalid unless the command is only checking the current path.
