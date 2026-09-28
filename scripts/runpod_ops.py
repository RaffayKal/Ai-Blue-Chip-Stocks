#!/usr/bin/env python3
"""Reconnect, inspect, restore scanner files, or push quote-only broker snapshots.

Uses the existing registered SSH key; never changes account access or trades.
The SSH proxy requires a PTY. No third-party SSH library is required.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import select
import subprocess
import tarfile
import textwrap
import time
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/workspace/apex"
SCANNER_CODE_FILES = (
    "scripts/runpod_lightweight_scanner.py",
    "scripts/threaded_scanner_lane_pool.py",
    "scripts/chatgpt_scanner_runtime.py",
    "scripts/chatgpt_medium_scanner_fleet.py",
    "algorithms/candidate_envelope_gate.py",
    "algorithms/apex_packet_monitor.py",
    "scripts/poll_robinhood_mcp_relay.py",
)
PUBLIC_QUOTE_FIELDS = frozenset({
    'symbol', 'asset_class', 'session', 'venue', 'broker_name',
    'timestamp', 'quote_timestamp', 'bid', 'ask', 'last',
    'source', 'routing', 'execution_authority',
})
PRIVATE_RESTORE_EXCLUDES = frozenset({
    'rules/brokerage_intake.json',
    'rules/user_settings.json',
})


def remote(script, timeout=90):
    config = json.loads((ROOT / "runpod_vllm_cpu_006.json").read_text())
    ssh = config["ssh"]
    process = subprocess.Popen(
        ["ssh", "-tt", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
         "-o", "StrictHostKeyChecking=yes", "-o", "IdentitiesOnly=yes",
         "-i", ssh["identity_file"], ssh["user_host"]],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    nonce = uuid.uuid4().hex
    ready, done = "APEX_READY_" + nonce, "APEX_DONE_" + nonce
    deadline = time.monotonic() + timeout

    def until(pattern):
        output = b""
        while time.monotonic() < deadline:
            if select.select([process.stdout], [], [], 0.5)[0]:
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("SSH closed before completion: " + output.decode(errors="replace")[-1000:])
                output += chunk
                if re.search(pattern, output):
                    return output
            if len(output) > 2_000_000:
                raise RuntimeError("Remote output exceeded safety bound")
        raise TimeoutError("RunPod SSH operation timed out")

    try:
        process.stdin.write(("stty -echo; export PS1='' PS2=''; printf '\\n" + ready + "\\n'\n").encode())
        process.stdin.flush()
        until((r"(?:\r?\n)" + ready + r"\r?\n").encode())
        # Short base64 lines avoid canonical PTY input-length limits.
        payload = "\n".join(textwrap.wrap(base64.b64encode(script.encode()).decode(), 120))
        wrapper = ("python3 - <<'APEX_SCRIPT'\nimport base64\nexec(compile(base64.b64decode('''\n"
                   + payload + "\n'''), '<apex-remote>', 'exec'))\nAPEX_SCRIPT\n"
                   + "apex_rc=$?; printf '\\n" + done + ":%s\\n' \"$apex_rc\"; exit\n")
        process.stdin.write(wrapper.encode())
        process.stdin.flush()
        output = until((done + r":\d+\r?\n").encode()).decode(errors="replace")
        result = re.search(done + r":(\d+)", output)
        clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output[:result.start()]).strip()
        if result.group(1) != "0":
            raise RuntimeError("Remote operation failed: " + clean[-2000:])
        return clean
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=3)


def status_script():
    return f"""
import json,os,pathlib,time
root=pathlib.Path({REMOTE!r})
result={{'remote_root':str(root),'installed':root.is_dir()}}
fields=('timestamp','timestamp_utc','status','scanner_active','scanner_viable',
        'trade_execution_allowed','candidate_decision','configured_lanes',
        'restart_count','fleet_size_configured','sample_count','consensus_decision',
        'execution_consensus_decision','execution_gate_decision','execution_search_state',
        'discovery_state')
for name in ('pod_scanner_supervisor_status.json','runpod_lightweight_scanner_status.json',
             'fleet_lane_manifest.json','fleet_synergy_status.json','chatgpt_medium_scanner_fleet.json'):
    p=root/'data'/name
    if p.exists():
        d=json.loads(p.read_text())
        result[name]={{k:d[k] for k in fields if k in d}}
        result[name]['file_age_seconds']=round(time.time()-p.stat().st_mtime,2)
p=root/'data/current_candidate_envelope.json'
if p.exists():
    d=json.loads(p.read_text())
    result['source_quality']=d.get('source_quality')
    market=d.get('market_input') if isinstance(d.get('market_input'),dict) else {{}}
    result['candidate_symbol']=market.get('symbol') or d.get('active_symbol')
    result['candidate_quote_source']=market.get('quote_source_path')
