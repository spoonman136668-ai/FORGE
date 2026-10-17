"""F129 fail-closed scheduled bootstrap, staggered lineage and cross-run tests."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f129_staged_admission as m

SOURCE="a"*40
PARENT="b"*40
RUN=39090000000

def item(run_id=39080000000,stages=()):
    f,_=m.frozen()
    run={"id":run_id,"status":"completed","conclusion":"success",
         "event":"schedule","head_branch":"main","run_attempt":1,
         "head_sha":PARENT,
         "path":".github/workflows/forge-integrated-synthetic-cycle.yml",
         "repository":{"full_name":"spoonman136668-ai/FORGE"},
         "head_repository":{"full_name":"spoonman136668-ai/FORGE"}}
    artifacts=[]
    for stage in stages:
        for i,name in enumerate(f["parents"][stage]):
            artifacts.append({"id":run_id+i+1000*len(artifacts),
                              "name":name,"expired":False,
                              "digest":"sha256:"+"c"*64,"size_in_bytes":101,
                              "workflow_run":{"id":run_id,"head_sha":PARENT}})
    return {"run":run,"artifacts":{"total_count":len(artifacts),"artifacts":artifacts}}

class F129Admission(unittest.TestCase):
    def setUp(self):
        self.orig=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE
    def tearDown(self):
        if self.orig is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.orig

    def test_freeze_exact_before_executor_work(self):
        a,h=m.frozen()
        self.assertEqual(m.f118.gitblob(
            m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),m.BLOB)
        self.assertEqual(len(h),64)
        self.assertTrue(all(a["limits"].values()))
        self.assertEqual(set(a["parents"]),{"F125","F127","F128"})

    def test_first_schedule_bootstraps_f124_f126_without_false_pr_lineage(self):
        report=m.admit(RUN,SOURCE,"schedule",{"runs":[item()]})
        self.assertTrue(report["first_schedule_bootstrap"])
        self.assertTrue(report["F124_base_execution"])
        self.assertTrue(report["F126_base_execution"])
        self.assertFalse(report["development_pr_evidence_mode"])
        for value in report["admissions"].values():
            self.assertFalse(value["admitted"])
            self.assertIsNone(value["prior_run_id"])
        self.assertFalse(report["two_genuine_scheduled_main_runs_proven"])

    def test_stage_by_stage_prior_runs_are_admitted_separately(self):
        first=item(39080000002,("F125","F127"))
        older=item(39080000001,("F128",))
        report=m.admit(RUN,SOURCE,"schedule",{"runs":[first,older]})
        self.assertFalse(report["first_schedule_bootstrap"])
        for key in ("F125","F127"):
            self.assertTrue(report["admissions"][key]["admitted"])
            self.assertEqual(report["admissions"][key]["prior_run_id"],39080000002)
        self.assertEqual(report["admissions"]["F128"]["prior_run_id"],39080000001)

    def test_closed_historical_pr_source_is_not_rehabilitated_on_new_pr(self):
        state=m.admit(RUN,SOURCE,"pull_request",{"runs":[]})
        self.assertFalse(state["development_pr_evidence_mode"])
        self.assertTrue(state["non_scheduled_source_bootstrap"])
        self.assertFalse(state["genuine_scheduled_source"])
        self.assertFalse(state["first_schedule_bootstrap"])
        self.assertTrue(all(not x["admitted"] for x in state["admissions"].values()))
        self.assertTrue(all(x["prior_run_id"] is None for x in state["admissions"].values()))
        self.assertFalse(state["two_genuine_scheduled_main_runs_proven"])

    def test_postmerge_push_cannot_reuse_closed_pr_fixture_or_claim_continuity(self):
        for event in ("push","workflow_dispatch"):
            report=m.admit(RUN,SOURCE,event,{"runs":[]})
            self.assertTrue(report["non_scheduled_source_bootstrap"])
            self.assertFalse(report["development_pr_evidence_mode"])
            self.assertFalse(report["genuine_scheduled_source"])
            self.assertFalse(report["first_schedule_bootstrap"])
            self.assertTrue(report["F124_base_execution"])
            self.assertTrue(report["F126_base_execution"])
            self.assertTrue(all(not row["admitted"]
                                for row in report["admissions"].values()))
            self.assertTrue(all(row["prior_run_id"] is None
                                for row in report["admissions"].values()))
            self.assertFalse(report["two_genuine_scheduled_main_runs_proven"])

    def test_prior_genuine_schedule_is_not_reused_by_push(self):
        for event in ("push","workflow_dispatch"):
            with self.assertRaisesRegex(m.Blocked,"NONSCHEDULED_PRIOR_HISTORY"):
                m.admit(RUN,SOURCE,event,{"runs":[item(stages=("F125",))]})

    def test_non_schedule_baseline_only_prevents_stale_fixture_replay(self):
        for event in ("pull_request","push","workflow_dispatch"):
            report=m.admit(RUN,SOURCE,event,{"runs":[]})
            self.assertFalse(report["development_pr_evidence_mode"])
            self.assertTrue(report["non_scheduled_source_bootstrap"])
            self.assertTrue(all(not row["admitted"]
                                for row in report["admissions"].values()))

    def test_partial_artifact_pair_quarantines_even_when_older_run_valid(self):
        new=item(39080000002,("F125",))
        new["artifacts"]["artifacts"].pop()
        new["artifacts"]["total_count"]-=1
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_HALF_PAIR"):
            m.admit(RUN,SOURCE,"schedule",
                    {"runs":[new,item(39080000001,("F125",))]})

    def test_untrusted_authenticity_and_wrong_branch_quarantine(self):
        for field,value in (("event","pull_request"),("head_branch","feature"),
                            ("conclusion","failure"),("status","in_progress"),
                            ("run_attempt",2),("head_sha","zz"),
                            ("path","different.yml")):
            bad=item()
            bad["run"][field]=value
            with self.assertRaisesRegex(m.Blocked,"SCHEDULED_GITHUB_RUN_INVALID"):
                m.admit(RUN,SOURCE,"schedule",{"runs":[bad]})

    def test_corrupt_artifact_index_rollback_and_digests(self):
        bad=item(stages=("F125",))
        bad["artifacts"]["total_count"]=3
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_ARTIFACT_INDEX"):
            m.admit(RUN,SOURCE,"schedule",{"runs":[bad]})
        bad=item(stages=("F125",))
        bad["artifacts"]["artifacts"][0]["digest"]="sha256:short"
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_ARTIFACT_SOURCE"):
            m.admit(RUN,SOURCE,"schedule",{"runs":[bad]})

    def test_run_ids_must_descend_and_be_earlier(self):
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_GITHUB_RUN_INVALID"):
            m.admit(RUN,SOURCE,"schedule",{"runs":[item(RUN)]})
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_GITHUB_RUN_INVALID"):
            m.admit(RUN,SOURCE,"schedule",{"runs":[item(39080000001),item(39080000002)]})

    def test_bad_current_source_ref_fails_closed(self):
        with self.assertRaisesRegex(m.Blocked,"CURRENT_SOURCE_NOT_PINNED"):
            m.admit(RUN,"c"*40,"schedule",{"runs":[]})

    def test_no_pr_run_can_claim_scheduled_prior(self):
        with self.assertRaisesRegex(m.Blocked,"NONSCHEDULED_PRIOR_HISTORY"):
            m.admit(RUN,SOURCE,"pull_request",{"runs":[item()]})

    def test_byte_identical_repeated_schedule_stage_receipt(self):
        h={"runs":[item(39080000002,("F125","F127")),
                   item(39080000001,("F128",))]}
        a=m.admit(RUN,SOURCE,"schedule",h)
        b=m.admit(RUN,SOURCE,"schedule",h)
        self.assertEqual(m.canonical(a),m.canonical(b))

    def test_duplicate_json_keys_and_nonfinite_values(self):
        with self.assertRaisesRegex(m.Blocked,"DUPLICATE_JSON_KEY"):
            m.strict(b'{"runs":[],"runs":[]}')
        with self.assertRaisesRegex(m.Blocked,"JSON_NONFINITE"):
            m.strict(b'{"runs":NaN}')

if __name__=="__main__":
    unittest.main()
