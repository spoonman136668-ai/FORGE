"""F108 scientific-claims denial and frozen public parent-vs-structural tests.

All in-memory fixture reports explicitly TEST-ONLY. Hosted qualification consumes
fresh F107 current-run report and SHA256 receipt from the existing GitHub runner.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f107_structural_mechanisms as f107
import f108_public_superiority as f108
import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve

SRC="a"*40

def create_f107_fixture(root):
    cfg,_=f108.get_config()
    lanes=[]
    for lane,expect in cfg["required_f107_selected"].items():
        ast=expect["ast"]
        lanes.append(dict(lane=lane,source_parent_C2=expect["parent"],
            selected_program_ast=ast,
            selected_program_fingerprint=f107.fingerprint(lane,ast),
            new_diagnostic_pairs=48,coded_oracle_separate_control_accuracy=1.0,
            no_protected_first_use=True,no_automatic_dispatch=True))
    payload=dict(schema=f107.REPORT,source_sha=SRC,
        F106_feedback_consumed=True,diagnostic_not_used_to_choose=True,
        choices_from_train_only=True,candidate_count=33,
        scientific_originals_executed=0,independent_science_accepted=0,
        protected_first_use_authorized=False,accepted_ref_mutations=0,
        codex_invocations=0,paid_api_calls=0,lanes=lanes)
    report=root/"forge-f107-development/f107-structural-mechanism-search.json"
    rec=root/"forge-f107-development/f107-structural-mechanism-search.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    contents=(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(contents)
    rec.write_text(hashlib.sha256(contents).hexdigest()+"  "+report.name+"\n")
    return report,rec

class F108FrozenProspective(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.hash=f108.get_config()

    def setUp(self):
        self.saved=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SRC

    def tearDown(self):
        if self.saved is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.saved

    def test_policy_frozen_before_implementation(self):
        self.assertEqual(self.cfg["parent_f107_exact_head_sha"],f108.PARENT_F107)
        self.assertEqual(len(self.hash),64)
        self.assertTrue(self.cfg["predeclared_metrics"]["negative_is_valid_outcome_not_ci_failure"])
        self.assertEqual(self.cfg["predeclared_metrics"]["improvement_gate"]["minimum_net_pair_advantage"],6)
        self.assertTrue(self.cfg["guardrails"]["no_independent_science_acceptance"])

    def test_new_public_seeds_and_verifiable_counterfactuals(self):
        w=f108.wingless_cases()
        y=f108.ygg_cases()
        self.assertEqual(len(w),48)
        self.assertEqual(len(y),48)
        self.assertEqual(len({p.seed for p in w}),48)
        self.assertEqual(len({p.seed for p in y}),48)
        self.assertTrue(all(65300<=p.seed<=65347 for p in w))
        self.assertTrue(all(65400<=p.seed<=65447 for p in y))
        self.assertEqual({p.block for p in w},{0,1,2})
        self.assertEqual({p.block for p in y},{0,1,2})
        for p in w:
            self.assertEqual(sum(a!=b for a,b in zip(p.positive_values,p.negative_values)),1)
            self.assertTrue(wobserve.coded_depth_observation_oracle(p,p.positive_values))
            self.assertFalse(wobserve.coded_depth_observation_oracle(p,p.negative_values))
            self.assertTrue(all(t in (0,1,2,3) for t in p.observation_depths))
        for p in y:
            self.assertEqual(len(p.edges),12)
            self.assertEqual(sum(a!=b for q,r in zip(p.positive_variables,p.negative_variables)
                                 for a,b in zip(q,r)),1)
            self.assertTrue(ybind.coded_exact_binding_oracle(p,p.positive_variables))
            self.assertFalse(ybind.coded_exact_binding_oracle(p,p.negative_variables))

    def test_inference_has_no_coded_oracle_leakage(self):
        w=f108.wingless_cases()[0]
        y=f108.ygg_cases()[0]
        wm=wobserve.LearnedObservationSelector()
        ym=ybind.LearnedVariableBinder()
        with mock.patch.object(wobserve,"coded_depth_observation_oracle",
                               side_effect=AssertionError("oracle leaked")), \
             mock.patch.object(ybind,"coded_exact_binding_oracle",
                               side_effect=AssertionError("oracle leaked")):
            f107.wing_pred(wm,tuple(self.cfg["required_f107_selected"]["Wingless"]["ast"]),
                           w,w.positive_values)
            f107.ygg_pred(ym,tuple(self.cfg["required_f107_selected"]["Yggdrasil"]["ast"]),
                          y,y.positive_variables)

    def test_genuine_source_bound_report(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);create_f107_fixture(root)
            data,digest=f108.get_current_F107(SRC,root,self.cfg)
        self.assertEqual(data["source_sha"],SRC)
        self.assertEqual(len(digest),64)

    def test_fail_closed_on_wrong_selected_mechanism_even_with_valid_checksum(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);report,receipt=create_f107_fixture(root)
            content=json.loads(report.read_text())
            content["lanes"][0]["selected_program_ast"][1]="single_argmax"
            payload=(json.dumps(content,sort_keys=True,separators=(",",":"))+"\n").encode()
            report.write_bytes(payload)
            receipt.write_text(hashlib.sha256(payload).hexdigest()+"  "+report.name+"\n")
            with self.assertRaisesRegex(f108.Quarantined,"SUBSTITUTED"):
                f108.get_current_F107(SRC,root,self.cfg)

    def test_missing_or_tampered_F107_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);report,receipt=create_f107_fixture(root)
            report.write_bytes(report.read_bytes()+b"x")
            with self.assertRaisesRegex(f108.Quarantined,"CONTENT_OR_HASH"):
                f108.get_current_F107(SRC,root,self.cfg)

    def test_full_scoring_retain_all_48_pair_discordances(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);create_f107_fixture(root)
            data=f108.evaluate(SRC,root)
        self.assertEqual(data["schema"],f108.REPORT)
        self.assertEqual(data["total_new_public_assessment_pairs"],96)
        self.assertEqual(len(data["diagnostic_results"]),2)
        for v in data["diagnostic_results"]:
            self.assertEqual(len(v["all_paired_record_details"]),48)
            self.assertEqual(v["diagnostic_pair_count"],48)
            self.assertEqual(v["coded_control_score"],1.)
            self.assertEqual(v["parent_training_updates"],100)
            self.assertEqual(v["candidate_only_correct"]-
                v["parent_only_correct"],v["net_paired_advantage"])
            self.assertEqual(sum(x["candidate_both_correct"] for x
                in v["all_paired_record_details"]),v["candidate_correct_pairs"])
            self.assertIn(v["outcome"],(
                "NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE",
                "PUBLIC_DEV_RESOURCE_MATCHED_ADVANTAGE_NO_SCIENCE"))
            if v["frozen_resource_matched_superiority_gate_passed"]:
                self.assertTrue(v["cost_parity_satisfied"])
                self.assertGreaterEqual(v["net_paired_advantage"],6)
        self.assertEqual(data["scientific_originals_dispatched"],0)
        self.assertEqual(data["independently_accepted_science"],0)
        self.assertEqual(data["accepted_ref_mutations"],0)
        self.assertEqual(data["codex_calls"],0)
        self.assertEqual(data["paid_model_api_calls"],0)
        self.assertFalse(data["definitive_mechanism_improvement_claim"])
        self.assertFalse(data["first_use_authorized"])

    def test_current_sha_required(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);create_f107_fixture(root)
            with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
                with self.assertRaisesRegex(f108.Quarantined,"RUN_SOURCE"):
                    f108.evaluate(SRC,root)

if __name__=="__main__":
    unittest.main()
