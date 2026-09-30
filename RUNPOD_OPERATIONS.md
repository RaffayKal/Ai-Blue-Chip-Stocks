# RunPod operations and recovery

Verified September 25, 2026. This document is a runbook, not a live health claim.

## Exact resource

- Pod: `t3yz4nrfl1utcr` / `apex-vllm-cpu-006`.
- Allocation: 2 vCPUs, 4 GB RAM, 20 GB container disk; reported compute rate $0.06/hour.
- SSH: configuration in `runpod_vllm_cpu_006.json`, using the registered
  `/Users/raffaykal/runpod_codex_bridge` identity. The proxy requires a PTY.
- Alternate SSH entry supplied by the user (documented only; not replacing the
  configured bridge identity):

  ```bash
  ssh t3yz4nrfl1utcr-644117fc@ssh.runpod.io -i ~/.ssh/id_ed25519
  ```

  Supplied host-key fingerprints: `SHA256:kB4aNBPZ8du9MjaNjk3ohjR1aqdJZpaKnnHrj9sc5dA` and
  `SHA256:8Y/A8lnJ8REcpqJcTsTnZKnSrYyOl8VrEo0yQbFVa4c`. Verify the expected
  fingerprint before trusting a new host; no private key material is stored here.
- Remote scanner directory: `/workspace/apex`.
- Model endpoint: `https://t3yz4nrfl1utcr-8000.proxy.runpod.net`.
- Model: `facebook/opt-125m`; this small test model is not proof of trading intelligence.

## Verified container start arguments

Image: `vllm/vllm-openai-cpu:latest-x86_64` (observed vLLM 0.30.0).
The entrypoint supplies `vllm serve`; do not add another `serve` to model arguments.

### Native web terminal repair — September 30, 2026

The live console displayed this same pod as `apex-vllm-cpu-002` during repair.
Previously vLLM was PID 1 and did not reap exited `gotty` terminal children.
Disabling the native terminal left a zombie and the console incorrectly reported
Running. The user authorized an entrypoint-only repair and restart.

The current entrypoint runs `/opt/venv/bin/python -c` with the source from
`scripts/runpod_container_init.py`, followed by `/opt/venv/bin/vllm serve`.
The wrapper blocks in `waitpid`, reaps adopted children, and forwards shutdown
signals to the model process group. Preserve this entrypoint on future updates.
The model arguments, image, resource allocation, ports and secrets were not changed.

Verified in external Chrome: native On → shell command → Off → On → shell
command → Off. Both shell commands returned their test markers; both Off actions
reached Stopped, and remote process checks showed no zombie or `gotty` processes.
Authenticated model inference returned HTTP 200 after the repair.
Terminal was left OFF. Scanner/execution operations and watchdogs remain paused
under the user's stop instruction; this test did not resume them.

```text
facebook/opt-125m --host 0.0.0.0 --port 8000 --dtype bfloat16 --max-model-len 512 --max-num-seqs 7 --enforce-eager --kv-cache-memory-bytes 134217728
```

Expose `8000/http`. Keep the existing `VLLM_API_KEY` secret; local verification
loads it from the macOS Keychain service `AI BLUE CHIP STOCKS RunPod VLLM API Key`,
not from a committed or plaintext project file, and
`VLLM_CPU_NUM_OF_RESERVED_CPU=1`. Do not print keys or the complete pod environment.
Do not set `VLLM_CPU_KVCACHE_SPACE`: that integer-only legacy variable overrides
the byte-based cache configuration. The successful inference health check also
verifies unauthenticated model requests receive HTTP 401.

## Checks and recovery

From the project root, agents can run:

```bash
python3 scripts/runpod_ops.py status
python3 scripts/check_vllm_service.py
```

The user authorized restoring this named resource at the existing allocation.
If API status is EXITED and there is no newer user stop instruction, inspect
logs and start that same pod through RunPod. Never terminate/recreate it merely
to reconnect. When scanner files are missing, restore them:

```bash
python3 scripts/runpod_ops.py restore
```

Restore transfers code, rules, watchlists and startup fixtures, not `.env.local`,
SSH private keys, or live broker snapshots. The supervisor's exclusive lock
prevents duplicate scanner trees. It restarts failed scanner processes and
survives SSH disconnection. Verify fresh fleet output after restoration; a
RUNNING API response or supervisor PID alone is insufficient.

## Storage and availability limits

RunPod reported no persistent mount and no network volumes. At 08:00 UTC the
pod was EXITED; system logs recorded stop/remove at 03:00:50/03:00:52 UTC without
identifying the cause. After starting it, `/workspace/apex` was absent. This is
direct evidence that container storage did not survive that lifecycle event.
RAM is working memory, not durable storage. Do not fill disk or create CPU
busy-loops to manufacture utilization.

