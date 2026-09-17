#!/usr/bin/env python3
import gzip
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/Users/raffaykal/AI BLUE CHIP STOCKS")
sys.path.insert(0, str(ROOT / "scripts"))

import stream_alpaca_market_data as stream


class AlpacaStreamLogRotationTests(unittest.TestCase):
    def test_small_log_is_not_rotated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alpaca_market_stream.jsonl"
            path.write_text('{"a":1}\n', encoding="utf-8")
            archive_dir = Path(tmp) / "archive"
            with patch.object(stream, "LOG_ARCHIVE_DIR", archive_dir):
                stream.rotate_jsonl_if_oversized(path)
            self.assertTrue(path.exists())
            self.assertFalse(archive_dir.exists())

    def test_oversized_log_is_archived_and_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alpaca_market_stream.jsonl"
            path.write_bytes(b'{"a":1}\n' * 100)
            archive_dir = Path(tmp) / "archive"
            with patch.object(stream, "LOG_ARCHIVE_DIR", archive_dir), \
                 patch.object(stream, "MAX_JSONL_LOG_BYTES", 10):
                stream.rotate_jsonl_if_oversized(path)
            self.assertFalse(path.exists())
            archived = list(archive_dir.glob("alpaca_market_stream.*.jsonl.gz"))
            self.assertEqual(len(archived), 1)
            with gzip.open(archived[0], "rt", encoding="utf-8") as handle:
                content = handle.read()
            self.assertEqual(content, '{"a":1}\n' * 100)

    def test_append_jsonl_rotates_then_writes_fresh_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alpaca_market_stream.jsonl"
            path.write_bytes(b'{"old":true}\n' * 100)
            archive_dir = Path(tmp) / "archive"
            with patch.object(stream, "LOG_ARCHIVE_DIR", archive_dir), \
                 patch.object(stream, "MAX_JSONL_LOG_BYTES", 10):
                stream.append_jsonl(path, {"new": True})
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8").strip(), '{"new":true}')
            self.assertEqual(len(list(archive_dir.glob("*.gz"))), 1)

    def test_rotation_failure_never_raises(self):
        # Simulate a permission-style failure during archiving; must not
        # propagate and block the actual stream write.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alpaca_market_stream.jsonl"
            path.write_bytes(b"x" * 100)
            with patch.object(stream, "MAX_JSONL_LOG_BYTES", 10), \
                 patch.object(stream, "LOG_ARCHIVE_DIR", Path("/dev/null/impossible")):
                stream.rotate_jsonl_if_oversized(path)  # must not raise
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
