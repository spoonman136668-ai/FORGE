"""F109 focused adversarial/public development qualification.

Synthetic local F107/F108 report fixtures are TEST-ONLY. Production intake
checks the same GitHub-run genuine F108 and all its source-bound ancestors.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f108_public_superiority as f108
import f109_failure_driven_mechanisms as f109
import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve
from test_f108_public_superiority import create_f107_fixture

TEST_SHA="a"*40

def build_fixture(root):
    create_f107_fixture(root)
    record=f108.evaluate(TEST_SHA,root)
    report=root/"forge-f108-development/f108-parent-superiority-public-transfer.json"
    receipt=root/"forge-f108-development/f108-parent-superiority-public-transfer.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(raw)
    receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
    return report,receipt

class F109FrozenNegativeDriven(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol,cls.digest=f109.frozen()

    def setUp(self):
        self.previous=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=TEST_SHA

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("GITHUB_SHA",None)
        else:
            os.environ["GITHUB_SHA"]=self.previous

    def test_preimplementation_contract_frozen_and_authority_denied(self):
        self.assertEqual(self.protocol["parent_f108_head_sha"],f109.PARENT)
        self.assertEqual(len(self.digest),64)
        self.assertEqual(self.protocol["screen"]["min_net_candidate_only_advantage_pairs"],6)
        self.assertTrue(self.protocol["authority"]["no_protected_first_use"])
        self.assertTrue(self.protocol["authority"]["no_codex"])

    def test_new_wingless_train_diagnostic_independent_and_query_truth(self):
        train,diagnostic=f109.wing_cohorts()
        self.assertEqual((len(train),len(diagnostic)),(96,48))
        self.assertTrue({x.base.seed for x in train}.isdisjoint(
            {x.base.seed for x in diagnostic}))
        self.assertEqual({x.offset for x in train},set(range(4)))
        self.assertEqual({x.offset for x in diagnostic},set(range(4)))
        for x in train+diagnostic:
            p=x.base
            queried=(p.query_depth+x.offset)%4
            pos=p.positive_values[p.observation_depths.index(queried)]
            neg=p.negative_values[p.observation_depths.index(queried)]
            self.assertEqual((pos,neg),(1.0,-1.0))
            self.assertEqual(sum(a!=b for a,b in
                zip(p.positive_values,p.negative_values)),1)

    def test_new_yggdrasil_seed_disjoint_and_oracle_truth(self):
        train,test=f109.ygg_cohorts()
        self.assertEqual((len(train),len(test)),(96,48))
        self.assertTrue({p.seed for p in train}.isdisjoint({p.seed for p in test}))
        for p in train+test:
            self.assertEqual(len(p.edges),12)
            self.assertTrue(ybind.coded_exact_binding_oracle(p,p.positive_variables))
            self.assertFalse(ybind.coded_exact_binding_oracle(p,p.negative_variables))
            self.assertEqual(sum(a!=b for a,b in
                zip(p.positive_variables,p.negative_variables)
                for a,b in zip(a,b)),1)

    def test_candidate_inference_does_not_call_ground_truth_oracle(self):
        w=f109.wing_cohorts()[1][0]
        y=f109.ygg_cohorts()[1][0]
        model_w=f109.LearnedSourceRouting()
        model_y=ybind.LearnedVariableBinder()
        with mock.patch.object(ybind,"coded_exact_binding_oracle",
                               side_effect=AssertionError("coded graph truth in inference")), \
             mock.patch.object(wobserve,"coded_depth_observation_oracle",
                               side_effect=AssertionError("coded source truth in inference")):
            model_w.predicts(w,w.base.positive_values)
            f109.strict_slot_predict(model_y,y,y.positive_variables)

    def test_full_actual_public_fit_and_negative_retention(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            build_fixture(root)
            record=f109.evaluate(TEST_SHA,root)
        self.assertEqual(record["schema"],f109.REPORT)
        self.assertEqual(len(record["lanes"]),2)
        self.assertTrue(record["prior_F108_negative_results_preserved"])
        for lane in record["lanes"]:
            self.assertEqual(lane["training_pairs"],96)
            self.assertEqual(lane["diagnostic_pairs"],48)
            self.assertEqual(len(lane["all_paired_records"]),48)
            self.assertEqual(lane["candidate_training_steps"],100)
            self.assertEqual(lane["parent_training_steps"],100)
            self.assertLessEqual(lane["candidate_resource_cost"],
                                 lane["parent_resource_cost"])
            self.assertEqual(lane["exact_control_score"],1.0)
            self.assertEqual(lane["candidate_only_correct"]-
                             lane["parent_only_correct"],
                             lane["net_pair_advantage"])
            self.assertIn(lane["disposition"],(
                "NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE",
                "POSITIVE_PUBLIC_DEV_SCREEN_NOT_INDEPENDENT_SCIENCE"))
        self.assertEqual(record["codex_calls"],0)
        self.assertEqual(record["paid_model_api_calls"],0)
        self.assertEqual(record["native_science_dispatches"],0)
        self.assertEqual(record["independent_science_accepted"],0)
        self.assertFalse(record["first_use_authorized"])

    def test_f108_tampering_or_replay_stops_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);report,receipt=build_fixture(root)
            report.write_bytes(report.read_bytes()+b"x")
            with self.assertRaisesRegex(f109.Quarantined,"F108_REPORT_DIGEST"):
                f109.read_parent(TEST_SHA,root,self.protocol)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);report,receipt=build_fixture(root)
            payload=json.loads(report.read_text())
            payload["diagnostic_results"][0]["candidate_score"]=1.0
            raw=(json.dumps(payload,sort_keys=True)+"\n").encode()
            report.write_bytes(raw)
            receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
            with self.assertRaisesRegex(f109.Quarantined,"F108_SOURCE_REPLAY"):
                f109.read_parent(TEST_SHA,root,self.protocol)

    def test_wrong_host_sha_denied(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f109.Quarantined,"EXACT_CURRENT"):
                f109.evaluate(TEST_SHA,"/tmp/not-a-source")

if __name__=="__main__":
    unittest.main()
