"""F136 source-bound development succession admission and scientific-denial tests."""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f136_succession as m

SHA="a"*40
NOW=dt.datetime(2026,10,17,18,10,tzinfo=dt.timezone.utc)
RID=45000000000

def trigger():
    return {"id":RID,"event":"schedule","status":"completed",
        "conclusion":"success","run_attempt":1,"head_branch":"main",
        "head_sha":SHA,"repository":{"full_name":m.REPO},
        "head_repository":{"full_name":m.REPO},
        "path":m.WORKFLOW,"created_at":"2026-10-17T18:02:00Z",
        "run_started_at":"2026-10-17T18:02:00Z",
        "updated_at":"2026-10-17T18:09:00Z"}

def artifacts():
    items=[]
    for _,(prefix,_,_) in m.ARTIFACTS.items():
        for os in ("ubuntu-latest","windows-latest"):
            items.append({"id":RID+len(items)+10,"name":prefix+os,
                "expired":False,"size_in_bytes":111,
                "digest":"sha256:"+"b"*64,
                "workflow_run":{"id":RID,"head_sha":SHA}})
    return {"total_count":len(items),"artifacts":items}

def recent():
    rows=[{"id":RID,"status":"completed","conclusion":"success",
           "event":"schedule","head_branch":"main","head_sha":SHA,
           "created_at":"2026-10-17T18:02:00Z"},
          {"id":RID-10,"status":"completed","conclusion":"success",
           "event":"schedule","head_branch":"main","head_sha":SHA,
           "created_at":"2026-10-16T23:44:00Z"}]
    return {"total_count":121,"workflow_runs":rows}

