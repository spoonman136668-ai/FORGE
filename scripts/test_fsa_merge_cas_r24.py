import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsa_merge_cas_r24 import preflight
from test_fsa_source_audit import Fake, HEAD, BASE, RULESET


class Prepared(Fake):
    def __init__(self):
        super().__init__()
        self.pages["/pulls/311"]["mergeable"] = True
        self.pages["/pulls/311"]["mergeable_state"] = "clean"
        self.pages["/pulls/311/reviews?per_page=100"] = []

    def get(self, path):
        return super().get(path)


class AtomicReadOnly(unittest.TestCase):
    def verify(self, f=None):
        f = f or Prepared()
        result = preflight(f, 311, HEAD, BASE)
        self.assertFalse(result["MergeAuthorized"])
        self.assertFalse(result["ScientificAuthority"])
        self.assertTrue(all(x.startswith("/") for x in f.calls))
        self.assertFalse(any("/merge" in x for x in f.calls))
        return result

    def test_hypothetical_clean_result_still_has_no_authority(self):
        f = Prepared()
        result = self.verify(f)
        self.assertEqual(result["Reason"],
                         "READ_ONLY_CAS_PREFLIGHT_OBSERVED_NO_MERGE_AUTHORITY")
        self.assertTrue(result["SourceChecksPassed"])
        self.assertTrue(result["StableHeadAndBase"])
        self.assertTrue(result["PolicyComplete"])
        self.assertTrue(result["MergeableObserved"])
        self.assertGreaterEqual(f.calls.count("/pulls/311"), 4)
        self.assertGreaterEqual(f.calls.count("/branches/main"), 4)

    def test_missing_bypass_metadata_blocks_approval(self):
        f = Prepared()
        del f.pages[f"/rulesets/{RULESET}"]["bypass_actors"]
        result = self.verify(f)
        self.assertTrue(result["SourceChecksPassed"])
        self.assertFalse(result["PolicyComplete"])
        self.assertEqual(result["Reason"],
                         "POLICY_VISIBILITY_BLOCKED:RULESET_BYPASS_VISIBILITY_MISSING")

    def test_nonempty_bypass_blocks(self):
        f = Prepared()
        f.pages[f"/rulesets/{RULESET}"]["bypass_actors"] = [{"actor_id": 7}]
        self.assertIn("RULESET_BYPASS_OR_CALLER_UNQUALIFIED",
                      self.verify(f)["Reason"])

    def test_full_sha_mismatch(self):
        f = Prepared()
        self.assertEqual(preflight(f, 311, "c" * 40, BASE)["Reason"],
                         "SOURCE_IDENTITY_OR_BASE_CHANGED")

    def test_base_mismatch(self):
        f = Prepared()
        self.assertEqual(preflight(f, 311, HEAD, "c" * 40)["Reason"],
                         "SOURCE_IDENTITY_OR_BASE_CHANGED")

    def test_short_sha_is_rejected(self):
        self.assertEqual(preflight(Prepared(), 311, HEAD[:12], BASE)["Reason"],
                         "INVALID_CAS_INPUT")

    def test_main_moves_during_final_check(self):
        class MovingMain(Prepared):
            def get(self, path):
                value = super().get(path)
                if path == "/branches/main" and self.calls.count(path) >= 4:
                    value["commit"]["sha"] = "c" * 40
                return value
        self.assertIn("MAIN_MOVED", self.verify(MovingMain())["Reason"])

    def test_pr_head_moves_after_source_audit(self):
        class MovingHead(Prepared):
            def get(self, path):
                value = super().get(path)
                if path == "/pulls/311" and self.calls.count(path) >= 4:
                    value["head"]["sha"] = "c" * 40
                return value
        self.assertEqual(self.verify(MovingHead())["Reason"],
                         "PR_HEAD_BASE_OR_BRANCH_DRIFT")

    def test_pr_becomes_draft_after_source_audit(self):
        class DraftFlip(Prepared):
            def get(self, path):
                value = super().get(path)
                if path == "/pulls/311" and self.calls.count(path) >= 4:
                    value["draft"] = True
                return value
        self.assertEqual(self.verify(DraftFlip())["Reason"], "PR_NO_LONGER_ELIGIBLE")

    def test_dirty_merge_state_denied(self):
        f = Prepared()
        f.pages["/pulls/311"]["mergeable_state"] = "blocked"
        self.assertEqual(self.verify(f)["Reason"], "GITHUB_MERGEABILITY_NOT_CLEAN")

    def test_changes_requested_denied_even_with_green_ci(self):
        f = Prepared()
        f.pages["/pulls/311/reviews?per_page=100"] = [
            {"state": "CHANGES_REQUESTED", "commit_id": HEAD}]
        self.assertEqual(self.verify(f)["Reason"], "CHANGES_REQUESTED")

    def test_missing_independent_fsa_workflow_denied(self):
        f = Prepared()
        key = "/actions/runs?head_sha=" + HEAD + "&per_page=100"
        f.pages[key]["workflow_runs"] = f.pages[key]["workflow_runs"][:1]
        self.assertIn("SOURCE_VERIFICATION_FAILED",
                      self.verify(f)["Reason"])

    def test_changed_ruleset_during_reads_denied(self):
        class MovingPolicy(Prepared):
            def get(self, path):
                value = super().get(path)
                if path == f"/rulesets/{RULESET}" and self.calls.count(path) >= 5:
                    value["updated_at"] = "changes-during-verification"
                return value
        self.assertEqual(self.verify(MovingPolicy())["Reason"],
                         "BRANCH_POLICY_CHANGED_DURING_PREFLIGHT")

    def test_untrusted_delta_never_admitted(self):
        f = Prepared()
        f.pages["/pulls/311/files?per_page=100"][0]["filename"] = ".github/workflows/evil.yml"
        self.assertIn("SOURCE_VERIFICATION_FAILED:UNSAFE_SOURCE_DELTA",
                      self.verify(f)["Reason"])


if __name__ == "__main__":
    unittest.main()
