"""Fixed original-source lineage, local Git checkout, and fail-closed controls."""
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from f139.rsi_r3_source_cycle import R3Denied, TARGET, fingerprint, rehearsal
from f139.rsi_r3_disposable_tree import (MARKER, SCHEMA, git,
                                         stage_generations, staged_source)
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
