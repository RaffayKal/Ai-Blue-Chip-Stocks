#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import ingest_robinhood_execution_snapshot as ingest


class IngestRobinhoodExecutionSnapshotTests(unittest.TestCase):
    def payload(self, direct_quantity="0.00006084"):
        return {
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "account_match_confirmed": True,
            "crypto_account_confirmed": True,
            "portfolio": {
                "data": {
                    "buying_power": {"buying_power": "0.0000"},
                    "crypto_buying_power": {"buying_power": "0.0000"},
                    "cash": "0",
                }
            },
            "positions": {
                "data": {
                    "results": [{
                        "currency": {"code": "BTC"},
                        "quantity": "0.00006084",
                        "quantity_transferable": "0.00006084",
                        "quantity_held_for_sell": "0",
                        "cost_bases": [{
                            "direct_quantity": direct_quantity,
                            "direct_cost_basis": "4.8",
                            "intraday_quantity": "0",
                            "intraday_cost_basis": "0",
                        }],
                    }]
                }
            },
        }

    def test_zero_buying_power_does_not_remove_sellable_position(self):
        snapshot = ingest.normalize(self.payload())
        self.assertEqual(snapshot["crypto_buying_power_usd"], 0.0)
        self.assertEqual(snapshot["positions"][0]["symbol"], "BTC")
        self.assertEqual(snapshot["positions"][0]["quantity_transferable"], 0.00006084)
        self.assertEqual(snapshot["positions"][0]["direct_cost_basis_usd"], 4.8)
        self.assertTrue(snapshot["positions"][0]["cost_basis_complete"])
        self.assertFalse(snapshot["positions"][0]["apex_harvest_gate_passed"])
        self.assertNotIn("account_number", snapshot)

    def test_partial_cost_basis_is_marked_incomplete(self):
        snapshot = ingest.normalize(self.payload(direct_quantity="0.00003000"))
        self.assertFalse(snapshot["positions"][0]["cost_basis_complete"])


if __name__ == "__main__":
    unittest.main()
