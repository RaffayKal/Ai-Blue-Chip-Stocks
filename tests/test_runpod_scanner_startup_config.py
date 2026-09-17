#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")


class RunpodScannerStartupConfigTests(unittest.TestCase):
    def test_runpod_defaults_to_seventy_medium_scanner_lanes(self):
        startup = (ROOT / "scripts" / "start_runpod_scanner_24_7.sh").read_text(encoding="utf-8")
        self.assertIn('export RUNPOD_SCANNER_LANES="${RUNPOD_SCANNER_LANES:-70}"', startup)


if __name__ == "__main__":
    unittest.main()
