"""Negative and cold-signature controls for the existing-task V1 recovery path."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_fresh_owner_source_forward import FIELDS, SCHEMA, sign
from f139.nci04_native_contract import canonical
from f139.nci04_v2_failed_prepare_restore_original import (
    CHECKPOINT_HASH, CHECKPOINT_SEQ, ORIGINAL, ORIGINAL_TREE,
    RestoreDenied, validate,
)


class RecoveryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.key = "read-only-test-owner-key-with-long-length-123456"
        self.db = object.__new__(Database)
        self.db.filename = self.folder / "state.sqlite"
        self.db.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.db.conn.close)
        self.db.conn.row_factory = sqlite3.Row
        self.db.conn.execute("CREATE TABLE events (seq INTEGER, kind TEXT, sha TEXT)")
        self.db.conn.execute("CREATE TABLE tasks (ticket TEXT, stage TEXT)")
        self.db.conn.executemany(
            "INSERT INTO events VALUES (?,?,?)", [
                (9, "FRESH_WORKER_PROVIDER_CUSTODY", "a" * 64),
                (23, "FRESH_WORKER_PROVIDER_CUSTODY", CHECKPOINT_HASH),
            ])
        self.db.conn.executemany("INSERT INTO tasks VALUES (?,?)", [
            ("a", "VERIFIED"), ("b", "VERIFIED"), ("c", "VERIFIED")])
        self.db.meta = lambda: {
            "head_seq": CHECKPOINT_SEQ, "head_hash": CHECKPOINT_HASH}
        self.release = {
            "admission_source_sha": "b" * 40,
            "worker_release_sha": "c" * 40,
            "worker_release_tree": "d" * 40,
        }
        doc = {key: 1 for key in FIELDS - {"owner_signature"}}
        doc.update({
            "schema": SCHEMA, "pr_number": 1865,
            "owner_source_sha": ORIGINAL, "owner_source_tree": ORIGINAL_TREE,
            "task_name": "FORGE-F139-UnifiedController",
            "terminal_seq": 9, "terminal_hash": "a" * 64,
            "admission_source_sha": self.release["admission_source_sha"],
            "worker_release_sha": self.release["worker_release_sha"],
            "worker_release_tree": self.release["worker_release_tree"],
            "development_only": True, "worker_release_unchanged": True,
            "scientific_first_use": False, "paid_model_calls": 0,
        })
        self.doc = dict(doc, owner_signature=sign(doc, self.key))
        (self.folder / "fresh-original-owner-source-forward.json").write_bytes(
            canonical(self.doc))
        self.entries = [
            {"stage": "VERIFIED", "negative": None, "custody": {"present": True}}
            for _ in range(3)]

    def _audit(self, seq=CHECKPOINT_SEQ, head=CHECKPOINT_HASH):
        with patch.object(SingleOwner, "held", return_value=True), patch(
                "f139.nci04_v2_failed_prepare_restore_original.read_lifecycle",
                return_value=(self.release, self.entries)):
            return validate(self.db, self.key, self.folder, seq, head)

    def test_cold_original_history_and_signature(self):
        report = self._audit()
        self.assertEqual(report["verified_tasks"], 3)
        self.assertEqual(report["original_source_sha"], ORIGINAL)
        self.assertEqual(report["sqlite_mutations"], 0)
        self.assertFalse(report["scientific_first_use"])

    def test_moved_checkpoint_is_denied(self):
        for seq, head in ((24, CHECKPOINT_HASH), (23, "0" * 64)):
            with self.subTest(seq=seq, head=head):
                with self.assertRaisesRegex(
                        RestoreDenied, "FAILED_PREPARE_CHECKPOINT_REQUIRED"):
                    self._audit(seq, head)

    def test_v2_certificate_collision_is_denied(self):
        (self.folder / "fresh-original-owner-source-forward-v2.json").write_bytes(
            b"{}")
        with self.assertRaisesRegex(
                RestoreDenied, "V1_SIGNED_CERT_REQUIRED_V2_MUST_BE_ABSENT"):
            self._audit()

    def test_missing_v1_certificate_is_denied(self):
        (self.folder / "fresh-original-owner-source-forward.json").unlink()
        with self.assertRaisesRegex(
                RestoreDenied, "V1_SIGNED_CERT_REQUIRED_V2_MUST_BE_ABSENT"):
            self._audit()

    def test_wrong_hmac_is_denied(self):
        bad = dict(self.doc, owner_signature="0" * 64)
        (self.folder / "fresh-original-owner-source-forward.json").write_bytes(
            canonical(bad))
        with self.assertRaisesRegex(
                RestoreDenied, "ORIGINAL_V1_OWNER_SIGNATURE_DRIFT"):
            self._audit()

    def test_unfinished_task_is_denied(self):
        self.db.conn.execute(
            "UPDATE tasks SET stage='READY' WHERE ticket='c'")
        with self.assertRaisesRegex(
                RestoreDenied, "OWNER_HAS_UNSETTLED_WORK"):
            self._audit()

    def test_signed_negative_is_denied(self):
        self.entries[-1]["negative"] = {"reason": "uncertain"}
        with self.assertRaisesRegex(
                RestoreDenied, "SIGNED_COLD_LIFECYCLE_OR_SOURCE_DRIFT"):
            self._audit()

    def test_unlocked_owner_is_denied(self):
        with patch.object(SingleOwner, "held", return_value=False):
            with self.assertRaisesRegex(
                    RestoreDenied, "ORIGINAL_SINGLE_OWNER_LOCK_REQUIRED"):
                validate(self.db, self.key, self.folder,
                         CHECKPOINT_SEQ, CHECKPOINT_HASH)

    def test_scoped_owner_only_workflow_and_order(self):
        repo = Path(__file__).resolve().parent.parent
        workflow = (repo / ".github/workflows/"
                    "f139-v2-failed-prepare-original-restore.yml").read_text()
        script = (repo / "f139/"
                  "nci04_v2_failed_prepare_restore_original.ps1").read_text()
        for needle in (
            "issue_comment:", "github.actor == 'spoonman136668-ai'",
            "github.event.comment.author_association == 'OWNER'",
            "github.event.issue.number == 1830",
            "forge-f139-fresh-existing-disabled-task-rebind",
            "runs-on: [self-hosted, Windows, forge-codex-isolated]",
        ):
            self.assertIn(needle, workflow)
        self.assertNotIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("push:", workflow)
        for needle in ("$failed=45091947666L", "$audit=45092273168L",
                       "COLD_SIGNED_V1_CUSTODY_REJECTED",
                       "Enable-ScheduledTask", "Start-ScheduledTask"):
            self.assertIn(needle, script)
        self.assertLess(script.index("COLD_SIGNED_V1_CUSTODY_REJECTED"),
                        script.index("Enable-ScheduledTask"))
        self.assertLess(script.index("EXACT_DISABLED_ORIGINAL_OWNER_REQUIRED"),
                        script.index("Enable-ScheduledTask"))
        self.assertEqual(script.count("Enable-ScheduledTask"), 1)
        self.assertEqual(script.count("Start-ScheduledTask"), 1)
        self.assertNotIn("Register-ScheduledTask", script)
        self.assertNotIn("Set-ScheduledTask", script)
        self.assertNotIn("Invoke-RestMethod", script)

        self.assertNotIn("/jobs?per_page=100", script)
        self.assertIn("FAILED_PREPARE_IDENTITY_NOT_VERIFIED", script)
        self.assertIn("ORIGINAL_OWNER_AUDIT_PROVENANCE", script)
        self.assertIn("ab87431e8718eec1e160b0bfbd077ee6550a3844", script)

        self.assertNotIn("ConvertFrom-Json -Depth", script)
        if os.name == "nt":
            power = shutil.which("powershell.exe")
            self.assertIsNotNone(power)
            verifier = self.folder / "parse-v2-restore.ps1"
            verifier.write_text(
                "param([string]$Source)\n"
                "$tokens=$null;$errors=$null\n"
                "[System.Management.Automation.Language.Parser]::ParseFile("
                "$Source,[ref]$tokens,[ref]$errors)|Out-Null\n"
                "if($errors.Count -ne 0){$errors|Out-String|Write-Error;exit 1}\n",
                encoding="utf-8")
            check = subprocess.run(
                [power, "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-File", str(verifier),
                 "-Source", str(repo / "f139" /
                                "nci04_v2_failed_prepare_restore_original.ps1")],
                capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_scoped_pr_admission_negative_controls(self):
        from scripts.check_rar_g145_pr_scope import (
            F139_V2_RESTORE_BASE, F139_V2_RESTORE_BASE_TREE,
            F139_V2_RESTORE_BLOBS, F139_V2_RESTORE_BRANCH,
            F139_V2_RESTORE_PATHS, F139_V2_RESTORE_PR,
            F139_V2_RESTORE_RESULT, admit_f139_v2_failed_restore,
            generic_paths_safe,
        )
        head = "3" * 40
        base = F139_V2_RESTORE_BASE
        self.assertEqual(F139_V2_RESTORE_PR, 1870)
        self.assertEqual(len(F139_V2_RESTORE_PATHS), 7)
        self.assertFalse(generic_paths_safe([
            ".github/workflows/f139-v2-failed-prepare-original-restore.yml"]))
        request = {
            "number": 1870,
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": head, "ref": F139_V2_RESTORE_BRANCH,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "base": {"sha": base, "ref": "main",
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
        }
        def git(*args):
            if args == ("merge-base", base, head):
                return base
            if args == ("rev-parse", base + "^{tree}"):
                return F139_V2_RESTORE_BASE_TREE
            if args[:1] == ("rev-parse",) and len(args) == 2:
                key = args[1]
                for path, sha in F139_V2_RESTORE_BLOBS.items():
                    if key == head + ":" + path:
                        return sha
            if args == ("diff", "--no-renames", "--name-only", base, head):
                return "\n".join(sorted(F139_V2_RESTORE_PATHS)) + "\n"
            raise AssertionError("Unscoped Git test route")
        self.assertEqual(admit_f139_v2_failed_restore(head, base, request, git),
                         F139_V2_RESTORE_RESULT)
        for bad_request in (
            dict(request, number=1869),
            dict(request, author_association="CONTRIBUTOR"),
            dict(request, user={"login": "other"}),
            dict(request, head=dict(request["head"], ref="other")),
            dict(request, base=dict(request["base"], sha="0" * 40)),
        ):
            with self.subTest(request=bad_request):
                with self.assertRaises(ValueError):
                    admit_f139_v2_failed_restore(head, base, bad_request, git)
        def wrong_git(*args):
            if args == ("rev-parse", head +
                        ":.github/workflows/f139-v2-failed-prepare-original-restore.yml"):
                return "0" * 40
            return git(*args)
        with self.assertRaisesRegex(ValueError, "BLOBS_OR_SCOPE_DRIFT"):
            admit_f139_v2_failed_restore(head, base, request, wrong_git)




if __name__ == "__main__":
    unittest.main()
