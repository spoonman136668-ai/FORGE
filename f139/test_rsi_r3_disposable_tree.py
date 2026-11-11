"""Fixed original-source lineage, local Git checkout, and fail-closed controls."""
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from f139.rsi_r3_source_cycle import (R3Denied, TARGET, fingerprint,
                                       generate, rehearsal, source_for)
from f139 import rsi_r3_disposable_tree as stage_module
from f139.rsi_r3_disposable_tree import (MARKER, END, SCHEMA, git,
                                         stage_generations, staged_selector,
                                         staged_source)
from f139.test_rsi_r3_source_cycle import G1, G2


@unittest.skipUnless(shutil.which("git"), "Requires existing Git")
class DisposableTreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forge-rsi-r3-test-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo = base / "repo"
        self.scratch = base / "scratch"
        self.repo.mkdir()
        self.scratch.mkdir()
        source = Path(__file__).with_name("rsi_r3_source_cycle.py").read_bytes()
        target = self.repo / TARGET
        target.parent.mkdir()
        target.write_bytes(source)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git(self.repo, "add", "--", TARGET)
        git(self.repo, "-c", "user.name=test", "-c", "user.email=test@invalid.local",
            "commit", "-q", "-m", "exact FORGE source")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        self.blob = fingerprint(source)
        self.generations = rehearsal(G1, G2)

    def stage(self, records=None, *, head=None, blob=None, scratch=None):
        return stage_generations(
            self.repo, self.scratch if scratch is None else scratch,
            self.generations if records is None else records,
            expected_head=self.sha if head is None else head,
            expected_target_sha256=self.blob if blob is None else blob)

    def test_two_actual_tracked_forgetree_edits_and_receipts(self):
        before = (self.repo / TARGET).read_bytes()
        a, b = self.stage()
        self.assertEqual([a.generation, b.generation], [1, 2])
        self.assertEqual(a.origin_head, self.sha)
        self.assertEqual(a.parent_head, self.sha)
        self.assertEqual(b.parent_head, a.staged_head)
        self.assertEqual(a.generated_source_sha256, self.generations[0].source_sha256)
        self.assertEqual(b.generated_source_sha256, self.generations[1].source_sha256)
        self.assertEqual(a.schema, SCHEMA)
        self.assertNotEqual(a.target_sha256, b.target_sha256)
        for receipt in (a, b):
            root = self.scratch / ("rsi-r3-g%d" % receipt.generation)
            self.assertEqual(git(root, "rev-parse", "HEAD"), receipt.staged_head)
            self.assertEqual(git(root, "remote"), "")
            actual = (root / TARGET).read_bytes()
            self.assertEqual(fingerprint(actual), receipt.target_sha256)
            self.assertEqual(actual.count(MARKER), 1)
            compile(actual, TARGET, "exec")
            self.assertEqual(git(root, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertEqual((self.repo / TARGET).read_bytes(), before)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.sha)

    def test_actual_staged_g1_selects_g2_from_verified_checkout_bytes(self):
        a, b = self.stage()
        g1_module = (self.scratch / "rsi-r3-g1" / TARGET).read_bytes()
        selected = staged_selector(g1_module)
        self.assertEqual(fingerprint(selected), a.generated_source_sha256)
        g2 = generate(parent_source=selected, generation=2, feedback=G2,
                      used_operators=frozenset({0, self.generations[0].operator}))
        self.assertEqual(g2, self.generations[1])
        self.assertEqual(g2.operator, 3)
        # Replaying G0 instead would select 2: the staged generation
        # contains the effective feedback-sensitive parent policy.
        other = generate(parent_source=source_for(0), generation=2,
                         feedback=G2, used_operators=frozenset({0, 1}))
        self.assertEqual(other.operator, 2)
        self.assertNotEqual(other.source_sha256, b.generated_source_sha256)

    def test_staged_selector_rejects_tampering_before_execution(self):
        self.stage()
        tracked = (self.scratch / "rsi-r3-g1" / TARGET).read_bytes()
        expected = self.generations[0].source
        self.assertEqual(staged_selector(tracked), expected)
        for corrupt in (tracked + b"UNTRUSTED_TRAILER",
                        tracked.replace(expected, b"import os\\n", 1),
                        tracked.replace(END, b"", 1),
                        tracked + MARKER):
            with self.subTest(corrupt=corrupt[-40:]), self.assertRaises(R3Denied):
                staged_selector(corrupt)

    def test_counterfeit_staged_g1_fails_before_g2_clone(self):
        original = stage_module.staged_source

        def counterfeit(before, generation):
            staged = original(before, generation)
            if generation.generation == 1:
                return staged.replace(generation.source, source_for(0), 1)
            return staged

        with patch.object(stage_module, "staged_source", side_effect=counterfeit):
            with self.assertRaisesRegex(R3Denied, "STAGED_PARENT_SOURCE_DRIFT"):
                self.stage()
        self.assertFalse((self.scratch / "rsi-r3-g2").exists())

    def test_original_dirty_source_preimage_and_scratch_rejected(self):
        for altered in [dict(head="0"*40), dict(blob="0"*64),
                        dict(scratch=self.repo)]:
            with self.subTest(altered=altered), self.assertRaises(R3Denied):
                self.stage(**altered)
        (self.repo / TARGET).write_bytes(b"# DRIFT\n")
        with self.assertRaises(R3Denied):
            self.stage()

    def test_corrupted_parent_lineage_rejected_before_clone(self):
        a, b = self.generations
        forged = replace(b, parent_sha256="f" * 64)
        with self.assertRaises(R3Denied):
            self.stage(records=(a, forged))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_generated_append_is_bounded_and_tampering_rejected(self):
        a, b = self.generations
        source = (self.repo / TARGET).read_bytes()
        with self.assertRaises(R3Denied):
            staged_source(source + MARKER + b"x" + b"evil trailer", b)
        out = staged_source(source, a)
        self.assertNotEqual(out, staged_source(out, b))
        self.assertEqual(staged_source(out, b).count(MARKER), 1)
        with self.assertRaises(R3Denied):
            staged_source(source + b"\n\n" + MARKER + MARKER, b)


if __name__ == "__main__":
    unittest.main()
