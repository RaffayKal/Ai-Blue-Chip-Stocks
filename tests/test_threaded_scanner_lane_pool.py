#!/usr/bin/env python3
import asyncio
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import lane_synergy_engine as synergy_engine
import threaded_scanner_lane_pool as pool


class ThreadedScannerLanePoolTests(unittest.TestCase):
    def test_lane_naming_matches_process_based_fleet(self):
        self.assertEqual(pool.lane_name_for(1), "primary")
        self.assertEqual(pool.lane_name_for(2), "lane_2")
        self.assertEqual(pool.lane_name_for(700), "lane_700")

    def test_seven_hundred_lanes_run_one_cycle_in_a_single_process(self):
        result = subprocess.run(
            [sys.executable, "scripts/threaded_scanner_lane_pool.py", "--lanes", "700", "--once"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("THREADED_LANE_POOL_SIZE: 700", result.stdout)
        # Per rules/MULTI_LANE_SYNERGY_RESEARCH_LAW.md, SYNERGY_LANE_SHARE of
        # the lanes are dedicated MATH/HISTORY/RESEARCH/TEMPORAL synergy
        # lanes (piling multiple lanes onto the same symbol/role once every
        # combo has at least one), and the remainder still run the legacy
        # generic scan.
        dedicated_synergy_lanes = synergy_engine.dedicated_role_lane_count(700, synergy_engine.synergy_symbols())
        self.assertEqual(
            result.stdout.count("STARTED_MEDIUM_WEIGHT_SCANNER_LANE:"),
            700 - dedicated_synergy_lanes,
        )
        self.assertEqual(result.stdout.count("STARTED_SYNERGY_LANE:"), dedicated_synergy_lanes)
        self.assertIn("FLEET_SYNERGY:", result.stdout)
        self.assertIn("LANE_SYNERGY_ROLLUP:", result.stdout)

    def test_extract_net_opportunity_reads_crypto_projection_score(self):
        status = {"projection": {"crypto": {"projection_scores": {"net_opportunity_score": 12.5}}}}
        self.assertEqual(pool.extract_net_opportunity(status), 12.5)
        self.assertIsNone(pool.extract_net_opportunity({}))
        self.assertIsNone(pool.extract_net_opportunity({"projection": None}))

    def test_synergy_aggregator_publishes_consensus_across_lane_samples(self):
        async def scenario():
            recent_results = [
                {"lane": "primary", "candidate_decision": "NO ACTION", "scanner_viable": False, "net_opportunity_score": 10.0},
                {"lane": "lane_2", "candidate_decision": "NO ACTION", "scanner_viable": False, "net_opportunity_score": 20.0},
                {"lane": "lane_3", "candidate_decision": "BUY", "scanner_viable": True, "net_opportunity_score": 30.0},
            ]
            stop_event = asyncio.Event()
            await pool.synergy_aggregator(recent_results, lane_count=3, interval_seconds=5, once=True, stop_event=stop_event)

        asyncio.run(scenario())
        payload = json.loads(pool.SYNERGY_STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["consensus_decision"], "NO ACTION")
        self.assertEqual(payload["sample_count"], 3)
        self.assertAlmostEqual(payload["agreement_ratio"], 2 / 3, places=3)
        self.assertAlmostEqual(payload["viable_ratio"], 1 / 3, places=3)
        self.assertEqual(payload["net_opportunity_score_avg"], 20.0)


if __name__ == "__main__":
    unittest.main()
