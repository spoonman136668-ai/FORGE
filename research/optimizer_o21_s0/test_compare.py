"""O21-S0 original-source-only guards; no original scientific trial."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from compare import (
    ACTIONS, CHAINS, DIAG_WORLDS, ORIGINAL_BLOB, ORIGINAL_TEST_BLOB,
    ConventionalExhaustiveTriple, canonical_checkout_git_blob, audit, load_original,
    SOURCE_LEARNER, SOURCE_TEST
)


class OriginalEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # github workflow passes one pinned external ORIGINAL source tree.
        import os
        cls.original_root=Path(os.environ["O21_PINNED_YGG"])
        cls.result=audit(cls.original_root)

    def test_original_source_and_test_blobs_exact(self):
        self.assertEqual(canonical_checkout_git_blob((self.original_root/SOURCE_LEARNER).read_bytes()),ORIGINAL_BLOB)
        self.assertEqual(canonical_checkout_git_blob((self.original_root/SOURCE_TEST).read_bytes()),ORIGINAL_TEST_BLOB)
        load_original(self.original_root)

    def test_training_source_and_role_separation(self):
        d=self.result
        self.assertEqual(d["public_training_rows"],2*3*192)
        self.assertEqual(d["diagnostic_worlds"],[7301,7302])
        self.assertEqual(d["original_external_environment_steps"],0)
        self.assertEqual(d["original_protected_cohorts_consumed"],0)
        self.assertFalse(d["science_go"])
        self.assertFalse(d["scientific_first_use"])

    def test_identical_native_vs_conventional_direct_and_composed_predictions(self):
        d=self.result
        self.assertEqual(d["direct_matched_predictions"],2*3*256)
        self.assertEqual(d["composed_matched_predictions"],2*16*len(CHAINS))
        self.assertEqual(d["direct_correct_native"],d["direct_correct_conventional"])
        self.assertEqual(d["disposition"],"O21_S0_NATIVE_EXHAUSTIVE_CONVENTIONAL_STRUCTURAL_EQUIVALENCE_NO_NOVELTY")

    def test_model_equality_bytes_and_valid_checkpoint(self):
        d=self.result
        self.assertGreater(d["model_canonical_bytes"],0)
        self.assertGreater(d["native_integrity_framed_checkpoint_bytes"],d["model_canonical_bytes"])
        self.assertEqual(len(bytes.fromhex(d["equal_model_sha256"])),32)
        self.assertTrue(d["zero_effect_tie_stress"])

    def test_independently_implemented_conventional_does_not_import_original_code(self):
        import inspect
        source=inspect.getsource(ConventionalExhaustiveTriple)
        self.assertNotIn("r7_pinned_native",source)
        self.assertNotIn("TRIPLES",source)
        self.assertNotIn("source_only_public_effect",source)
        self.assertEqual(len(ACTIONS),3)

    def test_mutated_original_model_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for source in (SOURCE_LEARNER,SOURCE_TEST):
                (root/source).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.original_root/source,root/source)
            target=root/SOURCE_LEARNER
            target.write_bytes(target.read_bytes()+b"\n# injected mutation\n")
            with self.assertRaisesRegex(ValueError,"IDENTITY_MISMATCH"):
                load_original(root)

    def test_mutated_original_test_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for source in (SOURCE_LEARNER,SOURCE_TEST):
                (root/source).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.original_root/source,root/source)
            target=root/SOURCE_TEST
            target.write_bytes(target.read_bytes()+b"\n# injected mutation\n")
            with self.assertRaisesRegex(ValueError,"IDENTITY_MISMATCH"):
                load_original(root)


if __name__=="__main__":
    unittest.main()
