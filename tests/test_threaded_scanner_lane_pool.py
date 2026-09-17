#!/usr/bin/env python3
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

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
        self.assertEqual(result.stdout.count("STARTED_MEDIUM_WEIGHT_SCANNER_LANE:"), 700)


if __name__ == "__main__":
    unittest.main()
