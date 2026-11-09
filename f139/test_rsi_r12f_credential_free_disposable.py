"""Real local Git source staging plus denial of untrusted R12-F authority."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139.rsi_r12b_signed_job import prepare
from f139.rsi_r12f_credential_free_disposable import (
    DisposableWorkerDenied, RECEIPT_NAME, STAGE_DIR, rehearse,
)
from f139.test_rsi_r12b_signed_job import synthetic_binding
from f139.test_rsi_r12_candidate_binding import BEFORE, CANDIDATE_SOURCE


def command(*args):
    result = subprocess.run(
        ["git", *map(str, args)], capture_output=True,
        text=True, check=False, timeout=20,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class CredentialFreeDisposableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.scratch = self.base / "scratch"
        self.repo.mkdir()
        self.scratch.mkdir()
        command("-C", self.repo, "init", "-q")
        source = self.repo / "f139" / "diagnostic.py"
        source.parent.mkdir()
        source.write_bytes(BEFORE)
        command("-C", self.repo, "add", "f139/diagnostic.py")
        command("-C", self.repo,
                "-c", "user.name=FORGE-R12F-TEST",
                "-c", "user.email=r12f@invalid.local",
                "-c", "core.hooksPath=/dev/null",
                "commit", "-q", "-m", "frozen test source")
        self.head = command("-C", self.repo, "rev-parse", "HEAD")
        self.tree = command("-C", self.repo, "rev-parse", "HEAD^{tree}")
        self.binding, _ = synthetic_binding()
        self.intent = prepare(
            binding=self.binding, source_sha=self.head,
            source_tree_sha=self.tree,
            worker_run_id=42570000000,
            worker_job_id=128999999999, runner_os="windows-latest")
        self.kw = dict(repo=self.repo, scratch=self.scratch,
                       binding=self.binding, intent=self.intent,
                       candidate_source=CANDIDATE_SOURCE)

    def test_real_git_disposable_staging_and_terminal_receipt(self):
        proof = rehearse(**self.kw)
        self.assertEqual(proof["protected_source_sha"], self.head)
        self.assertEqual(proof["protected_source_tree_sha"], self.tree)
        self.assertEqual(proof["candidate_sha256"],
                         sha256(CANDIDATE_SOURCE).hexdigest())
        self.assertTrue(proof["disposable_clone_only"])
        self.assertTrue(proof["python_syntax_qualified"])
        self.assertFalse(proof["full_regression_qualified"])
        for key in ("original_owner_issued", "original_owner_admitted",
                    "credentialed_original_signature_verified",
                    "credential_free_worker_admitted", "worker_dispatched",
                    "source_promoted", "scientific_first_use",
                    "autonomous_rsi_proven"):
            self.assertFalse(proof[key])
        self.assertEqual((self.repo / "f139" / "diagnostic.py").read_bytes(),
                         BEFORE)
        self.assertEqual((self.scratch / STAGE_DIR / "f139" /
                          "diagnostic.py").read_bytes(), CANDIDATE_SOURCE)
        self.assertEqual(command("-C", self.repo, "rev-parse", "HEAD"), self.head)
        self.assertEqual(command("-C", self.repo, "status", "--porcelain"), "")
        self.assertEqual(json.loads(
            (self.scratch / RECEIPT_NAME).read_text("ascii")), proof)
        # An identical attempted replay cannot overwrite staging or receipt.
        with self.assertRaises(DisposableWorkerDenied):
            rehearse(**self.kw)

    def test_credentials_and_authority_upgrade_rejected(self):
        for name in ("GH_TOKEN", "F139_WORKER_HMAC_KEY",
                     "GITHUB_TOKEN", "OPENAI_API_KEY"):
            with self.subTest(name=name):
                with patch.dict(os.environ, {name: "untrusted"}):
                    with self.assertRaisesRegex(
                            DisposableWorkerDenied, "CREDENTIAL_INHERITANCE"):
                        rehearse(**self.kw)
        for key in ("worker_admitted", "worker_dispatched",
                    "source_promoted", "scientific_first_use",
                    "autonomous_rsi_proven"):
            with self.subTest(key=key):
                bad = {**self.intent, key: True}
                with self.assertRaises(Exception):
                    rehearse(**{**self.kw, "intent": bad})

    def test_rejects_forged_candidate_and_untrusted_source(self):
        cases = [
            {"candidate_source": b"import os\n"},
            {"candidate_source": b"this isn't python\n"},
            {"candidate_source": b"\xff\xfe"},
            {"candidate_source": b""},
            {"candidate_source": BEFORE},
            {"intent": {**self.intent, "target_path": "../../escape.py"}},
            {"intent": {**self.intent, "source_tree_sha": "f" * 40}},
            {"intent": {**self.intent, "candidate_sha256": "f" * 64}},
            {"intent": {**self.intent, "original_ledger_head_sha256": "f" * 64}},
        ]
        for update in cases:
            with self.subTest(update=update):
                with self.assertRaises(Exception):
                    rehearse(**{**self.kw, **update})
                self.assertFalse(any(self.scratch.iterdir()))

    def test_source_drift_dirty_tree_and_root_overlap_denied(self):
        dirty = self.repo / "untracked.txt"
        dirty.write_text("dirty", encoding="ascii")
        with self.assertRaisesRegex(DisposableWorkerDenied, "CLEAN_TREE_DRIFT"):
            rehearse(**self.kw)
        dirty.unlink()
        source = self.repo / "f139" / "diagnostic.py"
        source.write_bytes(b"import sys\n")
        with self.assertRaises(Exception):
            rehearse(**self.kw)
        source.write_bytes(BEFORE)
        with self.assertRaises(Exception):
            rehearse(**{**self.kw, "scratch": self.repo})
        with self.assertRaises(Exception):
            rehearse(**{**self.kw, "scratch": self.base / "missing"})

    def test_original_worker_lanes_stay_closed(self):
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self", OWNER)
        self.assertNotIn("FORGE-self", WORKER)


if __name__ == "__main__":
    unittest.main()
