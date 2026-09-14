# DATA_SOURCE_RULES.md

Rules for plugin and data-source handling.

## Mandatory Multi-Plugin Orchestration Order

When multi-plugin agentic orchestration is requested or available, use this order:

1. Superpowers
2. Longbridge
3. Notion
4. Carta CRM
5. TradingCursor
6. Precise Special Functions
7. Stocktwits
8. Finances
9. Apex Synthesis
10. Ace Knowledge Graph
11. Sleep / Return to Watcher

Ace Knowledge Graph is always last for final synthesis mapping. Missing plugin outputs must be marked `PLUGIN_UNAVAILABLE` or `NO_APPLICABLE_ACTION`; never fabricate a plugin result. If a missing result is required for a trade-critical fact, return `NO ACTION`.

## Source Roles

- Superpowers: operational control and workflow validation
- Longbridge: primary securities-data and market-intelligence input
- Notion: operational memory, documentation, logs, plans, and run records
- Carta CRM: structured relationship and entity context when applicable
- TradingCursor: technical confirmation and market context input
- Precise Special Functions: special-function mathematical verification only when applicable
- Stocktwits: sentiment and crowd discussion input
- Finances: personal capital and portfolio-state input where connected
- Ace Knowledge Graph: final synthesis map and relationship structure

No single plugin is final authority.

`rules/plugin_runtime_stack.json` is the runtime plugin map for the APEX Prestige Runpod-first controller. It records which plugins are always-on eligible, burst-only, callable in the current session, and explicitly non-authoritative for trade execution.

## Timestamp Requirement

Every plugin result must include:

- source name
- retrieval time
- market timestamp when available
- timezone
- symbol or asset identifier

If a result has no timestamp, mark it `STALE_OR_UNUSABLE`.

## Conflict Rule

When sources conflict:

1. Prefer the broker/API execution source for executable quote fields.
2. Prefer the official exchange/session calendar for open/closed status.
3. Treat sentiment as non-executable context.
4. If conflict remains, output `NO ACTION`.
