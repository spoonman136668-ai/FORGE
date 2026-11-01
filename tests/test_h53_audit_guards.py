import unittest
from f139 import h53_audit_guards as g

class AdmissionTests(unittest.TestCase):
    def test_event_positive_and_negative(self):
        e={"ref":g.REF,"created":True,"deleted":False,"forced":False,
           "before":"0"*40,"after":"a"*40,"sender":{"login":g.OWNER}}
        args=dict(actor=g.OWNER,repository="spoonman136668-ai/FORGE",
                  ref=g.REF,attempt="1",runner=g.RUNNER,sha="a"*40)
        g.event_guard(e,**args)
        for key,value in [("created",False),("forced",True),("before","b"*40),
                          ("after","b"*40),("ref","refs/heads/main")]:
            bad={**e,key:value}
            with self.assertRaises(RuntimeError): g.event_guard(bad,**args)
        for key,value in [("actor","other"),("runner","other"),("attempt","2"),
                          ("ref","refs/heads/main")]:
            with self.assertRaises(RuntimeError): g.event_guard(e,**{**args,key:value})
    def test_ruleset(self):
        r={"enforcement":"active","target":"branch",
           "conditions":{"ref_name":{"include":[g.REF],"exclude":[]}},
           "bypass_actors":[],"rules":[{"type":"update"},{"type":"deletion"}]}
        g.ruleset_guard([r])
        for bad in [[],[r,r],[{**r,"bypass_actors":[{"actor_id":1}]}],
                    [{**r,"enforcement":"evaluate"}],
                    [{**r,"rules":[{"type":"deletion"}]}]]:
            with self.assertRaises(RuntimeError): g.ruleset_guard(bad)
    def test_approval(self):
        sha="a"*40
        c={"body":"F139-H53C-ORIGINAL-READONLY-ONCE "+sha,
           "user":{"login":g.OWNER},"author_association":"OWNER"}
        g.approval_guard([c],sha)
        for bad in [[],[c,c],[{**c,"body":"other"}],
                    [{**c,"user":{"login":"other"}}]]:
            with self.assertRaises(RuntimeError): g.approval_guard(bad,sha)
    def test_source_owner_and_ledger(self):
        s=dict(parents=["a"*40,g.SOURCE],changed=["workflow.yml","observer.py"],
               installed_sha=g.SOURCE,installed_dirty=False,audit_sha="a"*40,
               workflow_path="workflow.yml",observer_path="observer.py")
        g.source_guard(**s)
        for key,value in [("parents",[g.SOURCE]),("installed_sha","b"*40),
                          ("installed_dirty",True),("changed",["workflow.yml"])]:
            with self.assertRaises(RuntimeError): g.source_guard(**{**s,key:value})
        o=dict(task_name=g.TASK,task_state="Ready",task_sid="S-1",runner_sid="S-1",
               actions=1,triggers=3,poll_seconds=300,
               db_path="C:/Users/test/FORGE-F139/state.sqlite",
               expected_db="C:/Users/test/FORGE-F139/state.sqlite")
        g.owner_guard(**o)
        for key,value in [("task_sid","S-2"),("actions",2),("triggers",4),
                          ("poll_seconds",30),("db_path","C:/other.sqlite")]:
            with self.assertRaises(RuntimeError): g.owner_guard(**{**o,key:value})
        l=dict(source_sha=g.SOURCE,enabled=1,legacy_suspended=1,head_seq=350,
               baseline_sha="17614edebb1b067de8112615637160e2bd7e71a4b3ac05dbab78fc360eba3d97",
               query_only=1,quick_check="ok",cold_verified=True)
        g.ledger_guard(**l)
        for key,value in [("source_sha","bad"),("enabled",0),("head_seq",349),
                          ("baseline_sha","bad"),("query_only",0),("cold_verified",False)]:
            with self.assertRaises(RuntimeError): g.ledger_guard(**{**l,key:value})
if __name__=="__main__":
    unittest.main()
