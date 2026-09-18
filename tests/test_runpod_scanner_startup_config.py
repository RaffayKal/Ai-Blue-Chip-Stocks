#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")


class RunpodScannerStartupConfigTests(unittest.TestCase):
    def test_runpod_defaults_to_moderate_fourteen_lane_fanout(self):
        startup = (ROOT / "scripts" / "start_runpod_scanner_24_7.sh").read_text(encoding="utf-8")
        self.assertIn('export RUNPOD_SCANNER_LANES="${RUNPOD_SCANNER_LANES:-14}"', startup)

        fleet = (ROOT / "scripts" / "start_lightweight_scanner_fleet.sh").read_text(encoding="utf-8")
        self.assertIn('RUNPOD_MIN_LIGHTWEIGHT_LANES:-7', fleet)
        self.assertIn('RUNPOD_MAX_LIGHTWEIGHT_LANES:-13000', fleet)

    def test_fleet_startup_surfaces_a_visible_scanning_proof_heartbeat(self):
        # The pool's own per-lane output is redirected to a log file so 700
        # lanes don't flood the container log; without a separate visible
        # heartbeat there is nothing in the container log proving the
        # scanner is actively deciding anything, only infra-level price
        # ticks that look identical whether or not scanning is happening.
        fleet = (ROOT / "scripts" / "start_lightweight_scanner_fleet.sh").read_text(encoding="utf-8")
        self.assertIn("SCANNING_PROOF:", fleet)
        self.assertIn("candidate_decision=", fleet)
        self.assertIn("scanner_viable=", fleet)
        self.assertIn("fleet_consensus=", fleet)


if __name__ == "__main__":
    unittest.main()