class F136(unittest.TestCase):
    def test_frozen_protocol_and_budget(self):
        p,checksum=m.frozen()
        self.assertEqual(p["target_minutes"],7)
        self.assertEqual(p["fallback_minutes"],10)
        self.assertEqual(p["max_daily_initiated_development_cycles"],96)
        self.assertEqual(len(checksum),64)
        self.assertTrue(all(p["scientific"].values()))

    def test_authentic_completed_gives_one_bounded_dispatch_decision(self):
        d=m.decision(trigger(),artifacts(),recent(),SHA,NOW)
        self.assertTrue(d["dispatch"])
        self.assertEqual(d["event"],"schedule")
        self.assertEqual(d["run_seconds"],420)
        self.assertTrue(d["observed_end_to_end_target_met"])
        self.assertTrue(d["prior_evidence_two_os_index_verified"])
        self.assertFalse(d["scheduled_main_continuity_proven_by_dispatch"])
        self.assertEqual(d["scientific_originals_dispatched"],0)

    def test_end_to_end_includes_waiting_for_runner(self):
        slow=trigger()
        slow["created_at"]="2026-10-17T18:00:00Z"
        out=m.decision(slow,artifacts(),recent(),SHA,NOW)
        self.assertEqual(out["run_seconds"],540)
        self.assertFalse(out["observed_end_to_end_target_met"])

    def test_failing_rerun_wrong_origin_denied(self):
        for k,v in (("event","pull_request"),("event","push"),
                    ("conclusion","failure"),("status","in_progress"),
                    ("run_attempt",2),("head_branch","other"),
                    ("head_sha","c"*40),("path","other.yml")):
            t=trigger()
            t[k]=v
            with self.assertRaises(m.Invalid):
                m.decision(t,artifacts(),recent(),SHA,NOW)

    def test_prevent_active_pending_overlap(self):
        for status in ("queued","waiting","in_progress","pending","requested"):
            h=recent()
            h["workflow_runs"].insert(0,{"id":RID+5,"event":"workflow_dispatch",
                "status":status,"head_branch":"main","head_sha":SHA,
                "created_at":"2026-10-17T18:09:55Z"})
            d=m.decision(trigger(),artifacts(),h,SHA,NOW)
            self.assertFalse(d["dispatch"])
            self.assertIn("ACTIVE_OR_PENDING_INTEGRATED_RUN",d["reasons"])

    def test_operator_pause_budget_and_imminent_fallback(self):
        a=m.decision(trigger(),artifacts(),recent(),SHA,NOW,paused=True)
        self.assertFalse(a["dispatch"])
        self.assertIn("OPERATOR_PAUSED",a["reasons"])
        # At 18:15:30 the next 18:17 fallback is only 90 seconds away.
        near=NOW.replace(minute=15,second=30)
        d=m.decision(trigger(),artifacts(),recent(),SHA,near)
        self.assertFalse(d["dispatch"])
        self.assertIn("FALLBACK_SLOT_IMMINENT",d["reasons"])
        h=recent()
        for i in range(95):
            h["workflow_runs"].insert(1,{"id":RID-200-i,
                "event":"workflow_dispatch","status":"completed",
                "head_branch":"main","head_sha":SHA,
                "created_at":"2026-10-17T01:00:00Z"})
        d=m.decision(trigger(),artifacts(),h,SHA,NOW)
        self.assertFalse(d["dispatch"])
        self.assertIn("DAILY_START_CAP",d["reasons"])

    def test_lost_or_replayed_artifact_and_metadata_rejected(self):
        for mutation in ("missing","expired","wrong-run","wrong-sha","duplicate"):
            index=artifacts()
            if mutation=="missing":
                index["artifacts"].pop()
                index["total_count"]-=1
            elif mutation=="expired":
                index["artifacts"][0]["expired"]=True
            elif mutation=="wrong-run":
                index["artifacts"][0]["workflow_run"]["id"]=RID-1
            elif mutation=="wrong-sha":
                index["artifacts"][0]["digest"]="sha256:broken"
            else:
                index["artifacts"].append(copy.deepcopy(index["artifacts"][0]))
                index["total_count"]+=1
            with self.assertRaises(m.Invalid):
                m.decision(trigger(),index,recent(),SHA,NOW)

    def test_source_drift_budget_truncation_and_newer_success_fail_closed(self):
        with self.assertRaises(m.Invalid):
            m.decision(trigger(),artifacts(),recent(),"c"*40,NOW)
        a=recent()
        a["workflow_runs"][-1]["created_at"]="2026-10-17T17:10:00Z"
        with self.assertRaisesRegex(m.Invalid,"DAILY_BUDGET_INDEX_INCOMPLETE"):
            m.decision(trigger(),artifacts(),a,SHA,NOW)
        a=recent()
        a["workflow_runs"].insert(0,{"id":RID+1,"status":"completed",
            "conclusion":"success","event":"workflow_dispatch",
            "head_branch":"main","head_sha":SHA,
            "created_at":"2026-10-17T18:09:30Z"})
        self.assertFalse(m.decision(trigger(),artifacts(),a,SHA,NOW)["dispatch"])

    def test_independent_report_bytes_and_denied_science(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for section,(prefix,name,receipt) in m.ARTIFACTS.items():
                proof={"run_id":RID,"source_sha":SHA,"accepted_ref_mutations":0,
                       "optimizer_promotions":0,"scientific_first_use_authorized":False,
                       "scientific_originals":0,"new_accepted_scientific_originals":0,
                       "real_scientific_first_use":False,"scientific_originals_dispatched":0,
                       "two_genuine_scheduled_main_runs_proven":False}
                raw=(json.dumps(proof,sort_keys=True)+"\n").encode()
                for os in ("ubuntu-latest","windows-latest"):
                    folder=root/(prefix+os)
                    folder.mkdir()
                    (folder/name).write_bytes(raw)
                    (folder/receipt).write_text(hashlib.sha256(raw).hexdigest()+
                        "  "+name+"\n")
            self.assertEqual(set(m.validate_contents(root,SHA,RID)),set(m.ARTIFACTS))
            prefix,name,receipt=m.ARTIFACTS["f126"]
            folder=root/(prefix+"windows-latest")
            (folder/name).write_text("fake")
            with self.assertRaises(m.Invalid):
                m.validate_contents(root,SHA,RID)

    def test_no_uncontrolled_successor_claims_or_science_grants(self):
        d=m.decision(trigger(),artifacts(),recent(),SHA,NOW)
        for name in ("scientific_originals_dispatched","accepted_ref_mutations",
                     "optimizer_promotions","paid_API_calls","Codex_calls"):
            self.assertEqual(d[name],0)
        self.assertFalse(d["first_use_authorized"])

    def test_existing_integrated_workflow_reuses_10minute_fallback(self):
        root=Path(__file__).resolve().parents[1]
        w=(root/".github/workflows/forge-integrated-synthetic-cycle.yml").read_text()
        self.assertIn("cron: '7,17,27,37,47,57 * * * *'",w)
        self.assertIn("group: forge-integrated-synthetic-",w)
        self.assertIn("cancel-in-progress: false",w)
        self.assertIn("event_name == 'schedule'",w)
        self.assertIn("F136_", (root/".github/workflows/forge-development-succession.yml").read_text())

if __name__=="__main__":
    unittest.main()
