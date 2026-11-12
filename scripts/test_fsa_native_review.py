import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsa_native_review import Source, Denied, HOST

REPO = "spoonman136668-ai/FORGE"
SHA = "a" * 40


def pr(sha=SHA):
    return {"number": 241, "user": {"login": "spoonman136668-ai"},
            "head": {"sha": sha, "ref": "proposal/fsa-source",
                     "repo": {"full_name": REPO}},
            "base": {"ref": "main"}, "draft": False}


class Fake:
    def __init__(self):
        self.calls = []
        self.drift = False
        self.bad_link = False
        self.no_review = False
        self.truncated_thread = False
        self.pr_reads = 0

    def __call__(self, method, url, data):
        self.calls.append((method, url))
        path = urlsplit(url).path
        if method == "POST":
            if path != "/graphql" or "mutation" in str(data).lower():
                raise AssertionError("attempted mutation")
            threads = []
            if self.truncated_thread:
                threads = [{"isResolved": True,
                    "comments": {"nodes": [{"author": {"login": "chatgpt-codex-connector[bot]"}}],
                                 "pageInfo": {"hasNextPage": True}}}]
            return {"data": {"repository": {"pullRequest": {
                "reviewThreads": {"nodes": threads, "pageInfo": {
                    "hasNextPage": False, "endCursor": None}}}}}}, ""
        if path == "/repos/" + REPO + "/pulls/241":
            self.pr_reads += 1
            return pr("b" * 40 if self.drift and self.pr_reads == 2 else SHA), ""
        if path.endswith("/files"):
            if parse_qs(urlsplit(url).query).get("page") == ["2"]:
                return [], ""
            if self.bad_link:
                return [{"filename": "eligibility/f.go", "status": "added"}], (
                    '<https://attacker.example/x?page=2>; rel="next"')
            return [{"filename": "eligibility/f.go", "status": "added"}], (
                '<' + HOST + path + '?per_page=100&page=2>; rel="next"')
        if path.endswith("/reviews"):
            return ([] if self.no_review else [{"user": {
                "login": "chatgpt-codex-connector[bot]"},
                "commit_id": SHA, "state": "APPROVED"}]), ""
        if path.endswith("/comments"):
            return [], ""
        if path.endswith("/runs"):
            return {"workflow_runs": [
                {"id": 1, "path": ".github/workflows/qualify.yml",
                 "name": "FORGE public Linux and Windows qualification",
                 "head_sha": SHA, "status": "completed", "conclusion": "success"},
                {"id": 2, "path": ".github/workflows/qualify-fsa02.yml",
                 "name": "FORGE FSA-02 qualification",
                 "head_sha": SHA, "status": "completed", "conclusion": "success"}]}, ""
        if path.endswith("/1/jobs"):
            return {"jobs": [{"name": "linux", "conclusion": "success"},
                             {"name": "windows", "conclusion": "success"}]}, ""
        if path.endswith("/2/jobs"):
            return {"jobs": [{"name": "qualify", "conclusion": "success"}]}, ""
        raise AssertionError((method, url))


class SourceTests(unittest.TestCase):
    def test_real_shapes_pagination_and_exact_review(self):
        f = Fake()
        v = Source(REPO, transport=f).collect(241)
        self.assertEqual(v["PR"]["HeadSHA"], SHA)
        self.assertEqual(v["Reviews"][0]["CommitID"], SHA)
        self.assertEqual(v["Runs"][0]["Jobs"]["windows"], "success")
        self.assertTrue(all(v["Pages"].values()))
        self.assertEqual(f.pr_reads, 2)
        self.assertEqual([m for m, _ in f.calls].count("POST"), 1)
        self.assertFalse(any(m not in ("GET", "POST") for m, _ in f.calls))

    def test_drift_fails_closed(self):
        f = Fake()
        f.drift = True
        with self.assertRaisesRegex(Denied, "HEAD_OR_STATE_DRIFT"):
            Source(REPO, transport=f).collect(241)

    def test_untrusted_pagination_fails(self):
        f = Fake()
        f.bad_link = True
        with self.assertRaisesRegex(Denied, "UNTRUSTED_NEXT_LINK"):
            Source(REPO, transport=f).collect(241)

    def test_missing_native_review_not_invented(self):
        f = Fake()
        f.no_review = True
        self.assertEqual(Source(REPO, transport=f).collect(241)["Reviews"], [])

    def test_partial_thread_is_explicitly_incomplete(self):
        f = Fake()
        f.truncated_thread = True
        result = Source(REPO, transport=f).collect(241)
        self.assertFalse(result["Threads"][0]["Complete"])

    def test_scope_and_repo_validation(self):
        with self.assertRaisesRegex(Denied, "INVALID_REPOSITORY"):
            Source("not-a-repo", transport=Fake())


if __name__ == "__main__":
    unittest.main()
