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
             "north_star_sha256":"7"*64,"active_branch":branch,
             "controller_workflow":"research-auto-launch.yml"})
            self.items[(repo,"/branches/"+branch)]={"commit":{"sha":active}}
            self.items[(repo,"/contents/.research-autonomy/state.json?ref="+active)]=content({
             "schema":"research.repo-local-state.v1","program":name,
             "active_branch":branch,"north_star_sha256":"7"*64,
             "authority":"research-only","ckb_plane_role":"governance-only",
             "experiment":name+"-FUTURE-PLAN-01","classification":classified,
             "github_run_id":str(run),"last_completed_utc":done})
            workflow_id=218001 if name=="Wingless" else 218002
            self.items[(repo,"/actions/runs/"+str(run))]={
             "id":run,"workflow_id":workflow_id,
             "name":name+" research continuation launcher",
             "status":"completed","conclusion":"success","head_branch":"main",
             "head_sha":mainsha,"run_attempt":1,
             "created_at":"2026-10-16T16:58:00Z" if name=="Yggdrasil"
                          else "2026-10-16T16:55:00Z",
             "updated_at":"2026-10-16T17:05:00Z"}
            latest=deepcopy(self.items[(repo,"/actions/runs/"+str(run))])
            latest.update({"id":run+1,"event":"schedule",
                           "created_at":"2026-10-16T17:06:00Z",
                           "updated_at":"2026-10-16T17:07:00Z"})
            referenced=deepcopy(self.items[(repo,"/actions/runs/"+str(run))])
            referenced["event"]="workflow_dispatch"
            self.items[(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")]={
                "workflow_runs":[latest,referenced]}
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
            lambda obj:obj.__setitem__("north_star_sha256","bad-sha"),
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

    def test_legacy_other_project_role_labels_never_gate_forge_autonomy(self):
        # Real research sources may still retain a historical unrelated role
        # label. FORGE must not consume it as an authority or permission grant.
        for index in (0,1):
            a=API()
            repo=m.LANES[index][1]
            current=("a" if index==0 else "c")*40
            active=("b" if index==0 else "d")*40
            config=(repo,"/contents/.research-autonomy/config.json?ref="+current)
            state=(repo,"/contents/.research-autonomy/state.json?ref="+active)
            for key in (config,state):
                doc=json.loads(base64.b64decode(a.items[key]["content"]))
                doc["ckb_plane_role"]="historical-unrelated-value"
                a.items[key]=content(doc)
            out=m.scan(a,NOW)
            self.assertTrue(out["both_lanes_operationally_verified"])
            self.assertFalse(out["ckb_plane_accessed"])
            self.assertFalse(out["scientific_firstuse_authorized"])
            self.assertEqual(out["originals_dispatched"],0)
            self.assertFalse(out["optimizer_policy_updated"])

    def test_legacy_role_field_absence_does_not_require_external_infrastructure(self):
        a=API()
        for idx in (0,1):
            repo=m.LANES[idx][1]
            for commit,path in ((("a" if idx==0 else "c")*40,"config"),
                                (("b" if idx==0 else "d")*40,"state")):
                k=(repo,"/contents/.research-autonomy/"+path+".json?ref="+commit)
                d=json.loads(base64.b64decode(a.items[k]["content"]))
                d.pop("ckb_plane_role",None)
                a.items[k]=content(d)
        out=m.scan(a,NOW)
        self.assertTrue(out["both_lanes_operationally_verified"])
        self.assertFalse(out["ckb_plane_accessed"])
        self.assertFalse(out["scientific_firstuse_authorized"])

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

    def test_main_advances_without_falsifying_authentic_older_launcher_history(self):
        a=API()
        repo=m.LANES[0][1]
        old="a"*40
        current="f"*40
        a.items[(repo,"/branches/main")]={"commit":{"sha":current}}
        a.items[(repo,"/contents/.research-autonomy/config.json?ref="+current)]=deepcopy(
            a.items[(repo,"/contents/.research-autonomy/config.json?ref="+old)])
        a.items[(repo,"/compare/"+old+"..."+current)]={
            "status":"ahead","ahead_by":1,"behind_by":0,
            "base_commit":{"sha":old},"merge_base_commit":{"sha":old}}
        history=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
        new=deepcopy(a.items[history]["workflow_runs"][0])
        new.update({"id":new["id"]+20,"head_sha":current,
                    "created_at":"2026-10-16T17:15:00Z",
                    "updated_at":"2026-10-16T17:16:00Z"})
        a.items[history]["workflow_runs"].insert(0,new)
        report=m.scan(a,NOW)
        lane=report["lanes"][0]
        self.assertTrue(lane["source_and_workflow_confirmed"])
        self.assertEqual(lane["main_sha"],current)
        self.assertEqual(lane["last_reported_run_source_sha"],old)
        self.assertEqual(lane["latest_launcher_run_id"],new["id"])
        self.assertEqual(lane["latest_launcher_conclusion"],"success")
        self.assertFalse(lane["scientific_result_independently_accepted"])
        self.assertTrue(report["both_lanes_operationally_verified"])
        self.assertIn((repo,"/compare/"+old+"..."+current),a.calls)
        self.assertEqual(report["originals_dispatched"],0)

    def test_old_launcher_main_must_be_authenticated_ancestor_not_diverged(self):
        a=API()
        repo=m.LANES[1][1]
        old="c"*40
        current="f"*40
        a.items[(repo,"/branches/main")]={"commit":{"sha":current}}
        a.items[(repo,"/contents/.research-autonomy/config.json?ref="+current)]=deepcopy(
            a.items[(repo,"/contents/.research-autonomy/config.json?ref="+old)])
        a.items[(repo,"/compare/"+old+"..."+current)]={
            "status":"diverged","ahead_by":1,"behind_by":1,
            "base_commit":{"sha":old},"merge_base_commit":{"sha":"e"*40}}
        report=m.scan(a,NOW)
        self.assertTrue(report["lanes"][0]["source_and_workflow_confirmed"])
        self.assertFalse(report["lanes"][1]["source_and_workflow_confirmed"])
        self.assertEqual(report["lanes"][1]["quarantine_reason"],
                         "FORGE_AUTONOMY_CONTINUATION_HEAD_NOT_MAIN_ANCESTOR")
        self.assertFalse(report["both_lanes_operationally_verified"])
        self.assertEqual(report["originals_dispatched"],0)

    def test_missing_git_ancestry_evidence_does_not_get_assumed(self):
        a=API()
        repo=m.LANES[0][1]
        current="f"*40
        old="a"*40
        a.items[(repo,"/branches/main")]={"commit":{"sha":current}}
        a.items[(repo,"/contents/.research-autonomy/config.json?ref="+current)]=deepcopy(
            a.items[(repo,"/contents/.research-autonomy/config.json?ref="+old)])
        r=m.scan(a,NOW)
        self.assertFalse(r["lanes"][0]["source_and_workflow_confirmed"])
        self.assertTrue(r["lanes"][1]["source_and_workflow_confirmed"])
        self.assertFalse(r["scientific_firstuse_authorized"])

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


    def test_newer_failed_scheduled_attempt_blocks_old_success_for_each_lane(self):
        for index in (0,1):
            a=API();repo=m.LANES[index][1]
            path=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
            a.items[path]["workflow_runs"][0]["conclusion"]="failure"
            r=m.scan(a,NOW)
            self.assertFalse(r["both_lanes_operationally_verified"])
            self.assertFalse(r["lanes"][index]["source_and_workflow_confirmed"])
            self.assertEqual(r["lanes"][index]["quarantine_reason"],
                             "FORGE_AUTONOMY_LATEST_RESEARCH_CONTINUATION_NOT_SUCCESSFUL")
            self.assertTrue(r["lanes"][1-index]["source_and_workflow_confirmed"])
            self.assertEqual(r["originals_dispatched"],0)

    def test_in_flight_attempt_not_mistaken_for_completed_success(self):
        a=API();repo=m.LANES[0][1]
        path=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
        a.items[path]["workflow_runs"][0].update({"status":"in_progress","conclusion":None})
        r=m.scan(a,NOW)
        self.assertFalse(r["lanes"][0]["source_and_workflow_confirmed"])
        self.assertTrue(r["lanes"][1]["source_and_workflow_confirmed"])

    def test_current_success_has_authenticated_latest_run_identity(self):
        r=m.scan(API(),NOW)
        self.assertTrue(r["both_lanes_operationally_verified"])
        for x in r["lanes"]:
            self.assertEqual(x["latest_launcher_conclusion"],"success")
            self.assertEqual(x["latest_launcher_event"],"schedule")
            self.assertGreater(x["latest_launcher_run_id"],x["last_reported_run_id"])
            self.assertFalse(x["scientific_result_independently_accepted"])

    def test_newer_launcher_spoof_or_rerun_does_not_pass(self):
        variants=[
            ("workflow_id",8888),("head_sha","e"*40),
            ("head_branch","foreign"),("name","forged research evidence"),
            ("event","pull_request"),("run_attempt",2),
            ("created_at","2040-01-01T01:00:00Z"),
            ("status","cancelled"),("conclusion","skipped")
        ]
        for field,value in variants:
            a=API();repo=m.LANES[0][1]
            path=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
            a.items[path]["workflow_runs"][0][field]=value
            result=m.scan(a,NOW)
            self.assertFalse(result["lanes"][0]["source_and_workflow_confirmed"],
                             msg="accepted latest attempt drift "+field)

    def test_dropped_and_duplicate_history_fails_closed(self):
        for variant in ("empty","duplicate","missing"):
            a=API();repo=m.LANES[1][1]
            path=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
            rows=a.items[path]["workflow_runs"]
            if variant=="empty":rows[:]=[]
            elif variant=="duplicate":rows[1]["id"]=rows[0]["id"]
            else:del a.items[path]
            r=m.scan(a,NOW)
            self.assertFalse(r["lanes"][1]["source_and_workflow_confirmed"])
            self.assertTrue(r["lanes"][0]["source_and_workflow_confirmed"])

    def test_old_success_cannot_be_reframed_as_recent_after_timestamp_drift(self):
        a=API();repo=m.LANES[1][1]
        path=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
        a.items[path]["workflow_runs"][0]["created_at"]="2026-10-16T16:00:00Z"
        a.items[path]["workflow_runs"][:]=a.items[path]["workflow_runs"][:1]
        r=m.scan(a,NOW)
        self.assertFalse(r["lanes"][1]["source_and_workflow_confirmed"])

    def test_newer_success_can_restore_operational_verification_after_prior_failure(self):
        a=API();repo=m.LANES[1][1]
        path=(repo,"/actions/workflows/research-auto-launch.yml/runs?per_page=10")
        failed=deepcopy(a.items[path]["workflow_runs"][0])
        failed["conclusion"]="failure"
        failed["id"]=failed["id"]+3
        failed["created_at"]="2026-10-16T17:06:30Z"
        failed["updated_at"]="2026-10-16T17:06:45Z"
        a.items[path]["workflow_runs"].append(failed)
        r=m.scan(a,NOW)
        self.assertFalse(r["lanes"][1]["source_and_workflow_confirmed"])
        # A real later success makes the newest attempt healthy again.
        later=deepcopy(a.items[path]["workflow_runs"][0])
        later.update({"id":later["id"]+2,"created_at":"2026-10-16T17:09:00Z",
                      "updated_at":"2026-10-16T17:10:00Z"})
        a.items[path]["workflow_runs"].append(later)
        r=m.scan(a,NOW)
        self.assertTrue(r["lanes"][1]["source_and_workflow_confirmed"])
        self.assertFalse(r["lanes"][1]["scientific_result_independently_accepted"])

if __name__=="__main__":unittest.main()
