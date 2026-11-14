"""Separate original-owner V38 fresh-backup comment and inert job tests.

No original task or live owner database is touched by these provider fixtures.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest

from f139 import nci04_v41_hybrid_forward_backup as backup
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139.test_nci04_v41_hybrid_forward_readiness import FakeProvider


class ForwardBackupOwnerTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeProvider()
        self.backup_id = 6891111111
        self.ready_id = 6889999999
        body = (backup.PREFIX + self.api.target + " " +
                str(self.ready_id))
        self.api.comments[self.backup_id] = self.api.comment(
            self.backup_id, body, "2026-11-14T21:00:00Z")

    def event(self):
        event = self.api.event()
        event["comment"] = self.api.comments[self.backup_id]
        return event

    def test_separate_owner_approval_binds_new_readiness_and_old_commit(self):
        result = backup.authenticate_backup(
            self.api.get, self.api.env(), self.event(),
            self.api.target)
        self.assertEqual(result["backup_run_id"], 43512345678)
        self.assertEqual(result["readiness_comment_id"], self.ready_id)
        self.assertEqual(result["backup_comment_id"], self.backup_id)
        self.assertEqual(result["frozen_v37_commit"],
                         self.api.old_intent)

    def test_backup_comment_cannot_substitute_for_readiness(self):
        self.api.comments[self.backup_id]["body"] = (
            backup.PREFIX + self.api.target + " " +
            str(readiness.OLD_COMMIT_ID))
        with self.assertRaisesRegex(
                backup.ForwardBackupDenied,
                "DISTINCT_OWNER_EVENTS_REQUIRED"):
            backup.authenticate_backup(
                self.api.get, self.api.env(), self.event(),
                self.api.target)

    def test_unrelated_or_modified_prior_comment_rejected(self):
        self.api.comments[self.ready_id]["body"] = (
            readiness.PREFIX + "0" * 40 + " " +
            str(readiness.OLD_COMMIT_ID))
        with self.assertRaisesRegex(
                backup.ForwardBackupDenied,
                "ORIGINAL_FORWARD_READINESS_NOT_FOUND"):
            backup.authenticate_backup(
                self.api.get, self.api.env(), self.event(),
                self.api.target)

    def test_replayed_or_forced_runner_cannot_backup(self):
        env = self.api.env()
        env["GITHUB_RUN_ATTEMPT"] = "2"
        with self.assertRaisesRegex(
                backup.ForwardBackupDenied,
                "ORIGINAL_FIRST_ATTEMPT_REQUIRED"):
            backup.authenticate_backup(
                self.api.get, env, self.event(),
                self.api.target)

    def test_commit_proof_can_be_frozen_before_commit_comment_exists(self):
        approval = {
            "readiness_comment_id": self.ready_id,
            "backup_run_id": 43649999999,
            "target_source_sha": self.api.target,
        }
        receipt = {
            "manifest_sha256": "a" * 64,
            "logical_all_tables_sha256": "b" * 64,
            "candidate_sha": self.api.target,
            "original_source_sha": backup.forward.FROM,
            "original_head_seq": backup.forward.V37_SEQ,
            "original_head_sha256": backup.forward.V37_HEAD,
        }
        frozen = {
            "owner_event_id": self.ready_id,
            "to_source_sha": self.api.target,
            "backup_run_id": approval["backup_run_id"],
            "backup_manifest_sha256": receipt["manifest_sha256"],
        }
        original = object()
        with patch.object(backup.forward, "build_proof",
                          return_value=frozen) as built:
            sha = backup._frozen_source_proof_sha(
                original, approval, receipt)
        self.assertEqual(sha, digest(canonical(frozen)))
        built.assert_called_once_with(
            original, self.api.target, self.ready_id,
            approval["backup_run_id"], receipt["manifest_sha256"],
            receipt["logical_all_tables_sha256"])
        # Unknown future commit-comment ID never influences proof generation.
        self.assertNotIn("source_commit_comment_id",
                         str(built.call_args))
        receipt["original_head_seq"] = 1829
        with self.assertRaisesRegex(
                backup.ForwardBackupDenied,
                "BACKUP_NOT_BOUND_TO_FROZEN_READINESS"):
            backup._frozen_source_proof_sha(
                original, approval, receipt)

    def test_windows_original_provider_is_required(self):
        with self.assertRaisesRegex(
                backup.ForwardBackupDenied,
                "NATIVE_WINDOWS_ORIGINAL_PROVIDER_REQUIRED"):
            backup.original_backup(None, {}, {}, None)

    def test_backup_owner_action_is_not_registered_without_separate_authority(self):
        path = (Path(__file__).resolve().parent.parent / ".github" /
                "workflows" / "f139-v41-original-owner-live-install.yml")
        workflow = path.read_text("utf-8")
        self.assertNotIn("hybrid-v41-original-forward-backup:", workflow)
        self.assertNotIn("f139.nci04_v41_hybrid_forward_backup", workflow)
        # This file has no spontaneous execution path.
        source = Path(backup.__file__).read_text("utf-8")
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask",
                          "Enable-ScheduledTask", "Disable-ScheduledTask",
                          "workflow_dispatch", "gh workflow run",
                          "gh api --method PATCH"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
