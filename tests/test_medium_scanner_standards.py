#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path


ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import chatgpt_medium_scanner_fleet as fleet


class MediumScannerStandardsTests(unittest.TestCase):
    def test_medium_scanner_requires_factor_diversity_and_execution_economics(self):
        instructions = fleet.SCANNER_INSTRUCTIONS
        for phrase in ("value", "momentum", "quality", "liquidity", "spread", "slippage", "fees"):
            self.assertIn(phrase, instructions.lower())
        self.assertIn("Do not claim guaranteed returns", instructions)

    def test_apex_standards_document_layered_validation(self):
        text = (ROOT / "rules" / "APEX_INVESTING_ALGORITHM.md").read_text(encoding="utf-8")
        self.assertIn("Layered Tactical Standards", text)
        self.assertIn("execution friction", text)
        self.assertIn("source disagreement", text)


if __name__ == "__main__":
    unittest.main()
