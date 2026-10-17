"""F110 adversarial tests: same-parameter control, multiple untouched public blocks,
source-verified F109 and negative-preserving three-lane family evidence.
Local reports are TEST-ONLY; CI's main runner consumes its own F109 reports.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from unittest import mock

import f109_failure_driven_mechanisms as f109
import f110_capacity_transfer as f110
import f103_yggdrasil_public_binding as ybind
from test_f109_failure_driven_mechanisms import build_fixture

SOURCE="a"*40

def local_evidence(root):
    build_fixture(root)
    report_data=f109.evaluate(SOURCE,root)
    report=root/"forge-f109-development/f109-failure-driven-public-dev.json"
    receipt=root/"forge-f109-development/f109-failure-driven-public-dev.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(report_data,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(raw)
    receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
    return report,receipt

class F110IndependentCapacityTransfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=f110.frozen()

    def setUp(self):
        self.prior_sha=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE

    def tearDown(self):
        if self.prior_sha is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.prior_sha

    def test_first_commit_freeze_and_denied_scientific_authority(self):
        self.assertEqual(self.cfg["parent_f109_exact_head_sha"],f110.PARENT)
        self.assertEqual(len(self.digest),64)
        self.assertTrue(self.cfg["safety"]["no_accepted_refs"])
        self.assertTrue(self.cfg["safety"]["no_codex"])
        self.assertTrue(self.cfg["frozen_outcomes"]["no_retraining_after_diagnostic"])

    def test_three_disjoint_wingless_blocks_and_paired_public_truth(self):
        groups=f110.wing_blocks()
        self.assertEqual([len(x) for x in groups],[48,48,48])
        self.assertEqual(len({p.base.seed for g in groups for p in g}),144)
        for block,group in enumerate(groups):
            self.assertEqual({p.offset for p in group},{0,1,2,3})
            for p in group:
                tagged=(p.base.query_depth+p.offset)%4
                idx=p.base.observation_depths.index(tagged)
                self.assertEqual(sum(x!=y for x,y in zip(
                    p.base.positive_values,p.base.negative_values)),1)
                strength=[1.,1.,.25][block]
                self.assertEqual((p.base.positive_values[idx],
                                  p.base.negative_values[idx]),(strength,-strength))

    def test_new_yggdrasil_blocks_preserve_oracle_and_case_budget(self):
        groups=f110.ygg_blocks()
        self.assertEqual([len(x) for x in groups],[48,48,48])
        self.assertEqual(len({p.seed for g in groups for p in g}),144)
        for g in groups:
            for p in g:
                self.assertEqual(len(p.edges),12)
                self.assertTrue(ybind.coded_exact_binding_oracle(p,p.positive_variables))
                self.assertFalse(ybind.coded_exact_binding_oracle(p,p.negative_variables))

    def test_exact_capacity_training_budgets_and_one_observation(self):
        train,_=f109.wing_cohorts()
        proposed=f109.LearnedSourceRouting().train(train)
        comparator=f110.CapacityMatchedQueryOnly().train(train)
        self.assertEqual(proposed.parameters,comparator.parameters)
        self.assertEqual(proposed.parameters,64)
        self.assertEqual(proposed.steps,comparator.steps)
        self.assertEqual(proposed.steps,100)
        for p in f110.wing_blocks()[0]:
            idx=comparator.slot(p)
            self.assertIn(idx,range(4))
            self.assertEqual(comparator.predicts(p,p.base.positive_values),
                             p.base.positive_values[idx]>0)

    def test_query_only_capacity_control_cannot_use_offset_to_switch(self):
        p=f110.wing_blocks()[1][0]
        unmodified=f110.CapacityMatchedQueryOnly()
        initial_slot=unmodified.slot(p)
        for offset in range(4):
            self.assertEqual(initial_slot,unmodified.slot(replace(p,offset=offset)))
        proposed=f109.LearnedSourceRouting().train(f109.wing_cohorts()[0])
        selections=[proposed.selected_slot(replace(p,offset=z)) for z in range(4)]
        self.assertGreaterEqual(len(set(selections)),2)

    def test_f109_attested_report_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report,receipt=local_evidence(root)
            f110.authentic_f109(SOURCE,root,self.cfg)
            report.write_bytes(report.read_bytes()+b"t")
            with self.assertRaisesRegex(f110.Quarantined,"RECEIPT_DRIFT"):
                f110.authentic_f109(SOURCE,root,self.cfg)

    def test_full_public_transfer_retains_negative_and_positive_outcomes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);local_evidence(root)
            report=f110.evaluate(SOURCE,root)
        self.assertEqual(report["schema"],f110.REPORT)
        self.assertEqual(report["frozen_conditions_per_lane"],3)
        self.assertEqual(report["public_pairs_per_lane"],144)
        self.assertEqual(len(report["lanes"]),2)
        for lane in report["lanes"]:
            self.assertEqual(len(lane["blocks"]),3)
            self.assertEqual([len(b["all_paired_decisions"]) for b in lane["blocks"]],
                             [48,48,48])
            self.assertEqual(lane["total_assessment_pairs"],144)
            self.assertIn(lane["disposition"],(
                "BOUNDED_PUBLIC_TRANSFER_ADVANTAGE_NOT_SCIENCE",
                "CAPACITY_MATCHED_TRANSFER_NOT_DEMONSTRATED_RETAIN_ALL_NEGATIVES"))
        wing=report["lanes"][0]
        self.assertEqual(wing["candidate_parameters"],wing["matched_control_parameters"])
        self.assertEqual(wing["candidate_observation_reads"],wing["matched_control_observation_reads"])
        self.assertEqual(wing["net_capacity_control_paired_advantage"],
                         wing["candidate_only_correct"]-wing["capacity_control_only_correct"])
        self.assertEqual(report["independently_accepted_science"],0)
        self.assertEqual(report["codex_calls"],0)
        self.assertEqual(report["paid_model_api_calls"],0)
        self.assertFalse(report["protected_first_use_authorized"])
        self.assertFalse(report["new_scheduler_created"])

    def test_wrong_runner_source_sha_denied(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f110.Quarantined,"EXACT_CURRENT"):
                f110.evaluate(SOURCE,"/tmp/none")

if __name__=="__main__":
    unittest.main()
