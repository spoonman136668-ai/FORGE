"""Offline contract tests for portable G89/G90 replay (no model/GPU)."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from portable_replay import git_blob, patched_tree, prepare

class PortableReplayTests(unittest.TestCase):
    def test_git_blob_header(self):
        data = b"abc"
        expected = hashlib.sha1(b"blob 3" + bytes([0]) + data).hexdigest()
        self.assertEqual(git_blob(data), expected)

    def test_replace_exactly_one(self):
        tree = patched_tree('x="/mnt/data/g89/results.json"','/mnt/data/g89/results.json','C:/test/result.json')
        self.assertIn('C:/test/result.json', __import__('ast').unparse(tree))

    def test_reject_missing_literal(self):
        with self.assertRaisesRegex(RuntimeError, "OUTPUT_LITERAL_MATCH_COUNT_0"):
            patched_tree('x="no match"', 'x.json', 'y.json')

    def test_reject_duplicate_literal(self):
        with self.assertRaisesRegex(RuntimeError, "OUTPUT_LITERAL_MATCH_COUNT_2"):
            patched_tree('x="old"; y="old"', 'old', 'new')

    def test_reject_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"research/acc_g89/g89.py"
            p.parent.mkdir(parents=True)
            p.write_text('x="/mnt/data/g89/results.json"')
            with self.assertRaisesRegex(RuntimeError, "FROZEN_SOURCE_BLOB_DRIFT"):
                prepare(tmp, "g89", Path(tmp)/"out.json")

    def test_reject_unsupported_experiment(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_EXPERIMENT"):
            prepare(".", "g88", "out.json")

if __name__ == "__main__":
    unittest.main()
