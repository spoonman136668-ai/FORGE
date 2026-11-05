"""G97 frozen development manifest contract tests; no model inference."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g97_stream_manifest import freeze, canonical_bytes, STRATA

class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.selected = [{"source_row": i, "instruction_sha256": f"{i:064x}"} for i in range(12)]

    def test_deterministic_and_development_only(self):
        a, ah = freeze(self.selected)
        b, bh = freeze(self.selected)
        self.assertEqual(ah, bh)
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))
        self.assertEqual(a["rank_interval"], [276, 288])
        self.assertFalse(a["protected_heldout_used"])
        self.assertEqual(set(a["strata"]), set(STRATA))
        for item in a["strata"].values():
            self.assertEqual(len(item["requests"]), 48)

    def test_duplicate_rejected(self):
        self.selected[-1] = dict(self.selected[0])
        with self.assertRaisesRegex(ValueError, "COHORT_DRIFT"):
            freeze(self.selected)

if __name__ == "__main__":
    unittest.main()
