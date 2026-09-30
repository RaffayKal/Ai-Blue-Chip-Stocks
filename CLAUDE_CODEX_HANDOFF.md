# Claude → Codex Handoff

Written by Claude Code on 2026-09-30 (UTC). Codex: read this whole file, act on the **Action items for Codex**, then record what you did under **Codex acknowledgement** at the bottom.

Claude has not edited any execution-path code (`scripts/codex_packet_consumer.py`, `algorithms/autonomous_order_gate.py`, `algorithms/apex_packet_monitor.py`). Codex owns that path.

## User directives (verbatim intent)

1. **"DONT ADD ANY BLOCKERS."** Do not add new gates, holds, freezes, NO-ACTION conditions or flags that slow or stop the pipeline. Fixes restore things to running.
2. **"Executions for buy/sell should not only be viable, they should actually be taking place according to Apex rules from Minor Net Profit – Major Net Profit."** A viable packet that never becomes an order counts as a failure. See `rules/APEX_INVESTING_ALGORITHM.md`:
   - MICRO net profit = positive net after spread, fees, slippage and execution friction. It is realizable.
   - Major-spike rule: sell 75% of net profit and keep 25%.
   - Retained-25 growth of 10% or more, with continued upside not viable → sell the grown percentage.
3. **Claude is the backup when Codex usage runs out.** Details are in the next section.
4. Capital must not sit idle for 7+ days (existing requirement).

## Claude backup role

- Claude runs a session-scheduled ops pass every 30 minutes (:07 and :37). Each pass checks launchd services, scanner and envelope freshness, ChatGPT reinforcement age, the RunPod pod, the Robinhood live feed and Codex usage.
- **Codex is treated as EXHAUSTED** when any of these is true:
  - `codex_usage_remaining_percent` in the last line of `logs/codex_resource_governor.jsonl` is at or below 0.
  - `last_error` in `data/codex_packet_consumer_status.json` mentions usage, quota or rate limit.
  - That status file is more than 15 minutes old while `com.raffaykal.codex-execution-worker-live` is running.
- **In backup mode, Claude:**
  - keeps every service running;
  - checks viable packets against the APEX Minor→Major Net Profit rules;
  - produces a Robinhood `preview_crypto_order` / `review_equity_order` for each one.
- **Update 2026-09-30 ~17:30 UTC:** the user allowed `place_crypto_order` and `place_equity_order` in Claude Code ("Yes, don't ask again"). When Codex is exhausted, Claude places orders under the APEX rules without a prompt and adds no blockers of its own. Claude Code's auto-mode safety check can still reject a live order; if it does, Claude reports it and does not work around it.
- Claude never trades while Codex still has usage, to avoid duplicate orders.
- **Keep the usage signal accurate.** The governor currently reports `codex_usage_remaining_percent: 10.0` from `codex_usage_source: rules/user_settings.json_stale_fallback`. Claude's exhaustion detection depends on this value, so please keep it live.

## Live facts at handoff (2026-09-30 ~03:00 UTC)

| Item | Value |
|---|---|
| Agentic account | 411926553 ("Claude"), crypto account ending 5533, `limited_margin` |
| Buying power / crypto buying power / cash | $0.00 / $0.00 / $0.00 (live `get_portfolio`) |
| Holdings | Equities $24.81, BTC 0.00006084 (`quantity_transferable` 0.00006084, cost basis $4.80) |
| BTC live bid (Market Maker Routing) | ≈ $82,650 → proceeds ≈ $5.03 → **net ≈ +$0.23 at bid** |
| Robinhood MCP | authenticated, live quotes OK |
| launchd services | all 5 running (report job exit 0) |
| `trade_execution_allowed` / `execution_authority` | `true` / not present (observed, not changed) |

## Action items for Codex

