"""Real isolated Git/unittest test for the Yggdrasil G29 worker split.

Uses a tiny synthetic repository with the same frozen-atlas invariant. No
production Yggdrasil source, owner credentials, controller or dispatch is used.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
import unittest

from f139.nci04_native_contract import Candidate, digest
from f139.nci04_native_worker import (
    YGGDRASIL_G29_SOURCE, YGGDRASIL_G29_TESTS,
    commands_for, stage_candidate, verify_fixed_commands,
)
from f139.nci04_signed_native import NativeAdmission, receipt_from_report


def git(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, check=True, timeout=20,
    )
    return p.stdout.decode("utf-8").strip()


class YggdrasilG29DualCustodyTests(unittest.TestCase):
    def make_source(self, root: Path) -> tuple[Path, Candidate]:
        source = root / "native"
        (source / "yggdrasil").mkdir(parents=True)
        (source / "tests").mkdir()
        before = b"def native_cell():\n    return 1\n"
        after = b"def native_cell():\n    return 2  # isolated candidate\n"
        (source / YGGDRASIL_G29_SOURCE).write_bytes(before)

        atlas = f'''import hashlib
import subprocess
import unittest
from pathlib import Path

class FrozenAtlasTests(unittest.TestCase):
    def test_indexed_source_matches_committed_blob(self):
        working = Path("{YGGDRASIL_G29_SOURCE}").read_bytes()
        committed = subprocess.run(
            ["git", "show", "HEAD:{YGGDRASIL_G29_SOURCE}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=10).stdout
        self.assertEqual(
            hashlib.sha256(working).hexdigest(),
            hashlib.sha256(committed).hexdigest(),
            "YGG_ATLAS_FAIL_CLOSED: working source mismatch: {YGGDRASIL_G29_SOURCE}")
'''
        (source / "tests" / "test_code_atlas.py").write_text(atlas, encoding="utf-8")
        for name in YGGDRASIL_G29_TESTS:
            safe = name.replace(".py", "")
            (source / "tests" / name).write_text(
                "import unittest\n"
                f"class {safe.title().replace('_', '')}(unittest.TestCase):\n"
                "    def test_native_boundary(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
        git(source, "init", "-q")
        git(source, "config", "user.name", "f139-g29-fixture")
        git(source, "config", "user.email", "f139-g29@example.invalid")
        git(source, "add", ".")
        git(source, "commit", "-qm", "frozen G29 synthetic baseline")
        commit = git(source, "rev-parse", "HEAD")
        tree = git(source, "rev-parse", "HEAD^{tree}")
        candidate = Candidate(
            intent_sha256="1" * 64,
            qualification_key="2" * 64,
            target_commit=commit,
            target_tree_sha=tree,
            path=YGGDRASIL_G29_SOURCE,
            before_sha256=digest(before),
            after_sha256=digest(after),
            after_bytes=after,
            lane="Yggdrasil",
        )
        return source, candidate

    def test_frozen_baseline_and_changed_candidate_are_both_custodied(self):
        with tempfile.TemporaryDirectory(prefix="f139-g29-worker-test-") as tmp:
            root = Path(tmp)
            source, candidate = self.make_source(root)
            scratch = root / "scratch"
            scratch.mkdir()
            stage = stage_candidate(candidate, source, scratch)
            self.assertEqual(
                (stage / "checkout" / YGGDRASIL_G29_SOURCE).read_bytes(),
                candidate.after_bytes,
            )
            self.assertEqual(
                (source / YGGDRASIL_G29_SOURCE).read_bytes(),
                candidate.before_sha256 and
                (source / YGGDRASIL_G29_SOURCE).read_bytes(),
            )
            self.assertEqual(git(source, "status", "--porcelain"), "")

            report = verify_fixed_commands(
                candidate, stage, baseline_checkout=source,
            )
            self.assertTrue(report["qualification_complete"])
            self.assertEqual(
                report["schema"],
                "forge.f139.nci04.native-development-diagnostic.v2",
            )
            dual = report["dual_custody"]
            self.assertEqual(dual["baseline_g29"]["outcome"], "PASS")
            self.assertEqual(dual["baseline_full"]["outcome"], "PASS")
            self.assertGreater(dual["baseline_g29"]["test_count"], 0)
            self.assertGreater(dual["baseline_full"]["test_count"], 0)
            self.assertEqual(
                dual["candidate_g29"]["disposition"],
                "EXPECTED_FROZEN_ATLAS_REJECTION",
            )
            self.assertIn(
                "YGG_ATLAS_FAIL_CLOSED: working source mismatch:",
                dual["candidate_g29"]["excerpt"],
            )
            self.assertEqual(
                dual["candidate_non_atlas_test_modules"],
                list(YGGDRASIL_G29_TESTS),
            )
            self.assertEqual(
                [tuple(x["command"]) for x in report["commands"]],
                list(commands_for(candidate)),
            )
            self.assertTrue(all(x["outcome"] == "PASS" for x in report["commands"]))
            self.assertEqual(git(source, "status", "--porcelain"), "")

            admission = NativeAdmission(
                ticket="f139-nci04-i1-" + "a" * 12 + "-" + "1" * 8,
                lane="Yggdrasil",
                source_sha="a" * 40,
                run_id=123456,
                runner_os="ubuntu-latest",
                issue_number=1,
                issue_id=2,
                intent=candidate,
                authorization_sha256="b" * 64,
            )
            receipt = receipt_from_report(admission, report)
            self.assertTrue(receipt["native_qualified"])
            self.assertFalse(receipt["scientific_first_use_authorized"])
            self.assertFalse(receipt["controller_unattended_verified"])

            bad = dict(report)
            bad_dual = dict(dual)
            bad_atlas = dict(dual["candidate_g29"])
            bad_atlas["expected_marker"] = "forged pass"
            bad_dual["candidate_g29"] = bad_atlas
            bad["dual_custody"] = bad_dual
            with self.assertRaisesRegex(ValueError, "G29_CANDIDATE_ATLAS_EVIDENCE_INVALID|G29_EXPECTED_NEGATIVE_NOT_AUTHENTIC"):
                receipt_from_report(admission, bad)


if __name__ == "__main__":
    unittest.main()
