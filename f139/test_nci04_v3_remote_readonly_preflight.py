"""Negative first-gate tests. No owner task, signing key or provider mutation."""
from __future__ import annotations

from copy import deepcopy
import unittest

from f139.nci04_fresh_owner_source_forward_v2 import CI_JOBS
from f139.nci04_v3_remote_readonly_preflight import (
    BASE_MAIN, BASE_TREE, REPO, V3RemotePreflightDenied,
    inspect_merged_source_readonly,
)

HEAD = "a" * 40
MERGE = "b" * 40
TREE = "c" * 40
PR = 1871
RUNS = {"regression_run_id": 111, "source_run_id": 222,
        "rehearsal_run_id": 333}


class FakeGET:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []
        self.alternate_main = None

    def get(self, path):
        self.calls.append(path)
        if (path == REPO + "/branches/main" and
                self.alternate_main is not None and
                self.calls.count(path) == 2):
            return deepcopy(self.alternate_main)
        return deepcopy(self.documents[path])


def fixture():
    branch = {"name": "main", "protected": True,
              "commit": {"sha": MERGE}}
    data = {
        REPO + "/branches/main": branch,
        REPO + "/git/commits/" + BASE_MAIN:
            {"sha": BASE_MAIN, "tree": {"sha": BASE_TREE}},
        REPO + "/git/commits/" + MERGE:
            {"sha": MERGE, "tree": {"sha": TREE},
             "parents": [{"sha": BASE_MAIN}, {"sha": HEAD}]},
        REPO + "/pulls/" + str(PR): {
            "number": PR, "state": "closed", "merged": True,
            "merge_commit_sha": MERGE,
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": HEAD, "repo": {"full_name":
                       "spoonman136668-ai/FORGE"}},
            "base": {"sha": BASE_MAIN, "ref": "main",
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
        },
    }
    for key, names in CI_JOBS:
        run_id = RUNS[key]
        data[REPO + "/actions/runs/" + str(run_id)] = {
            "id": run_id, "head_sha": HEAD, "event": "pull_request",
            "run_attempt": 1, "status": "completed", "conclusion": "success",
        }
        data[REPO + "/actions/runs/" + str(run_id) + "/jobs?per_page=100"] = {
            "total_count": len(names),
            "jobs": [{"name": name, "status": "completed",
                      "conclusion": "success"} for name in sorted(names)],
        }
    return FakeGET(data)


def verify(api=None, **changes):
    args = {"owner_source_sha": MERGE, "owner_source_tree": TREE,
            "pr_number": PR, "pr_head_sha": HEAD, **RUNS}
    args.update(changes)
    return inspect_merged_source_readonly(api or fixture(), **args)


class RemoteOnlyGateTests(unittest.TestCase):
    def test_exact_remote_evidence_verifies_without_creating_authority(self):
        api = fixture()
        result = verify(api)
        self.assertEqual(result["remote_evidence"], "VERIFIED_READ_ONLY")
        self.assertFalse(result["safe_to_disable_task"])
        self.assertFalse(result["signed_source_forward"])
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(result["worker_dispatches"], 0)
        self.assertEqual(api.calls[-1], REPO + "/branches/main")
        self.assertEqual(set(api.calls), set(api.documents))

    def test_historical_pr_and_source_replay_fail_before_network(self):
        for args in ({"pr_number": 1869}, {"pr_number": 1870},
                     {"owner_source_sha": BASE_MAIN},
                     {"owner_source_sha": HEAD},
                     {"regression_run_id": True},
                     {"owner_source_tree": "not-a-tree"}):
            with self.subTest(args=args):
                api = fixture()
                with self.assertRaises(V3RemotePreflightDenied):
                    verify(api, **args)
                self.assertEqual(api.calls, [])

    def test_merged_owner_and_parentage_are_immutable(self):
        for path, member, replacement in (
            (REPO + "/pulls/" + str(PR), "merged", False),
            (REPO + "/pulls/" + str(PR), "state", "open"),
            (REPO + "/pulls/" + str(PR), "merge_commit_sha", HEAD),
        ):
            with self.subTest(field=member):
                api = fixture()
                api.documents[path][member] = replacement
                with self.assertRaises(V3RemotePreflightDenied):
                    verify(api)
        api = fixture()
        api.documents[REPO + "/pulls/" + str(PR)]["user"]["login"] = "attacker"
        with self.assertRaises(V3RemotePreflightDenied):
            verify(api)
        api = fixture()
        api.documents[REPO + "/git/commits/" + MERGE]["parents"][1]["sha"] = "d" * 40
        with self.assertRaises(V3RemotePreflightDenied):
            verify(api)

    def test_moving_main_and_unprotected_main_rejected(self):
        api = fixture()
        api.alternate_main = {"name": "main", "protected": True,
                              "commit": {"sha": "d" * 40}}
        with self.assertRaisesRegex(V3RemotePreflightDenied, "MOVED"):
            verify(api)
        api = fixture()
        api.documents[REPO + "/branches/main"]["protected"] = False
        with self.assertRaises(V3RemotePreflightDenied):
            verify(api)

    def test_missing_failed_replayed_or_foreign_ci_denied(self):
        for change in ("missing", "failed", "rerun", "different-head",
                       "duplicate-job", "wrong-job-count"):
            with self.subTest(change=change):
                api = fixture()
                run = REPO + "/actions/runs/111"
                jobs = run + "/jobs?per_page=100"
                if change == "missing":
                    del api.documents[run]
                elif change == "failed":
                    api.documents[run]["conclusion"] = "failure"
                elif change == "rerun":
                    api.documents[run]["run_attempt"] = 2
                elif change == "different-head":
                    api.documents[run]["head_sha"] = "d" * 40
                elif change == "duplicate-job":
                    api.documents[jobs]["jobs"][1]["name"] = api.documents[jobs]["jobs"][0]["name"]
                else:
                    api.documents[jobs]["total_count"] += 1
                with self.assertRaises(V3RemotePreflightDenied):
                    verify(api)

    def test_source_tree_drift_and_provider_error_fail_closed(self):
        api = fixture()
        api.documents[REPO + "/git/commits/" + BASE_MAIN]["tree"]["sha"] = "d" * 40
        with self.assertRaises(V3RemotePreflightDenied):
            verify(api)
        api = fixture()
        api.documents[REPO + "/git/commits/" + MERGE]["tree"]["sha"] = "d" * 40
        with self.assertRaises(V3RemotePreflightDenied):
            verify(api)
        api = fixture()
        del api.documents[REPO + "/branches/main"]
        with self.assertRaises(V3RemotePreflightDenied):
            verify(api)


if __name__ == "__main__":
    unittest.main()