The code-only restore provides recovery, not uninterrupted uptime. Persistent
storage or a custom bootstrap image remains necessary for cloud-only recovery
independent of the Codex host. Do not add billable storage or change the image
without resolving the user's $0.06/hour spending constraint.

## Broker-data and reinforcement boundaries

- Robinhood MCP was live-verified twice at the 4 AM check. Positions and open
  orders were unchanged; equity and crypto buying power were zero. Held assets
  remain a possible SELL funding path, not spendable cash.
- Preserve broker routing and original timestamps when ingesting quotes.
  Never infer liquidity, eligibility, risk or quorum from a quote alone.
- `runpod_ops.py sync-quotes` now transfers only routed Robinhood market-quote
  snapshots, preserving the broker timestamps. Buying power, portfolio value,
  positions, orders, and other private account data remain on the authenticated
  host MCP and are never copied to RunPod by this path. Do not relabel stale
  snapshots as fresh or expand freshness windows.
- A Codex-hosted MCP connection is not a persistent Robinhood connection inside
  the pod. Report actual snapshot ingestion separately from connection status.
- OpenAI reinforcement returned HTTP 429 `credit_balance_exhausted`. The local
  and pod workers use clearly labeled deterministic fallback. Funding RunPod
  does not replenish OpenAI credits.
- No new orders were submitted during this infrastructure repair. Preserve
  all existing broker and execution safeguards and verify fills at the broker.

## Monitoring

Current policy: keep the authorized scanner infrastructure and 3-minute
watchdog active 24/7, without a buying-power prerequisite. Refresh and verify
data continuously within the documented freshness limits between watchdog
wakes. Crypto may be evaluated at any hour; stocks may be scanned at any hour,
but execution remains limited to the actual broker-supported session and
instrument. Missing buying power blocks buys, not scanning or a sell backed by
fresh broker-confirmed sellable quantity and eligibility. Holdings and
unconfirmed proceeds are not spendable cash. All other execution gates remain.

- `robinhood-frontline-24-7-monitor`: checks health and recovery at 4:00 AM and
  8:00 PM America/New_York; these are not start/stop boundaries.
- `blue-chip-operations-heartbeat`: active every 3 minutes, every day, as a
  watchdog for continuous data and scanner operation. It never declares a
  trade viable merely because infrastructure is running.
- Off-market scanners remain active. Stock order eligibility still follows
  broker-supported sessions. Existing execution permissions and safeguards
  are unchanged.

### Off-market pause limitation

The live RunPod action set for `t3yz4nrfl1utcr` is `stop`, `restart` and
`terminate`; it does not expose a safe reversible `pause` with guaranteed
autonomous resume. The current 24/7 scanning policy does not pause the monitor
or authorized scanner layers after hours merely because funding is absent. Do
not call `stop` merely to save usage: stopping this pod can clear its ephemeral
container state. Any later pause policy must verify a safe recovery path.

### Continuous freshness and 3-minute watchdog

The 3-minute automation first refreshes public Robinhood routed quotes when
the connected broker source is available, then audits and repairs the scanner
and feed chain. A failed private portfolio read must not suppress public quote
refresh; it still blocks execution requiring broker capital or inventory.
This schedule is not a millisecond market-data stream. During continuous
operation, scanner/feed workers must advance
their own timestamps continuously within the configured freshness bounds. The
watchdog checks timestamp continuity, restart/error state, supervisor and lane
count agreement, and source freshness; it does not accept a single fresh file
as proof that the chain stayed live between wakes.

`threaded_scanner_lane_pool.py` refreshes `fleet_lane_manifest.json` from its
running aggregation loop (at least once per minute). A stale or lane-count
mismatched manifest is therefore a scanner defect: deploy the current code,
restart only the affected scanner process through the supervisor with
`python3 scripts/runpod_ops.py repair-scanner`, and verify that the timestamp
advances on subsequent checks. That action targets only the existing lane-pool
worker; it does not stop the pod, touch vLLM, or submit orders. Never rewrite a
timestamp manually to conceal a dead worker. Robinhood MCP remains host-side authority;
continuous Robinhood-to-RunPod quote delivery requires an explicitly
configured authorized relay. Without that relay, stale or missing broker data
is non-authoritative and must remain fail-closed.

The relay poller and local relay now agree on `/v1/robinhood/crypto-quote` and
the factual Robinhood snapshot format. The poller rejects stale timestamps and
copies only public quote fields. This protocol repair does not create the
missing persistent OAuth-backed producer, relay token, or network route; a
one-shot quote sync is not a continuous feed.

