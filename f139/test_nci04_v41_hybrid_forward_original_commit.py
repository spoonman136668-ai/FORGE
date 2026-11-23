"""Source-only future V38 original owner forward-commit auth/negative tests.

Synthetic GitHub objects are evidence-free fixtures: NOT owner approvals,
not a qualified backup, and not a reason to start the original Windows task.
"""
import unittest
from copy import deepcopy
from pathlib import Path

from f139.nci04_native_contract import canonical
from f139 import nci04_v41_hybrid_forward_original_commit as commit
from f139 import nci04_v41_hybrid_forward_backup as backup
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139.test_nci04_v41_hybrid_forward_readiness import FakeProvider


class CommitProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.ready_id = 6889999999
        self.backup_id = 6891111111
        self.commit_id = 6892222222
        self.run_id = 43649999999
        self.comments[self.backup_id] = self.comment(
            self.backup_id, backup.PREFIX + self.target + " " +
            str(self.ready_id), "2026-11-14T21:00:00Z")
        self.intent = {
            "schema": commit.SCHEMA,
            "target_source_sha": self.target,
            "readiness_comment_id": self.ready_id,
            "backup_comment_id": self.backup_id,
            "backup_run_id": self.run_id,
            "backup_manifest_sha256": "a" * 64,
            "backup_logical_all_tables_sha256": "b" * 64,
            "original_head_seq": commit.forward.V37_SEQ,
            "original_head_sha256": commit.forward.V37_HEAD,
            "expected_proof_sha256": "c" * 64,
            "source_transition_requested": True,
            "task_resume_authorized": False,
            "policy_update_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0,
        }
        self._update()
        self.run = {
            "id": self.run_id, "name": commit.BACKUP_WORKFLOW,
            "event": "issue_comment", "head_sha": self.target,
            "run_attempt": 1, "status": "completed",
            "conclusion": "success", "actor": {"login": readiness.OWNER},
        }
        self.jobs = {
            "total_count": 1,
            "jobs": [{
                "id": 132500000001, "run_id": self.run_id,
                "name": commit.BACKUP_JOB, "status": "completed",
                "conclusion": "success",
            }],
        }

    def _update(self):
        body = commit.PREFIX + canonical(self.intent).decode("ascii")
        self.comments[self.commit_id] = self.comment(
            self.commit_id, body, "2026-11-14T22:00:00Z")

    def event(self):
        obj = super().event()
        obj["comment"] = self.comments[self.commit_id]
        return obj

    def get(self, path):
        root = ("repos/" + readiness.REPO + "/actions/runs/" +
                str(self.run_id))
        if path == root:
            return self.run
        if path == root + "/jobs?per_page=100":
            return self.jobs
        return super().get(path)


class ForwardSourceOwnerTests(unittest.TestCase):
    def setUp(self):
        self.api = CommitProvider()

    def test_distinct_protected_source_and_successful_single_backup_job(self):
        info = commit.authenticate_commit(
            self.api.get, self.api.env(), self.api.event())
        self.assertEqual(info["target_source_sha"], self.api.target)
        self.assertEqual(info["backup_run_id"], self.api.run_id)
        self.assertEqual(info["backup_job_id"], 132500000001)
        self.assertEqual(info["source_commit_comment_id"],
                         self.api.commit_id)
        self.assertEqual(info["frozen_v37_commit"],
                         self.api.old_intent)
        self.assertEqual(len(commit.FIELDS), len(self.api.intent))

    def test_failed_or_retried_backup_job_never_authorizes_commit(self):
        for key, bad in (
                ("conclusion", "failure"), ("run_attempt", 2),
                ("head_sha", "0" * 40)):
            with self.subTest(key=key):
                old = self.api.run[key]
                self.api.run[key] = bad
                with self.assertRaisesRegex(
                        commit.ForwardCommitDenied,
                        "ORIGINAL_BACKUP_RUN_NOT_SUCCESSFUL"):
                    commit.authenticate_commit(
                        self.api.get, self.api.env(), self.api.event())
                self.api.run[key] = old
        self.api.jobs["jobs"][0]["conclusion"] = "failure"
        with self.assertRaisesRegex(
                commit.ForwardCommitDenied,
                "ORIGINAL_BACKUP_OWNER_JOB_NOT_QUALIFIED"):
            commit.authenticate_commit(
                self.api.get, self.api.env(), self.api.event())

    def test_forged_or_replayed_owner_intent_and_wrong_head_denied(self):
        original = deepcopy(self.api.intent)
        for field, bad in (
                ("source_transition_requested", False),
                ("hybrid_admission", True),
                ("task_resume_authorized", True),
                ("original_head_seq", 1829),
                ("target_source_sha", "0" * 40),
                ("backup_logical_all_tables_sha256", "not-a-hash"),
                ("new_dispatches", 1)):
            with self.subTest(field=field):
                self.api.intent = {**original, field: bad}
                self.api._update()
                with self.assertRaisesRegex(
                        commit.ForwardCommitDenied,
                        "EXACT_SOURCE_ONLY_NONSCIENCE_INTENT_REQUIRED"):
                    commit.authenticate_commit(
                        self.api.get, self.api.env(), self.api.event())
        self.api.intent = original
        self.api._update()

    def test_stale_backup_comment_and_reused_identity_denied(self):
        self.api.comments[self.api.backup_id]["body"] = (
            backup.PREFIX + "0" * 40 + " " + str(self.api.ready_id))
        with self.assertRaisesRegex(
                commit.ForwardCommitDenied,
                "BACKUP_COMMENT_NOT_QUALIFIED_FOR_SOURCE"):
            commit.authenticate_commit(
                self.api.get, self.api.env(), self.api.event())

    def test_wrong_runner_and_lack_of_windows_owner_denied(self):
        env = self.api.env()
        env["GITHUB_RUN_ATTEMPT"] = "2"
        with self.assertRaisesRegex(
                commit.ForwardCommitDenied,
                "ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED"):
            commit.authenticate_commit(
                self.api.get, env, self.api.event())
        with self.assertRaisesRegex(
                commit.ForwardCommitDenied,
                "WINDOWS_ORIGINAL_NATIVE_PROVIDER_REQUIRED"):
            commit.original_source_commit(None, {}, {}, None)

    def test_forward_commit_does_not_register_a_task_or_workflow(self):
        workflow = (Path(__file__).resolve().parent.parent / ".github" /
                    "workflows" /
                    "f139-v41-original-owner-live-install.yml").read_text(
                        "utf-8")
        self.assertNotIn("hybrid-v38-original-forward-commit:", workflow)
        source = Path(commit.__file__).read_text("utf-8")
        for forbidden in ("Start-ScheduledTask", "Enable-ScheduledTask",
                          "gh workflow run", "gh api --method PATCH",
                          "workflow_dispatch"):
            self.assertNotIn(forbidden, source)
        self.assertIn("F139_HYBRID_FORWARD_SOURCE_COMMIT_HOLD=", source)


if __name__ == "__main__":
    unittest.main()
