"""Tests for inert V38 release and original held-owner readiness controls.

Synthetic provider records are explicitly not original owner acceptance and
cannot execute source commits, source migration or restart any Windows task.
"""
import json
import sqlite3
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from f139.nci04_native_contract import canonical
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_original_commit as original_commit


class FakeProvider:
    def __init__(self):
        self.target = "b" * 40
        self.head = "c" * 40
        self.tree = "d" * 40
        self.main = {"name": "main", "protected": True,
                     "commit": {"sha": self.target}}
        self.pr = {
            "number": readiness.PR, "state": "closed", "merged": True,
            "merge_commit_sha": self.target,
            "user": {"login": readiness.OWNER},
            "head": {"ref": readiness.BRANCH, "sha": self.head,
                     "repo": {"full_name": readiness.REPO}},
            "base": {"ref": "main", "repo": {"full_name": readiness.REPO}},
        }
        self.comparison = {
            "status": "ahead", "ahead_by": 2, "behind_by": 0,
            "merge_base_commit": {"sha": readiness.forward.FROM},
        }
        self.events = [
            {"name": name, "head_sha": self.head,
             "event": "pull_request", "head_branch": readiness.BRANCH,
             "status": "completed", "conclusion": "success",
             "run_attempt": 1, "id": index + 1001,
             "actor": {"login": readiness.OWNER}}
            for index, name in enumerate(sorted(readiness.CI))]
        self.push = [{
            "name": "FORGE public Linux and Windows qualification",
            "head_sha": self.target, "event": "push", "head_branch": "main",
            "status": "completed", "conclusion": "success",
            "run_attempt": 1, "id": 2001,
            "actor": {"login": readiness.OWNER},
        }]
        self.old_intent = {
            "schema": original_commit.SCHEMA,
            "target_source_sha": readiness.forward.FROM,
            "original_head_seq": 1829,
            "original_head_sha256": readiness.forward.v37.ACTIVATED_HASH,
            "backup_run_id": 435,
            "backup_manifest_sha256": "e" * 64,
            "paired_approval_id": 10,
            "readiness_comment_id": 11,
            "expected_proof_sha256": "a" * 64,
            "source_transition_requested": True,
            "task_resume_authorized": False,
            "policy_update_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0,
        }
        self.old_body = original_commit.PREFIX + canonical(
            self.old_intent).decode("ascii")
        self.new_body = (readiness.PREFIX + self.target + " " +
                         str(readiness.OLD_COMMIT_ID))
        self.comments = {
            readiness.OLD_COMMIT_ID:
                self.comment(readiness.OLD_COMMIT_ID,
                             self.old_body, "2026-11-14T17:00:00Z"),
            6889999999:
                self.comment(6889999999, self.new_body, "2026-11-14T20:00:00Z"),
        }

    @staticmethod
    def comment(number, body, stamp):
        return {
            "id": number, "body": body, "created_at": stamp,
            "user": {"login": readiness.OWNER},
            "author_association": "OWNER",
            "issue_url":
                "https://api.github.com/repos/" + readiness.REPO +
                "/issues/807",
        }

    def get(self, path):
        prefix = "repos/" + readiness.REPO + "/"
        assert path.startswith(prefix), path
        relative = path[len(prefix):]
        if relative == "branches/main":
            return self.main
        if relative == "pulls/1759":
            return self.pr
        if relative.startswith("compare/"):
            return self.comparison
        if relative in ("git/commits/" + self.target,
                        "git/commits/" + self.head):
            sha = relative.rsplit("/", 1)[-1]
            return {"sha": sha, "tree": {"sha": self.tree}}
        if relative.startswith("actions/runs?"):
            return {"workflow_runs": self.events if "event=pull_request" in relative
                    else self.push}
        if relative.startswith("issues/comments/"):
            return self.comments[int(relative.rsplit("/", 1)[-1])]
        raise AssertionError("unexpected provider path " + relative)

    def env(self):
        return {
            "GITHUB_REPOSITORY": readiness.REPO,
            "GITHUB_ACTOR": readiness.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": self.target,
            "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
            "GITHUB_RUN_ID": "43512345678",
        }

    def event(self):
        return {
            "action": "created",
            "issue": {"number": 807, "user": {"login": readiness.OWNER}},
            "sender": {"login": readiness.OWNER},
            "comment": self.comments[6889999999],
        }


class ForwardReadinessTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeProvider()

    def test_pinned_workflow_is_not_silently_extended(self):
        root = Path(__file__).resolve().parent.parent
        workflow = (root / ".github" / "workflows" /
                    "f139-v41-original-owner-live-install.yml").read_text(
                        encoding="utf-8")
        # Historical #1758 owner workflow is source-hash pinned. No new
        # privileged runner job can be silently registered by this PR.
        self.assertNotIn("hybrid-v41-original-forward-readonly:", workflow)
        self.assertNotIn(
            "f139.nci04_v41_hybrid_forward_readiness", workflow)
        self.assertNotIn("hybrid-v41-original-forward-backup:", workflow)

    def test_readiness_main_is_not_a_second_worker_or_automatic_controller(self):
        from pathlib import Path
        source = Path(readiness.__file__).read_text("utf-8")
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask",
                          "Enable-ScheduledTask", "Disable-ScheduledTask",
                          "workflow_dispatch", "gh workflow run",
                          "gh api --method PATCH", "subprocess.run("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn(
            "F139_HYBRID_FORWARD_READONLY_PREFLIGHT=", source)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(
                    readiness.ForwardReadinessDenied,
                    "EXACT_SHA_ARGUMENT_REQUIRED"):
                readiness.main(["--target", "b" * 40])

    def test_exact_merged_release_requires_all_ci_and_same_tree(self):
        receipt = readiness._release(self.api.get, self.api.target)
        self.assertEqual(receipt["target_source_sha"], self.api.target)
        self.assertEqual(len(receipt["pr_qualification_runs"]), 3)
        self.assertEqual(receipt["main_qualification_run"], 2001)

    def test_missing_main_postmerge_ci_is_not_release(self):
        self.api.push = []
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "POSTMERGE_FULL_MAIN_REGRESSION_REQUIRED"):
            readiness._release(self.api.get, self.api.target)

    def test_unmerged_pr_cannot_be_forward_release(self):
        self.api.pr["merged"] = False
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "MERGED_PR1759_PROTECTED_MAIN_REQUIRED"):
            readiness._release(self.api.get, self.api.target)

    def test_forged_ancestry_is_rejected(self):
        self.api.comparison["merge_base_commit"]["sha"] = "0" * 40
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "COMMITTED_V37_ANCESTRY_REQUIRED"):
            readiness._release(self.api.get, self.api.target)

    def test_partial_or_replayed_pr_ci_not_accepted(self):
        self.api.events.pop()
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "ALL_PR_QUALIFICATION_REQUIRED"):
            readiness._release(self.api.get, self.api.target)
        self.api.events = FakeProvider().events
        self.api.events[0]["run_attempt"] = 2
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "PR_CI_NOT_UNIQUE_FIRST_ATTEMPT_PASS"):
            readiness._release(self.api.get, self.api.target)

    def test_authenticated_new_comment_binds_old_original_source(self):
        frozen = readiness.authenticate_readiness(
            self.api.get, self.api.env(), self.api.event(),
            self.api.target)
        self.assertEqual(frozen, self.api.old_intent)

    def test_wrong_actor_or_comment_does_not_authorize(self):
        bad_env = self.api.env()
        bad_env["RUNNER_NAME"] = "FORGED-RUNNER"
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "NATIVE_FIRST_ATTEMPT_RUNNER_REQUIRED"):
            readiness.authenticate_readiness(
                self.api.get, bad_env, self.api.event(), self.api.target)
        self.api.comments[readiness.OLD_COMMIT_ID]["author_association"] = "NONE"
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "ORIGINAL_OWNER_COMMENT_PROVIDER_DRIFT"):
            readiness.authenticate_readiness(
                self.api.get, self.api.env(), self.api.event(),
                self.api.target)

    def test_old_commit_change_and_noncanonical_json_rejected(self):
        self.api.old_intent["task_resume_authorized"] = True
        self.api.comments[readiness.OLD_COMMIT_ID]["body"] = (
            original_commit.PREFIX + canonical(
                self.api.old_intent).decode("ascii"))
        with self.assertRaisesRegex(
                readiness.ForwardReadinessDenied,
                "FROZEN_V37_SOURCE_APPROVAL_DRIFT"):
            readiness.authenticate_readiness(
                self.api.get, self.api.env(), self.api.event(),
                self.api.target)

    def test_held_readonly_receipt_does_not_authorize_mutation(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.execute("PRAGMA query_only=ON")
        observed = SimpleNamespace(
            classification="COMMITTED_SOURCE_HOLD",
            source_commit_recorded=True,
            event_seq=readiness.forward.V37_SEQ,
            event_head_sha256=readiness.forward.V37_HEAD,
            full_detached_cold_backup_verified=True,
            readback_database_mutations=0,
            scientific_first_use=False,
        )
        fake = object.__new__(readiness.Database)
        fake.conn = conn
        fake._readonly_opened = True
        fake.filename = Path("synthetic-held.sqlite")
        with patch.object(readiness.SingleOwner, "held", return_value=True):
            with patch.object(readiness.held, "inspect_held_ledger",
                              return_value=vars(observed)):
                outcome = readiness.inspect_held_original(
                    fake, self.api.old_intent)
        self.assertEqual(outcome["event_seq"], readiness.forward.V37_SEQ)
        self.assertEqual(conn.total_changes, 0)


if __name__ == "__main__":
    unittest.main()