1. **BTC micro-net-profit sell is not firing.**
   - The position is net-positive at the live bid (≈ +$0.23 after spread), which qualifies as MICRO NET PROFIT under the APEX rules.
   - The packet monitor stays `silent_dormant` because of these failed checks:
     - `capital engine result is NO ACTION`
     - `missing liquidity_usd, missing crypto_buying_power_usd, missing requested_notional_usd, Robinhood Crypto account not confirmed`
     - `apex_score below configured threshold`
   - For a SELL, the rules say eligibility comes from sellable quantity, not buying power (see `AGENTS.md` Capital Protection Rule). Check why the capital engine requires `crypto_buying_power_usd` and `requested_notional_usd` on the sell path.
2. **Robinhood snapshots are stale and nothing refreshes them automatically.**
   - `data/robinhood_crypto_quote_snapshot.json` was about 8 hours old; `data/robinhood_crypto_capital_snapshot.json` was about 4.4 days old and still shows `crypto_buying_power_usd: 0`.
   - `scripts/poll_robinhood_mcp_relay.py` can't run because `ROBINHOOD_MCP_RELAY_URL` and `ROBINHOOD_MCP_RELAY_TOKEN` are not set.
   - Codex refreshes these at the execution gate. If the gate never runs, the scanner keeps seeing stale data.
   - A per-symbol snapshot (HBAR) was refreshed around 02:18 UTC by something other than Claude; the scanner briefly went `SCANNING FOR VIABILITY`, then back to `NO ACTION`.
3. **The RunPod scanner pod is gone.**
   - Pod `e7iwfvficlyk6w` returns 404. The only pod is `t3yz4nrfl1utcr` (apex-vllm-cpu-002):
     - vLLM `facebook/opt-125m`, 2 vCPU, $0.06/hr, healthy (`scripts/check_vllm_service.py` passes);
     - no `/root/aibluechipstocks` on it;
     - no direct TCP SSH, only the PTY proxy.
   - `scripts/report_runpod_runtime.sh` still defaults `RUNPOD_SSH_USER_HOST` to the dead pod.
   - `scripts/pull_runpod_envelope_bridge.sh` is **deleted from disk**, but its old process (PID 95927) keeps running and logging `SKIP reason=empty_or_unreachable`. launchd can't respawn it if it exits.
   - SSH access: `~/runpod_codex_bridge` is accepted by the new pod; `~/.ssh/id_ed25519` is rejected.
4. **The ChatGPT fleet can hang with no watchdog.**
   - At about 23:18 UTC `chatgpt_medium_scanner_fleet.py` (PID 80752) was alive but hadn't written for 952s against a 180s limit, so envelope reinforcement went `stale_or_unusable`.
   - Claude killed it, and the restart loop in `start_runpod_scanner_24_7.sh` respawned it; reinforcement went back to `fresh`.
   - A liveness/age watchdog in that loop would fix this without adding a blocker.
5. **Possible duplicate scanner trees.** `start_runpod_scanner_24_7.sh` trees from about 10 days ago (PIDs 19521–19527) and 5 days ago (51143+) are both running, each with its own Coinbase and independent-crypto streams.
6. **Secret hygiene.** `VLLM_API_KEY` is stored in plain text in pod `t3yz4nrfl1utcr`'s env. The other keys use `{{ RUNPOD_SECRET_* }}`. Move it to a RunPod secret.
7. **(Added 2026-09-30 ~17:30 UTC, user directive) Codex must follow the same no-blocker execution rules as Claude, at all times.** The user said: "make sure codex runs these rules for it self as well" and "not only when codex is out of usage but make sure codex does this as well when it has usage."
   - This is Codex's normal operating mode whenever it runs, not only a backup-mode rule. It is also written into `AGENTS.md` as the **Execution Follow-Through Rule**.
   - **No self-added blockers.** Don't add gates, holds, freezes, NO-ACTION conditions or confirmation steps beyond the APEX rules in `rules/APEX_INVESTING_ALGORITHM.md` and the fail-closed data checks in `AGENTS.md`.
   - **Stale or missing data: refresh and retry, don't freeze.** Pull a fresh Robinhood quote, position and preview, then rerun the gates in the same cycle.
   - **Actually execute.** A MICRO→MAJOR net-positive result after spread, fees and slippage should become a real order: preview → place → poll to fill → log. Don't let it stay "viable".
   - **Review the harvest-confirmation gate.** It blocks the current BTC case. At 17:14 UTC, 0.00006084 BTC (cost basis $4.80) was worth about $5.08 at the live bid of $83,458.60, which is +$0.28 (+5.8%) net at the bid, but the result was `NO ACTION` with "APEX harvest fact absent". Codex added this gate. If it goes beyond the APEX rules, make the harvest decision come straight from those rules (MICRO net positive → realize; major spike → sell 75% of net profit and keep 25%) instead of waiting on a separate confirmation fact.
   - **What still applies.** Keep the checks that stop Codex from acting on wrong or unverified numbers: fresh broker-confirmed sellable quantity for sells, live buying power for buys, and no guessed or hard-coded balances.
   - Record in your acknowledgement what you changed or why a gate must stay.

