"""F103 adversarial checks for frozen Yggdrasil variable-slot development."""
import dataclasses
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import f103_yggdrasil_public_binding as f103

class F103FrozenDevelopment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol,cls.digest=f103.frozen()
        cls.cohorts=f103.public_cohorts()
        cls.learner=f103.LearnedVariableBinder().fit(cls.cohorts[0]+cls.cohorts[1])
        cls.blind=f103.LearnedVariableBinder(blind=True).fit(cls.cohorts[0]+cls.cohorts[1])

    def test_protocol_preregistered_before_implementation(self):
        self.assertEqual(self.protocol["parent_f102_head_sha"],f103.PARENT)
        self.assertEqual(self.protocol["candidate_id"],"Y100-C2")
        self.assertEqual(self.protocol["trainable_candidate"]["maximum_optimizer_steps"],100)
        self.assertEqual(self.protocol["public_development"]["train_counterfactual_pairs"],96)
        self.assertEqual(self.protocol["public_development"]["assessment_counterfactual_pairs"],48)
        self.assertEqual(len(self.digest),64)
        self.assertEqual(self.learner.parameter_count,20)

    def test_144_frozen_counterfactuals_and_no_seed_reuse(self):
        cohort=tuple(p for group in self.cohorts for p in group)
        self.assertEqual(len(cohort),144)
        self.assertEqual(len({(p.seed,p.specimen) for p in cohort}),144)
        for p in cohort:
            self.assertTrue(f103.coded_exact_binding_oracle(p,p.positive_variables))
            self.assertFalse(f103.coded_exact_binding_oracle(p,p.negative_variables))
            self.assertEqual(sum(a!=b for x,y in
                zip(p.positive_variables,p.negative_variables)
                for a,b in zip(x,y)),1)
            self.assertEqual(len(p.edges),len(p.roles))
            self.assertEqual(len(p.edges),12)
        with self.assertRaises(f103.Rejected):
            f103.generate(63400,0,0)
        with self.assertRaises(f103.Rejected):
            f103.generate(51400,0,0)

    def test_actual_training_beats_blind_and_shortcut_on_public_dev(self):
        assessment=self.cohorts[2]
        learned=f103.paired_accuracy(assessment,self.learner.predicts)
        blind=f103.paired_accuracy(assessment,self.blind.predicts)
        always=f103.paired_accuracy(assessment,lambda p,v:True)
        self.assertGreaterEqual(learned,0.75)
        self.assertGreaterEqual(learned-blind,0.15)
        self.assertEqual(blind,0)
        self.assertEqual(always,0)
        self.assertEqual(self.learner.training_updates,100)
        self.assertEqual(self.blind.training_updates,100)
        self.assertNotEqual(self.learner.slot[0],self.learner.slot[1])

    def test_alpha_renaming_and_node_remapping_preserve_predictions(self):
        for p in self.cohorts[2]:
            changed=f103.remap_variables(p)
            nodes=f103.remap_nodes(p)
            for vars1,vars2 in ((p.positive_variables,changed.positive_variables),
                                (p.negative_variables,changed.negative_variables)):
                self.assertEqual(self.learner.predicts(p,vars1),
                                 self.learner.predicts(changed,vars2))
                self.assertEqual(f103.coded_exact_binding_oracle(p,vars1),
                                 f103.coded_exact_binding_oracle(changed,vars2))
                self.assertEqual(self.learner.predicts(p,vars1),
                                 self.learner.predicts(nodes,vars1))

    def test_inference_does_not_use_coded_oracle(self):
        p=self.cohorts[2][0]
        with mock.patch.object(f103,"coded_exact_binding_oracle",
                               side_effect=AssertionError("oracle in inference")):
            self.learner.probability(p,p.positive_variables)
            self.learner.probability(p,p.negative_variables)

    def test_mutated_preregistration_rejected(self):
        original=f103.FREEZE.read_text(encoding="utf-8")
        changed=json.loads(original)
        changed["metrics"]["screen_only_thresholds"]["minimum_paired_accuracy"]=0
        with tempfile.TemporaryDirectory() as td:
            forged=pathlib.Path(td)/"f103-unsafe.json"
            forged.write_text(json.dumps(changed),encoding="utf-8")
            with mock.patch.object(f103,"FREEZE",forged):
                with self.assertRaisesRegex(f103.Rejected,"CONTRACT_DRIFT"):
                    f103.frozen()

    def test_budget_exactness_and_retraining_deny(self):
        with self.assertRaisesRegex(f103.Rejected,"TRAINING_BUDGET"):
            self.learner.fit(self.cohorts[0]+self.cohorts[1],steps=100)
        with self.assertRaisesRegex(f103.Rejected,"TRAINING_BUDGET"):
            f103.LearnedVariableBinder().fit(self.cohorts[0]+self.cohorts[1],steps=101)

    def test_evidence_inference_and_source_authority_denied(self):
        with mock.patch.dict("os.environ",{"GITHUB_SHA":"a"*40}):
            with self.assertRaisesRegex(f103.Rejected,"EXACT_SOURCE_REF"):
                f103.evaluate("b"*40)
        with mock.patch.dict("os.environ",{"GITHUB_SHA":"a"*40}):
            proof=f103.evaluate("a"*40)
        self.assertEqual(proof["schema"],f103.REPORT)
        self.assertEqual(proof["candidate_id"],"Y100-C2")
        self.assertEqual(proof["total_development_pairs"],144)
        self.assertEqual(proof["scientific_originals_executed"],0)
        self.assertEqual(proof["accepted_ref_mutations"],0)
        self.assertEqual(proof["codex_invocations"],0)
        self.assertEqual(proof["paid_api_calls"],0)
        self.assertFalse(proof["first_use_authorized"])
        self.assertFalse(proof["optimizer_promotion_authorized"])

if __name__=="__main__":
    unittest.main()
