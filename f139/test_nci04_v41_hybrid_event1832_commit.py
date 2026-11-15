"""Synthetic source-commit owner authentication; no original SQLite write."""
import copy
import unittest
from pathlib import Path

from f139.nci04_native_contract import canonical
from f139 import nci04_v41_hybrid_event1832_commit as commit
from f139 import nci04_v41_hybrid_event1832_successor as successor
from f139.test_nci04_v41_hybrid_event1832_owner import FakeV39Owner


class FakeCommittedV39(FakeV39Owner):
    def __init__(self):
        super().__init__()
        self.commit_id = 6900000200
        self.commit_run_id = 43799999222
        self.intent = {
            "schema": commit.SCHEMA,
            "target_source_sha": self.target,
            "readiness_comment_id": self.readiness_id,
            "backup_comment_id": self.backup_id,
            "backup_run_id": 43799999111,
            "backup_manifest_sha256": "a" * 64,
            "backup_logical_all_tables_sha256": "b" * 64,
            "original_head_seq": successor.PREDECESSOR_SEQ,
            "original_head_sha256": successor.PREDECESSOR_SHA,
            "expected_proof_sha256": "c" * 64,
            "source_transition_requested": True,
            "task_resume_authorized": False,
            "owner_policy_update_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0,
        }
        self.comments[self.commit_id] = self.comment(
            self.commit_id,
            commit.PREFIX + canonical(self.intent).decode("ascii"),
            "2026-11-15T22:00:00Z")
        self.backup_run = {
            "id": self.intent["backup_run_id"],
            "name": commit.BACKUP_WORKFLOW,
            "event": "issue_comment", "head_sha": self.target,
            "run_attempt": 1, "status": "completed",
            "conclusion": "success",
            "actor": {"login": commit.owner.OWNER},
        }
        self.jobs = {
            "total_count": 1,
            "jobs": [{
                "id": 132999999999, "run_id": self.backup_run["id"],
                "name": commit.BACKUP_JOB,
                "status": "completed", "conclusion": "success",
            }],
        }

    def env(self):
        data = super().env()
        data["GITHUB_RUN_ID"] = str(self.commit_run_id)
        return data

    def event(self):
        out = super().event("backup")
        out["comment"] = self.comments[self.commit_id]
        return out

    def get(self, path):
        if path == ("repos/" + commit.owner.REPO +
                    "/actions/runs/" + str(self.backup_run["id"])):
            return self.backup_run
        if path == ("repos/" + commit.owner.REPO +
                    "/actions/runs/" + str(self.backup_run["id"]) +
                    "/jobs?per_page=100"):
            return self.jobs
        if "/actions/runs/" in path and "/jobs?" not in path:
            return {"id": int(path.rsplit("/", 1)[-1]), "name": "UNRELATED"}
        return super().get(path)


class Event1832SourceCommitContractTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeCommittedV39()

    def auth(self):
        return commit.authenticate_commit(
            self.provider.get, self.provider.env(),
            self.provider.event())

    def test_distinct_owner_commit_binds_successful_original_backup_run(self):
        req = self.auth()
        self.assertEqual(req["target_source_sha"], self.provider.target)
        self.assertEqual(req["backup_job_id"], 132999999999)
        self.assertEqual(req["backup_run_id"], 43799999111)
        self.assertNotEqual(req["backup_run_id"], self.provider.commit_run_id)
        self.assertEqual(req["source_commit_comment_id"],
                         self.provider.commit_id)

    def test_wrong_previous_run_result_is_never_source_commit_right(self):
        for field, bad in (
            ("conclusion", "failure"), ("run_attempt", 2),
            ("event", "workflow_dispatch"), ("head_sha", "0"*40),
        ):
            with self.subTest(field=field):
                previous = self.provider.backup_run[field]
                self.provider.backup_run[field] = bad
                with self.assertRaisesRegex(
                        commit.Event1832CommitDenied,
                        "ACTUAL_PRIOR_BACKUP_RUN_NOT_QUALIFIED"):
                    self.auth()
                self.provider.backup_run[field] = previous

    def test_other_job_cannot_impersonate_native_backup(self):
        self.provider.jobs["jobs"][0]["name"] = "unrelated"
        with self.assertRaisesRegex(
                commit.Event1832CommitDenied,
                "ACTUAL_ORIGINAL_BACKUP_JOB_NOT_SUCCESSFUL"):
            self.auth()

    def test_source_only_intent_cannot_grant_activation_or_science(self):
        for field, bad in (
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("task_resume_authorized", True),
            ("owner_policy_update_authorized", True),
            ("new_dispatches", 1),
            ("original_head_seq", 1830),
        ):
            with self.subTest(field=field):
                self.provider = FakeCommittedV39()
                self.provider.intent[field] = bad
                self.provider.comments[self.provider.commit_id]["body"] = (
                    commit.PREFIX +
                    canonical(self.provider.intent).decode("ascii"))
                with self.assertRaisesRegex(
                        commit.Event1832CommitDenied,
                        "EXACT_SOURCE_ONLY_COMMIT_INTENT_REQUIRED"):
                    self.auth()

    def test_malformed_and_duplicate_json_refused(self):
        self.provider.comments[self.provider.commit_id]["body"] = (
            commit.PREFIX + '{"schema":"x","schema":"y"}')
        with self.assertRaises(commit.Event1832CommitDenied):
            self.auth()

    def test_legacy_1831_backup_not_replayed_as_new_event1832(self):
        self.provider.intent["backup_run_id"] = 43746555256
        self.provider.comments[self.provider.commit_id]["body"] = (
            commit.PREFIX + canonical(self.provider.intent).decode("ascii"))
        with self.assertRaisesRegex(
                commit.Event1832CommitDenied,
                "ACTUAL_PRIOR_BACKUP_RUN_NOT_QUALIFIED"):
            self.auth()

    def test_original_source_commit_denied_on_nonowner_host(self):
        with self.assertRaisesRegex(
                commit.Event1832CommitDenied,
                "ACTUAL_ORIGINAL_WINDOWS_OWNER_REQUIRED"):
            commit.original_source_commit(None, {}, {}, None)

    def test_original_sqlite_payload_canonical_newline_not_owner_proof_hash(self):
        from f139.local_controller import canonical as event_canonical
        from f139.nci04_native_contract import canonical as proof_canonical
        doc = {"schema": successor.SCHEMA, "source_sha": self.provider.target}
        self.assertEqual(event_canonical(doc), proof_canonical(doc) + b"\\n")
        source = Path(commit.__file__).read_text("utf-8")
        self.assertIn('row["payload"] == event_canonical(expected_proof).decode("ascii")', source)
        self.assertNotIn('row["payload"] == canonical(expected_proof).decode("ascii")', source)

    def test_no_second_controller_or_scheduler_registered(self):
        script = Path(commit.__file__).read_text("utf-8")
        for forbidden in (
            "Register-ScheduledTask", "Start-ScheduledTask",
            "Set-ScheduledTask", "Enable-ScheduledTask",
            "gh workflow run", "workflow_dispatch",
            "gh api --method PATCH"):
            self.assertNotIn(forbidden, script)
        self.assertIn("successor.commit_transition(", script)
        self.assertIn("cold.verify_detached_restore(", script)
        self.assertIn("original_owner_mutations", script)
        self.assertIn("from f139.local_controller import Database, GitHub, SingleOwner",
                      script)


if __name__ == "__main__":
    unittest.main()
