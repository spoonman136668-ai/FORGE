"""Offline F137 Windows wake eligibility and source-safety regressions."""
import copy
import datetime as dt
import unittest

import f137_windows_wake as m

NOW=dt.datetime(2026,10,18,3,21,30,tzinfo=dt.timezone.utc)
SHA="9c4bfd99eba1052d888a54f6197db5bd7b9df68f"
RID=39099990111

def wake():
    return {
      "id":RID,"repository":{"full_name":m.f.REPO},
      "head_repository":{"full_name":m.f.REPO},
      "actor":{"login":"spoonman136668-ai"},
      "triggering_actor":{"login":"spoonman136668-ai"},
      "path":m.CONTROLLER,"head_branch":"main","head_sha":SHA,
      "event":"workflow_dispatch","status":"in_progress",
      "run_attempt":1,"created_at":"2026-10-18T03:21:00Z"
    }

def recent():
    return {"total_count":2,"workflow_runs":[
      {"id":39086308141,"head_branch":"main","head_sha":SHA,
       "event":"push","status":"completed","conclusion":"success",
       "created_at":"2026-10-18T01:23:26Z",
       "updated_at":"2026-10-18T01:25:00Z"},
      {"id":39077777777,"head_branch":"main","head_sha":SHA,
       "event":"schedule","status":"completed","conclusion":"success",
       "created_at":"2026-10-17T23:10:00Z",
       "updated_at":"2026-10-17T23:13:00Z"},
    ]}

def wakes():
    return {"total_count":1,"workflow_runs":[{
      "id":RID,"event":"workflow_dispatch","head_branch":"main",
      "created_at":"2026-10-18T03:21:00Z"
    }]}

