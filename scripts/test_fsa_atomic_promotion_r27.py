import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsa_atomic_promotion_r27 import check, run
from test_fsa_source_audit import Fake, HEAD, BASE, RULESET, PUBLIC, FSA, workflow


class Ready(Fake):
    def __init__(self):
        super().__init__()
        self.pages["/pulls/311"]["mergeable"] = True
        self.pages["/pulls/311"]["mergeable_state"] = "clean"
        self.pages["/pulls/311/reviews?per_page=100"] = []


class R27FailClosed(unittest.TestCase):
    def inspect(self, fake=None):
        f = fake or Ready()
        r = check(f, 311, HEAD, BASE)
        self.assertFalse(r["MergeAuthorized"])
        self.assertFalse(r["ScientificAuthority"])
        self.assertTrue(all(url.startswith("/") for url in f.calls))
        self.assertFalse(any("/merge" in url for url in f.calls))
        return r

    def test_full_policy_hypothetical_clean_still_does_not_merge(self):
        f = Ready()
        r = self.inspect(f)
        self.assertTrue(r["SourceTestsQualified"])
        self.assertTrue(r["PolicyAnchorUnchanged"])
        self.assertTrue(r["FullRulesetVisible"])
        self.assertTrue(r["HeadAndBaseStable"])
        self.assertTrue(r["NativeReviewsUnblocked"])
        self.assertTrue(r["NativeMergeabilityClean"])
        self.assertEqual(r["Reason"], "R27_READ_ONLY_ATOMIC_PREFLIGHT_NO_MERGE_AUTHORITY")
        self.assertGreaterEqual(f.calls.count("/pulls/311"), 5)
        self.assertGreaterEqual(f.calls.count("/branches/main"), 5)

    def test_realistic_ephemeral_token_redacts_bypass(self):
        f = Ready()
        del f.pages[f"/rulesets/{RULESET}"]["bypass_actors"]
        del f.pages[f"/rulesets/{RULESET}"]["current_user_can_bypass"]
        r = self.inspect(f)
        self.assertTrue(r["SourceTestsQualified"])
        self.assertTrue(r["PolicyAnchorUnchanged"])
        self.assertFalse(r["FullRulesetVisible"])
        self.assertTrue(r["HeadAndBaseStable"])
        self.assertEqual(r["Reason"], "R27_REDACTED_BYPASS_ACTORS_NO_MERGE_AUTHORITY")

    def test_full_head_oid_required(self):
        f = Ready()
        r = check(f, 311, HEAD[:12], BASE)
        self.assertEqual(r["Reason"], "R27_INVALID_ATOMIC_SOURCE_IDENTITY")

    def test_full_base_oid_required(self):
        self.assertEqual(check(Ready(), 311, HEAD, "d" * 20)["Reason"],
                         "R27_INVALID_ATOMIC_SOURCE_IDENTITY")

    def test_initial_source_drift_denied(self):
        self.assertEqual(check(Ready(), 311, "c" * 40, BASE)["Reason"],
                         "R27_PR_SOURCE_OR_BASE_DRIFT")

    def test_initial_base_drift_denied(self):
        self.assertEqual(check(Ready(), 311, HEAD, "c" * 40)["Reason"],
                         "R27_PR_SOURCE_OR_BASE_DRIFT")

    def test_main_moves_at_start_denied(self):
        f = Ready()
        f.pages["/branches/main"]["commit"]["sha"] = "c" * 40
        self.assertEqual(self.inspect(f)["Reason"], "R27_MAIN_MOVED_BEFORE_AUDIT")

    def test_main_moves_at_final_snapshot_denied(self):
        class MovingMain(Ready):
            def get(self, path):
                value = super().get(path)
                if path == "/branches/main" and self.calls.count(path) >= 5:
                    value["commit"]["sha"] = "c" * 40
                return value
        self.assertEqual(self.inspect(MovingMain())["Reason"], "R27_FINAL_MAIN_DRIFT")

    def test_head_moves_at_last_pr_read_denied(self):
        class MovingHead(Ready):
            def get(self, path):
                value = super().get(path)
                if path == "/pulls/311" and self.calls.count(path) >= 5:
                    value["head"]["sha"] = "d" * 40
                return value
        self.assertEqual(self.inspect(MovingHead())["Reason"],
                         "R27_FINAL_HEAD_BASE_OR_MERGEABILITY_DRIFT")

    def test_pr_drafted_at_last_read_denied(self):
        class DraftAtEnd(Ready):
            def get(self, path):
                value = super().get(path)
                if path == "/pulls/311" and self.calls.count(path) >= 5:
                    value["draft"] = True
                return value
        self.assertEqual(self.inspect(DraftAtEnd())["Reason"],
                         "R27_FINAL_HEAD_BASE_OR_MERGEABILITY_DRIFT")

    def test_native_dirty_merge_denied(self):
        f = Ready()
        f.pages["/pulls/311"]["mergeable_state"] = "blocked"
        self.assertEqual(self.inspect(f)["Reason"], "R27_NATIVE_MERGEABILITY_NOT_CLEAN")

    def test_native_mergeability_unknown_denied(self):
        f = Ready()
        f.pages["/pulls/311"]["mergeable"] = None
        self.assertEqual(self.inspect(f)["Reason"], "R27_NATIVE_MERGEABILITY_NOT_CLEAN")

    def test_native_changes_requested_denied(self):
        f = Ready()
        f.pages["/pulls/311/reviews?per_page=100"] = [
            {"state": "CHANGES_REQUESTED", "commit_id": HEAD}]
        self.assertEqual(self.inspect(f)["Reason"], "R27_NATIVE_REVIEW_BLOCKED_OR_UNKNOWN")

    def test_native_dismissed_review_denied(self):
        f = Ready()
        f.pages["/pulls/311/reviews?per_page=100"] = [
            {"state": "DISMISSED", "commit_id": HEAD}]
        self.assertEqual(self.inspect(f)["Reason"], "R27_NATIVE_REVIEW_BLOCKED_OR_UNKNOWN")

    def test_unknown_native_review_state_fails_closed(self):
        f = Ready()
        f.pages["/pulls/311/reviews?per_page=100"] = [
            {"state": "UNKNOWN"}]
        self.assertEqual(self.inspect(f)["Reason"],
                         "R27_NATIVE_REVIEW_BLOCKED_OR_UNKNOWN")

    def test_missing_independent_fsa_workflow_denied(self):
        f = Ready()
        key = "/actions/runs?head_sha=" + HEAD + "&per_page=100"
        f.pages[key]["workflow_runs"] = [workflow(80, PUBLIC, "pull_request")]
        self.assertIn("R27_SOURCE_CHECKS_NOT_QUALIFIED",
                      self.inspect(f)["Reason"])

    def test_missing_required_windows_job_denied(self):
        f = Ready()
        f.pages["/actions/runs/80/jobs?per_page=100"]["jobs"] = [
            f.pages["/actions/runs/80/jobs?per_page=100"]["jobs"][0]]
        self.assertIn("R27_SOURCE_CHECKS_NOT_QUALIFIED",
                      self.inspect(f)["Reason"])

    def test_policy_changed_between_two_reads_denied(self):
        class PolicyChanges(Ready):
            def get(self, path):
                value = super().get(path)
                if path == f"/rulesets/{RULESET}" and self.calls.count(path) >= 4:
                    value["updated_at"] = "2026-10-15T21:08:13.052Z"
                return value
        self.assertEqual(self.inspect(PolicyChanges())["Reason"],
                         "R27_POLICY_CHANGED_DURING_AUDIT:RULESET_UPDATED_AFTER_AUTHENTICATED_OBSERVATION")

    def test_extra_policy_actor_denied(self):
        f = Ready()
        f.pages[f"/rulesets/{RULESET}"]["bypass_actors"] = [{"actor_id": 4}]
        self.assertIn("R27_SOURCE_POLICY_DENIED:RULESET_BYPASS_OR_CALLER_UNQUALIFIED",
                      self.inspect(f)["Reason"])

    def test_unsafe_workflow_path_change_denied(self):
        f = Ready()
        f.pages["/pulls/311/files?per_page=100"][0]["filename"] = \
            ".github/workflows/forge-automerge.yml"
        self.assertIn("R27_SOURCE_CHECKS_NOT_QUALIFIED", self.inspect(f)["Reason"])

    def test_no_eligible_candidates_performs_no_write(self):
        f = Ready()
        f.pages["/pulls?state=open&per_page=20"] = []
        r = run(f)
        self.assertEqual(r["Count"], 0)
        self.assertFalse(r["MergeAuthorized"])
        self.assertFalse(r["ScientificAuthority"])
        self.assertTrue(all(p.startswith("/") for p in f.calls))

    def test_open_pr_overflow_is_fail_closed(self):
        from fsa_source_audit import Blocked
        f = Ready()
        f.pages["/pulls?state=open&per_page=20"] = [f.candidate] * 20
        with self.assertRaises(Blocked):
            run(f)

    def test_stale_base_in_open_pr_is_denied_not_promoted(self):
        f = Ready()
        f.pages["/pulls?state=open&per_page=20"] = [f.candidate]
        f.pages["/pulls/311"]["base"]["sha"] = "c" * 40
        r = run(f)
        self.assertEqual(r["Count"], 1)
        self.assertEqual(r["Candidates"][0]["Reason"],
                         "R27_PR_SOURCE_OR_BASE_DRIFT")
        self.assertFalse(r["MergeAuthorized"])


if __name__ == "__main__":
    unittest.main()
