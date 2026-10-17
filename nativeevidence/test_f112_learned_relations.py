"""F112 frozen public mechanism challenge and authentic ancestor evidence checks.

Unit fixtures are explicitly TEST-ONLY and never scientific results. Hosted
run reads the real current F111 evidence with all ancestors independently
recomputed, and tests three preregistered assessment blocks per lane.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f112_learned_relations as f112
import f111_nonadditive_transfer as f111
import f103_yggdrasil_public_binding as ybind
from test_f111_nonadditive_transfer import fixture as previous_fixture

SOURCE="a"*40
def fixture(root):
    previous_fixture(root)
    data=f111.evaluate(SOURCE,root)
    report=root/"forge-f111-development/f111-nonadditive-strong-controls.json"
    receipt=root/"forge-f111-development/f111-nonadditive-strong-controls.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(raw)
    receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
    return report,receipt

class F112LearnedRelations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.freeze_hash=f112.freeze()
    def setUp(self):
        self.saved=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE
    def tearDown(self):
        if self.saved is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.saved

    def test_first_commit_frozen_source_and_no_scientific_authority(self):
        self.assertEqual(self.cfg["parent_exact_head_sha"],
                         "559f5979feea3b3e538de38c82b02db00d3ab37c")
        self.assertEqual(len(self.freeze_hash),64)
        self.assertEqual(self.cfg["Wingless"]["max_trainable_parameters"],32)
        self.assertTrue(self.cfg["source_and_authority"]["no_codex"])
        self.assertTrue(self.cfg["source_and_authority"]["no_protected_first_use"])

    def test_learned_character_relation_features_are_not_exact_boolean_truth(self):
        self.assertEqual(len(f112.features("abc","abc")),6)
        one=f112.features("abcX","abcY")
        two=f112.features("abcX","abcX")
        self.assertTrue(all(0<=v<=1 for v in one+two))
        self.assertNotEqual(one,two)
        self.assertTrue(any(0<v<1 for v in one))
        self.assertEqual(f112.LearnedRelationAttention.parameters,6)

    def test_new_identifier_alphabets_and_disjoint_cohorts(self):
        training,groups=f112.wing_cohorts()
        self.assertEqual(len(training),96)
        self.assertEqual([len(g) for g in groups],[48,48,48])
        self.assertEqual(len({p.seed for g in groups for p in g}),144)
        self.assertTrue({p.seed for p in training}.isdisjoint(
            {p.seed for g in groups for p in g}))
        for group in groups:
            for p in group:
                self.assertEqual(len(set(p.source_codes)),4)
                self.assertIn(p.requested_code,p.source_codes)
                self.assertEqual(sum(a!=b for a,b in zip(
                    p.positive_values,p.negative_values)),1)
                self.assertTrue(f112.exact_lookup(p,p.positive_values))
                self.assertFalse(f112.exact_lookup(p,p.negative_values))

    def test_inference_uses_character_metadata_not_coded_truth_or_labels(self):
        train,groups=f112.wing_cohorts()
        model=f112.LearnedRelationAttention().train(train)
        self.assertEqual(model.updates,100)
        self.assertLessEqual(model.parameters,32)
        p=groups[0][0]
        with mock.patch.object(f112,"exact_lookup",
                               side_effect=AssertionError("oracle during candidate prediction")):
            self.assertIsInstance(model.predicts(p,p.positive_values),bool)
            self.assertIsInstance(f112.fixed_similarity(p,p.positive_values),bool)

    def test_three_collision_graph_groups_valid_and_source_disjoint(self):
        groups=f112.graph_groups()
        self.assertEqual([len(g) for g in groups],[48,48,48])
        self.assertEqual(len({p.seed for g in groups for p in g}),144)
        for group in groups:
            for p in group:
                self.assertEqual(len(p.edges),12)
                self.assertEqual(len(set(p.edges)),12)
                self.assertTrue(ybind.coded_exact_binding_oracle(p,p.positive_variables))
                self.assertFalse(ybind.coded_exact_binding_oracle(p,p.negative_variables))
                self.assertEqual(sum(a!=b for e1,e2 in zip(
                    p.positive_variables,p.negative_variables)
                    for a,b in zip(e1,e2)),1)

    def test_f111_digest_tamper_quarantines(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            report,receipt=fixture(root)
            self.assertEqual(len(f112.prior_evidence(SOURCE,root,self.cfg)),64)
            report.write_bytes(report.read_bytes()+b"x")
            with self.assertRaisesRegex(f112.Quarantined,"RECEIPT_TAMPER"):
                f112.prior_evidence(SOURCE,root,self.cfg)

    def test_full_new_evaluation_preserves_negative_and_positive_disposition(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root)
            report=f112.evaluate(SOURCE,root)
        self.assertEqual(report["schema"],f112.REPORT)
        self.assertEqual(report["new_diagnostic_pairs_per_lane"],144)
        self.assertTrue(report["all_288_paired_records_preserved"])
        self.assertEqual(len(report["lanes"]),2)
        for lane in report["lanes"]:
            self.assertEqual(len(lane["blocks"]),3)
            self.assertEqual([len(b["individual_cases"]) for b in lane["blocks"]],
                             [48,48,48])
            self.assertTrue(all(b["correct_pairs_by_arm"][
                "full_metadata_exact_lookup"]==48 for b in lane["blocks"])
                if lane["lane"]=="Wingless" else
                all(b["correct_pairs_by_arm"][
                    "exact_coded_oracle_separate"]==48 for b in lane["blocks"]))
        self.assertEqual(report["codex_calls"],0)
        self.assertEqual(report["paid_model_api_calls"],0)
        self.assertFalse(report["protected_first_use_authorized"])
        self.assertEqual(report["accepted_ref_mutations"],0)

    def test_untrusted_hosted_SHA_denied(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f112.Quarantined,"HOSTED_SOURCE_DRIFT"):
                f112.evaluate(SOURCE,"/tmp/none")

if __name__=="__main__":
    unittest.main()
