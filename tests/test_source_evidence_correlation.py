#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import runpod_lightweight_scanner as scanner


def quote_source(name, bid, ask, last, status="fresh"):
    return {"source": name, "status": status, "bid": bid, "ask": ask, "last": last}


class SourceEvidenceCorrelationTests(unittest.TestCase):
    def test_independent_sources_each_count_separately(self):
        records = [
            quote_source("Coinbase", 100.0, 100.2, 100.1),
            quote_source("Binance", 100.05, 100.25, 100.15),
            quote_source("Kraken", 99.98, 100.18, 100.08),
        ]
        result = scanner.compute_effective_evidence(records)
        self.assertEqual(result["raw_fresh_count"], 3)
        self.assertEqual(result["effective_fresh_count"], 3)
        self.assertEqual(result["duplicated_source_members"], 0)

    def test_mirrored_feed_counts_once_not_twice(self):
        records = [
            quote_source("Coinbase", 100.0, 100.2, 100.1),
            quote_source("CoinbaseMirror", 100.0, 100.2, 100.1),
        ]
        result = scanner.compute_effective_evidence(records)
        self.assertEqual(result["raw_fresh_count"], 2)
        self.assertEqual(result["effective_fresh_count"], 1)
        self.assertEqual(result["duplicated_source_members"], 1)
        self.assertEqual(len(result["source_families"]), 1)
        self.assertCountEqual(result["source_families"][0], ["Coinbase", "CoinbaseMirror"])

    def test_stale_sources_are_excluded_from_evidence_count(self):
        records = [
            quote_source("Coinbase", 100.0, 100.2, 100.1),
            quote_source("Binance", 100.0, 100.2, 100.1, status="stale_or_unusable"),
        ]
        result = scanner.compute_effective_evidence(records)
        self.assertEqual(result["raw_fresh_count"], 1)
        self.assertEqual(result["effective_fresh_count"], 1)

    def test_records_without_quote_fields_each_count_as_their_own_family(self):
        records = [
            {"source": "volatile_crypto_candidates.active_symbol", "status": "fresh"},
            {"source": "another_non_quote_source", "status": "fresh"},
        ]
        result = scanner.compute_effective_evidence(records)
        self.assertEqual(result["raw_fresh_count"], 2)
        self.assertEqual(result["effective_fresh_count"], 2)
        self.assertEqual(result["duplicated_source_members"], 0)

    def test_medium8_projection_exposes_effective_evidence_and_uses_it_for_scoring(self):
        duplicated_sources = [
            quote_source("Coinbase", 100.0, 100.2, 100.1),
            quote_source("CoinbaseMirror", 100.0, 100.2, 100.1),
        ]
        independent_sources = [
            quote_source("Coinbase", 100.0, 100.2, 100.1),
            quote_source("Binance", 101.0, 101.3, 101.15),
        ]
        duplicated_projection = scanner.build_medium8_projection(
            duplicated_sources, True, {}, {}, {}, "TEST_TIER"
        )
        independent_projection = scanner.build_medium8_projection(
            independent_sources, True, {}, {}, {}, "TEST_TIER"
        )
        self.assertEqual(duplicated_projection["effective_evidence"]["effective_fresh_count"], 1)
        self.assertEqual(independent_projection["effective_evidence"]["effective_fresh_count"], 2)
        # Two independently-confirmed sources must score deeper evidence than
        # two mirrored copies of the same feed.
        self.assertGreater(
            independent_projection["projection_scores"]["source_depth_score"],
            duplicated_projection["projection_scores"]["source_depth_score"],
        )


if __name__ == "__main__":
    unittest.main()
