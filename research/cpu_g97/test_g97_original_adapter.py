"""G97 adapter isolation and restoration tests (no model download)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g97_original_adapter import frozen, run_g97, OverflowBypassCache

class AdapterTests(unittest.TestCase):
    def test_restores_g96_class_after_failure(self):
        original = frozen.AdmissionCache
        with self.assertRaisesRegex(AttributeError, "inference_mode"):
            run_g97(None, None, None, None, None, None)
        self.assertIs(frozen.AdmissionCache, original)

    def test_candidate_is_separate_from_frozen_controls(self):
        self.assertIsNot(OverflowBypassCache, frozen.AdmissionCache)
        self.assertEqual(OverflowBypassCache().capacity, 4)

if __name__ == "__main__":
    unittest.main()
