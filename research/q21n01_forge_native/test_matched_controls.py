"""Seven-comparator Q21N-01 contract checks on handwritten toys only."""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import matched_controls as candidate


class MatchedControlsTests(unittest.TestCase):
    def test_exact_seven_handwritten_trained_comparators(self):
        with patch("generator.generate",
                   side_effect=AssertionError("NO_FROZEN_ROLE_BIRTH")):
            receipt = candidate.preflight()
        self.assertEqual(set(receipt["validation_arm_nll"]),
                         set(candidate.ARM_NAMES))
        self.assertEqual(receipt["handwritten_fit_arms"], 7)
        self.assertEqual(receipt["role_cohorts_generated"], 0)
        self.assertEqual(receipt["role_models_trained"], 0)
        self.assertEqual(receipt["fsa_authorization"], "NOT_GRANTED")
        self.assertFalse(receipt["experiment_started"])
        self.assertFalse(receipt["protected_first_use"])
        self.assertIn(receipt["current_fit_valid_winner"],
                      candidate.ARM_NAMES[:2])
        self.assertIn(receipt["history_fit_valid_winner"],
                      candidate.ARM_NAMES[2:])
        self.assertTrue(all(math.isfinite(s) for s in
                            receipt["validation_arm_nll"].values()))

    def test_explicit_only_handwritten_rows_refuse_role_or_private(self):
        cases = candidate.handwritten_examples()
        for fit, valid in (
            (cases[:2] + [cases[2]], cases[2:]),
            (cases[:2], cases[1:]),
            (cases[:2], [cases[2] + ({"latent": 0},)]),
            (cases[:1], cases[2:]),
            ([("HELD", cases[0][1], cases[0][2]), cases[1]],
             cases[2:]),
        ):
            with self.subTest(fit=len(fit), valid=len(valid)):
                with self.assertRaisesRegex(candidate.ComparatorBlocked,
                                            "NOT_EXACT_HANDWRITTEN_TOY"):
                    candidate.compare_toy_only(fit, valid)

    def test_frozen_source_blob_identity_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in candidate.SOURCE_BLOBS:
                (root / name).write_bytes((candidate.LEGACY / name).read_bytes())
            with patch.object(candidate, "LEGACY", root):
                candidate.source_guard()
                (root / "models.py").write_bytes(
                    (root / "models.py").read_bytes() + b"\n# tampered")
                with self.assertRaisesRegex(candidate.ComparatorBlocked,
                                            "QUALIFIED_MODEL_SOURCE_CHANGED"):
                    candidate.source_guard()

    def test_no_runtime_or_authority_entanglement(self):
        code = Path(candidate.__file__).read_text(encoding="utf-8")
        self.assertNotIn("workflow_dispatch", code)
        self.assertNotIn("github.com/", code)
        self.assertNotIn("CKB_Q21_AUTH_READ_TOKEN", code)
        self.assertNotIn(".generate(", code)
        self.assertNotIn("execute_development(", code)
        cases = candidate.handwritten_examples()
        self.assertTrue(all(len(row[2]) == 4 and len(row[1]) == 5
                            for row in cases))


if __name__ == "__main__":
    unittest.main()
