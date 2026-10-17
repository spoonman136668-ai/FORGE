"""F113 adversarial tests for genuine query-source tag independence and controls.

Fixture evidence is test-only: CI revalidates the genuine current-run F112 report
and every ancestor receipt. New diagnostic conditions are frozen and never tuned.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f113_shortcut_resistant as f113
import f112_learned_relations as f112
import f103_yggdrasil_public_binding as ybind
from test_f112_learned_relations import fixture as fixture_F112_ancestors

SRC="a"*40
def test_fixture(root):
    fixture_F112_ancestors(root)
    data=f112.evaluate(SRC,root)
    report=root/"forge-f112-development/f112-learned-relations-branch-collisions.json"
    receipt=root/"forge-f112-development/f112-learned-relations-branch-collisions.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(raw)
    receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
    return report,receipt

class F113Falsification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=f113.frozen()
    def setUp(self):
        self.old=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SRC
    def tearDown(self):
        if self.old is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old

    def test_prereg_first_contract_locked_and_safety_denied(self):
        self.assertEqual(self.cfg["parent_F112_exact_head_sha"],f113.PARENT)
        self.assertEqual(len(self.digest),64)
        self.assertTrue(self.cfg["integrity"]["no_protected_first_use"])
        self.assertTrue(self.cfg["integrity"]["no_codex"])
        self.assertTrue(self.cfg["integrity"]["no_hindsight_diagnostic_retuning"])

    def test_all_16_query_vs_tag_cells_have_exactly_three_per_block(self):
        train,groups=f113.wing_groups()
        self.assertEqual(len(train),96)
        self.assertEqual([len(group) for group in groups],[48]*3)
        self.assertEqual(len({c.public.seed for g in groups for c in g}),144)
        self.assertTrue({c.public.seed for c in train}.isdisjoint(
                        {c.public.seed for g in groups for c in g}))
        for group in groups:
            matrix={(q,t):0 for q in range(4) for t in range(4)}
            for item in group:
                matrix[item.public.query_depth,item.true_source_tag]+=1
                self.assertNotIn(item.public.requested_code,item.public.source_codes)
                self.assertEqual(sum(a!=b for a,b in zip(
                    item.public.positive_values,item.public.negative_values)),1)
                self.assertTrue(f113.edit_distance_control(item.public,
                    item.public.positive_values))
                self.assertFalse(f113.edit_distance_control(item.public,
                    item.public.negative_values))
            self.assertEqual(set(matrix.values()),{3})
            self.assertEqual(sum(c.public.query_depth==c.true_source_tag
                                 for c in group),12)

    def test_learned_inference_cannot_call_exact_edit_control_or_label(self):
        train,groups=f113.wing_groups()
        learner=f112.LearnedRelationAttention().train(
            tuple(item.public for item in train))
        item=groups[0][0].public
        with mock.patch.object(f113,"edit_distance_control",
                    side_effect=AssertionError("label oracle leaked")), \
             mock.patch.object(f113,"oracle",
                    side_effect=AssertionError("truth leaked")):
            self.assertIsInstance(learner.predicts(item,item.positive_values),bool)
            self.assertIsInstance(f112.fixed_similarity(item,
                                  item.positive_values),bool)

    def test_near_miss_three_branch_graphs_not_all_easy_positives(self):
        groups=f113.graph_groups()
        self.assertEqual([len(group) for group in groups],[48]*3)
        self.assertEqual(len({p.seed for g in groups for p in g}),144)
        for group in groups:
            for p in group:
                self.assertEqual(len(p.edges),12)
                self.assertEqual(len(set(p.edges)),12)
                self.assertEqual(sum(a!=b for pair,other in zip(
                    p.positive_variables,p.negative_variables)
                    for a,b in zip(pair,other)),1)
                self.assertTrue(ybind.coded_exact_binding_oracle(
                    p,p.positive_variables))
                self.assertFalse(ybind.coded_exact_binding_oracle(
                    p,p.negative_variables))

    def test_parent_current_source_report_checksum_tamper_quarantine(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);report,receipt=test_fixture(base)
            self.assertEqual(len(f113.receive_F112(SRC,base,self.cfg)),64)
            report.write_bytes(report.read_bytes()+b"x")
            with self.assertRaisesRegex(f113.Quarantined,"SHA256_RECEIPT_TAMPER"):
                f113.receive_F112(SRC,base,self.cfg)

    def test_full_frozen_model_selection_and_negative_retention(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);test_fixture(base)
            report=f113.evaluate(SRC,base)
        self.assertEqual(report["schema"],f113.REPORT)
        self.assertEqual(report["frozen_counterfactuals_per_lane"],144)
        self.assertTrue(report["all_288_paired_decisions_retained"])
        self.assertTrue(report["preexisting_negative_evidence_retained"])
        self.assertEqual(len(report["lanes"]),2)
        w,y=report["lanes"]
        self.assertEqual(w["learned_parameters"],6)
        self.assertEqual(w["trained_query_control_parameters"],64)
        self.assertEqual([len(b["all_paired_decisions"]) for b in w["blocks"]],
                         [48,48,48])
        self.assertTrue(all(b["correct_pairs_by_arm"][
            "full_public_edit_distance_one_read"]==48 for b in w["blocks"]))
        self.assertEqual([len(b["all_paired_decisions"]) for b in y["blocks"]],
                         [48,48,48])
        self.assertTrue(all(b["correct_pairs_by_arm"][
            "separate_exact_coded_oracle"]==48 for b in y["blocks"]))
        self.assertIn(w["disposition"],(
          "PUBLIC_BOUNDED_LEARNED_RELATION_SCREEN_NO_SCIENCE",
          "NO_SUPERIORITY_OVER_STRONG_PUBLIC_CONTROLS_NEGATIVE_RETAINED"))
        self.assertFalse(report["protected_first_use_authorized"])
        self.assertEqual(report["accepted_ref_mutations"],0)
        self.assertEqual(report["codex_calls"],0)
        self.assertEqual(report["paid_model_calls"],0)

    def test_runtime_source_sha_not_malleable(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f113.Quarantined,"CURRENT_GITHUB_SHA"):
                f113.evaluate(SRC,"/tmp/nonexistent")

if __name__=="__main__":
    unittest.main()
