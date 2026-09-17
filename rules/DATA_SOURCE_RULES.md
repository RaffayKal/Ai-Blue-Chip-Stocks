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

## Stocktwits Widget Rule

`widgets/stocktwits_cards_widget.html` is a browser display surface for fresh Stocktwits cards and market-pricing context. The live loader fetches the widget manifest with no-store behavior, so the widget may display fresh pricing and sentiment cards in a browser.

The scanner must not treat the widget HTML or script tag alone as verified scanner-ingested data. Rendered widget prices become scanner input only after a separate browser/DOM capture step records symbol, asset class, price, retrieval timestamp, timezone, and source into a machine-readable project artifact.

Mediumweight blue-chip/crypto scanning may use Stocktwits only from a timestamped machine-readable payload under `data/plugin_runtime_snapshot.json` at `sources.Stocktwits.sentiment` and `sources.Stocktwits.symbol_pulse`.

If the Stocktwits payload is missing, untimestamped, stale, contradictory, or unavailable, mark it `STALE_OR_UNUSABLE` or `PLUGIN_UNAVAILABLE`. Sentiment remains non-executable context and never authorizes order preview, order placement, or broker mutation.

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
# Tier-2 Broker Data Resource

Robinhood Legend is classified as a Tier-2 read-only broker-data resource when its existing authenticated Robinhood MCP surface is available. It may provide current quote, account, position, buying-power, and tradability confirmation to the validation layers.

The Legend browser URL is not itself a machine-readable data authority. No password, MFA code, browser cookie, or session token may be placed in project files, RunPod startup commands, logs, or chat. Robinhood remains the execution authority only through the existing authorized MCP execution path, after independent APEX and Codex validation.

If the Robinhood MCP artifact is missing, stale, contradictory, or unavailable, the affected candidate returns `NO ACTION`.
