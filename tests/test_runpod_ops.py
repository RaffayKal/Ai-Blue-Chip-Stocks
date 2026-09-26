import ast
import base64
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runpod_ops',ROOT/'scripts/runpod_ops.py')
ops=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


class RunPodOpsTests(unittest.TestCase):
    def test_restore_contains_required_fixture_but_no_credentials_or_live_accounts(self):
        source=ast.parse(ops.deployment_script())
        call=next(node.value for node in source.body if isinstance(node,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='blob' for t in node.targets))
        blob=base64.b64decode(ast.literal_eval(call.args[0]))
        with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
            names=archive.getnames()
        self.assertIn('data/sample_qualified_candidate_envelope.json',names)
        self.assertIn('scripts/run_pod_scanner_supervisor.py',names)
        self.assertNotIn('.env.local',names)
        self.assertFalse(any('robinhood_crypto_capital_snapshot' in n for n in names))
        self.assertFalse(any(n.startswith('data/robinhood_crypto_quote_snapshot') for n in names))
        self.assertFalse(any('__pycache__' in n for n in names))

    def test_sync_preserves_timestamps_and_rejects_stale_or_older_evidence(self):
        now=datetime.now(timezone.utc)
        recent=(now-timedelta(seconds=10)).isoformat()
        old=(now-timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as root, patch.object(ops,'REMOTE',root):
            payload={'robinhood_crypto_quote_snapshot_BTC.json':{'quote_timestamp':recent},
                     'robinhood_crypto_quote_snapshot_ETH.json':{'quote_timestamp':old}}
            with redirect_stdout(io.StringIO()):
                exec(ops.sync_script(payload),{})
                exec(ops.sync_script({'robinhood_crypto_quote_snapshot_BTC.json':{'quote_timestamp':old}}),{})
            self.assertEqual(json.loads((Path(root)/'data/robinhood_crypto_quote_snapshot_BTC.json').read_text())['quote_timestamp'],recent)
            self.assertFalse((Path(root)/'data/robinhood_crypto_quote_snapshot_ETH.json').exists())

    def test_sync_does_not_allow_path_escape(self):
        with tempfile.TemporaryDirectory() as root, patch.object(ops,'REMOTE',root):
            with self.assertRaises(ValueError):
                exec(ops.sync_script({'../outside.json':{}}),{})


if __name__=='__main__':
    unittest.main()
