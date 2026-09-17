#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")


class RunpodScannerStartupConfigTests(unittest.TestCase):
    def test_runpod_defaults_to_automatic_seven_to_seven_hundred_lanes(self):
        startup = (ROOT / "scripts" / "start_runpod_scanner_24_7.sh").read_text(encoding="utf-8")
        self.assertIn('export RUNPOD_SCANNER_LANES="${RUNPOD_SCANNER_LANES:-auto}"', startup)

        fleet = (ROOT / "scripts" / "start_lightweight_scanner_fleet.sh").read_text(encoding="utf-8")
        self.assertIn('RUNPOD_MIN_LIGHTWEIGHT_LANES:-7', fleet)
        self.assertIn('RUNPOD_MAX_LIGHTWEIGHT_LANES:-700', fleet)


if __name__ == "__main__":
    unittest.main()