If `pod_scanner_supervisor_status.json` stops advancing, check the pod process
list and cgroup `memory.events` before recovery. On the existing pod only,
`python3 scripts/runpod_ops.py start-scanner` idempotently starts a missing
supervisor; it does not restart vLLM or the pod. Recheck the supervisor,
primary scanner status, manifest and fleet summary on more than one sample.
If only scanner code needs updating, `deploy-scanner-code` transfers the named
scanner source files without account records, then `repair-scanner` reloads
the lane-pool worker. The broad `restore` path excludes brokerage intake and
user settings; do not use it merely for a source-code label change.

The local `apex_prestige_supervisor.py` uses the separate `supervisor_health`
scanner lane, leaving the fleet's primary lane as the owner of the global
scanner status and candidate envelope. After each successful health pass it
runs `apex_packet_monitor.py --once` against that primary envelope. This is the qualified packet-emission
check feeding the local Codex inbox. A live consumer with an empty inbox does
not prove a trading handoff. `SCANNING FOR VIABILITY` is discovery state, not
an executable order; the packet monitor and broker still revalidate any
candidate before execution.

For local drift, compare the live worker's command and interpreter with its
manifest before recovery. The local launchd fleet and the remote RunPod fleet
are separate; a historical 700-lane manifest does not prove 700 live workers.
`start_lightweight_scanner_fleet.sh` honors `PYTHON3_BIN` and selects the
installed Python 3.13 on this Mac before falling back to `python3` on PATH.
After a verified local code/runtime mismatch, reload only the affected
`com.raffaykal.apex-prestige-runpod-scanner` or
`com.raffaykal.apex-packet-monitor` launchd service, then verify advancing
primary, `supervisor_health`, and manifest timestamps. Never refresh a
manifest by hand to disguise an old worker. A supervisor health scan must
not write the primary envelope or status.

The live packet consumer now uses the host's existing Codex OAuth profile for
Robinhood MCP, rather than an isolated home that omitted MCP credentials.
Packet-derived market input carries the scanner's original market and risk
facts; the consumer binds execution permission to both local authorization
records instead of overwriting it to false. Buy-side sizing uses a fresh,
account-matched Robinhood `get_portfolio` result supplied at runtime, not the
old intake-file buying-power value. Sell-side sizing uses refreshed broker
sellable quantity. A running consumer, successful OAuth probe, or scanner
viability still does not establish an executable ticket, submitted order, or
fill; inspect the exact packet, gate, preview, broker order, and reconciliation.

`python3 scripts/runpod_ops.py sync-quotes` sends public routed quote
snapshots only. Before upload it promotes the newest factual per-symbol
Robinhood snapshot into the aggregate snapshot consumed by the required-source
gate, so an older aggregate file cannot mask a fresh Robinhood feed. It never
promotes account, portfolio, position, buying-power or order data.

These automations monitor, refresh local broker evidence, and perform authorized
same-pod recovery; they do not submit orders. Routine unchanged results stay
quiet. Host availability still affects Codex heartbeat execution; do not
describe this as a cloud scheduler or proof of continuous broker ingestion.

### Latest recovery checkpoint: September 25, approximately 18:42 UTC

The pod was EXITED. Its saved arguments incorrectly included a second
`vllm serve` command. The arguments-only command above was saved through the
RunPod API, preserving the user's seven-sequence setting, existing environment,
allocation and $0.06/hour configuration. Container logs timed out, so the
original exit cause was not established. The subsequent start request failed:
`There are not enough free vcpu on the host machine to start this pod.`
Do not call the pod, model or scanner fleet operational from this checkpoint.
Retry same-pod recovery when capacity is available; do not increase price,
provision a replacement or upload private broker snapshots without approval.
Two consecutive Robinhood portfolio reads returned zero equity and crypto
buying power. This is an observation, not a restriction on scanner operation.

## Earlier verification results (not current uptime proof)

- SSH reconnect and code-only restore were exercised against the named pod.
- Model health HTTP 200, unauthenticated model access HTTP 401, authenticated
  model access HTTP 200, and a real completion HTTP 200 were verified after recovery.
- Fresh remote scanner and fleet artifacts confirmed 70 lanes and 210 aggregate
  fleet samples. Execution permission remained true; the candidate was NO ACTION.
- The 14 reinforcement tests and 3 reconnect/deployment tests passed.
- The full suite ran 172 tests: 171 passed; the existing 700-lane single-cycle
  test exceeded its 60-second timeout. Do not claim a fully passing suite or
  verified 700-lane operation from the successful 70-lane deployment.
