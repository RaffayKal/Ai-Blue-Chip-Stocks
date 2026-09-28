#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import runpod_ops


class RunpodOpsPrivacyTests(unittest.TestCase):
    def test_quote_sync_drops_private_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data = root / "data"
            data.mkdir()
            (data / "robinhood_crypto_quote_snapshot_BTC.json").write_text(json.dumps({
                "broker_name": "Robinhood",
                "symbol": "BTC",
                "quote_timestamp": "2026-09-28T19:00:00Z",
                "bid": 100,
                "ask": 101,
                "routing": "Market Maker Routing",
                "account_number": "private-account",
                "crypto_buying_power_usd": 50,
                "positions": ["private-position"],
            }))
            with patch.object(runpod_ops, "ROOT", root):
                payload = runpod_ops.snapshot_payload()
            self.assertEqual(payload["robinhood_crypto_quote_snapshot_BTC.json"]["symbol"], "BTC")
            self.assertEqual(payload["robinhood_crypto_quote_snapshot.json"]["symbol"], "BTC")
            self.assertFalse({"account_number", "crypto_buying_power_usd", "positions"} & set(payload["robinhood_crypto_quote_snapshot_BTC.json"]))

    def test_scanner_code_deploy_excludes_rules_and_data(self):
        self.assertTrue(runpod_ops.SCANNER_CODE_FILES)
        self.assertTrue(all(name.startswith(("scripts/", "algorithms/")) for name in runpod_ops.SCANNER_CODE_FILES))

    def test_broad_restore_excludes_account_and_runtime_settings(self):
        self.assertIn("rules/brokerage_intake.json", runpod_ops.PRIVATE_RESTORE_EXCLUDES)
        self.assertIn("rules/user_settings.json", runpod_ops.PRIVATE_RESTORE_EXCLUDES)


if __name__ == "__main__":
    unittest.main()
