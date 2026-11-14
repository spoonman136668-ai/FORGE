"""V41 safe-abort approval and complete-readonly-preimage negative controls.

This never operates the original Windows controller. Owner comments, provider
identity and sealed backup are simulated. SQLite queries and table-content
hashes run on disposable real SQLite, with 1829 historic replay mocked.
"""
from contextlib import closing
import copy
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock

from f139 import nci04_v41_hybrid_safe_abort as abort
from f139 import nci04_v41_hybrid_successor_release as release
from f139 import nci04_v41_hybrid_pair_owner as paired
from f139 import nci04_v41_hybrid_source_transition as source
from f139 import nci04_v41_hybrid_cold_bundle as cold
from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import digest, canonical
from f139 import test_nci04_v41_hybrid_successor_release as fixture_remote
from f139 import test_nci04_v41_hybrid_source_transition as fixture_sql

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "f139" / "v41_hybrid_original_safe_abort.ps1"
TARGET = fixture_remote.TARGET
RUN_ID = 987654
APPROVAL_ID = 112
ABORT_ID = 114
MANIFEST = fixture_remote.BACKUP_SHA
BASE_HEAD = source.ACTIVATED_HASH


def request():
    return {
        "target_source_sha": TARGET,
        "hold_approval_comment_id": APPROVAL_ID,
        "backup_request_comment_id": 111,
        "abort_owner_comment_id": ABORT_ID,
        "backup_run_id": RUN_ID,
        "backup_manifest_sha256": MANIFEST,
        "original_head_seq": source.ACTIVATED_SEQ,
        "original_head_sha256": BASE_HEAD,
        "safe_abort_requested": True,
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
    }


def new_event():
    e = fixture_remote.event()
    text = (abort.PREFIX + " ".join([
        TARGET, str(APPROVAL_ID), str(RUN_ID), MANIFEST,
        str(source.ACTIVATED_SEQ), BASE_HEAD]))
    e["comment"] = {
        "id": ABORT_ID, "body": text,
        "user": {"login": release.OWNER},
        "author_association": "OWNER",
        "created_at": "2026-11-14T16:00:00Z",
    }
    return e


class OriginalOwnerSafeAbortApprovalTests(unittest.TestCase):
    def setUp(self):
        self.remote = fixture_remote.Provider()
        event = new_event()
        self.event = event
        self.env = fixture_remote.env()
        self.remote.entries[
            fixture_remote.PREFIX+"issues/comments/"+str(ABORT_ID)] = {
                **event["comment"],
                "issue_url": "https://api.github.com/repos/" +
                             release.REPO + "/issues/807",
                "updated_at": event["comment"]["created_at"],
            }

    def auth(self, env=None, event=None):
        return abort.authenticate_abort(
            self.env if env is None else env,
            self.event if event is None else event, self.remote)

    def test_exact_distinct_new_owner_abort_and_old_hold_chain(self):
        permit = self.auth()
        self.assertEqual(permit, request())
        self.assertTrue(permit["safe_abort_requested"])
        self.assertFalse(permit["source_transition_authorized"])
        self.assertEqual(self.remote.calls.count(
            fixture_remote.PREFIX+"issues/comments/"+str(ABORT_ID)), 2)

    def test_pause_resume_readiness_or_source_commit_not_abort(self):
        for body in (
            fixture_remote.event()["comment"]["body"],
            paired.PREFIX + TARGET + " 111",
            "F139-HYBRID-V41-SOURCE-COMMIT " + TARGET,
        ):
            with self.subTest(body=body), self.assertRaises(
                    abort.SafeAbortDenied):
                self.auth(event={
                    **self.event, "comment": {**self.event["comment"],
                                               "body": body}})

    def test_wrong_original_runner_run_attempt_or_paid_api_denied(self):
        for key, bad in (
            ("GITHUB_SHA", "f"*40),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_ACTOR", "different"),
            ("RUNNER_NAME", "hosted"),
            ("OPENAI_API_KEY", "paid-key"),
            ("GITHUB_RUN_ID", str(RUN_ID)),
        ):
            with self.subTest(key=key), self.assertRaises(
                    abort.SafeAbortDenied):
                self.auth(env={**self.env, key: bad})

    def test_edited_approval_wrong_order_and_foreign_hold_denied(self):
        id = fixture_remote.PREFIX+"issues/comments/112"
        original = copy.deepcopy(self.remote.entries[id])
        for key, value in (
            ("body", paired.PREFIX+TARGET+" 111"),
            ("updated_at", "2026-11-14T16:12:00Z"),
            ("created_at", "2026-11-15T01:00:00Z"),
            ("author_association", "CONTRIBUTOR"),
        ):
            with self.subTest(key=key):
                self.remote.entries[id][key] = value
                try:
                    with self.assertRaises((abort.SafeAbortDenied,
                                            release.HybridSuccessorDenied)):
                        self.auth()
                finally:
                    self.remote.entries[id] = copy.deepcopy(original)

    def test_old_owner_backup_or_approval_comment_cannot_be_edited(self):
        key = fixture_remote.PREFIX+"issues/comments/111"
        self.remote.entries[key]["updated_at"] = "2026-11-14T16:23:00Z"
        with self.assertRaisesRegex(
                abort.SafeAbortDenied, "BACKUP_REQUEST_EDITED"):
            self.auth()


