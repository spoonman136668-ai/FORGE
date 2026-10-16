import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsa_source_audit import (audit_one, run, eligible, verify_ruleset,
                              GitHub, Blocked, REPO, RULESET, APP_ID, PUBLIC, FSA)

HEAD = "a" * 40
BASE = "b" * 40
BRANCH = "proposal/fsa-r21-test"


def pr():
    return {"number": 311, "state": "open", "draft": False,
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": HEAD, "ref": BRANCH, "repo": {"full_name": REPO}},
            "base": {"ref": "main", "sha": BASE}}


def rules():
    return {"id": RULESET, "name": "FORGE main qualified-source only",
            "source": REPO, "target": "branch", "enforcement": "active",
            "conditions": {"ref_name": {
                "include": ["refs/heads/main"], "exclude": []}},
            "node_id": "RRS_lACqUmVwb3NpdG9yec5UPTgWzgF9810",
            "updated_at": "2026-10-13T17:08:13.052-04:00",
            "current_user_can_bypass": "never", "bypass_actors": [],
            "rules": [{"type": "deletion"}, {"type": "non_fast_forward"},
              {"type": "pull_request", "parameters": {
                "dismiss_stale_reviews_on_push": True,
                "required_reviewers": [],
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": True,
                "allowed_merge_methods": ["merge"],
                "required_approving_review_count": 0,
                "require_extra_approval_for_unattributed_changes": True}},
              {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": True,
                "do_not_enforce_on_create": False,
                "required_status_checks": [
                 {"context": "linux", "integration_id": APP_ID},
                 {"context": "windows", "integration_id": APP_ID}]}}]}


def workflow(runid, path, event):
    return {"id": runid, "path": path, "head_sha": HEAD,
            "head_branch": BRANCH, "event": event, "run_attempt": 1,
            "status": "completed", "conclusion": "success",
            "repository": {"full_name": REPO}}


def jobs(runid, names):
    return {"jobs": [{"run_id": runid, "name": n, "status": "completed",
                      "conclusion": "success"} for n in names]}


class Fake:
    def __init__(self):
        self.calls = []
        self.candidate = pr()
        self.pages = {
            "/pulls?state=open&per_page=100": [self.candidate],
            "/pulls/311": self.candidate,
            "/branches/main": {"protected": True, "commit": {"sha": BASE}},
            "/pulls/311/files?per_page=100": [
                {"filename": "eligibility/source_test.go", "status": "added"}],
            "/actions/runs?head_sha=" + HEAD + "&per_page=100": {
                "workflow_runs": [
                 workflow(80, PUBLIC, "pull_request"),
                 workflow(81, FSA, "pull_request")]},
            "/actions/runs/80/jobs?per_page=100": jobs(80, ["linux", "windows"]),
            "/actions/runs/81/jobs?per_page=100": jobs(
                81, ["qualify (ubuntu-latest)", "qualify (windows-latest)"]),
            "/rulesets?includes_parents=true": [
                {"id": RULESET, "enforcement": "active"}],
            f"/rulesets/{RULESET}": rules(),
        }

    def get_page(self, path):
        # Synthetic GitHub Link-next transport; each response is bounded.
        self.calls.append(path)
        if path not in self.pages:
            raise Blocked("MISSING_OR_UNBOUNDED_GITHUB_PAGE")
        items = copy.deepcopy(self.pages[path])
        if not isinstance(items, list):
            raise Blocked("MISSING_OR_UNBOUNDED_GITHUB_PAGE")
        return items, len(items) == 100

    def get(self, path):
        self.calls.append(path)
        if path not in self.pages:
            raise AssertionError("unexpected API endpoint " + path)
        return copy.deepcopy(self.pages[path])


