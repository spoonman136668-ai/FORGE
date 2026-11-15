"""Negative controls for the one-shot original V38 read-only cold ledger route."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical
from f139 import nci04_v38_owner_ledger_cold_readonly as cold
from f139 import nci04_v41_hybrid_original_commit as original
from f139 import nci04_v41_hybrid_forward_repair as forward
from scripts import check_rar_g145_pr_scope as g145

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/f139-v38-original-owner-readonly-once.yml"
DOC = ROOT / "docs/F139-V38-ORIGINAL-LEDGER-COLD-READONLY.md"


class V38ColdLedgerReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.target = "a" * 40
        self.head = "b" * 40
        self.mergetree = "c" * 40

    def release_get(self, route, *, broken=None):
        base = "repos/" + cold.REPO + "/"
        record = {
            base + "branches/main": {
                "name": "main", "protected": True,
                "commit": {"sha": self.target}},
            base + "pulls/1771": {
                "number": 1771, "state": "closed", "merged": True,
                "merge_commit_sha": self.target,
                "user": {"login": cold.OWNER},
                "head": {"ref": cold.BRANCH,
                         "sha": self.head, "repo": {"full_name": cold.REPO}},
                "base": {"ref": "main", "repo": {"full_name": cold.REPO}}},
            base + "git/commits/" + self.target: {
                "sha": self.target, "tree": {"sha": self.mergetree},
                "parents": [{"sha": cold.BASE}, {"sha": self.head}]},
            base + "git/commits/" + self.head: {
                "sha": self.head, "tree": {"sha": self.mergetree}},
            base + "actions/runs?head_sha=" + self.target +
            "&event=push&branch=main&per_page=100": {
                "workflow_runs": [{
                    "id": 9001, "head_sha": self.target, "event": "push",
                    "name": "FORGE public Linux and Windows qualification",
                    "run_attempt": 1, "status": "completed",
                    "conclusion": "success"}]},
            base + "actions/runs/9001/jobs?per_page=100": {
                "total_count": 8, "jobs": [
                    {"name": name, "status": "completed",
                     "conclusion": "success"}
                    for name in sorted(cold.EXPECTED_JOBS)]},
        }
        if broken:
            route_to_change, change = broken
            record[route_to_change] = change(record[route_to_change])
        if route not in record:
            raise AssertionError("unanticipated provider read " + route)
        return copy.deepcopy(record[route])

    def test_release_is_bound_to_exact_pr_tree_parent_and_8_full_jobs(self):
        self.assertEqual(cold._qualified_release(self.release_get, self.target),
                         self.target)
        base = "repos/" + cold.REPO + "/"
        for route, edit in (
            (base + "branches/main",
             lambda z: {**z, "commit": {"sha": cold.BASE}}),
            (base + "pulls/1771",
             lambda z: {**z, "merge_commit_sha": "e" * 40}),
            (base + "pulls/1771",
             lambda z: {**z, "user": {"login": "wrong-owner"}}),
            (base + "git/commits/" + self.target,
             lambda z: {**z, "tree": {"sha": "d" * 40}}),
            (base + "git/commits/" + self.target,
             lambda z: {**z, "parents": [{"sha": "d" * 40},
                                        {"sha": self.head}]}),
            (base + "actions/runs?head_sha=" + self.target +
             "&event=push&branch=main&per_page=100",
             lambda z: {"workflow_runs": [{**z["workflow_runs"][0],
                                            "run_attempt": 2}]}),
            (base + "actions/runs/9001/jobs?per_page=100",
             lambda z: {**z, "jobs": z["jobs"][:-1]}),
            (base + "actions/runs/9001/jobs?per_page=100",
             lambda z: {**z, "jobs": [{**j, "conclusion": "failure"}
                                      if j["name"] == "windows" else j
                                      for j in z["jobs"]]}),
        ):
            with self.subTest(route=route, changed=str(edit)):
                def get(k):
                    return self.release_get(k, broken=(route, edit))
                with self.assertRaises(cold.LedgerColdDenied):
                    cold._qualified_release(get, self.target)

    def test_frozen_owner_approval_is_canonical_and_nonactivation(self):
        frozen = {
            "schema": original.SCHEMA,
            "target_source_sha": forward.FROM,
            "backup_run_id": 43631799596,
            "backup_manifest_sha256": "d" * 64,
            "paired_approval_id": 6882932815,
            "readiness_comment_id": 6883009224,
            "original_head_seq": 1829,
            "original_head_sha256":
                "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8",
            "expected_proof_sha256": "e" * 64,
            "source_transition_requested": True,
            "task_resume_authorized": False,
            "policy_update_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0,
        }
        self.assertEqual(set(frozen), original.FIELDS)
        def getter(doc):
            return lambda route: {
                "id": cold.FROZEN_COMMIT, "author_association": "OWNER",
                "user": {"login": cold.OWNER},
                "body": original.PREFIX + canonical(doc).decode("ascii")}
        self.assertEqual(cold._frozen_approval(getter(frozen)), frozen)
        for k, changed in (("hybrid_admission", True),
                           ("task_resume_authorized", True),
                           ("new_dispatches", 1),
                           ("target_source_sha", "f" * 40),
                           ("original_head_seq", 1828)):
            with self.subTest(field=k):
                bad = {**frozen, k: changed}
                with self.assertRaises(cold.LedgerColdDenied):
                    cold._frozen_approval(getter(bad))

    def test_authentication_denies_wrong_owner_runner_replay_or_prior(self):
        id = cold.PREV_COMMENT + 5
        env = {
            "GITHUB_SHA": self.target, "GITHUB_REPOSITORY": cold.REPO,
            "GITHUB_REF": "refs/heads/main", "GITHUB_ACTOR": cold.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE", "GITHUB_RUN_ID": "90001",
        }
        event = {
            "action": "created",
            "issue": {"number": 807, "user": {"login": cold.OWNER}},
            "sender": {"login": cold.OWNER},
            "comment": {
                "id": id, "body": cold.PREFIX + self.target + " " +
                str(cold.PREV_COMMENT), "author_association": "OWNER",
                "user": {"login": cold.OWNER},
            },
        }
        prefix = "repos/" + cold.REPO + "/"
        def get(route):
            if route == prefix + "issues/comments/" + str(id):
                return {"id": id, "body": event["comment"]["body"],
                        "author_association": "OWNER",
                        "user": {"login": cold.OWNER},
                        "created_at": "2026-11-15T18:00:00Z",
                        "issue_url": "https://api.github.com/repos/" +
                                     cold.REPO + "/issues/807"}
            if route == prefix + "issues/comments/" + str(cold.PREV_COMMENT):
                return {"id": cold.PREV_COMMENT, "body": cold.PREV_BODY,
                        "author_association": "OWNER",
                        "user": {"login": cold.OWNER},
                        "created_at": "2026-11-15T10:15:00Z",
                        "issue_url": "https://api.github.com/repos/" +
                                     cold.REPO + "/issues/807"}
            if route == prefix + "actions/runs/" + str(cold.PREV_RUN):
                return {"id": cold.PREV_RUN, "head_sha": cold.PREV_SHA,
                        "run_attempt": 1, "event": "issue_comment",
                        "status": "completed", "conclusion": "success",
                        "actor": {"login": cold.OWNER}}
            if route == (prefix + "actions/runs/" + str(cold.PREV_RUN) +
                          "/jobs?per_page=100"):
                return {"total_count": 1, "jobs": [{
                    "name": "original-owner-readonly-task-snapshot",
                    "status": "completed", "conclusion": "success"}]}
            raise AssertionError("unexpected route")
        with (patch.object(cold.owner, "_owner_policy", return_value="policy"),
              patch.object(cold, "_qualified_release",
                           return_value=self.target),
              patch.object(cold, "_frozen_approval",
                           return_value={"sealed": True})):
            evidence = cold.authenticate(get, env, event)
            self.assertEqual(evidence["target"], self.target)
            self.assertEqual(evidence["frozen"], {"sealed": True})
            for patch_env in (
                {"GITHUB_RUN_ATTEMPT": "2"},
                {"GITHUB_ACTOR": "wrong"},
                {"RUNNER_NAME": "wrong"},
                {"OPENAI_API_KEY": "never"},
                {"GITHUB_SHA": cold.BASE},
            ):
                with self.assertRaises(cold.LedgerColdDenied):
                    cold.authenticate(get, {**env, **patch_env}, event)
            with self.assertRaises(cold.LedgerColdDenied):
                cold.authenticate(get, env, {**event,
                    "comment": {**event["comment"],
                                "author_association": "CONTRIBUTOR"}})

    def test_only_existing_owner_readonly_workflow_and_scope(self):
        w = WF.read_text("utf-8")
        self.assertIn("group: forge-f139-v38-original-ledger-cold-readonly-v1", w)
        self.assertIn("F139-V38-LEDGER-COLD-READONLY-V1 ", w)
        self.assertIn("6892848524", w)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", w)
        self.assertIn("nci04_v38_owner_ledger_cold_readonly", w)
        for forbidden in (
            "\n  schedule:", "\n  workflow_dispatch:", "\n  push:",
            "actions: write", "issues: write", "contents: write",
            "Set-ScheduledTask", "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Register-ScheduledTask", "upgrade-hybrid-lane",
            "gh api --method", "Start-Process",
        ):
            self.assertNotIn(forbidden, w)
        self.assertFalse(g145.generic_paths_safe([str(WF.relative_to(ROOT))]))
        self.assertTrue(DOC.is_file())
        self.assertIn("No hybrid scientific first-use", DOC.read_text("utf-8"))
        g145.v38_cold_ledger_negative_controls()


if __name__ == "__main__":
    unittest.main()