class OriginalOwnerAbortSqliteTests(unittest.TestCase):
    def setUp(self):
        case = fixture_sql.HybridSyntheticSqlTransactionTests(
            "test_atomic_source_commit_keeps_history_and_new_dispatches_zero")
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.case = case
        self.bundle = case.simulated_external_qualification()
        self.whole = digest(canonical(cold.rollback_view(case.db.conn)))
        self.bundle.return_value["logical_all_tables_sha256"] = self.whole
        self.req = {**request(),
                    "target_source_sha": case.target,
                    "backup_run_id": 800001,
                    "backup_manifest_sha256": "5"*64}

    def inspect(self):
        with closing(Database.open_readonly(self.case.file)) as readonly:
            return abort.inspect_precommit(readonly, self.req)

    def test_unchanged_original_entire_sqlite_and_sealed_restore(self):
        f = self.case
        before = f.state()
        with SingleOwner(f.file.with_suffix(".lock")):
            proof = self.inspect()
            self.assertEqual(f.state(), before)
            self.assertTrue(proof["frozen_precommit_unchanged"])
            self.assertTrue(proof["complete_detached_restore_verified"])
            self.assertTrue(
                proof["eligible_for_separately_approved_same_original_task_abort"])
            self.assertFalse(proof["source_transition_authorized"])
            self.assertFalse(proof["hybrid_admission"])
            self.assertEqual(proof["logical_all_tables_sha256"], self.whole)
            self.bundle.assert_called_once()
            self.assertEqual(
                self.bundle.call_args.kwargs["expected_head_sha256"],
                source.ACTIVATED_HASH)

    def test_source_commit_already_admitted_never_resume_v41(self):
        f = self.case
        with SingleOwner(f.file.with_suffix(".lock")):
            proof = source.build_proof(
                f.db, f.target, 31, 800001, "5"*64)
            source.commit_transition(
                f.db, proof, disabled_owner_witness=lambda: True,
                verified_release_witness=lambda: True)
            with self.assertRaisesRegex(
                    source.HybridSourceDenied, "IDLE_ORIGINAL_V41_REQUIRED"):
                self.inspect()

    def test_full_sqlite_mutation_without_head_change_is_denied(self):
        f = self.case
        f.db.conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket=?",
                          ("f"*64, "synthetic-positive-001"))
        with SingleOwner(f.file.with_suffix(".lock")):
            with self.assertRaisesRegex(abort.SafeAbortDenied,
                                        "COMPLETE_SQLITE_CONTENT_NOT_IDENTICAL"):
                self.inspect()

    def test_rogue_manifest_or_mismatched_original_head_denied(self):
        f = self.case
        with SingleOwner(f.file.with_suffix(".lock")):
            self.req["original_head_sha256"] = "f"*64
            try:
                with self.assertRaisesRegex(
                        abort.SafeAbortDenied, "V41_UNCHANGED_PREIMAGE_REQUIRED"):
                    self.inspect()
            finally:
                self.req["original_head_sha256"] = source.ACTIVATED_HASH
            self.bundle.return_value["logical_all_tables_sha256"] = "f"*64
            with self.assertRaisesRegex(
                    abort.SafeAbortDenied, "COMPLETE_SQLITE_CONTENT_NOT_IDENTICAL"):
                self.inspect()

    def test_no_lock_or_wrong_connection_and_non_windows_denied(self):
        with closing(Database.open_readonly(self.case.file)) as db:
            with self.assertRaisesRegex(
                    abort.SafeAbortDenied, "ORIGINAL_LOCKED_READONLY"):
                abort.inspect_precommit(db, self.req)
        with self.assertRaisesRegex(
                abort.SafeAbortDenied, "NATIVE_WINDOWS_ORIGINAL_OWNER_REQUIRED"):
            abort.original_preflight(
                Path("/tmp/not-owner.sqlite"), {}, {}, object())


class OriginalOwnerSafeAbortWrapperTests(unittest.TestCase):
    def test_inert_unregistered_abort_without_new_controller_or_retry(self):
        text = WRAPPER.read_text("utf-8")
        self.assertIn("F139-HYBRID-V41-SAFE-ABORT ", text)
        self.assertIn("nci04_v41_hybrid_safe_abort", text)
        self.assertIn("F139_HYBRID_V41_SAFE_ABORT_LOCKED_FULL_SQLITE=PASS", text)
        self.assertIn("F139_HYBRID_V41_ABORT_START_UNCERTAIN_NO_RETRY", text)
        self.assertIn("F139_HYBRID_V41_SAFE_ABORT_SAME_ORIGINAL_TASK=PASS", text)
        for forbidden in (
            "Register-ScheduledTask", "New-ScheduledTask",
            "Set-ScheduledTask", "Disable-ScheduledTask", "Stop-ScheduledTask",
            "workflow_dispatch", "gh api --method POST", "gh api --method PATCH",
            "Start-Sleep", "retry", "Start-Job"):
            if forbidden == "retry":
                continue  # NO RETRY is explicit in error labels.
            self.assertNotIn(forbidden, text)
        self.assertEqual(text.count("Enable-ScheduledTask -TaskName"), 1)
        self.assertEqual(text.count("Start-ScheduledTask -TaskName"), 1)
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            self.assertNotIn(WRAPPER.name, workflow.read_text("utf-8"))

    @unittest.skipUnless(os.name == "nt", "Native Windows PS5 syntax check")
    def test_original_windows_safe_abort_parser(self):
        exe = shutil.which("powershell.exe")
        self.assertIsNotNone(exe)
        script = (
            "$tokens=$null;$errors=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:F139_SAFE_ABORT_FILE,[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){"
            "$errors|ForEach-Object{Write-Output $_.Message};exit 1}")
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            env={**os.environ, "F139_SAFE_ABORT_FILE": str(WRAPPER)},
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0,
                         result.stdout+"\n"+result.stderr)


if __name__ == "__main__":
    unittest.main()
