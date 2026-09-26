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

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/workspace/apex"


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
    paths = [ROOT / 'data/robinhood_crypto_quote_snapshot.json']
    paths += sorted((ROOT / 'data').glob('robinhood_crypto_quote_snapshot_*.json'))
    return {p.name: json.loads(p.read_text()) for p in paths if p.is_file()}


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
        return datetime.fromisoformat((d.get('quote_timestamp') or d.get('crypto_capital_retrieved_at') or '').replace('Z','+00:00'))
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('status','sync-quotes','restore'))
    args=parser.parse_args()
    script = (status_script() if args.action=='status' else
              sync_script(snapshot_payload()) if args.action=='sync-quotes' else deployment_script())
    try:
        print(remote(script,timeout=120 if args.action=='restore' else 45))
    except (OSError, RuntimeError, TimeoutError) as exc:
        raise SystemExit(str(exc)) from None


if __name__=='__main__':
    main()