p=root/'data/volatile_crypto_candidates.json'
if p.exists():
    d=json.loads(p.read_text())
    if isinstance(d,dict): result['active_symbol']=d.get('active_symbol') or d.get('fallback_symbol')
for name in ('memory.current','memory.max'):
    p=pathlib.Path('/sys/fs/cgroup')/name
    if p.exists(): result[name]=p.read_text().strip()
s=os.statvfs('/workspace')
result['disk_used_percent']=round((1-s.f_bavail/s.f_blocks)*100,2)
print(json.dumps(result,indent=2))
"""


def snapshot_payload():
    # RunPod receives market quotes only. Account, buying-power, portfolio,
    # position, and order data stay on the authenticated host MCP.
    paths = sorted((ROOT / 'data').glob('robinhood_crypto_quote_snapshot_*.json'))
    snapshots = {}
    for path in paths:
        if not path.is_file():
            continue
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict) or raw.get('broker_name') != 'Robinhood':
            continue
        # A quote file can acquire additional local fields over time. Never
        # send account, funding, position, or order fields to the pod.
        snapshots[path.name] = {key: raw[key] for key in PUBLIC_QUOTE_FIELDS if key in raw}
    aggregate_name = 'robinhood_crypto_quote_snapshot.json'
    aggregate = snapshots.get(aggregate_name)

    def quote_time(data):
        value = data.get('quote_timestamp') or data.get('timestamp') or ''
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    # The scanner's required-source gate reads the aggregate artifact. Keep it
    # factual by promoting the newest already-authenticated per-symbol quote,
    # rather than letting an older aggregate hide a fresh Robinhood feed.
    per_symbol = [data for name, data in snapshots.items()
                  if name != aggregate_name and data.get('broker_name') == 'Robinhood']
    newest = max(per_symbol, key=quote_time, default=None)
    if newest is not None and (aggregate is None or quote_time(newest) > quote_time(aggregate)):
        snapshots[aggregate_name] = newest
    return snapshots


def sync_script(payload):
    return f"""
import json,os,pathlib
from datetime import datetime,timezone
root=pathlib.Path({REMOTE!r})/'data'
root.mkdir(parents=True,exist_ok=True)
payload=json.loads({json.dumps(payload)!r})
count=0
for name,data in payload.items():
    if '/' in name or not name.startswith('robinhood_crypto_'): raise ValueError('Invalid snapshot filename')
    def stamp(d):
        return datetime.fromisoformat((d.get('quote_timestamp') or '').replace('Z','+00:00'))
    incoming=stamp(data)
    age=(datetime.now(timezone.utc)-incoming).total_seconds()
    if age<0 or age>180: continue
    path=root/name
    if path.exists() and stamp(json.loads(path.read_text()))>=incoming: continue
    temporary=path.with_suffix('.json.'+str(os.getpid())+'.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\\n')
    temporary.replace(path)
    count+=1
print(json.dumps({{'snapshots_written':count,'timestamps_preserved':True}}))
"""


def repair_scanner_script():
    """Ask the existing supervisor to recreate only the lane-pool worker."""
    return f"""
import json,os,pathlib,signal,time
root=pathlib.Path({REMOTE!r})
matches=[]
proc_root=pathlib.Path('/proc')
for entry in proc_root.iterdir():
    if not entry.name.isdigit():
        continue
    try:
        command=b' '.join((entry/'cmdline').read_bytes().split(b'\\0')).decode(errors='replace')
    except (OSError,UnicodeError):
        continue
    lane_pool = 'scripts/threaded_scanner_lane_pool.py' in command and '--lanes' in command
    fleet_wrapper = command.strip().endswith('scripts/start_lightweight_scanner_fleet.sh')
    if lane_pool or fleet_wrapper:
        matches.append({{'pid':int(entry.name),'command':command,
                        'target':('lane_pool' if lane_pool else 'fleet_wrapper')}})
terminated=[]
forced=[]
for match in matches:
    try:
        os.kill(match['pid'], signal.SIGTERM)
        terminated.append(match['pid'])
    except ProcessLookupError:
        pass
deadline=time.monotonic()+15
while time.monotonic()<deadline and any((proc_root/str(pid)).exists() for pid in terminated):
    time.sleep(0.25)
for pid in terminated:
    if (proc_root/str(pid)).exists():
        try:
            os.kill(pid, signal.SIGKILL)
            forced.append(pid)
        except ProcessLookupError:
            pass
print(json.dumps({{'scanner_matches':len(matches),'terminated_pids':terminated,'forced_pids':forced,
                  'supervisor_expected_to_restart':bool(terminated),
                  'execution_authority':False}}))
