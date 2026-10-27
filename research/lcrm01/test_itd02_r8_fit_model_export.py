#!/usr/bin/env python3
"""Fail-closed fixture tests for FIT model export (no MiniGrid episodes)."""
import hashlib
import json
import unittest
from collections import Counter, defaultdict

from itd02_r8_fit_only_run import verify_and_serialize


class FitModelExportTest(unittest.TestCase):
    def setUp(self):
        self.model = defaultdict(Counter)
        self.model[(0, False, 2)][(1, 0, 0)] = 7
        self.model[(1, True, 0)][(0, 0, 0)] = 4
        self.digest = hashlib.sha256(
            json.dumps(
                [([0, False, 2], [([1, 0, 0], 7)]),
                 ([1, True, 0], [([0, 0, 0], 4)])],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def test_lossless_export(self):
        payload = verify_and_serialize(self.model, self.digest)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), self.digest)

    def test_tampered_digest_refused(self):
        with self.assertRaisesRegex(ValueError, "DIGEST_MISMATCH"):
            verify_and_serialize(self.model, "0" * 64)

    def test_empty_model_refused(self):
        payload = b"[]"
        with self.assertRaisesRegex(ValueError, "MALFORMED"):
            verify_and_serialize({}, hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    unittest.main()
