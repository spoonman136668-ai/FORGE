"""Standalone event1832 postcommit owner-intent authentication and refusal.

No original-owner SQLite, scheduled task or live native run is exercised.
"""
import unittest
from pathlib import Path

from f139 import nci04_v41_hybrid_event1832_postcommit as postcommit
from f139 import nci04_v41_hybrid_event1832_successor as successor
from f139.test_nci04_v41_hybrid_event1832_commit import FakeCommittedV39


class FakePostcommitV39(FakeCommittedV39):
    def __init__(self):
        super().__init__()
        self.postcommit_id = 6900000300
        self.comments[self.postcommit_id] = self.comment(
            self.postcommit_id,
            postcommit.PREFIX + self.target + " " + str(self.commit_id),
            "2026-11-15T23:00:00Z")

    def event(self):
        event = super().event()
        event["comment"] = self.comments[self.postcommit_id]
        return event

    def env(self):
        env = super().env()
        env["GITHUB_RUN_ID"] = "43799999333"
        return env


class PostcommitV39OwnerTests(unittest.TestCase):
    def setUp(self):
        self.api = FakePostcommitV39()

    def auth(self):
        return postcommit.authenticate(
            self.api.get, self.api.env(), self.api.event())

    def test_independent_new_owner_postcommit_bound_to_prior_real_job(self):
        req = self.auth()
        self.assertEqual(req["target_source_sha"], self.api.target)
        self.assertEqual(req["source_commit_comment_id"], self.api.commit_id)
        self.assertEqual(req["postcommit_comment_id"], self.api.postcommit_id)
        self.assertEqual(req["backup_run_id"], 43799999111)
        self.assertEqual(req["backup_job_id"], 132999999999)

    def test_drifted_prior_source_or_duplicate_postcommit_refused(self):
        self.api.comments[self.api.postcommit_id]["body"] = (
            postcommit.PREFIX + self.api.target + " " +
            str(self.api.backup_id))
        with self.assertRaisesRegex(
                postcommit.Event1832PostcommitDenied,
                "AUTHENTICATED_COMMIT_INTENT_MISSING"):
            self.auth()
        self.api = FakePostcommitV39()
        self.api.comments[self.api.postcommit_id]["body"] = (
            postcommit.PREFIX + self.api.target + " " +
            str(self.api.postcommit_id))
        with self.assertRaisesRegex(
                postcommit.Event1832PostcommitDenied,
                "FRESH_COMMIT_PRECEDES_POSTCOMMIT_REQUIRED"):
            self.auth()

    def test_unqualified_prior_backup_job_is_not_postcommit(self):
        self.api.jobs["jobs"][0]["conclusion"] = "failure"
        with self.assertRaisesRegex(
                postcommit.committed.Event1832CommitDenied,
                "ACTUAL_ORIGINAL_BACKUP_JOB_NOT_SUCCESSFUL"):
            self.auth()

    def test_query_only_readback_uses_event_payload_not_hash_canonical(self):
        from f139.local_controller import canonical as event_canonical
        from f139.nci04_native_contract import canonical as proof_canonical
        doc = {"schema": successor.SCHEMA, "source_sha": self.api.target}
        self.assertEqual(event_canonical(doc), proof_canonical(doc) + b"\n")
        source = Path(postcommit.__file__).read_text("utf-8")
        self.assertIn('row["payload"] == event_canonical(doc).decode("ascii")', source)
        self.assertNotIn('row["payload"] == canonical(doc).decode("ascii")', source)
        self.assertIn('digest(canonical(doc)) == request["expected_proof_sha256"]', source)

    def test_read_only_module_does_not_resume_or_migrate(self):
        with self.assertRaisesRegex(
                postcommit.Event1832PostcommitDenied,
                "EXACT_ORIGINAL_WINDOWS_OWNER_REQUIRED"):
            postcommit.original_postcommit(None, {}, {}, None)
        source = Path(postcommit.__file__).read_text("utf-8")
        for forbidden in (
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Set-ScheduledTask", "workflow_dispatch", "gh workflow run",
            "gh api --method PATCH",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("committed._fresh_cold(", source)
        self.assertIn("db.verify()", source)
        self.assertIn("db.conn.total_changes == 0", source)


if __name__ == "__main__":
    unittest.main()
