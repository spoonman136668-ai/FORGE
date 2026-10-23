"""Adversarial, network-free tests of the CKB-owned Q21 first-use fence."""
import copy
import unittest
import admit_exact as a


def env():
    return {
        "GITHUB_REPOSITORY": a.CKB, "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_ACTOR": a.OWNER,
        "GITHUB_WORKFLOW_REF": a.CKB + "/.github/workflows/" +
                               a.WORKFLOW + "@refs/heads/main",
        "GITHUB_RUN_ID": "12345678", "GITHUB_SHA": "d" * 40,
    }


def response(route):
    if route == "/repos/" + a.CKB + "/actions/runs/12345678":
        return {"id": 12345678, "event": "workflow_dispatch",
                "head_sha": "d" * 40, "head_branch": "main",
                "path": ".github/workflows/" + a.WORKFLOW,
                "run_attempt": 1, "actor": {"login": a.OWNER},
                "triggering_actor": {"login": a.OWNER},
                "status": "in_progress", "conclusion": None}
    if route.startswith("/repos/" + a.CKB + "/actions/workflows/"):
        return {"total_count": 1, "workflow_runs": [{"id": 12345678}]}
    if route == "/repos/" + a.CKB + "/actions/runs/" + str(a.CKB_QUAL_RUN):
        return {"id": a.CKB_QUAL_RUN, "head_sha": a.CKB_QUAL_HEAD,
                "status": "completed", "conclusion": "success"}
    if route.startswith("/repos/" + a.CKB + "/contents/"):
        if route.endswith("/forge_q21_intake_v1.go?ref=" + "d" * 40):
            return {"type": "file", "sha": a.CKB_INTAKE}
        if route.endswith("/forge_q21_intake_v1_test.go?ref=" + "d" * 40):
            return {"type": "file", "sha": a.CKB_INTAKE_TESTS}
        raise AssertionError("Unrecognized CKB route: " + route)
    if route == "/repos/" + a.FORGE + "/git/commits/" + a.SOURCE:
        return {"tree": {"sha": a.TREE}}
    if route == "/repos/" + a.FORGE + "/git/blobs/" + a.PROTOCOL:
        return {"sha": a.PROTOCOL}
    if route == "/repos/" + a.FORGE + "/actions/runs/" + str(a.FORGE_FOCUSED_RUN):
        return {"id": a.FORGE_FOCUSED_RUN, "head_sha": a.SOURCE,
                "status": "completed", "conclusion": "success"}
    if route == "/repos/" + a.FORGE + "/actions/runs/" + str(a.FORGE_FULL_RUN):
        return {"id": a.FORGE_FULL_RUN, "head_sha": a.SOURCE,
                "status": "completed", "conclusion": "success"}
    if route == "/repos/" + a.FORGE + "/actions/runs/" + str(a.FORGE_FOCUSED_RUN) + "/jobs?per_page=100":
        return {"total_count": 2, "jobs": [
            {"name": "prequalify (windows-2022)", "conclusion": "success"},
            {"name": "prequalify (ubuntu-24.04)", "conclusion": "success"}]}
    raise AssertionError("Unexpected route: " + route)


class TestQ21AuthenticatedOneShot(unittest.TestCase):
    def test_positive_is_bounded_and_does_not_execute_science(self):
        result = a.admit(env(), response)
        self.assertEqual(result["decision"], "OWNER_AUTHENTICATED_SOURCEFREE_DEVELOPMENT_ONLY")
        self.assertEqual(result["ckb_run_id"], 12345678)
        self.assertFalse(result["scientific_execution_performed"])
        self.assertFalse(result["paid_external_models"])
        self.assertFalse(result["production_authority"])

    def test_preflight_does_not_call_network(self):
        # Without authenticated owner evidence, no science decision can be reached.
        for field, val in (
            ("GITHUB_REPOSITORY", a.FORGE),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_REF", "refs/heads/research"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_ACTOR", "other"),
            ("GITHUB_WORKFLOW_REF", a.CKB + "/.github/workflows/other.yml@refs/heads/main"),
            ("GITHUB_RUN_ID", "-1"),
            ("GITHUB_SHA", "malformed")):
            with self.subTest(field=field):
                e = env()
                e[field] = val
                with self.assertRaises(a.Refused):
                    a.admit(e, lambda _: self.fail("no network allowed"))

    def test_fail_closed_authenticated_github_mutations(self):
        paths = [
            "/repos/" + a.CKB + "/actions/runs/12345678",
            "/repos/" + a.CKB + "/actions/workflows/" +
            a.WORKFLOW + "/runs?event=workflow_dispatch&per_page=100",
            "/repos/" + a.CKB + "/actions/runs/" + str(a.CKB_QUAL_RUN),
            "/repos/" + a.CKB + "/contents/snapshot/source/internal/plane/forge_q21_intake_v1.go?ref=" + "d"*40,
            "/repos/" + a.FORGE + "/git/commits/" + a.SOURCE,
            "/repos/" + a.FORGE + "/git/blobs/" + a.PROTOCOL,
            "/repos/" + a.FORGE + "/actions/runs/" + str(a.FORGE_FOCUSED_RUN),
            "/repos/" + a.FORGE + "/actions/runs/" + str(a.FORGE_FOCUSED_RUN) + "/jobs?per_page=100"]
        changes = [
            ("CURRENT_CKB_RUN_WRONG_ACTOR", 0, lambda x: x["actor"].update(login="impostor")),
            ("CURRENT_CKB_RUN_ATTEMPT", 0, lambda x: x.update(run_attempt=2)),
            ("CURRENT_CKB_RUN_SOURCE", 0, lambda x: x.update(head_sha="0"*40)),
            ("CURRENT_CKB_RUN_STATUS", 0, lambda x: x.update(status="completed")),
            ("PRIOR_RUN_HISTORY_REPLAY", 1, lambda x: x.update(total_count=2)),
            ("CURRENT_HISTORY_MISSING", 1, lambda x: x.update(workflow_runs=[])),
            ("CKB_QUALIFIER_FAILED", 2, lambda x: x.update(conclusion="failure")),
            ("CKB_INTAKE_BLOB_DRIFT", 3, lambda x: x.update(sha="0"*40)),
            ("FORGE_TREE_DRIFT", 4, lambda x: x.update(tree={"sha":"0"*40})),
            ("PREREG_BLOB_DRIFT", 5, lambda x: x.update(sha="0"*40)),
            ("FORGE_QUALIFICATION_FAILED", 6, lambda x: x.update(conclusion="failure")),
            ("QUALIFIER_WINDOWS_MISSING", 7, lambda x: x["jobs"][0].update(conclusion="failure")),
            ("QUALIFIER_TRUNCATED", 7, lambda x: x.update(total_count=3))]
        for name, idx, mutate in changes:
            with self.subTest(name=name):
                path = paths[idx]
                def get(route):
                    val = copy.deepcopy(response(route))
                    if route == path: mutate(val)
                    return val
                with self.assertRaises(a.Refused):
                    a.admit(env(), get)

    def test_no_http_redirect_or_arbitrary_url(self):
        for token in ("", "x"*22+"\n"):
            with self.assertRaises(a.Refused):
                a.github_get(token, "/repos/" + a.CKB + "/actions/runs/1")
        with self.assertRaises(a.Refused):
            a.github_get("x"*22, "/repos/../secrets")


if __name__ == "__main__":
    unittest.main()
