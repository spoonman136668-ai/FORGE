"""Frozen merged-main/PR-tree/source-CI original-owner trust negatives."""
import unittest

from f139 import nci04_v41_hybrid_protected_main as bridge

TARGET = "a"*40
TREE = "b"*40
PR_HEAD = "c"*40
PR_BRANCH = "engineering/f139-hybrid-reader-route-20261110"


class ProtectedMainHybridTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "GITHUB_REPOSITORY":bridge.REPO,"GITHUB_ACTOR":bridge.OWNER,
            "GITHUB_REF":"refs/heads/main","GITHUB_EVENT_NAME":"issue_comment",
            "GITHUB_SHA":TARGET,"GITHUB_RUN_ATTEMPT":"1",
            "RUNNER_NAME":"FORGE-CODEX-REMOTE"}
        self.main = {"name":"main","protected":True,
                     "commit":{"sha":TARGET}}
        self.pr = {"number":1660,"state":"closed","merged":True,
                   "merge_commit_sha":TARGET,
                   "user":{"login":bridge.OWNER},
                   "head":{"sha":PR_HEAD,"ref":PR_BRANCH,
                           "repo":{"full_name":bridge.REPO}},
                   "base":{"ref":"main","sha":bridge.V41,
                           "repo":{"full_name":bridge.REPO}}}
        self.main_commit = {"sha":TARGET,"tree":{"sha":TREE}}
        self.pr_commit = {"sha":PR_HEAD,"tree":{"sha":TREE}}
        self.ancestry = {"status":"ahead","ahead_by":3,"behind_by":0,
                         "merge_base_commit":{"sha":bridge.V41}}
        self.pr_runs = {"workflow_runs":[
            {"id":i+200,"name":name,"head_sha":PR_HEAD,
             "event":"pull_request","head_branch":PR_BRANCH,
             "status":"completed","conclusion":"success",
             "run_attempt":1,"actor":{"login":bridge.OWNER}}
            for i,name in enumerate(sorted(bridge.CI_NAMES))]}
        self.main_runs = {"workflow_runs":[{
            "id":345,"name":"FORGE public Linux and Windows qualification",
            "head_sha":TARGET,"event":"push","head_branch":"main",
            "status":"completed","conclusion":"success",
            "run_attempt":1,"actor":{"login":bridge.OWNER}
        }]}
        self.paths = []

    def get(self,path):
        self.paths.append(path)
        prefix="repos/"+bridge.REPO+"/"
        if path==prefix+"branches/main":return self.main
        if path==prefix+"pulls/1660":return self.pr
        if path==prefix+"git/commits/"+TARGET:return self.main_commit
        if path==prefix+"git/commits/"+PR_HEAD:return self.pr_commit
        if path==(prefix+"compare/"+bridge.V41+"..."+TARGET
                 +"?per_page=1&page=2"):
            return self.ancestry
        if path==prefix+"actions/runs?head_sha="+PR_HEAD+"&event=pull_request&per_page=100":
            return self.pr_runs
        if path==prefix+"actions/runs?head_sha="+TARGET+"&event=push&branch=main&per_page=100":
            return self.main_runs
        raise AssertionError("unexpected native route: "+path)

    def auth(self,env=None,get=None):
        return bridge.require_protected_main_release(
            self.get if get is None else get,
            self.env if env is None else env,target_sha=TARGET)

    def test_merged_main_exact_tree_with_four_pr_and_one_push_ci(self):
        value=self.auth()
        self.assertEqual(value["source_sha"],TARGET)
        self.assertEqual(value["qualified_pr_source_sha"],PR_HEAD)
        self.assertEqual(value["source_tree_sha"],TREE)
        self.assertEqual(len(value["qualification_run_ids"]),4)
        self.assertEqual(value["protected_main_qualification_run_id"],345)
        self.assertTrue(value["qualified_source_tree_parity"])
        self.assertFalse(value["owner_maintenance_authorized"])
        self.assertFalse(value["source_transition_authorized"])
        self.assertFalse(value["hybrid_admission"])
        self.assertEqual(self.paths.count(
            "repos/"+bridge.REPO+"/branches/main"),2)

    def test_unmerged_open_pr_is_never_owner_execution_authority(self):
        self.pr["state"]="open"
        self.pr["merged"]=False
        with self.assertRaisesRegex(bridge.ProtectedHybridSourceDenied,
                                    "MERGED_PR1660"):
            self.auth()

    def test_unprotected_main_or_old_v41_denied(self):
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
        cases=[
            ("state","open"),
            ("merge_commit_sha","f"*40),
            ("base",{"ref":"main","sha":"f"*40,
                     "repo":{"full_name":bridge.REPO}}),
            ("head",{"sha":PR_HEAD,"ref":PR_BRANCH,
                     "repo":{"full_name":"other/FORGE"}}),
            ("user",{"login":"other"}),
        ]
        for field,bad in cases:
            old=self.pr[field]
            self.pr[field]=bad
            with self.subTest(field=field),self.assertRaisesRegex(
                    bridge.ProtectedHybridSourceDenied,"MERGED_PR1660"):
                self.auth()
            self.pr[field]=old

    def test_original_v41_ancestry_required_and_base_pointer_can_move(self):
        self.pr["base"]["sha"]=TARGET
        self.assertTrue(self.auth()["postmerge_ci_verified"])
        for change in ({"status":"diverged"},{"behind_by":1},
                       {"merge_base_commit":{"sha":"f"*40}}):
            old=self.ancestry
            self.ancestry={**old,**change}
            with self.subTest(change=change),self.assertRaisesRegex(
                    bridge.ProtectedHybridSourceDenied,
                    "V41_SOURCE_ANCESTRY"):
                self.auth()
            self.ancestry=old

    def test_merge_tree_is_exact_qualified_pr_tree(self):
        self.main_commit["tree"]["sha"]="f"*40
        with self.assertRaisesRegex(
                bridge.ProtectedHybridSourceDenied,
                "PROTECTED_MAIN_TREE_DIFFERS"):
            self.auth()

    def test_wrong_main_event_rerun_or_untrusted_runner_denied(self):
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

    def test_pr_missing_duplicate_failure_wrong_sha_or_retry_denied(self):
        saved=self.pr_runs["workflow_runs"]
        try:
            for case in ("missing","duplicate","failed","attempt2",
                         "wrongsha","wrongactor","pending"):
                items=[dict(z) for z in saved]
                if case=="missing":items.pop()
                if case=="duplicate":items.append(dict(items[0]))
                if case=="failed":items[0]["conclusion"]="failure"
                if case=="attempt2":items[0]["run_attempt"]=2
                if case=="wrongsha":items[0]["head_sha"]="f"*40
                if case=="wrongactor":items[0]["actor"]={"login":"other"}
                if case=="pending":items[0]["status"]="in_progress"
                self.pr_runs["workflow_runs"]=items
                with self.subTest(case=case),self.assertRaisesRegex(
                        bridge.ProtectedHybridSourceDenied,"PREMERGE"):
                    self.auth()
        finally:
            self.pr_runs["workflow_runs"]=saved

    def test_main_push_missing_failed_rerun_or_mismatched_denied(self):
        saved=self.main_runs["workflow_runs"]
        try:
            for case in ("missing","duplicate","failed","attempt2",
                         "wrongsha","wrongactor","pending"):
                items=[dict(z) for z in saved]
                if case=="missing":items.pop()
                if case=="duplicate":items.append(dict(items[0]))
                if case=="failed":items[0]["conclusion"]="failure"
                if case=="attempt2":items[0]["run_attempt"]=2
                if case=="wrongsha":items[0]["head_sha"]="f"*40
                if case=="wrongactor":items[0]["actor"]={"login":"other"}
                if case=="pending":items[0]["status"]="in_progress"
                self.main_runs["workflow_runs"]=items
                with self.subTest(case=case),self.assertRaisesRegex(
                        bridge.ProtectedHybridSourceDenied,"POSTMERGE"):
                    self.auth()
        finally:
            self.main_runs["workflow_runs"]=saved

    def test_protected_main_drift_on_second_read_denied(self):
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

    def test_no_owner_mutation_or_task_control(self):
        import inspect
        code=inspect.getsource(bridge)
        for forbidden in ("workflow_dispatch(","db.event(","UPDATE meta SET",
                          "Stop-ScheduledTask","Start-ScheduledTask",
                          "gh api --method PATCH","create_ref("):
            self.assertNotIn(forbidden,code)


if __name__=="__main__":
    unittest.main()
