"""Source-authenticated G1/G2 disposable tree regression for the RSI-R3 growth seam."""
from dataclasses import replace
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139 import rsi_r3_growth_staging as staging
from f139.rsi_r3_disposable_tree import END, MARKER, git
from f139.rsi_r3_source_cycle import R3Denied, _operator_for
from f139.rsi_r3_source_grammar_growth import (
    ORIGINAL_BLOB, TARGET, git_blob, propose,
)

ROOT = Path(__file__).resolve().parents[1]


def pinned_source() -> bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", "HEAD:" + TARGET],
        capture_output=True, check=True, timeout=30)
    return result.stdout


BASE = pinned_source()


class StagedGrowthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forge-rsi-r3-growth-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo, self.scratch = root / "original", root / "scratch"
        self.repo.mkdir()
        self.scratch.mkdir()
        target = self.repo / TARGET
        target.parent.mkdir(parents=True)
        self.assertEqual(git_blob(BASE), ORIGINAL_BLOB)
        target.write_bytes(BASE)
        subprocess.run(["git", "init", "-q", str(self.repo)],
                       check=True, capture_output=True, timeout=30)
        git(self.repo, "config", "core.autocrlf", "false")
        git(self.repo, "add", "--", TARGET)
        git(self.repo, "-c", "user.name=FORGE-RSI-R3-TEST",
            "-c", "user.email=forge-rsi-r3-test@invalid.local",
            "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "frozen preimage")
        self.head = git(self.repo, "rev-parse", "HEAD")
        self.record = propose(original=BASE, consumed=frozenset())

    def stage(self, **changes):
        params = {"expected_head": self.head, "growth": self.record}
        params.update(changes)
        return staging.stage_growth(self.repo, self.scratch, **params)

    def test_two_git_tracked_source_generations_and_actual_g1_selection(self):
        a, b = self.stage()
        self.assertEqual((a.generation, b.generation), (1, 2))
        self.assertEqual(a.parent_head, self.head)
        self.assertEqual(b.parent_head, a.staged_head)
        self.assertEqual(a.origin_head, self.head)
        self.assertEqual(b.origin_head, self.head)
        self.assertNotEqual(a.staged_head, b.staged_head)
        self.assertNotEqual(a.module_sha256, b.module_sha256)
        self.assertNotEqual(a.selector_sha256, b.selector_sha256)
        for stage in (a, b):
            clone = self.scratch / ("rsi-r3-growth-g%d" % stage.generation)
            self.assertEqual(git(clone, "rev-parse", "HEAD"), stage.staged_head)
            self.assertEqual(git(clone, "remote"), "")
            self.assertEqual(git(clone, "status", "--porcelain",
                                 "--untracked-files=all"), "")
            self.assertEqual(git(clone, "diff-tree", "--no-commit-id",
                                 "--name-only", "-r", "HEAD"), TARGET)
            module = staging.git_bytes(clone, "show", "HEAD:" + TARGET)
            self.assertEqual(staging.digest(module), stage.module_sha256)
            core, selector = staging.source_parts(module)
            self.assertEqual(core, self.record.source)
            self.assertEqual(staging.digest(selector), stage.selector_sha256)
            compile(module, TARGET, "exec")
            self.assertFalse(stage.autonomous_rsi_proven)
            self.assertFalse(stage.original_owner_admitted)
            self.assertFalse(stage.scientific_first_use)
            self.assertFalse(stage.deployment_authorized)
        g2_module = staging.git_bytes(
            self.scratch / "rsi-r3-growth-g2", "show", "HEAD:" + TARGET)
        _, g2_selector = staging.source_parts(g2_module)
        with self.assertRaises(R3Denied):
            _operator_for(g2_selector)  # The original four-operator grammar.
        permitted = {"__builtins__": {"max": max, "min": min}}
        exec(compile(g2_selector, "<reviewed-g2>", "exec"), permitted)
        self.assertEqual(permitted["rank"]((10, 1, 8, 5)), 14)
        self.assertEqual(permitted["rank"]((10, 1, 5, 8)), 14)
        self.assertEqual(staging.git_bytes(self.repo, "show", "HEAD:" + TARGET), BASE)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.head)
        self.assertEqual(git(self.repo, "status", "--porcelain",
                             "--untracked-files=all"), "")

    def test_pinned_source_and_untrusted_record_denied_before_cloning(self):
        for wrong in (
            replace(self.record, source=self.record.source + b"\n"),
            replace(self.record, autonomous_rsi_proven=True),
            replace(self.record, after_sha256="0" * 64),
            replace(self.record, original_owner_admitted=True),
        ):
            with self.subTest(wrong=wrong), self.assertRaises(
                    staging.GrowthStagingDenied):
                self.stage(growth=wrong)
            self.assertEqual(tuple(self.scratch.iterdir()), ())
        with self.assertRaises(staging.GrowthStagingDenied):
            self.stage(expected_head="0" * 40)
        self.assertEqual(tuple(self.scratch.iterdir()), ())

    def test_dirty_original_and_existing_scratch_rejected(self):
        (self.repo / TARGET).write_bytes(BASE + b"\n# dirty\n")
        with self.assertRaises(staging.GrowthStagingDenied):
            self.stage()
        self.assertEqual(tuple(self.scratch.iterdir()), ())
        (self.repo / TARGET).write_bytes(BASE)
        (self.scratch / "unrelated").write_bytes(b"existing")
        with self.assertRaises(staging.GrowthStagingDenied):
            self.stage()
        self.assertEqual((self.scratch / "unrelated").read_bytes(), b"existing")

    def test_counterfeit_committed_g1_is_rejected_before_g2_clone(self):
        original = staging.git_bytes

        def counterfeit(repo, *args):
            raw = original(repo, *args)
            if (repo.name == "rsi-r3-growth-g1" and
                    args == ("show", "HEAD:" + TARGET)):
                return raw.replace(b"min(row[2], row[3])", b"eval(row)", 1)
            return raw

        with patch.object(staging, "git_bytes", side_effect=counterfeit):
            with self.assertRaisesRegex(staging.GrowthStagingDenied,
                                        "STAGED_COMMITTED_BYTES_DRIFT"):
                self.stage()
        self.assertFalse((self.scratch / "rsi-r3-growth-g2").exists())
        self.assertEqual(git(self.repo, "status", "--porcelain",
                             "--untracked-files=all"), "")

    def test_marker_and_generated_source_injection_fail_closed(self):
        env = {"__name__": "__main__"}
        exec(compile(self.record.source, TARGET, "exec"), env)
        good = env["source_for"](4)
        module = staging.render(self.record.source, good)
        self.assertEqual(staging.source_parts(module), (self.record.source, good))
        for bad in (module + b"untrusted trailer",
                    module + MARKER, module[:-len(END)],
                    module.replace(MARKER, MARKER + MARKER, 1)):
            with self.subTest(bad=bad[-30:]), self.assertRaises(
                    staging.GrowthStagingDenied):
                staging.source_parts(bad)
        for bad in (good + MARKER, good + END, b""):
            with self.subTest(bad=bad), self.assertRaises(
                    staging.GrowthStagingDenied):
                staging.render(self.record.source, bad)


if __name__ == "__main__":
    unittest.main()