class WindowsWakeTests(unittest.TestCase):
    def decide(self,**changes):
        args=dict(wake=wake(),integrated=recent(),wake_runs=wakes(),
                  main_sha=SHA,pinned_sha=SHA,nonce="abcdef0123456789"*2,
                  now=NOW,paused=False,enabled=True)
        args.update(changes)
        return m.decision(**args)

    def test_verified_idle_bootstrap_is_explicitly_not_science(self):
        d=self.decide()
        self.assertTrue(d["dispatch"])
        self.assertEqual(d["reasons"],[])
        self.assertEqual(d["origin"],"f137-windows-recovery")
        self.assertFalse(d["genuine_schedule_claim"])
        self.assertFalse(d["scientific_first_use_authorized"])
        self.assertEqual(d["science_originals"],0)
        self.assertEqual(d["codex_calls"],0)
        self.assertEqual(d["accepted_ref_mutations"],0)

    def test_disabled_by_default_and_paused_fail_closed(self):
        self.assertEqual(self.decide(enabled=False)["reasons"],
                         ["OPERATOR_ENABLE_NOT_GRANTED"])
        self.assertEqual(self.decide(paused=True)["reasons"],
                         ["OPERATOR_PAUSED"])

    def test_wrong_actor_protected_head_and_rerun_rejected(self):
        for change in (
                {"actor":{"login":"attacker"}},
                {"head_sha":"0"*40},
                {"run_attempt":2},
                {"event":"schedule"},
                {"status":"completed"},
                {"path":"other-workflow.yml"}):
            w=wake();w.update(change)
            with self.assertRaises(m.f.Invalid):
                self.decide(wake=w)
        with self.assertRaises(m.f.Invalid):
            self.decide(pinned_sha="1"*40)
        with self.assertRaises(m.f.Invalid):
            self.decide(nonce="../forged")

    def test_recent_running_or_queued_integrated_blocks(self):
        for status in ("in_progress","queued","pending"):
            x=recent()
            x["workflow_runs"][0]["status"]=status
            d=self.decide(integrated=x)
            self.assertFalse(d["dispatch"])
            self.assertIn("INTEGRATED_RUN_ACTIVE",d["reasons"])

    def test_recent_completed_integrated_blocks(self):
        x=recent()
        x["workflow_runs"][0]["created_at"]="2026-10-18T03:19:00Z"
        x["workflow_runs"][0]["updated_at"]="2026-10-18T03:20:00Z"
        self.assertIn("RECENT_INTEGRATED_RUN",
                      self.decide(integrated=x)["reasons"])
        self.assertIn("COMPLETION_CONTROLLER_GRACE",
                      self.decide(integrated=x)["reasons"])

    def test_two_wakes_in_same_window_block(self):
        x=wakes()
        x["workflow_runs"].append({
            "id":RID-1,"event":"workflow_dispatch",
            "head_branch":"main","created_at":"2026-10-18T03:20:59Z"})
        x["total_count"]=2
        self.assertIn("COMPETING_WAKE",
                      self.decide(wake_runs=x)["reasons"])

    def test_daily_budget_at_96_denies(self):
        x=recent()
        rows=[]
        for i in range(96):
            rows.append({
             "id":RID-1000-i,"event":"workflow_dispatch",
             "head_branch":"main","head_sha":SHA,
             "status":"completed","conclusion":"success",
             "created_at":(
                 NOW-dt.timedelta(minutes=10+i)).isoformat(),
             "updated_at":(
                 NOW-dt.timedelta(minutes=9+i)).isoformat()})
        oldest=x["workflow_runs"][-1].copy()
        oldest["created_at"]="2026-10-17T08:00:00Z"
        oldest["updated_at"]="2026-10-17T08:03:00Z"
        x["workflow_runs"]=rows+[oldest]
        x["total_count"]=len(x["workflow_runs"])
        d=self.decide(integrated=x)
        self.assertEqual(d["daily_starts"],96)
        self.assertIn("DAILY_START_CAP",d["reasons"])

    def test_missing_prior_utc_day_fails_closed(self):
        x=recent();x["workflow_runs"]=x["workflow_runs"][:1]
        x["total_count"]=1
        with self.assertRaises(m.f.Invalid):
            self.decide(integrated=x)

    def test_pagination_collisions_and_bad_rows_fail_closed(self):
        x=recent();x["workflow_runs"]*=2;x["total_count"]=4
        with self.assertRaises(m.f.Invalid):
            self.decide(integrated=x)
        z=wakes();z["workflow_runs"]=[]
        with self.assertRaises(m.f.Invalid):
            self.decide(wake_runs=z)

    def test_imminent_fallback_is_not_overridden(self):
        near=NOW.replace(minute=16,second=0)
        w=wake();w["created_at"]="2026-10-18T03:15:59Z"
        z=wakes()
        z["workflow_runs"][0]["created_at"]=w["created_at"]
        d=self.decide(wake=w,wake_runs=z,now=near)
        self.assertFalse(d["dispatch"])
        self.assertIn("FALLBACK_SLOT_IMMINENT",d["reasons"])

    def test_bounded_five_minute_nonce_age(self):
        w=wake();w["created_at"]="2026-10-18T03:10:00Z"
        with self.assertRaises(m.f.Invalid):
            self.decide(wake=w)

    def test_dpapi_assembly_loaded_before_unprotect(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts/f137-windows-wake.ps1").read_text()
        loader = "Add-Type -AssemblyName System.Security -ErrorAction Stop"
        decrypt = "[Security.Cryptography.ProtectedData]::Unprotect("
        self.assertEqual(script.count(loader), 1)
        self.assertEqual(script.count(decrypt), 1)
        self.assertLess(script.index(loader), script.index(decrypt))

    def test_same_source_and_synthetic_workflow_contract(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        controller=(root/".github/workflows/forge-development-succession.yml").read_text()
        integrated=(root/".github/workflows/forge-integrated-synthetic-cycle.yml").read_text()
        self.assertIn("F137_WINDOWS_WAKE_SOURCE_GUARD",controller)
        self.assertIn("FORGE_F137_WINDOWS_WAKE_ENABLED",controller)
        self.assertIn("f137-windows-recovery",integrated)
        self.assertIn("GITHUB_RUN_ATTEMPT",controller)

if __name__=="__main__":
    unittest.main()
