"""Synthetic provider tests; no owner runner, SQLite mutation or deployment."""
import copy
from pathlib import Path
import unittest
from unittest import mock

from f139 import nci04_v41_hybrid_successor_release as gate
from f139 import nci04_v41_hybrid_release_readiness as owner

TARGET = "e"*40
HEAD = "d"*40
TREE = "a"*40
BACKUP_SHA = "b"*64
PREFIX = "repos/" + gate.REPO + "/"
REQUEST = gate.PREFIX + TARGET + " 987654 " + BACKUP_SHA + " 112"


def env():
    return {"GITHUB_REPOSITORY": gate.REPO, "GITHUB_ACTOR": gate.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": TARGET, "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "87654", "RUNNER_NAME": "FORGE-CODEX-REMOTE"}


def event():
    return {"action": "created", "issue": {"number": 807,
            "user": {"login": gate.OWNER}}, "sender": {"login": gate.OWNER},
            "comment": {"id": 113, "body": REQUEST,
                        "created_at": "2026-11-14T15:00:00Z",
                        "author_association": "OWNER",
                        "user": {"login": gate.OWNER}}}


class Provider:
    def __init__(self):
        self.calls = []
        def run(name, id, sha, kind, branch):
            return {"name": name, "id": id, "head_sha": sha,
                    "event": kind, "head_branch": branch,
                    "status": "completed", "conclusion": "success",
                    "run_attempt": 1, "actor": {"login": gate.OWNER}}
        def comment(id, body, created):
            return {"id": id, "body": body,
                    "author_association": "OWNER",
                    "user": {"login": gate.OWNER},
                    "issue_url": "https://api.github.com/repos/" +
                                 gate.REPO + "/issues/807",
                    "created_at": created, "updated_at": created}
        self.entries = {
            PREFIX + "branches/main": {"name": "main", "protected": True,
                                       "commit": {"sha": TARGET}},
            PREFIX + "pulls/1660": {
                "number": 1660, "state": "closed", "merged": True,
                "merge_commit_sha": gate.BASE,
                "base": {"ref": "main", "sha":
                         "1a40fe4e3ec6e93a1631d59863b95e90981d734e"}},
            PREFIX + "pulls/1757": {"number": 1757, "state": "closed",
                "merged": True, "merge_commit_sha": TARGET,
                "user": {"login": gate.OWNER},
                "base": {"ref": "main", "sha": gate.BASE,
                         "repo": {"full_name": gate.REPO}},
                "head": {"ref": gate.BRANCH, "sha": HEAD,
                         "repo": {"full_name": gate.REPO}}},
            PREFIX + "compare/" + gate.BASE + "..." + TARGET +
            "?per_page=1&page=2": {"status": "ahead", "ahead_by": 3,
                "behind_by": 0, "merge_base_commit": {"sha": gate.BASE}},
            PREFIX + "git/commits/" + TARGET: {"sha": TARGET,
                                               "tree": {"sha": TREE}},
            PREFIX + "git/commits/" + HEAD: {"sha": HEAD,
                                             "tree": {"sha": TREE}},
            PREFIX + "actions/runs?head_sha=" + HEAD +
            "&event=pull_request&per_page=100": {"workflow_runs": [
                run(name, n+10, HEAD, "pull_request", gate.BRANCH)
                for n, name in enumerate(sorted(gate.CI))]},
            PREFIX + "actions/runs?head_sha=" + TARGET +
            "&event=push&branch=main&per_page=100": {"workflow_runs": [
                run("FORGE public Linux and Windows qualification",
                    50, TARGET, "push", "main")]},
            PREFIX + "issues/comments/111":
                comment(111, gate.BACKUP + TARGET, "2026-11-14T12:00:00Z"),
            PREFIX + "issues/comments/112":
                comment(112, gate.PAIR + TARGET + " 111",
                        "2026-11-14T13:00:00Z"),
            PREFIX + "issues/comments/113":
                comment(113, REQUEST, "2026-11-14T15:00:00Z"),
        }

    def __call__(self, route):
        self.calls.append(route)
        return copy.deepcopy(self.entries[route])


class HybridSuccessorProtectedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.remote = Provider()

    def source(self, environment=None):
        return gate.require_successor_source(
            self.remote, TARGET, env=env() if environment is None else environment)

    def intent(self, environment=None, issued=None):
        return gate.authenticate_owner_intent(
            self.remote, env() if environment is None else environment,
            event() if issued is None else issued,
            target=TARGET, run_id=987654,
            manifest_sha=BACKUP_SHA, approval_id=112)

    def test_qualified_merged_source_tree_pr_and_main_ci(self):
        proof = self.source()
        self.assertEqual(proof["qualified_pr_sha"], HEAD)
        self.assertEqual(set(proof["pr_run_ids"]), gate.CI)
        self.assertFalse(proof["source_transition_authorized"])
        self.assertFalse(proof["hybrid_admission"])

    def test_real_pair_and_legacy_bridge_route_to_successor_gate(self):
        from f139 import nci04_v41_hybrid_cold_pair as pair
        from f139 import nci04_v41_hybrid_protected_main as bridge
        self.assertEqual(pair._authenticate_candidate(
            self.remote, TARGET), TARGET)
        result = bridge.require_protected_main_release(
            self.remote, env(), target_sha=TARGET)
        self.assertEqual(result["source_sha"], TARGET)
        self.assertEqual(result["qualified_pr_sha"], HEAD)
        self.assertFalse(result["source_transition_authorized"])
        self.remote.entries[PREFIX+"pulls/1757"]["merged"] = False
        with self.assertRaises(gate.HybridSuccessorDenied):
            pair._authenticate_candidate(self.remote, TARGET)
        with self.assertRaises(gate.HybridSuccessorDenied):
            bridge.require_protected_main_release(
                self.remote, env(), target_sha=TARGET)

    def test_draft_bad_merge_ancestry_tree_denied(self):
        edits = [
            (PREFIX + "pulls/1757", ("merged", False)),
            (PREFIX + "pulls/1757", ("merge_commit_sha", HEAD)),
            (PREFIX + "branches/main", ("protected", False)),
            (PREFIX + "git/commits/" + HEAD, ("tree", {"sha": "f"*40})),
            (PREFIX + "compare/" + gate.BASE + "..." + TARGET +
             "?per_page=1&page=2", ("behind_by", 1)),
        ]
        for path, (key, bad) in edits:
            with self.subTest(key=key, path=path):
                old = copy.deepcopy(self.remote.entries[path])
                self.remote.entries[path][key] = bad
                try:
                    with self.assertRaises(gate.HybridSuccessorDenied):
                        self.source()
                finally:
                    self.remote.entries[path] = old

    def test_missing_failed_or_replayed_ci_denied(self):
        pr_path = PREFIX + "actions/runs?head_sha=" + HEAD + "&event=pull_request&per_page=100"
        main_path = PREFIX + "actions/runs?head_sha=" + TARGET + "&event=push&branch=main&per_page=100"
        for path, key, value in [
            (pr_path, "conclusion", "failure"),
            (pr_path, "run_attempt", 2),
            (pr_path, "head_branch", "other"),
            (main_path, "status", "in_progress"),
            (main_path, "actor", {"login": "other"}),
        ]:
            with self.subTest(path=path, key=key):
                old = copy.deepcopy(self.remote.entries[path])
                self.remote.entries[path]["workflow_runs"][0][key] = value
                try:
                    with self.assertRaises(gate.HybridSuccessorDenied):
                        self.source()
                finally:
                    self.remote.entries[path] = old
        old = copy.deepcopy(self.remote.entries[pr_path])
        self.remote.entries[pr_path]["workflow_runs"].pop()
        try:
            with self.assertRaises(gate.HybridSuccessorDenied):
                self.source()
        finally:
            self.remote.entries[pr_path] = old

    def test_three_owner_comments_order_and_identity(self):
        proof = self.intent()
        self.assertEqual(proof["owner_event_id"], 113)
        self.assertEqual(proof["backup_request_comment_id"], 111)
        self.assertEqual(self.remote.calls.count(PREFIX + "issues/comments/113"), 2)
        self.assertFalse(proof["source_transition_authorized"])

    def test_replayed_event_modified_comment_and_wrong_backup_denied(self):
        for key, value in [("GITHUB_RUN_ATTEMPT", "2"),
                           ("GITHUB_SHA", HEAD),
                           ("OPENAI_API_KEY", "forbidden"),
                           ("RUNNER_NAME", "hosted")]:
            with self.subTest(key=key), self.assertRaises(gate.HybridSuccessorDenied):
                self.intent(environment={**env(), key: value})
        with self.assertRaises(gate.HybridSuccessorDenied):
            self.intent(issued={**event(), "action": "edited"})
        path = PREFIX + "issues/comments/112"
        old = copy.deepcopy(self.remote.entries[path])
        self.remote.entries[path]["created_at"] = "2026-11-14T16:00:00Z"
        try:
            with self.assertRaises(gate.HybridSuccessorDenied):
                self.intent()
        finally:
            self.remote.entries[path] = old
        with self.assertRaises(gate.HybridSuccessorDenied):
            gate.authenticate_owner_intent(
                self.remote, env(), event(), target=TARGET, run_id=987654,
                manifest_sha="0"*64, approval_id=112)

    def test_original_owner_readiness_fails_closed_without_windows(self):
        with mock.patch.object(owner, "os", name="fake") as fake:
            fake.name = "posix"
            with self.assertRaisesRegex(
                    gate.HybridSuccessorDenied, "ORIGINAL_WINDOWS_HOST_REQUIRED"):
                owner.inspect_original(
                    Path("/tmp/not-original.sqlite"), env(), event(), self.remote,
                    target=TARGET, run_id=987654, manifest_sha=BACKUP_SHA,
                    approval_id=112)

    def test_readiness_never_touches_owner_task_or_database_writer(self):
        body = Path(owner.__file__).read_text(encoding="utf-8")
        ps = Path(owner.__file__).with_name(
            "v41_hybrid_successor_readiness.ps1").read_text(encoding="utf-8")
        for raw in (body, ps):
            for forbidden in (
                "Disable-ScheduledTask", "Enable-ScheduledTask",
                "Start-ScheduledTask", "Stop-ScheduledTask",
                "commit_transition(", "UPDATE meta SET",
                "workflow_dispatch", "gh api --method PATCH"):
                self.assertNotIn(forbidden, raw)
        self.assertIn("Database.open_readonly(", body)
        self.assertIn("transition.build_proof(", body)


if __name__ == "__main__":
    unittest.main()
