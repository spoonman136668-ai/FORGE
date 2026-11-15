"""Original Windows event1831 V39 source-readiness and backup owner fixtures.

No fake provider result authorizes a live GitHub job, source event, task action,
policy update or scientific use. Tests exercise fail-closed contracts only.
"""
import unittest
from pathlib import Path

from f139 import nci04_v41_hybrid_event1832_owner as owner
from f139 import nci04_v41_hybrid_event1832_successor as successor


class FakeV39Owner:
    def __init__(self):
        self.target = "b" * 40
        self.head = "c" * 40
        self.tree = "d" * 40
        self.main = {
            "name": "main", "protected": True,
            "commit": {"sha": self.target},
        }
        self.pr = {
            "number": owner.PR, "state": "closed", "merged": True,
            "merge_commit_sha": self.target,
            "user": {"login": owner.OWNER},
            "head": {
                "ref": owner.BRANCH, "sha": self.head,
                "repo": {"full_name": owner.REPO},
            },
            "base": {
                "ref": "main", "repo": {"full_name": owner.REPO}
            },
        }
        self.compare = {
            "status": "ahead", "ahead_by": 2, "behind_by": 0,
            "merge_base_commit": {"sha": successor.SOURCE}
        }
        self.pr_runs = [
            {
                "name": name, "id": index + 4001,
                "head_sha": self.head,
                "event": "pull_request",
                "head_branch": owner.BRANCH,
                "status": "completed", "conclusion": "success",
                "run_attempt": 1,
                "actor": {"login": owner.OWNER},
            }
            for index, name in enumerate(sorted(owner.CI))
        ]
        self.main_runs = [{
            "name": "FORGE public Linux and Windows qualification",
            "id": 5001, "head_sha": self.target,
            "event": "push", "head_branch": "main",
            "status": "completed", "conclusion": "success",
            "run_attempt": 1,
            "actor": {"login": owner.OWNER},
        }]
        self.readiness_id = 6900000000
        self.backup_id = 6900000100
        self.comments = {
            owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID:
                self.comment(
                    owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID,
                    owner.postcommit.PREFIX + successor.SOURCE + " " +
                    str(owner.PREDECESSOR_SOURCE_COMMIT_COMMENT_ID),
                    "2026-11-15T18:30:00Z"),
            self.readiness_id:
                self.comment(
                    self.readiness_id,
                    owner.READINESS + self.target + " " +
                    str(owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID),
                    "2026-11-15T20:00:00Z"),
            self.backup_id:
                self.comment(
                    self.backup_id,
                    owner.BACKUP + self.target + " " +
                    str(self.readiness_id),
                    "2026-11-15T21:00:00Z"),
        }

    @staticmethod
    def comment(i, body, created_at):
        return {
            "id": i, "body": body, "created_at": created_at,
            "author_association": "OWNER",
            "user": {"login": owner.OWNER},
            "issue_url": ("https://api.github.com/repos/" +
                          owner.REPO + "/issues/807"),
        }

    def get(self, path):
        prefix = "repos/" + owner.REPO + "/"
        assert path.startswith(prefix), path
        name = path[len(prefix):]
        if name == "branches/main":
            return self.main
        if name == "pulls/1774":
            return self.pr
        if name.startswith("compare/"):
            return self.compare
        if name in (
                "git/commits/" + self.target,
                "git/commits/" + self.head):
            return {"sha": name.rsplit("/", 1)[-1],
                    "tree": {"sha": self.tree}}
        if name.startswith("actions/runs?"):
            return {"workflow_runs":
                    self.pr_runs if "event=pull_request" in name
                    else self.main_runs}
        if name.startswith("issues/comments/"):
            return self.comments[int(name.rsplit("/", 1)[-1])]
        raise AssertionError(name)

    def env(self):
        return {
            "GITHUB_REPOSITORY": owner.REPO,
            "GITHUB_ACTOR": owner.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
            "GITHUB_SHA": self.target,
            "GITHUB_RUN_ID": "43799999111",
        }

    def event(self, which="readiness"):
        i = self.readiness_id if which == "readiness" else self.backup_id
        return {
            "action": "created",
            "issue": {"number": 807, "user": {"login": owner.OWNER}},
            "sender": {"login": owner.OWNER},
            "comment": self.comments[i],
        }