"""


def start_scanner_script():
    """Recover only a missing scanner supervisor on the existing pod."""
    return f"""
import json,pathlib,subprocess
root=pathlib.Path({REMOTE!r})
if not (root/'scripts/run_pod_scanner_supervisor.py').is_file():
    raise FileNotFoundError('scanner supervisor code missing')
running=[]
for entry in pathlib.Path('/proc').iterdir():
    if not entry.name.isdigit(): continue
    try:
        command=b' '.join((entry/'cmdline').read_bytes().split(b'\\0')).decode(errors='replace')
    except OSError: continue
    if 'scripts/run_pod_scanner_supervisor.py' in command:
        running.append(int(entry.name))
if running:
    print(json.dumps({{'scanner_supervisor':'already_running','pids':running}}))
else:
    with (root/'logs/pod_scanner_supervisor.log').open('a') as log:
        process=subprocess.Popen(['python3','scripts/run_pod_scanner_supervisor.py'],cwd=root,
                                 stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps({{'scanner_supervisor':'started','pid':process.pid}}))
"""


def deployment_script():
    buffer = io.BytesIO()
    paths = [ROOT / name for name in ('AGENTS.md','START_TODAY.md','COMMANDS.md')]
    for folder in ('algorithms','scripts','rules'):
        paths += sorted((ROOT/folder).rglob('*'))
    paths += [ROOT/'data'/name for name in (
        'blue_chip_watchlist.txt','crypto_watchlist.txt',
        'robinhood_watchlist_snapshot.json',
        'sample_qualified_candidate_envelope.json','sample_robinhood_volatile_crypto_input.json')]
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for path in paths:
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:
                continue
            if str(path.relative_to(ROOT)) in PRIVATE_RESTORE_EXCLUDES:
                continue
            if path.suffix not in ('.py','.sh','.md','.json','.txt','.plist'):
                continue
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    blob=buffer.getvalue()
    digest=hashlib.sha256(blob).hexdigest()
    return f"""
import base64,hashlib,io,json,pathlib,subprocess,tarfile
root=pathlib.Path({REMOTE!r})
root.mkdir(parents=True,exist_ok=True)
blob=base64.b64decode({base64.b64encode(blob).decode()!r})
assert hashlib.sha256(blob).hexdigest()=={digest!r}
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
    archive.extractall(root,filter='data')
(root/'data').mkdir(exist_ok=True)
(root/'logs').mkdir(exist_ok=True)
(root/'data/deployment_sha256.txt').write_text({digest!r}+'\\n')
# The supervisor's exclusive lock prevents duplicate scanner trees.
with (root/'logs/pod_scanner_supervisor.log').open('a') as log:
    subprocess.Popen(['python3','scripts/run_pod_scanner_supervisor.py'],cwd=root,
                     stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({{'deployment_sha256':{digest!r},'supervisor_requested':True}}))
"""


def scanner_code_script():
    """Deploy only named source files; never bundle account records or secrets."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name in SCANNER_CODE_FILES:
            path = ROOT / name
            if not path.is_file() or path.is_symlink():
                raise FileNotFoundError(name)
            archive.add(path, arcname=name, recursive=False)
    blob = buffer.getvalue()
    digest = hashlib.sha256(blob).hexdigest()
    return f"""
import base64,hashlib,io,json,pathlib,tarfile
root=pathlib.Path({REMOTE!r})
if not root.is_dir(): raise FileNotFoundError(root)
blob=base64.b64decode({base64.b64encode(blob).decode()!r})
assert hashlib.sha256(blob).hexdigest()=={digest!r}
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
    names=set(archive.getnames())
    if names!={set(SCANNER_CODE_FILES)!r}: raise ValueError('Unexpected scanner deployment member')
    archive.extractall(root,filter='data')
print(json.dumps({{'scanner_code_sha256':{digest!r},'files_updated':len(names),'private_account_data_transferred':False}}))
"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('status','sync-quotes','restore','repair-scanner','deploy-scanner-code','start-scanner'))
    args=parser.parse_args()
    script = (status_script() if args.action=='status' else
              sync_script(snapshot_payload()) if args.action=='sync-quotes' else
              repair_scanner_script() if args.action=='repair-scanner' else
              scanner_code_script() if args.action=='deploy-scanner-code' else
              start_scanner_script() if args.action=='start-scanner' else deployment_script())
    try:
        print(remote(script,timeout=120 if args.action=='restore' else 45))
    except (OSError, RuntimeError, TimeoutError) as exc:
        raise SystemExit(str(exc)) from None


if __name__=='__main__':
    main()
