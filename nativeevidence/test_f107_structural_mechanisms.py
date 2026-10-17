"""F107 adversarial regression: genuine grammar composition, train-only selection,
unchanged diagnostic, negative preservation, source custody and no science permits.
Only synthetic local unit-test fixtures; actual CI reads F106 current-run reports.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f107_structural_mechanisms as f107
import f106_automatic_challenge as f106
import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve

SHA="a"*40

def fixture(root,wrong_advice=False):
    row=[]
    directions=[]
    for lane,candidate,feedback in (
        ("Wingless","W100-C2","HARDER_UNSEEN_PUBLIC_OBSERVATION_TOPOLOGY"),
        ("Yggdrasil","Y100-C2","ADVERSARIAL_NOVEL_BINDING_GRAPH_TOPOLOGY")):
        row.append(dict(lane=lane,parent_candidate_id=candidate,
                        new_challenge_screen_passed=True,new_assessment_pairs=48,
                        coded_oracle_control_accuracy=1.,
                        outcome="PUBLIC_TRANSFER_SCREEN_POSITIVE_NOT_SCIENCE"))
        directions.append(dict(lane=lane,
                               advice=("WRONG_DIRECTION" if wrong_advice and lane=="Yggdrasil"
                                       else feedback),
                               based_on_negative=False,dispatch_allowed=False))
    r=dict(schema=f106.REPORT,source_sha=SHA,
           run_scoped_selection_verified=True,new_public_challenge_pairs=96,
           distinct_parent_model_lanes=2,real_cpu_model_training=True,
           protected_first_use_authorized=False,accepted_ref_mutations=0,
           new_protected_originals=0,native_research_workers_dispatched=0,
           external_paid_model_calls=0,codex_invocations=0,
           trained_policy_promoted=False,lanes=row,
           feedback_next_directions=directions)
    report=root/"forge-f106-development/f106-automatic-new-public-challenge.json"
    receipt=root/"forge-f106-development/f106-automatic-new-public-challenge.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(data)
    receipt.write_text(hashlib.sha256(data).hexdigest()+"  "+report.name+"\n",
                       encoding="utf-8")
    return report,receipt

class F107BoundedStructuralNovelty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=f107.frozen()

    def setUp(self):
        self.old=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SHA

    def tearDown(self):
        if self.old is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old

    def test_protocol_frozen_lineage_and_denied_authority(self):
        self.assertEqual(self.cfg["parent_f106_exact_head_sha"],f107.PARENT)
        self.assertEqual(len(self.digest),64)
        self.assertTrue(self.cfg["authority"]["no_free_form_GPT_hypothesis_generation_claim"])
        self.assertTrue(self.cfg["authority"]["no_protected_first_use"])
        self.assertTrue(self.cfg["public_new_generator"]["no_candidate_selection_on_diagnostic"])

    def test_grammar_recombines_distinct_executable_dataflows(self):
        for lane in ("Wingless","Yggdrasil"):
            programs=f107.generated_programs(lane,self.cfg)
            self.assertGreaterEqual(len(programs),3)
            self.assertLessEqual(len(programs),18)
            self.assertGreaterEqual(len({p["family"] for p in programs}),3)
            self.assertEqual(len({p["sha256"] for p in programs}),len(programs))
            original=tuple(self.cfg["mechanism_grammar"][lane]["parent_program"])
            self.assertTrue(all(p["ast"]!=original and
                                p["ast"][:-1]!=original[:-1] for p in programs))
            self.assertTrue(all(p["sha256"]==f107.fingerprint(lane,p["ast"])
                                for p in programs))
            self.assertEqual(programs,f107.generated_programs(lane,self.cfg))
        self.assertTrue(any(p["ast"][1]=="top_two_contrast"
                            for p in f107.generated_programs("Wingless",self.cfg)))
        self.assertTrue(any(p["ast"][0]=="node_pooled"
                            for p in f107.generated_programs("Yggdrasil",self.cfg)))

    def test_new_public_train_diagnostic_disjoint_and_ground_truth(self):
        for lane in ("Wingless","Yggdrasil"):
            train,diagnostic=f107.groups(lane)
            self.assertEqual((len(train),len(diagnostic)),(48,48))
            self.assertTrue({(p.seed,p.specimen) for p in train}.isdisjoint(
                            {(p.seed,p.specimen) for p in diagnostic}))
            for p in train+diagnostic:
                if lane=="Wingless":
                    self.assertTrue(wobserve.coded_depth_observation_oracle(p,p.positive_values))
                    self.assertFalse(wobserve.coded_depth_observation_oracle(p,p.negative_values))
                    self.assertEqual(sum(a!=b for a,b in zip(
                        p.positive_values,p.negative_values)),1)
                else:
                    self.assertTrue(ybind.coded_exact_binding_oracle(p,p.positive_variables))
                    self.assertFalse(ybind.coded_exact_binding_oracle(p,p.negative_variables))
                    self.assertEqual(sum(a!=b for x,y in zip(
                        p.positive_variables,p.negative_variables)
                        for a,b in zip(x,y)),1)

    def test_oracle_never_called_from_executable_program(self):
        wing=f107.groups("Wingless")[0][0]
        ygg=f107.groups("Yggdrasil")[0][0]
        wm=wobserve.LearnedObservationSelector()
        ym=ybind.LearnedVariableBinder()
        with mock.patch.object(wobserve,"coded_depth_observation_oracle",
                               side_effect=AssertionError("coded oracle in candidate")), \
             mock.patch.object(ybind,"coded_exact_binding_oracle",
                               side_effect=AssertionError("coded oracle in candidate")):
            f107.wing_pred(wm,("query_attention","top_two_contrast",
                               "signed_soft_margin"),wing,wing.positive_values)
            f107.ygg_pred(ym,("node_pooled","max","target_relative_mass"),
                          ygg,ygg.positive_variables)

    def test_current_run_F106_sha_receipt_and_wrong_directive_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report,receipt=fixture(root)
            data,digest=f107.receipt_current(report,receipt,SHA)
            self.assertEqual(data["source_sha"],SHA)
            self.assertEqual(len(digest),64)
            report.write_bytes(report.read_bytes()+b"x")
            with self.assertRaisesRegex(f107.Quarantined,"TAMPERED"):
                f107.receipt_current(report,receipt,SHA)
        with tempfile.TemporaryDirectory() as td:
            report,receipt=fixture(Path(td),wrong_advice=True)
            with self.assertRaisesRegex(f107.Quarantined,"UNSUPPORTED_NEXT"):
                f107.receipt_current(report,receipt,SHA)

    def test_wrong_hosted_source_or_firstuse_claim_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            report,receipt=fixture(Path(td))
            with self.assertRaisesRegex(f107.Quarantined,"RUN_SOURCE"):
                with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
                    f107.evaluate(SHA,td)
            data=json.loads(report.read_text())
            data["protected_first_use_authorized"]=True
            raw=(json.dumps(data,sort_keys=True)+"\n").encode()
            report.write_bytes(raw)
            receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
            with self.assertRaisesRegex(f107.Quarantined,"UNQUALIFIED"):
                f107.receipt_current(report,receipt,SHA)

    def test_actual_generator_screen_retains_all_losers_and_authority_zero(self):
        with tempfile.TemporaryDirectory() as td:
            fixture(Path(td))
            report=f107.evaluate(SHA,td)
        self.assertEqual(report["schema"],f107.REPORT)
        self.assertEqual(report["source_sha"],SHA)
        self.assertEqual(report["independent_new_cohorts_per_lane"],2)
        self.assertEqual(len(report["lanes"]),2)
        self.assertEqual(report["candidate_count"],sum(
            x["candidates_generated"] for x in report["lanes"]))
        for row in report["lanes"]:
            self.assertEqual(len(row["all_candidate_train_results"]),
                             row["candidates_generated"])
            self.assertGreaterEqual(row["distinct_structural_families"],3)
            self.assertEqual(row["new_train_pairs"],48)
            self.assertEqual(row["new_diagnostic_pairs"],48)
            self.assertEqual(row["parent_training_updates"],100)
            self.assertEqual(row["coded_oracle_separate_control_accuracy"],1.)
            self.assertTrue(any(p["sha256"]==row["selected_program_fingerprint"]
                                for p in row["all_candidate_train_results"]))
            self.assertIn(row["outcome"],("POSITIVE_DEV_NEW_STRUCTURE_ONLY",
                                         "NEGATIVE_DEV_NEW_STRUCTURE_PRESERVED"))
            self.assertTrue(row["no_protected_first_use"])
            self.assertTrue(row["no_automatic_dispatch"])
        self.assertEqual(report["scientific_originals_executed"],0)
        self.assertEqual(report["codex_invocations"],0)
        self.assertEqual(report["paid_api_calls"],0)
        self.assertEqual(report["accepted_ref_mutations"],0)
        self.assertFalse(report["protected_first_use_authorized"])
        self.assertFalse(report["free_form_GPT_inference"])

if __name__=="__main__":
    unittest.main()
