"""Autonomy operational supervision: real-lane identities, no scientific release."""
import base64
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import pulse as m
NOW=datetime.fromisoformat("2026-10-16T18:00:00+00:00")

def content(doc):
    raw=json.dumps(doc).encode()
    return {"type":"file","encoding":"base64","content":base64.b64encode(raw).decode(),
            "size":len(raw)}
class API:
    def __init__(self):
        self.items={}
        self.calls=[]
        for name,repo in m.LANES:
            short=name.lower()
            mainsha=("a" if name=="Wingless" else "c")*40
            active=("b" if name=="Wingless" else "d")*40
            branch="research/autonomy-"+short+"-active"
            run=38935997749 if name=="Wingless" else 38936334823
            classified=("qualified-scientific-result" if name=="Wingless"
                        else "preregistered-blocked")
            done=("2026-10-16T17:04:49Z" if name=="Wingless"
                  else "2026-10-16T17:03:08Z")
            self.items[(repo,"/branches/main")]={"commit":{"sha":mainsha}}
            self.items[(repo,"/contents/.research-autonomy/config.json?ref="+mainsha)]=content({
             "schema":"research.autonomy.v2","program":name,
             "authority":"research-only","mode":"repo-local-self-chain",
             "ckb_plane_role":"governance-only","enabled":True,
             "north_star_sha256":"7"*64,"active_branch":branch})
            self.items[(repo,"/branches/"+branch)]={"commit":{"sha":active}}
            self.items[(repo,"/contents/.research-autonomy/state.json?ref="+active)]=content({
             "schema":"research.repo-local-state.v1","program":name,
             "active_branch":branch,"north_star_sha256":"7"*64,
             "authority":"research-only","ckb_plane_role":"governance-only",
             "experiment":name+"-FUTURE-PLAN-01","classification":classified,
             "github_run_id":str(run),"last_completed_utc":done})
            self.items[(repo,"/actions/runs/"+str(run))]={
             "id":run,"name":name+" research continuation launcher",
             "status":"completed","conclusion":"success","head_branch":"main",
             "head_sha":mainsha,"run_attempt":1,
             "created_at":"2026-10-16T16:58:00Z" if name=="Yggdrasil"
                          else "2026-10-16T16:55:00Z",
             "updated_at":"2026-10-16T17:05:00Z"}
            self.items[(repo,"/commits/"+mainsha)]={"sha":mainsha}
    def get(self,repo,route):
        self.calls.append((repo,route))
        return deepcopy(self.items[(repo,route)])