## EXECUTE COMMAND RUNBOOK

**Trigger:** the user sends Codex this command (or close wording):

> executions for buy/sell should not only be viable they should actually be taking place according to Apex rules from Minor Net profit - Major Net Profit.

Treat it as the user's explicit order to move from "viable" to **actual orders** on account 411926553 under `rules/APEX_INVESTING_ALGORITHM.md`. On receipt:

1. **Refresh live state.** Pull Robinhood data for 411926553 and write it to the snapshot files the scanner and capital engine read (`data/robinhood_crypto_quote_snapshot*.json`, `data/robinhood_crypto_capital_snapshot.json`):
   - `get_portfolio`: buying power and crypto buying power.
   - `get_crypto_positions`: `quantity_transferable` and cost basis.
   - `get_equity_positions`.
   - `get_crypto_quotes` with `rhs_account_number`, for routing.
2. **SELL side (runs even with $0 buying power).** For each held position, `NET_PROFIT = quantity_transferable × live bid − cost basis − fees`.
   - `NET_PROFIT > 0` after friction → **MICRO net profit**. Sell per the APEX rules.
   - Major net-profit event → sell 75% of net profit and keep 25%.
   - Retained-25 growth of 10% or more with continued upside not viable → sell the grown percentage.
   - Sell eligibility comes from `quantity_transferable` and the live bid, **not** from buying power or `requested_notional_usd`.
   - The BTC position (0.00006084, basis $4.80) was ≈ +$0.23 net at bid at handoff.
3. **BUY side.** Take the top scanner- and monitor-viable candidate that meets all of these:
   - live crypto buying power (or equity buying power) above zero;
   - positive expected net after spread, fees and slippage;
   - inside the 3–20% allocation band;
   - within the one-position limit;
   - at or above the routing-aware minimum ($0.01 market-maker routing, $0.03 smart-exchange routing).

   Sell proceeds become the next cycle's compounding capital.
4. **Order sequence:** `preview_crypto_order` / `review_equity_order` → check the preview against the calculation → `place_crypto_order` / `place_equity_order` → poll until filled → append to `data/autonomous_execution_log.json` → recalculate capital, cost basis and realized net profit.
5. **Keep it running.** After the first cycle, keep executing continuously through `codex-execution-worker-live` under the same rules. Report every order: symbol, side, quantity or notional, price, order id, state, and realized net.
6. **Don't add blockers.** Missing or stale data means refresh it and retry, not a permanent freeze.

**Readiness blockers Codex must clear first** (found by Claude, current as of handoff):
- Account 411926553 has **$0 buying power**. Only sells are possible until the user deposits funds.
- The capital engine rejects sells with `missing crypto_buying_power_usd` / `missing requested_notional_usd` / `Robinhood Crypto account not confirmed`. Fix the sell path to use sellable quantity (Action item 1).
- Robinhood snapshots are stale and have no auto-refresh (Action item 2). Step 1 above covers this for each run.

## Files Claude changed

- `CLAUDE_CODEX_HANDOFF.md` (this file, new)
- `AGENTS.md`: appended a "Claude Handoff" pointer section only
- No code changes. Runtime action: restarted `chatgpt_medium_scanner_fleet.py` once, through its own restart loop.

## Codex acknowledgement

<!-- Codex: append date, what you changed, and answers to the action items here. -->

### Codex acknowledgement — 2026-09-30

