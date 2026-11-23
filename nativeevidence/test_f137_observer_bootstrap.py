"""F137: schedule-fed recovery using existing read-only observer, not science."""
import copy
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f136_succession as m

SHA="a"*40
NOW=dt.datetime(2026,10,17,18,10,tzinfo=dt.timezone.utc)
RUN=500000111
def observer():
    return {"id":RUN,"name":m.OBSERVER_NAME,
            "event":"schedule","path":m.OBSERVER_WORKFLOW,
            "repository":{"full_name":m.REPO},
            "head_repository":{"full_name":m.REPO},
            "status":"completed","conclusion":"success","run_attempt":1,
            "head_branch":"main","head_sha":SHA,
            "created_at":"2026-10-17T18:00:00Z",
            "run_started_at":"2026-10-17T18:01:00Z",
            "updated_at":"2026-10-17T18:08:00Z"}
def artifacts():
    return {"total_count":2,"artifacts":[
        {"id":RUN+10+i,"name":name,"expired":False,"size_in_bytes":200,
         "digest":"sha256:"+("b" if i==0 else "c")*64,
         "workflow_run":{"id":RUN,"head_sha":SHA}}
        for i,name in enumerate(m.OBSERVER_ARCHIVES)]}
def recent():
    return {"total_count":10,"workflow_runs":[
        {"id":RUN-1,"event":"workflow_dispatch","status":"completed",
         "conclusion":"success","head_branch":"main","head_sha":SHA,
         "created_at":"2026-10-17T17:30:00Z"},
        {"id":RUN-100,"event":"schedule","status":"completed",
         "conclusion":"success","head_branch":"main","head_sha":SHA,
         "created_at":"2026-10-16T22:30:00Z"}]}

class F137ObserverRecovery(unittest.TestCase):
    def test_genuine_scheduled_observer_bootstraps_development_only(self):
        report=m.observer_bootstrap_decision(
            observer(),artifacts(),recent(),SHA,NOW)
        self.assertTrue(report["dispatch"])
        self.assertTrue(report["observer_two_artifact_provenance_verified"])
        self.assertTrue(report["development_only"])
        self.assertEqual(report["observer_event"],"schedule")
        self.assertEqual(report["daily_main_development_starts"],1)
        self.assertFalse(report["genuine_integrated_schedule_claimed"])
        self.assertFalse(report["first_use_authorized"])
        for key in ("scientific_originals_dispatched","accepted_ref_mutations",
                    "optimizer_promotions","paid_API_calls","Codex_calls"):
            self.assertEqual(report[key],0)
        self.assertFalse(report["ckb_plane_accessed"])
        self.assertFalse(report["mind_palace_written"])

    def test_reject_non_scheduled_or_wrong_origin(self):
        for key,value in (
            ("event","push"),("event","workflow_dispatch"),
            ("name","forged_observer"),("path",m.WORKFLOW),
            ("head_branch","feature"),("head_sha","c"*40),
            ("run_attempt",2),("conclusion","failure"),
            ("status","in_progress"),("updated_at","2026-10-17T17:00:00Z")):
            item=observer()
            item[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(m.Invalid):
                m.observer_bootstrap_decision(item,artifacts(),recent(),SHA,NOW)

    def test_reject_fake_or_missing_source_artifacts(self):
        for mutation in ("expired","duplicate","missing","digest","run","source","index"):
            index=artifacts()
            if mutation=="expired":index["artifacts"][0]["expired"]=True
            if mutation=="duplicate":
                index["artifacts"].append(copy.deepcopy(index["artifacts"][0]))
                index["total_count"]+=1
            if mutation=="missing":
                index["artifacts"].pop()
                index["total_count"]-=1
            if mutation=="digest":index["artifacts"][0]["digest"]="sha256:no"
            if mutation=="run":index["artifacts"][0]["workflow_run"]["id"]=12
            if mutation=="source":index["artifacts"][0]["workflow_run"]["head_sha"]="c"*40
            if mutation=="index":index["total_count"]=12
            with self.subTest(mutation=mutation),self.assertRaises(m.Invalid):
                m.observer_bootstrap_decision(observer(),index,recent(),SHA,NOW)

    def test_paused_or_recent_or_active_is_noop(self):
        d=m.observer_bootstrap_decision(
            observer(),artifacts(),recent(),SHA,NOW,paused=True)
        self.assertFalse(d["dispatch"])
        self.assertIn("OPERATOR_PAUSED",d["reasons"])
        r=recent()
        r["workflow_runs"][0]["created_at"]="2026-10-17T18:05:00Z"
        d=m.observer_bootstrap_decision(observer(),artifacts(),r,SHA,NOW)
        self.assertFalse(d["dispatch"])
        self.assertIn("INTEGRATED_CYCLE_RECENTLY_STARTED",d["reasons"])
        r=recent()
        r["workflow_runs"][0]["status"]="queued"
        d=m.observer_bootstrap_decision(observer(),artifacts(),r,SHA,NOW)
        self.assertFalse(d["dispatch"])
        self.assertIn("ACTIVE_OR_PENDING_INTEGRATED_RUN",d["reasons"])

    def test_existing_recent_genuine_schedule_suppresses_relay(self):
        r=recent()
        r["workflow_runs"][0]["event"]="schedule"
        r["workflow_runs"][0]["created_at"]="2026-10-17T17:40:00Z"
        d=m.observer_bootstrap_decision(observer(),artifacts(),r,SHA,NOW)
        self.assertFalse(d["dispatch"])
        self.assertIn("GENUINE_INTEGRATED_SCHEDULE_ALREADY_PRESENT",d["reasons"])

    def test_daily_budget_and_complete_utc_boundary(self):
        r=recent()
        r["workflow_runs"]=[
            {"id":RUN+100+i,"event":"workflow_dispatch","status":"completed",
             "head_branch":"main","head_sha":SHA,"created_at":"2026-10-17T01:00:00Z"}
            for i in range(96)]+[r["workflow_runs"][-1]]
        r["total_count"]=len(r["workflow_runs"])
        d=m.observer_bootstrap_decision(observer(),artifacts(),r,SHA,NOW)
        self.assertFalse(d["dispatch"])
        self.assertIn("DAILY_START_CAP",d["reasons"])
        r=recent()
        r["workflow_runs"].pop()
        with self.assertRaisesRegex(m.Invalid,"DAILY_BUDGET_INCOMPLETE"):
            m.observer_bootstrap_decision(observer(),artifacts(),r,SHA,NOW)

    def test_workflow_reuses_controller_and_seals_science(self):
        root=Path(__file__).resolve().parents[1]
        controller=(root/".github/workflows/forge-development-succession.yml").read_text()
        integrated=(root/".github/workflows/forge-integrated-synthetic-cycle.yml").read_text()
        self.assertIn(m.OBSERVER_NAME,controller)
        self.assertIn("source-gated-observer-recovery:",controller)
        self.assertIn("F137_SCHEDULED_OBSERVER_ONLY_DEVELOPMENT",controller)
        self.assertIn("f137-scheduled-recovery",integrated)
        self.assertIn("if: github.event_name == 'schedule'",integrated)
        self.assertIn("cancel-in-progress: false",integrated)
        self.assertNotIn("cron:",controller)
if __name__=="__main__":
    unittest.main()
