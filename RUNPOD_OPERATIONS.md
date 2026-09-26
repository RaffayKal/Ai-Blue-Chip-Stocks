# RunPod operations and recovery

Verified September 25, 2026. This document is a runbook, not a live health claim.

## Exact resource

- Pod: `t3yz4nrfl1utcr` / `apex-vllm-cpu-006`.
- Allocation: 2 vCPUs, 4 GB RAM, 20 GB container disk; reported compute rate $0.06/hour.
- SSH: configuration in `runpod_vllm_cpu_006.json`, using the existing registered
  `/Users/raffaykal/.runpod/ssh/runpodctl-ssh-key`. The proxy requires a PTY.
- Remote scanner directory: `/workspace/apex`.
- Model endpoint: `https://t3yz4nrfl1utcr-8000.proxy.runpod.net`.
- Model: `facebook/opt-125m`; this small test model is not proof of trading intelligence.

## Verified container start arguments

Image: `vllm/vllm-openai-cpu:latest-x86_64` (observed vLLM 0.30.0).
Its entrypoint already supplies `vllm serve`; do not add another `serve`.

```text
facebook/opt-125m --host 0.0.0.0 --port 8000 --dtype bfloat16 --max-model-len 512 --max-num-seqs 7 --enforce-eager --kv-cache-memory-bytes 134217728
```

Expose `8000/http`. Keep the existing `VLLM_API_KEY` secret and
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

Current conditional policy: 4:00 AM America/New_York starts or resumes the
daily operations window. Two consecutive fresh Robinhood reads confirming
positive spendable crypto buying power unlock 24/7 scanning. Until that happens,
operations run only on actual U.S. trading days from 4:00 AM through 8:00 PM ET,
including early, regular and late sessions. At the off-market close, the pod,
ChatGPT scanner layers and Codex/Claude heavy-agent layers are dormant or
paused. Equity buying power, total portfolio value, unsold holdings, projected
profit and promised funding do not unlock 24/7 mode. Actual asset sessions and
spendable broker funds still determine trade eligibility and sizing.

- `robinhood-frontline-24-7-monitor`: state controller at 4:00 AM and 8:00 PM
  America/New_York. It starts/resumes the daily window, checks funding, and
  pauses/stops operations off-market when 24/7 funding is not verified.
- `blue-chip-operations-heartbeat`: active every 10 minutes during the market
  window by default; it switches to 24/7 only after positive crypto buying power
  is confirmed twice.
- Off-market shutdown is conditional: confirmed positive crypto buying power
  keeps 24/7 scanning active; zero/unknown/contradictory funding makes the pod
  and heavy agent layers dormant until the next start. Existing execution
  permissions and safeguards are unchanged.

### Off-market pause limitation

The live RunPod action set for `t3yz4nrfl1utcr` is `stop`, `restart` and
`terminate`; it does not expose a safe reversible `pause` with guaranteed
autonomous resume. The conditional controller therefore pauses the monitor and
Codex/ChatGPT/Claude heavy layers after hours when funding is absent, but does
not call `stop` merely to save usage. Stopping this pod can clear its ephemeral
container state. The pod is left untouched until a provider-supported pause or
an explicit future stop authorization exists.

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
