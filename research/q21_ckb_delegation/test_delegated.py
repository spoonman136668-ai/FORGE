"""Untrusted-run, replay, CKB receipt, and no-science-before-owner negatives."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import delegated as d


def env():
    return {
        "GITHUB_REPOSITORY":d.owner.FORGE,
        "GITHUB_EVENT_NAME":"workflow_dispatch",
        "GITHUB_REF":"refs/heads/main",
        "GITHUB_RUN_ATTEMPT":"1",
        "GITHUB_ACTOR":d.owner.OWNER,
        "GITHUB_WORKFLOW_REF":d.owner.FORGE+
             "/.github/workflows/"+d.WORKFLOW+"@refs/heads/main",
        "GITHUB_RUN_ID":"12345678",
        "GITHUB_SHA":"a"*40,
    }


def route(path):
    if path=="/repos/"+d.owner.FORGE+"/actions/runs/12345678":
        return {"id":12345678,"head_sha":"a"*40,
                "head_branch":"main","event":"workflow_dispatch",
                "path":".github/workflows/"+d.WORKFLOW,
                "run_attempt":1,"actor":{"login":d.owner.OWNER},
                "triggering_actor":{"login":d.owner.OWNER},
                "status":"in_progress","conclusion":None}
    if path=="/repos/"+d.owner.CKB+"/actions/runs/87654321":
        return {"id":87654321,"event":"workflow_dispatch",
                "head_branch":"main",
                "head_sha":d.CKB_AUTHORIZED_COMMIT,
                "path":".github/workflows/"+d.owner.WORKFLOW,
                "run_attempt":1,"actor":{"login":d.owner.OWNER},
                "triggering_actor":{"login":d.owner.OWNER},
                "status":"in_progress","conclusion":None}
    if path.startswith("/repos/"+d.owner.FORGE+"/actions/workflows/"):
        return {"total_count":1,"workflow_runs":[{"id":12345678}]}
    if path.startswith("/repos/"+d.owner.CKB+"/actions/workflows/"):
        return {"total_count":1,"workflow_runs":[{"id":87654321}]}
    if path=="/repos/"+d.owner.CKB+"/git/commits/"+d.CKB_AUTHORIZED_COMMIT:
        return {"tree":{"sha":d.CKB_TREE}}
    if path.startswith("/repos/"+d.owner.CKB+"/contents/"):
        if path.endswith("/"+d.owner.WORKFLOW+"?ref="+d.CKB_AUTHORIZED_COMMIT):
            return {"sha":d.CKB_WORKFLOW_BLOB,"type":"file"}
        if path.endswith("/admit_exact.py?ref="+"b"*40):
            return {"sha":"cebda244cf0899e60ef07162969b594340b67b74","type":"file"}
        if path.endswith("/execute_dev.py?ref="+"b"*40):
            return {"sha":d.CKB_EXECUTOR_BLOB,"type":"file"}
    if path=="/repos/"+d.owner.CKB+"/actions/runs/87654321/jobs?per_page=100":
        return {"total_count":1,"jobs":[{"name":"owner-once",
                                         "status":"completed",
                                         "conclusion":"success"}]}
    if path=="/repos/"+d.owner.CKB+"/actions/runs/87654321/artifacts?per_page=100":
        return {"total_count":1,"artifacts":[{"name":"q21-owner-admission-87654321",
                                              "expired":False,
                                              "size_in_bytes":843}]}
    raise AssertionError("unexpected authenticated remote route "+path)


class TestDelegate(unittest.TestCase):
    def test_real_owner_metadata_required_even_with_lookup_hint(self):
        result=d.attest("87654321",env(),route)
        self.assertEqual(result["ckb_run_id"],87654321)
        self.assertEqual(result["scope"],d.SCOPE)

    def test_no_host_environment_impersonation(self):
        for field,value in (
            ("GITHUB_REPOSITORY",d.owner.CKB),
            ("GITHUB_EVENT_NAME","push"),
            ("GITHUB_REF","refs/heads/development"),
            ("GITHUB_ACTOR","other"),
            ("GITHUB_RUN_ATTEMPT","2"),
            ("GITHUB_RUN_ID","-1"),
            ("GITHUB_WORKFLOW_REF","other"),
            ("GITHUB_SHA","notsha")):
            with self.subTest(field=field):
                ctx=env();ctx[field]=value
                with self.assertRaises(d.Blocked):
                    d.attest("87654321",ctx,lambda _:self.fail("remote read on invalid run"))

    def test_remote_mutations_refused(self):
        paths=[
            "/repos/"+d.owner.FORGE+"/actions/runs/12345678",
            "/repos/"+d.owner.FORGE+"/actions/workflows/"+d.WORKFLOW+
              "/runs?event=workflow_dispatch&per_page=100",
            "/repos/"+d.owner.CKB+"/actions/runs/87654321",
            "/repos/"+d.owner.CKB+"/actions/workflows/"+d.owner.WORKFLOW+
              "/runs?event=workflow_dispatch&per_page=100",
            "/repos/"+d.owner.CKB+"/git/commits/"+d.CKB_AUTHORIZED_COMMIT,
            "/repos/"+d.owner.CKB+"/contents/.github/workflows/"+
              d.owner.WORKFLOW+"?ref="+d.CKB_AUTHORIZED_COMMIT,
            "/repos/"+d.owner.CKB+"/actions/runs/87654321/jobs?per_page=100",
            "/repos/"+d.owner.CKB+"/actions/runs/87654321/artifacts?per_page=100",
            "/repos/"+d.owner.CKB+"/actions/runs/87654321",
        ]
        mutate=[
            lambda z:z["actor"].update(login="impostor"),
            lambda z:z.update(total_count=2),
            lambda z:z.update(head_branch="not-main"),
            lambda z:z.update(workflow_runs=[]),
            lambda z:z.update(tree={"sha":"0"*40}),
            lambda z:z.update(sha="0"*40),
            lambda z:z["jobs"][0].update(conclusion="failure"),
            lambda z:z["artifacts"][0].update(expired=True),
            lambda z:z.update(head_sha="0"*40),
        ]
        for n,(path,alter) in enumerate(zip(paths,mutate)):
            with self.subTest(index=n):
                def fetch(href):
                    val=copy.deepcopy(route(href))
                    if href==path:alter(val)
                    return val
                with self.assertRaises(d.Blocked):
                    d.attest("87654321",env(),fetch)

    def test_no_science_without_authenticated_ckb(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td);dest=src/"science.json"
            with patch.object(d.ckbdev,"sourcefree_import",
                              side_effect=AssertionError("candidate imported before authority")):
                with self.assertRaises(d.Blocked):
                    d.execute(env(),"000",(src),dest,route)
            self.assertFalse(dest.exists())

    def test_no_science_on_source_drift_after_owner(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);dest=root/"science.json"
            with patch.object(d.ckbdev,"verify_source",
                              side_effect=d.Blocked("Q21_SOURCE_GIT_DRIFT")), \
                 patch.object(d.ckbdev,"sourcefree_import",
                              side_effect=AssertionError("candidate imported despite drift")):
                with self.assertRaises(d.Blocked):
                    d.execute(env(),"87654321",root,dest,route)
            self.assertFalse(dest.exists())

    def test_sourceonly_preflight(self):
        r=d.preflight()
        self.assertEqual(r["q21_episodes_generated"],0)
        self.assertEqual(r["delegated_authority"],"NONE")


if __name__=="__main__":
    unittest.main()
