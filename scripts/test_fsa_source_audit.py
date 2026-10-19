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
            "/pulls?state=open&per_page=20": [self.candidate],
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
        return items, len(items) == 20

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
        f.pages["/pulls?state=open&per_page=20"] = []
        r = run(f)
        self.assertEqual(r["Count"], 0)
        self.assertEqual(r["Candidates"], [])
        self.assertFalse(r["MergeAuthorized"])
        self.assertEqual(len(f.calls), 1)

    def test_duplicate_open_prs_fail_closed_not_partial(self):
        f = Fake()
        f.pages["/pulls?state=open&per_page=20"] = [pr() for _ in range(20)]
        with self.assertRaisesRegex(Blocked, "DUPLICATE"):
            run(f)

    def test_101_open_prs_paginates_without_missing_eligible_candidate(self):
        f = Fake()
        # The same 101 identities must all be examined across six *small*
        # GitHub Link-announced pages: no truncation or sampling.
        for page in range(1, 6):
            rows = []
            for num in range((page - 1) * 20 + 1, page * 20 + 1):
                item = pr()
                item["number"] = num
                item["draft"] = True
                rows.append(item)
            f.pages["/pulls?state=open&per_page=20" +
                    ("&page=" + str(page) if page > 1 else "")] = rows
        f.pages["/pulls?state=open&per_page=20&page=6"] = [f.candidate]
        r = run(f)
        self.assertEqual(r["Count"], 1)
        self.assertEqual(r["Candidates"][0]["PR"], 311)
        self.assertIn("/pulls?state=open&per_page=20&page=6", f.calls)
        self.assertFalse(r["MergeAuthorized"])
        self.assertFalse(r["ScientificAuthority"])

    def test_pagination_page_missing_or_swapped_identity_denied(self):
        f = Fake()
        first = []
        for num in range(1, 21):
            item = pr()
            item["number"] = num
            item["draft"] = True
            first.append(item)
        f.pages["/pulls?state=open&per_page=20"] = first
        with self.assertRaisesRegex(Blocked, "MISSING_OR_UNBOUNDED"):
            run(f)
        f.pages["/pulls?state=open&per_page=20&page=2"] = [first[0]]
        with self.assertRaisesRegex(Blocked, "DUPLICATE"):
            run(f)

    def test_hard_page_ceiling_does_not_scan_or_authorize_partially(self):
        f = Fake()
        for page in range(1, 51):
            items = []
            for offset in range(20):
                item = pr()
                item["number"] = (page - 1) * 20 + offset + 1
                item["draft"] = True
                items.append(item)
            path = "/pulls?state=open&per_page=20"
            if page > 1:
                path += "&page=" + str(page)
            f.pages[path] = items
        with self.assertRaisesRegex(Blocked, "OPEN_PR_PAGE_BOUND_EXCEEDED"):
            run(f)
        self.assertFalse(any("/merge" in call for call in f.calls))

    def test_github_canonical_numeric_repo_link_is_identity_pinned(self):
        from unittest.mock import patch
        import json
        class HTTP:
            def __init__(self, link):
                self.headers = {"Link": link}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, max_bytes):
                return json.dumps([{"number": 311}]).encode()
        g = GitHub(token="synthetic-test-token")
        for suffix,should_accept in (
            ("/repositories/1413298198/pulls",True),
            ("/repos/spoonman136668-ai/FORGE/pulls",True),
            ("/repositories/1413298199/pulls",False),
            ("/repos/other/FORGE/pulls",False),
        ):
            link = "<https://api.github.com" + suffix + \
                   "?state=open&per_page=20&page=2>; rel=\"next\""
            with patch("urllib.request.urlopen",return_value=HTTP(link)):
                if should_accept:
                    page,next_page=g.get_page("/pulls?state=open&per_page=20")
                    self.assertEqual(len(page),1)
                    self.assertTrue(next_page)
                else:
                    with self.assertRaisesRegex(Blocked, "UNTRUSTED_PAGINATION_NEXT_ROUTE"):
                        g.get_page("/pulls?state=open&per_page=20")

    def test_oversized_single_response_remains_fail_closed(self):
        from unittest.mock import patch
        class HTTP:
            headers = {"Link": ""}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                self_read_limit = count
                return b"x" * self_read_limit
        with patch("urllib.request.urlopen",return_value=HTTP()):
            with self.assertRaisesRegex(Blocked,"RESPONSE_TOO_LARGE"):
                GitHub(token="fixture").get_page("/pulls?state=open&per_page=20")

    def test_non_inventory_page_size_is_rejected(self):
        with self.assertRaisesRegex(Blocked,"UNSAFE_OPEN_PR_PAGINATION"):
            GitHub(token="fixture").get_page("/pulls?state=open&per_page=100")

    def test_partial_first_page_with_unexpected_next_is_denied(self):
        from unittest.mock import patch
        import json
        class HTTP:
            headers = {"Link": "<https://api.github.com/repos/spoonman136668-ai/FORGE/pulls?state=open&per_page=20&page=2>; rel=\"next\""}
            def __enter__(self):
                return self
            def __exit__(self,*args):
                return False
            def read(self,n):
                return json.dumps([{"number":1}]).encode()
        with patch("urllib.request.urlopen",return_value=HTTP()):
            g=GitHub(token="fixture")
            with self.assertRaisesRegex(Blocked,"INCOMPLETE_OPEN_PR_PAGINATION"):
                # The Link-announced continuation must never conceal a
                # short page or let a partial census pass.
                from fsa_source_audit import list_open_prs
                list_open_prs(g)

    def test_unqualified_workflow_run_attempt(self):
        f = Fake()
        f.pages["/actions/runs?head_sha=" + HEAD + "&per_page=100"][
            "workflow_runs"][0]["run_attempt"] = 2
        self.assertEqual(audit_one(f, f.candidate)["Reason"],
                         "UNQUALIFIED_WORKFLOW_ATTEMPT")


if __name__ == "__main__":
    unittest.main()
