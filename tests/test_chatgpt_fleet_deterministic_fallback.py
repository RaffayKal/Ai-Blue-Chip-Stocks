#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import chatgpt_medium_scanner_fleet as fleet


def lane_fixture(**overrides):
    lane = {
        "scanner_viable": True,
        "candidate_decision": "WATCHLIST ONLY",
        "required_sources": [
            {"source": "Robinhood.crypto_quote", "status": "fresh"},
            {"source": "Coinbase.crypto_quote", "status": "stale_or_unusable"},
        ],
        "market_input": {"source_conflict": False},
        "projection": {
            "crypto": {
                "projection_scores": {"continuation_probability": 61.5, "net_opportunity_score": 12.3},
                "reversal_risk_score": 40.2,
                "stale_penalty_score": 5.0,
            },
            "blue_chips": {
                "projection_scores": {"continuation_probability": 30.0, "net_opportunity_score": -4.0},
                "reversal_risk_score": 70.0,
                "stale_penalty_score": 20.0,
            },
        },
    }
    lane.update(overrides)
    return lane


class ChatGptFleetDeterministicFallbackTests(unittest.TestCase):
    def test_fallback_is_never_labeled_as_a_real_openai_result(self):
        result = fleet.deterministic_role_result("crypto_momentum", [lane_fixture()], "fp1")
        self.assertEqual(result["status"], "OK_DETERMINISTIC_FALLBACK")
        self.assertNotEqual(result["status"], "OK")
        self.assertEqual(result["fallback_source"], "RUNPOD_MEDIUM_WEIGHT_SCANNER_DETERMINISTIC")

    def test_crypto_momentum_reuses_existing_medium8_projection_scores(self):
        result = fleet.deterministic_role_result("crypto_momentum", [lane_fixture()], "fp1")
        self.assertEqual(result["projection"]["continuation_probability"], 61.5)
        self.assertEqual(result["projection"]["net_opportunity_score"], 12.3)

    def test_blue_chip_reversal_reuses_existing_reversal_score(self):
        result = fleet.deterministic_role_result("blue_chip_reversal", [lane_fixture()], "fp1")
        self.assertEqual(result["projection"]["reversal_risk_score"], 70.0)

    def test_multi_source_quality_counts_fresh_sources_from_the_scanner_itself(self):
        result = fleet.deterministic_role_result("multi_source_quality", [lane_fixture()], "fp1")
        self.assertEqual(result["projection"]["fresh_source_count"], 1)
        self.assertEqual(result["projection"]["total_source_count"], 2)

    def test_multi_source_quality_marks_not_viable_when_zero_fresh_sources(self):
        lane = lane_fixture(required_sources=[{"source": "Robinhood.crypto_quote", "status": "stale_or_unusable"}])
        result = fleet.deterministic_role_result("multi_source_quality", [lane], "fp1")
        self.assertFalse(result["scanner_viable"])

    def test_fundamentals_news_is_honestly_reported_as_unavailable_not_fabricated(self):
        result = fleet.deterministic_role_result("fundamentals_news", [lane_fixture()], "fp1")
        self.assertFalse(result["scanner_viable"])
        self.assertEqual(result["candidate_decision"], "NO ACTION")
        self.assertIn("fundamentals_and_news_narrative_unavailable_without_chatgpt", result["missing_facts"])
        self.assertEqual(result["projection"], {})

    def test_forward_projection_role_carries_both_lanes_of_medium8_scores(self):
        result = fleet.deterministic_role_result("forward_projection", [lane_fixture()], "fp1")
        self.assertEqual(result["projection"]["crypto"]["net_opportunity_score"], 12.3)
        self.assertEqual(result["projection"]["blue_chips"]["net_opportunity_score"], -4.0)

    def test_missing_lane_data_is_flagged_not_silently_ignored(self):
        result = fleet.deterministic_role_result("crypto_momentum", [], "fp1")
        self.assertIn("no_candidate_lane_available", result["missing_facts"])

    def test_openai_error_detail_is_carried_through_for_visibility(self):
        result = fleet.deterministic_role_result("crypto_momentum", [lane_fixture()], "fp1", openai_error="RuntimeError: HTTP 429")
        self.assertEqual(result["openai_error"], "RuntimeError: HTTP 429")

    def test_run_role_falls_back_when_openai_unavailable_without_raising(self):
        result = fleet.run_role("gpt-5.5", "crypto_momentum", "instruction", [lane_fixture()], "fp1", openai_available=False)
        self.assertEqual(result["status"], "OK_DETERMINISTIC_FALLBACK")


if __name__ == "__main__":
    unittest.main()