class SourceAuditTests(unittest.TestCase):
    def test_complete_fixture_qualifies_only_read_only(self):
        f = Fake()
        r = audit_one(f, f.candidate)
        self.assertTrue(r["SourceTestsQualified"])
        self.assertTrue(r["RulesetVisible"])
        self.assertEqual(r["Reason"], "SOURCE_ONLY_READ_AUDIT_PASSED_NO_MERGE_AUTHORITY")
        self.assertFalse(r["MergeAuthorized"])
        self.assertFalse(r["ScientificAuthority"])
        self.assertEqual(f.calls.count("/pulls/311"), 2)
        self.assertEqual(f.calls.count("/branches/main"), 2)
        self.assertTrue(all(url.startswith("/") for url in f.calls))

    def test_missing_independent_fsa_workflow_denied(self):
        f = Fake()
        f.pages["/actions/runs?head_sha=" + HEAD + "&per_page=100"][
            "workflow_runs"] = [workflow(80, PUBLIC, "pull_request")]
        r = audit_one(f, f.candidate)
        self.assertEqual(r["Reason"], "EXACT_HEAD_WORKFLOW_NOT_UNIQUE_OR_MISSING")

    def test_fake_successful_workflow_by_name_denied(self):
        f = Fake()
        f.pages["/actions/runs?head_sha=" + HEAD + "&per_page=100"][
            "workflow_runs"][1]["path"] = ".github/workflows/untrusted.yml"
        self.assertEqual(audit_one(f, f.candidate)["Reason"],
                         "EXACT_HEAD_WORKFLOW_NOT_UNIQUE_OR_MISSING")

    def test_stale_head_denied(self):
        f = Fake()
        f.pages["/pulls/311"] = pr()
        f.pages["/pulls/311"]["head"]["sha"] = "c" * 40
        self.assertEqual(audit_one(f, f.candidate)["Reason"], "PR_MUTATED_BEFORE_AUDIT")

    def test_stale_base_denied(self):
        f = Fake()
        f.pages["/branches/main"]["commit"]["sha"] = "c" * 40
        self.assertEqual(audit_one(f, f.candidate)["Reason"], "BASE_IDENTITY_CHANGED")

    def test_job_identity_denied(self):
        f = Fake()
        f.pages["/actions/runs/80/jobs?per_page=100"]["jobs"][1]["run_id"] = 999
        self.assertEqual(audit_one(f, f.candidate)["Reason"], "EXACT_HEAD_JOB_FAILED")

    def test_partial_windows_denied(self):
        f = Fake()
        f.pages["/actions/runs/80/jobs?per_page=100"]["jobs"][1]["conclusion"] = "skipped"
        self.assertEqual(audit_one(f, f.candidate)["Reason"], "EXACT_HEAD_JOB_FAILED")

    def test_unsafe_source_path_denied(self):
        f = Fake()
        f.pages["/pulls/311/files?per_page=100"][0]["filename"] = ".github/workflows/qualify.yml"
        self.assertEqual(audit_one(f, f.candidate)["Reason"], "UNSAFE_SOURCE_DELTA")

    def test_seven_files_denied(self):
        f = Fake()
        f.pages["/pulls/311/files?per_page=100"] = [
            {"filename": f"eligibility/source_{i}.go", "status": "added"}
            for i in range(7)]
        self.assertEqual(audit_one(f, f.candidate)["Reason"],
                         "MISSING_OR_UNBOUNDED_GITHUB_PAGE")

    def test_missing_bypass_is_not_assumed_empty(self):
        f = Fake()
        del f.pages[f"/rulesets/{RULESET}"]["bypass_actors"]
        r = audit_one(f, f.candidate)
        self.assertTrue(r["SourceTestsQualified"])
        self.assertFalse(r["RulesetVisible"])
        self.assertEqual(r["Reason"], "RULESET_BYPASS_VISIBILITY_MISSING")
        self.assertFalse(r["MergeAuthorized"])

    def test_nonempty_bypass_denied(self):
        f = Fake()
        f.pages[f"/rulesets/{RULESET}"]["bypass_actors"] = [{"actor_id": 2}]
        self.assertEqual(audit_one(f, f.candidate)["Reason"],
                         "RULESET_BYPASS_OR_CALLER_UNQUALIFIED")

    def test_draft_and_other_owner_not_eligible(self):
        f = Fake()
        f.candidate["draft"] = True
        self.assertFalse(eligible(f.candidate))
        f.candidate["draft"] = False
        f.candidate["user"]["login"] = "attacker"
        self.assertFalse(eligible(f.candidate))

    def test_no_candidates_is_no_action(self):
        f = Fake()
        f.pages["/pulls?state=open&per_page=100"] = []
        r = run(f)
        self.assertEqual(r["Count"], 0)
        self.assertEqual(r["Candidates"], [])
        self.assertFalse(r["MergeAuthorized"])
        self.assertEqual(len(f.calls), 1)

    def test_duplicate_open_prs_fail_closed_not_partial(self):
        f = Fake()
        f.pages["/pulls?state=open&per_page=100"] = [pr() for _ in range(100)]
        with self.assertRaisesRegex(Blocked, "DUPLICATE"):
            run(f)

    def test_101_open_prs_paginates_without_missing_eligible_candidate(self):
        f = Fake()
        first = []
        for num in range(1, 101):
            item = pr()
            item["number"] = num
            item["draft"] = True
            first.append(item)
        f.pages["/pulls?state=open&per_page=100"] = first
        f.pages["/pulls?state=open&per_page=100&page=2"] = [f.candidate]
        r = run(f)
        self.assertEqual(r["Count"], 1)
        self.assertEqual(r["Candidates"][0]["PR"], 311)
        self.assertIn("/pulls?state=open&per_page=100&page=2", f.calls)
        self.assertFalse(r["MergeAuthorized"])
        self.assertFalse(r["ScientificAuthority"])

    def test_pagination_page_missing_or_swapped_identity_denied(self):
        f = Fake()
        first = []
        for num in range(1, 101):
            item = pr()
            item["number"] = num
            item["draft"] = True
            first.append(item)
        f.pages["/pulls?state=open&per_page=100"] = first
        with self.assertRaisesRegex(Blocked, "MISSING_OR_UNBOUNDED"):
            run(f)
        f.pages["/pulls?state=open&per_page=100&page=2"] = [first[0]]
        with self.assertRaisesRegex(Blocked, "DUPLICATE"):
            run(f)

    def test_hard_page_ceiling_does_not_scan_or_authorize_partially(self):
        f = Fake()
        for page in range(1, 11):
            items = []
            for offset in range(100):
                item = pr()
                item["number"] = (page - 1) * 100 + offset + 1
                item["draft"] = True
                items.append(item)
            path = "/pulls?state=open&per_page=100"
            if page > 1:
                path += "&page=" + str(page)
            f.pages[path] = items
        with self.assertRaisesRegex(Blocked, "OPEN_PR_PAGE_BOUND_EXCEEDED"):
            run(f)
        self.assertFalse(any("/merge" in call for call in f.calls))

    def test_unqualified_workflow_run_attempt(self):
        f = Fake()
        f.pages["/actions/runs?head_sha=" + HEAD + "&per_page=100"][
            "workflow_runs"][0]["run_attempt"] = 2
        self.assertEqual(audit_one(f, f.candidate)["Reason"],
                         "UNQUALIFIED_WORKFLOW_ATTEMPT")


if __name__ == "__main__":
    unittest.main()