class Event1832OwnerContractTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeV39Owner()

    def test_exact_merged_1774_source_and_three_ci_receipts(self):
        released = owner.release(
            self.provider.get, self.provider.target)
        self.assertEqual(released["source_sha"], self.provider.target)
        self.assertEqual(released["qualified_tree_sha"], self.provider.tree)
        self.assertEqual(released["main_qualification_run"], 5001)
        self.assertEqual(len(released["pr_qualification_runs"]), 3)

    def test_release_denies_unmerged_and_nonidentical_tree(self):
        self.provider.pr["merged"] = False
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied,
                "PR1774_MERGED_PROTECTED_MAIN_REQUIRED"):
            owner.release(self.provider.get, self.provider.target)
        self.provider.pr["merged"] = True
        self.provider.tree = "0" * 40
        original = self.provider.get
        def forged_tree(path):
            if path.endswith("git/commits/" + self.provider.target):
                return {"sha": self.provider.target,
                        "tree": {"sha": "1" * 40}}
            return original(path)
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied, "PROTECTED_RELEASE_TREE_NOT_QUALIFIED"):
            owner.release(forged_tree, self.provider.target)

    def test_release_requires_full_main_and_unique_pr_qualification(self):
        self.provider.main_runs = []
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied,
                "PROTECTED_MAIN_FULL_REGRESSION_REQUIRED"):
            owner.release(self.provider.get, self.provider.target)
        self.provider.main_runs = FakeV39Owner().main_runs
        self.provider.pr_runs[0]["run_attempt"] = 2
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied,
                "NONUNIQUE_OR_UNQUALIFIED_PR_CI"):
            owner.release(self.provider.get, self.provider.target)

    def test_readiness_binds_actual_postcommit_comment_and_new_target(self):
        receipt = owner.authenticate_readiness(
            self.provider.get, self.provider.env(), self.provider.event())
        self.assertEqual(
            receipt["event1831_postcommit_comment_id"],
            owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID)
        self.assertEqual(receipt["target_source_sha"], self.provider.target)
        self.assertEqual(
            receipt["readiness_comment_id"], self.provider.readiness_id)

    def test_new_backup_binds_readiness_not_old_source_commit(self):
        receipt = owner.authenticate_backup(
            self.provider.get, self.provider.env(),
            self.provider.event("backup"))
        self.assertEqual(receipt["backup_run_id"], 43799999111)
        self.assertEqual(receipt["readiness_comment_id"],
                         self.provider.readiness_id)
        self.assertEqual(receipt["backup_comment_id"],
                         self.provider.backup_id)

    def test_predecessor_wrong_owner_or_unknown_replay_refused(self):
        self.provider.comments[
            owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID]["author_association"] = "NONE"
        with self.assertRaisesRegex(
                owner.previous_release.ForwardReadinessDenied,
                "ORIGINAL_OWNER_COMMENT_PROVIDER_DRIFT"):
            owner.authenticate_readiness(
                self.provider.get, self.provider.env(),
                self.provider.event())
        self.provider = FakeV39Owner()
        event = self.provider.event()
        event["comment"] = {
            **event["comment"], "body":
                owner.READINESS + "0" * 40 + " " +
                str(owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID),
        }
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied,
                "NEW_OWNER_EVENT_NOT_SOURCE_BOUND"):
            owner.authenticate_readiness(
                self.provider.get, self.provider.env(), event)

    def test_backup_rejects_legacy_readiness_and_run_attempt_replay(self):
        self.provider.comments[self.provider.backup_id]["body"] = (
            owner.BACKUP + self.provider.target + " " +
            str(owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID))
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied,
                "DISTINCT_SEQUENTIAL_SOURCE_OWNER_EVENTS_REQUIRED"):
            owner.authenticate_backup(
                self.provider.get, self.provider.env(),
                self.provider.event("backup"))
        self.provider = FakeV39Owner()
        env = self.provider.env()
        env["GITHUB_RUN_ATTEMPT"] = "2"
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied,
                "EXACT_ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED"):
            owner.authenticate_backup(
                self.provider.get, env, self.provider.event("backup"))

    def test_no_live_owner_route_registered_by_source_module(self):
        with self.assertRaisesRegex(
                owner.Event1832OwnerDenied, "WINDOWS_ORIGINAL_OWNER_REQUIRED"):
            owner.original_backup(None, {}, {}, None)
        source = Path(owner.__file__).read_text("utf-8")
        for forbidden in (
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "workflow_dispatch", "gh workflow run",
            "gh api --method PATCH"):
            self.assertNotIn(forbidden, source)
        self.assertIn('if __name__ == "__main__":', source)
        self.assertIn('choices=("readiness", "backup")', source)
        self.assertIn("original_readiness(db, env, event, GitHub())", source)
        self.assertIn("original_backup(db, env, event, GitHub())", source)
        self.assertIn("cold.stage_complete_cold_bundle(", source)


if __name__ == "__main__":
    unittest.main()
