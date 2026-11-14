"""Separate original-owner V38 fresh-backup comment and inert job tests.

No original task or live owner database is touched by these provider fixtures.
"""
import unittest
from pathlib import Path

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

    def test_windows_original_provider_is_required(self):
        with self.assertRaisesRegex(
                backup.ForwardBackupDenied,
                "NATIVE_WINDOWS_ORIGINAL_PROVIDER_REQUIRED"):
            backup.original_backup(None, {}, {}, None)

    def test_existing_workflow_backup_has_no_task_or_policy_mutation(self):
        path = (Path(__file__).resolve().parent.parent / ".github" /
                "workflows" / "f139-v41-original-owner-live-install.yml")
        workflow = path.read_text("utf-8")
        name = "  hybrid-v41-original-forward-backup:"
        self.assertEqual(workflow.count(name), 1)
        job = workflow.split(name, 1)[1]
        self.assertIn("github.event_name == 'issue_comment'", job)
        self.assertIn("github.event.issue.number == 807", job)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", job)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", job)
        self.assertIn("persist-credentials: false", job)
        self.assertIn("f139.nci04_v41_hybrid_forward_backup", job)
        for forbidden in (
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "gh api --method PATCH", "gh workflow run",
            "workflow_dispatch", "issues: write"):
            self.assertNotIn(forbidden, job)


if __name__ == "__main__":
    unittest.main()
