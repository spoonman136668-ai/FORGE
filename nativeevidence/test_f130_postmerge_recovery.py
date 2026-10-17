"""F130 post-merge source custody recovery without invented previous evidence."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f129_staged_admission as admission
import f118_autonomy_feedback as f118

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/"reference/research-intake/f130-postmerge-source-admission-freeze.json"
AMEND=ROOT/"reference/research-intake/f130-historical-pr-custody-amendment.json"
PRE_BLOB="33f4158d93b953d6cb5f09da89a7b9e9bfeb8e89"

class F130Recovery(unittest.TestCase):
    def setUp(self):
        self.old=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]="a"*40

    def tearDown(self):
        if self.old is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old

    def test_scoped_original_freeze_was_saved_first(self):
        raw=PRE.read_bytes().replace(b"\r\n",b"\n")
        self.assertEqual(f118.gitblob(raw),PRE_BLOB)
        data=json.loads(raw)
        self.assertEqual(data["original_authorized_merge"],
                         "0f0a5835f062e6e8843c93c9aa7c8772f236dbdc")
        self.assertTrue(all(data["limits"].values()))

    def test_custody_amendment_disallows_rebuilt_pr_provenance(self):
        x=json.loads(AMEND.read_bytes())
        self.assertTrue(x["no_protected_merge_authorized"])
        self.assertEqual(x["schema"],
                         "forge.autonomy.f130.custody-amendment-pr-after-ancestor-merge.v1")

    def test_pr_push_and_manual_cannot_advance_from_old_merged_pr(self):
        for event in ("pull_request","push","workflow_dispatch"):
            proof=admission.admit(39090000000,"a"*40,event,{"runs":[]})
            self.assertFalse(proof["development_pr_evidence_mode"])
            self.assertTrue(proof["non_scheduled_source_bootstrap"])
            self.assertFalse(proof["genuine_scheduled_source"])
            self.assertFalse(proof["two_genuine_scheduled_main_runs_proven"])
            for data in proof["admissions"].values():
                self.assertFalse(data["admitted"])
                self.assertIsNone(data["prior_run_id"])

    def test_first_scheduled_run_has_bootstrap_base_sources_only(self):
        p=admission.admit(39090000000,"a"*40,"schedule",{"runs":[]})
        self.assertTrue(p["first_schedule_bootstrap"])
        self.assertTrue(p["F124_base_execution"])
        self.assertTrue(p["F126_base_execution"])
        self.assertTrue(all(not x["admitted"] for x in p["admissions"].values()))

    def test_exact_workflow_gates_all_predecessor_dependent_steps(self):
        workflow=(ROOT/".github/workflows/forge-integrated-synthetic-cycle.yml").read_text()
        for step in ("f125","f127","f128"):
            gate="github.event_name == 'schedule' && steps.f129-admission.outputs."+step+" == 'true'"
            self.assertIn(gate,workflow)
            self.assertEqual(workflow.count(gate),2)
        self.assertIn("f129-durable-cross-run-proof:",workflow)
        self.assertIn("F130_DOWNSTREAM_BOUNDARY_REGRESSION_",workflow)

if __name__=="__main__":
    unittest.main()