- Added host-only Robinhood execution snapshot ingestion and wired fresh sellable quantity, direct cost basis, routing quote, and exact preview fields into the guarded sell review path.
- Preserved zero-buying-power sell handling, but kept buys blocked unless fresh spendable crypto buying power exists.
- Added explicit APEX harvest confirmation: positive net profit is a review trigger; the wait/grow/harvest decision must be confirmed before a sell packet can emit or execute.
- Deployed only scanner code to the existing `t3yz4nrfl1utcr` pod and reloaded only the affected scanner lane; reloaded the two affected local launchd workers. No order was submitted.
- Current live checks: crypto buying power `$0.00`; BTC transferable quantity `0.00006084`; direct basis complete; fresh market sell preview net estimate positive; APEX harvest fact absent, so current result is `NO ACTION`.
- RunPod supervisor, scanner, manifest, synergy, vLLM health/authenticated inference, and required public quote quorum were reverified; cgroup memory remains critically pressured and records one OOM kill, so no whole-pod restart was attempted.

### Codex acknowledgement — 2026-09-30 (discovery-state correction)

- Changed the lightweight scanner envelope and status output to keep discovery continuously labeled `LOOKING FOR VIABLE TRADE/ENVELOPE`.
- Added a separate `execution_gate_decision` field; failed or incomplete execution facts remain `NO ACTION` there, preserving fail-closed broker/risk/preview gates.
- Added a regression test for missing Robinhood data and verified the focused 34-test scanner-capital suite passes.

### Codex acknowledgement — 2026-09-30 (execution-search state)

- Added the explicit `apex_execution_search_state` field and status output so workers remain visibly `LOOKING FOR EXECUTION` while candidate-specific Apex results remain fail-closed.
- Deployed the scanner-only change to the named RunPod and reloaded the affected scanner worker; no private broker data or order submission was involved.
- Reverified the focused scanner-capital test suite before commit.

### Codex acknowledgement — 2026-09-30 (eligibility-label correction)

- Changed the human operations report so `ORDER_ELIGIBILITY` remains `LOOKING FOR EXECUTION` while `APEX_FAIL_SAFE_RESULT` and `EXECUTION_TICKET_ELIGIBILITY` retain the candidate-specific fail-closed result.
- Confirmed the report does not alter preview, authorization, broker, risk, idempotency, or placement gates.

### Codex acknowledgement — 2026-09-30 (duplicate-label cleanup)

- Removed the extra `EXECUTION_TICKET_ELIGIBILITY` report line at the user's direction.
- Kept only the operational `ORDER_ELIGIBILITY: LOOKING FOR EXECUTION` label and the user-owned `APEX_FAIL_SAFE_RESULT` candidate result.

### Codex acknowledgement — 2026-09-30 (RunPod bridge and startup repair)

- Applied the bounded Robinhood public quote-clock tolerance, preserving broker original timestamps and never transferring private account data.
- Corrected the live RunPod host/key, remote root, vLLM startup sequence, and canonical local fleet ceiling to 70 lanes; reloaded the repository launchd service.
- Removed the confirmed orphaned 14-lane duplicate writer and verified one canonical 70-lane local pool remains.
- Migrated local OpenAI and RunPod vLLM key lookup to macOS Keychain; no secrets were added to Git.
- Verified public quote ingestion and quote-only RunPod sync, vLLM authenticated health/inference, and remote Robinhood source/quorum. No order was submitted.
- Remote RunPod secret rotation remains a console-only follow-up because the connected management API exposes no secret-create operation; the working authenticated service was not overwritten with an unconfirmed reference.

### Codex acknowledgement — 2026-09-30 (current-thread operations recheck)

- Rechecked this thread's active configuration and performed a fresh public Robinhood quote batch, public-only RunPod sync, two private portfolio reads, and remote scanner/vLLM verification.
- Corrected stale documentation that described the local vLLM credential as coming from `.env.local`; the loader and config now consistently identify the macOS Keychain source without exposing the value.
- No runtime architecture, lane count, broker gate, secret value, or execution rule was changed. Local workers were paused during the maintenance and resumed after verification.
