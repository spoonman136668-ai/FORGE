"""Source-only FORGE-self admission negations, never installed-owner tests."""
from dataclasses import replace
from pathlib import Path
import unittest

from f139.rsi_r3_forge_self_contract import (
    FROZEN_PARENT_COMMIT, FROZEN_PARENT_TREE, OPERATOR,
    REQUIRED_QUALIFICATION, SelfContractDenied, TARGET, TARGET_BLOB,
    digest, git_blob, propose, rewrite, verify,
)

BEFORE = (Path(__file__).resolve().parents[1] / TARGET).read_bytes()


def candidate(**kwargs):
    args = dict(original_source=BEFORE, pinned_commit=FROZEN_PARENT_COMMIT,
                pinned_tree=FROZEN_PARENT_TREE, path=TARGET, operator=OPERATOR,
                consumed_source_hashes=frozenset())
    return propose(**{**args, **kwargs})


class ForgeSelfContractTests(unittest.TestCase):
    def test_real_forge_target_and_source_candidate(self):
        self.assertEqual(git_blob(BEFORE), TARGET_BLOB)
        p = candidate()
        self.assertTrue(verify(p, BEFORE, frozenset()))
        self.assertNotEqual(p.after_sha256, p.before_sha256)
        self.assertEqual(p.after_sha256, digest(p.after))
        self.assertNotEqual(p.after, BEFORE)
        self.assertIn(b"new_ast = (old_ast if candidate.after == before", p.after)
        self.assertEqual(p.qualification_commands, REQUIRED_QUALIFICATION)
        self.assertFalse(p.eligible_for_owner)
        self.assertFalse(p.scientific_first_use)
        self.assertFalse(p.deployment_authorized)
        self.assertFalse(p.rsi_proven)
        self.assertNotIn("shell", str(REQUIRED_QUALIFICATION).lower())

    def test_untrusted_source_parent_and_path_reject(self):
        for changes in (dict(original_source=BEFORE + b"# dirty\n"),
                        dict(pinned_commit="0" * 40),
                        dict(pinned_tree="0" * 40),
                        dict(path="../f139/local_controller.py"),
                        dict(path="f139/local_controller.py"),
                        dict(operator="execute_code")):
            with self.subTest(changes=changes), self.assertRaises(SelfContractDenied):
                candidate(**changes)

    def test_consumed_and_duplicate_source_fail_closed(self):
        p = candidate()
        with self.assertRaisesRegex(SelfContractDenied, "CONSUMED_SOURCE_NO_REPLAY"):
            candidate(consumed_source_hashes=frozenset({p.after_sha256}))
        for invalid in (None, [], {"bad"}, frozenset({"wrong"})):
            with self.subTest(invalid=invalid), self.assertRaises(SelfContractDenied):
                candidate(consumed_source_hashes=invalid)

    def test_modified_receipts_deny_all_authority_and_metadata_drift(self):
        p = candidate()
        for mutated in (replace(p, after=p.after+b"\n"),
                        replace(p, before_blob="0"*40),
                        replace(p, provenance_sha256="0"*64),
                        replace(p, qualification_commands=()),
                        replace(p, eligible_for_owner=True),
                        replace(p, scientific_first_use=True),
                        replace(p, deployment_authorized=True),
                        replace(p, rsi_proven=True)):
            with self.subTest(mutated=mutated), self.assertRaises(SelfContractDenied):
                verify(mutated, BEFORE, frozenset())

    def test_original_maintained_source_is_unchanged(self):
        before = bytes(BEFORE)
        for _ in range(2):
            self.assertEqual(candidate().after, rewrite(BEFORE, OPERATOR))
        self.assertEqual(before, BEFORE)
        self.assertEqual(git_blob(BEFORE), TARGET_BLOB)


if __name__ == "__main__":
    unittest.main()