class TestAutonomyPulse(unittest.TestCase):
    def test_two_lanes_success_does_not_promote_blocked_research(self):
        r=m.scan(API(),NOW)
        self.assertTrue(r["both_lanes_operationally_verified"])
        self.assertEqual([x["lane"] for x in r["lanes"]],["Wingless","Yggdrasil"])
        self.assertEqual(r["lanes"][0]["operational_disposition"],
                         "REPO_REPORTED_QUALIFIED_NOT_INDEPENDENT_SCIENCE_ACCEPTANCE")
        self.assertEqual(r["lanes"][1]["operational_disposition"],
                         "REPO_REPORTED_BLOCKED_DO_NOT_DISPATCH")
        for x in r["lanes"]:
            self.assertFalse(x["science_first_use_approved"])
            self.assertFalse(x["scientific_result_independently_accepted"])
        self.assertEqual(r["originals_dispatched"],0)
        self.assertEqual(r["workflow_mutations"],0)
        self.assertFalse(r["optimizer_policy_updated"])
        self.assertFalse(r["scientific_firstuse_authorized"])

    def test_lane_origin_drift_is_local_quarantine(self):
        for mutate in (
            lambda obj:obj.__setitem__("enabled",False),
            lambda obj:obj.__setitem__("authority","source-and-worker-owner"),
            lambda obj:obj.__setitem__("ckb_plane_role","research-controller"),
            lambda obj:obj.__setitem__("mode","live-first-use-dispatch")
        ):
            a=API();repo=m.LANES[1][1]
            path=(repo,"/contents/.research-autonomy/config.json?ref="+"c"*40)
            v=json.loads(base64.b64decode(a.items[path]["content"]))
            mutate(v)
            a.items[path]=content(v)
            r=m.scan(a,NOW)
            self.assertTrue(r["lanes"][0]["source_and_workflow_confirmed"])
            self.assertFalse(r["lanes"][1]["source_and_workflow_confirmed"])
            self.assertEqual(r["lanes"][1]["operational_disposition"],
                             "QUARANTINED_UNVERIFIED_NO_REPLAY")
            self.assertFalse(r["both_lanes_operationally_verified"])
            self.assertEqual(r["originals_dispatched"],0)

    def test_stale_source_or_forged_success_run_is_quarantined(self):
        variants=[
          ("head_sha","f"*40),("run_attempt",2),("head_branch","other"),
          ("status","in_progress"),("conclusion","failure"),
          ("name","Yggdrasil accepted original science")]
        for field,value in variants:
            a=API()
            a.items[(m.LANES[1][1],"/actions/runs/38936334823")][field]=value
            r=m.scan(a,NOW)
            self.assertTrue(r["lanes"][0]["source_and_workflow_confirmed"])
            self.assertFalse(r["lanes"][1]["source_and_workflow_confirmed"])

    def test_future_or_reverse_timeline_never_accepted(self):
        for time in ("2040-01-01T01:00:00Z","2026-10-16T15:00:00Z"):
            a=API();repo=m.LANES[0][1]
            path=(repo,"/contents/.research-autonomy/state.json?ref="+"b"*40)
            v=json.loads(base64.b64decode(a.items[path]["content"]))
            v["last_completed_utc"]=time;a.items[path]=content(v)
            self.assertFalse(m.scan(a,NOW)["lanes"][0]["source_and_workflow_confirmed"])

    def test_mid_read_source_change_is_quarantined_without_losing_other_lane(self):
        a=API();g=a.get;count=[0]
        def moving(repo,route):
            v=g(repo,route)
            if repo==m.LANES[0][1] and route.startswith("/branches/research/"):
                count[0]+=1
                if count[0]>1:v["commit"]["sha"]="f"*40
            return v
        a.get=moving
        r=m.scan(a,NOW)
        self.assertFalse(r["lanes"][0]["source_and_workflow_confirmed"])
        self.assertTrue(r["lanes"][1]["source_and_workflow_confirmed"])

    def test_older_than_day_diagnosed_but_never_retried(self):
        a=API()
        r=m.scan(a,datetime.fromisoformat("2026-10-18T19:00:00+00:00"))
        self.assertTrue(r["both_lanes_operationally_verified"])
        self.assertTrue(all(x["stale_over_24_hours"] for x in r["lanes"]))
        self.assertEqual(r["first_use_claims_written"],0)

    def test_unknown_label_never_assumed_scientifically_accepted(self):
        a=API();repo=m.LANES[0][1]
        path=(repo,"/contents/.research-autonomy/state.json?ref="+"b"*40)
        v=json.loads(base64.b64decode(a.items[path]["content"]))
        v["classification"]="unreviewed-novel-label";a.items[path]=content(v)
        x=m.scan(a,NOW)["lanes"][0]
        self.assertEqual(x["operational_disposition"],"UNKNOWN_OR_OTHER_RESEARCH_STATE_REQUIRES_REVIEW")
        self.assertFalse(x["scientific_result_independently_accepted"])

    def test_missing_one_origin_does_not_fake_both_lane_observation(self):
        a=API();del a.items[(m.LANES[1][1],"/branches/main")]
        r=m.scan(a,NOW)
        self.assertTrue(r["lanes"][0]["source_and_workflow_confirmed"])
        self.assertFalse(r["both_lanes_operationally_verified"])
        self.assertEqual(r["originals_dispatched"],0)

    def test_strict_json_denies_duplicate_keys_and_nonfinite(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}'):
            with self.assertRaises(m.Blocked):m.strict_json(raw)

if __name__=="__main__":unittest.main()
