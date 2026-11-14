"""Frozen protected-main original-owner Hybrid bridge negative controls."""
import unittest

from f139 import nci04_v41_hybrid_protected_main as bridge

TARGET = "a"*40
TREE = "b"*40


class ProtectedMainHybridTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "GITHUB_REPOSITORY":bridge.REPO, "GITHUB_ACTOR":bridge.OWNER,
            "GITHUB_REF":"refs/heads/main","GITHUB_EVENT_NAME":"issue_comment",
            "GITHUB_SHA":TARGET,"GITHUB_RUN_ATTEMPT":"1",
            "RUNNER_NAME":"FORGE-CODEX-REMOTE"}
        self.main = {"name":"main","protected":True,
                     "commit":{"sha":TARGET}}
        self.pr = {"number":1660,"state":"closed","merged":True,
                   "merge_commit_sha":TARGET,
                   "user":{"login":bridge.OWNER},
                   "head":{"repo":{"full_name":bridge.REPO}},
                   "base":{"ref":"main","sha":bridge.V41,
                           "repo":{"full_name":bridge.REPO}}}
        self.commit = {"sha":TARGET,"tree":{"sha":TREE}}
        self.runs = {"workflow_runs":[
            {"id":i+200,"name":name,"head_sha":TARGET,"event":"push",
             "head_branch":"main","status":"completed",
             "conclusion":"success","run_attempt":1,
             "actor":{"login":bridge.OWNER}}
            for i,name in enumerate(sorted(bridge.CI_NAMES))]}
        self.paths = []

    def get(self,path):
        self.paths.append(path)
        prefix="repos/"+bridge.REPO+"/"
        if path==prefix+"branches/main":
            return self.main
        if path==prefix+"pulls/1660":
            return self.pr
        if path==prefix+"git/commits/"+TARGET:
            return self.commit
        if path==prefix+"actions/runs?head_sha="+TARGET+"&event=push&branch=main&per_page=100":
            return self.runs
        raise AssertionError("noncanonical route: "+path)

    def auth(self,env=None,get=None):
        return bridge.require_protected_main_release(
            self.get if get is None else get,
            self.env if env is None else env, target_sha=TARGET)

    def test_protected_merge_with_four_postmerge_workflows(self):
        value=self.auth()
        self.assertEqual(value["source_sha"],TARGET)
        self.assertEqual(value["source_tree_sha"],TREE)
        self.assertEqual(len(value["qualification_run_ids"]),4)
        self.assertFalse(value["owner_maintenance_authorized"])
        self.assertFalse(value["source_transition_authorized"])
        self.assertFalse(value["hybrid_admission"])
        self.assertEqual(self.paths.count(
            "repos/"+bridge.REPO+"/branches/main"),2)

    def test_open_pr_unmerged_source_not_execution_authority(self):
        self.pr["state"]="open"
        self.pr["merged"]=False
        with self.assertRaisesRegex(bridge.ProtectedHybridSourceDenied,
                                    "MERGED_PR1660"):
            self.auth()

    def test_unprotected_main_or_old_v41_main_denied(self):
        self.main["protected"]=False
        with self.assertRaisesRegex(bridge.ProtectedHybridSourceDenied,
                                    "PROTECTED_MAIN"):
            self.auth()
        self.main["protected"]=True
        self.main["commit"]["sha"]=bridge.V41
        with self.assertRaisesRegex(bridge.ProtectedHybridSourceDenied,
                                    "PROTECTED_MAIN"):
            self.auth()

    def test_bad_pr_origin_or_merge_sha_denied(self):
        for field in ("state","merge_commit_sha","base","head","user"):
            old=self.pr[field]
            if field=="state": self.pr[field]="open"
            if field=="merge_commit_sha": self.pr[field]="f"*40
            if field=="base": self.pr[field]={"ref":"main","sha":"f"*40,
                                            "repo":{"full_name":bridge.REPO}}
            if field=="head": self.pr[field]={"repo":{"full_name":"other/FORGE"}}
            if field=="user": self.pr[field]={"login":"other"}
            with self.subTest(field=field),self.assertRaisesRegex(
                    bridge.ProtectedHybridSourceDenied,"MERGED_PR1660"):
                self.auth()
            self.pr[field]=old

    def test_wrong_main_event_or_rerun_denied(self):
        for key,val in (
                ("GITHUB_SHA",bridge.V41),
                ("GITHUB_REF","refs/pull/1660/merge"),
                ("GITHUB_ACTOR","other"),
                ("RUNNER_NAME","ubuntu-latest"),
                ("GITHUB_RUN_ATTEMPT","2"),
                ("GITHUB_EVENT_NAME","pull_request"),
                ("OPENAI_API_KEY","secret")):
            with self.subTest(key=key),self.assertRaisesRegex(
                    bridge.ProtectedHybridSourceDenied,"OWNER_EVENT"):
                self.auth(env={**self.env,key:val})

    def test_missing_duplicate_failed_or_replayed_ci_denied(self):
        original=self.runs["workflow_runs"]
        try:
            for operation in ("missing","duplicate","failed","attempt2",
                              "wrongsha","wrongactor","pending"):
                items=[dict(row) for row in original]
                if operation=="missing": items.pop()
                if operation=="duplicate": items.append(dict(items[0]))
                if operation=="failed": items[0]["conclusion"]="failure"
                if operation=="attempt2": items[0]["run_attempt"]=2
                if operation=="wrongsha": items[0]["head_sha"]="f"*40
                if operation=="wrongactor": items[0]["actor"]={"login":"other"}
                if operation=="pending": items[0]["status"]="in_progress"
                self.runs["workflow_runs"]=items
                with self.subTest(operation=operation),self.assertRaisesRegex(
                        bridge.ProtectedHybridSourceDenied,"CI_"):
                    self.auth()
        finally:
            self.runs["workflow_runs"]=original

    def test_main_changed_between_proofs_denied(self):
        seen=[0]
        def changing(route):
            if route.endswith("/branches/main"):
                seen[0]+=1
                if seen[0]==2:
                    return {"name":"main","protected":True,
                            "commit":{"sha":"f"*40}}
            return self.get(route)
        with self.assertRaisesRegex(
                bridge.ProtectedHybridSourceDenied,
                "PROTECTED_MAIN"):
            self.auth(get=changing)
        self.assertEqual(seen,[2])

    def test_no_writes_or_live_execution(self):
        import inspect
        code=inspect.getsource(bridge)
        for forbidden in ("workflow_dispatch(","db.event(","UPDATE meta SET",
                          "Stop-ScheduledTask","Start-ScheduledTask",
                          "gh api --method PATCH","create_ref("):
            self.assertNotIn(forbidden,code)


if __name__=="__main__":
    unittest.main()
