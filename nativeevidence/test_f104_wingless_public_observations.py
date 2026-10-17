"""F104 bounded adversarial qualification for real learned one-observation selection."""
import json
import pathlib
import tempfile
import unittest
from dataclasses import replace
from unittest import mock

import f104_wingless_public_observations as f104

class F104LearnedObservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol,cls.digest=f104.frozen()
        cls.groups=f104.public_groups()
        cls.trained=f104.LearnedObservationSelector().fit(cls.groups[0]+cls.groups[1])
        cls.blind=f104.LearnedObservationSelector(depth_blind=True).fit(
            cls.groups[0]+cls.groups[1])

    def test_preregistration_identity_and_hard_budget(self):
        self.assertEqual(self.protocol["parent_f103_head_sha"],f104.PARENT)
        self.assertEqual(self.protocol["candidate_id"],"W100-C2")
        self.assertEqual(self.protocol["cohort"]["training_counterfactual_pairs"],96)
        self.assertEqual(self.protocol["cohort"]["assessment_counterfactual_pairs"],48)
        self.assertEqual(self.trained.parameters,18)
        self.assertEqual(self.trained.training_updates,100)
        self.assertEqual(self.blind.training_updates,100)
        self.assertEqual(len(self.digest),64)

    def test_all_public_counterfactuals_and_disjoint_seeds(self):
        all_cases=[c for b in self.groups for c in b]
        self.assertEqual(len(all_cases),144)
        self.assertEqual(len({(x.seed,x.specimen) for x in all_cases}),144)
        for p in all_cases:
            self.assertEqual(set(p.observation_depths),set(range(4)))
            self.assertTrue(f104.coded_depth_observation_oracle(p,p.positive_values))
            self.assertFalse(f104.coded_depth_observation_oracle(p,p.negative_values))
            self.assertEqual(sum(a!=b for a,b in zip(
                p.positive_values,p.negative_values)),1)
        with self.assertRaises(f104.Rejected):
            f104.generate(63100,0,0)
        with self.assertRaises(f104.Rejected):
            f104.generate(51300,0,0)

    def test_learned_one_observation_beats_query_blind(self):
        cohort=self.groups[2]
        learned=f104.paired_accuracy(cohort,self.trained.predicts)
        blind=f104.paired_accuracy(cohort,self.blind.predicts)
        self.assertGreaterEqual(learned,0.75)
        self.assertGreaterEqual(learned-blind,0.15)
        self.assertEqual(f104.paired_accuracy(cohort,lambda p,v:True),0)
        self.assertGreaterEqual(sum(
            self.trained.selected_depth(p)==p.query_depth for p in cohort)/len(cohort),
            0.75)

    def test_query_changes_selected_slot_on_same_observations(self):
        cohort=self.groups[2]
        for p in cohort:
            selections={self.trained.selected_depth(replace(p,query_depth=depth))
                        for depth in range(4)}
            self.assertGreaterEqual(len(selections),3)
            self.assertIn(self.trained.choose(p),range(4))
            self.assertEqual(len(self.trained.attention_weights(p)),4)

    def test_prediction_never_calls_coded_oracle(self):
        p=self.groups[2][0]
        with mock.patch.object(f104,"coded_depth_observation_oracle",
                               side_effect=AssertionError("coded oracle use")):
            self.trained.probability(p,p.positive_values)
            self.trained.probability(p,p.negative_values)
            f104.LearnedObservationSelector().fit(
                self.groups[0]+self.groups[1])

    def test_no_post_freeze_threshold_or_lineage_modification(self):
        original=f104.FREEZE.read_text(encoding="utf8")
        mutant=json.loads(original)
        mutant["metrics"]["screen_only_thresholds"]["minimum_paired_accuracy"]=0
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/"altered.json"
            path.write_text(json.dumps(mutant),encoding="utf8")
            with mock.patch.object(f104,"FREEZE",path):
                with self.assertRaisesRegex(f104.Rejected,"DRIFT"):
                    f104.frozen()

    def test_retraining_and_extra_budget_rejected(self):
        with self.assertRaisesRegex(f104.Rejected,"TRAINING_BUDGET"):
            self.trained.fit(self.groups[0]+self.groups[1],steps=100)
        with self.assertRaisesRegex(f104.Rejected,"TRAINING_BUDGET"):
            f104.LearnedObservationSelector().fit(
                self.groups[0]+self.groups[1],steps=101)

    def test_source_bound_and_non_authorizing_receipt(self):
        with mock.patch.dict("os.environ",{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f104.Rejected,"SOURCE_REF"):
                f104.evaluate("a"*40)
        with mock.patch.dict("os.environ",{"GITHUB_SHA":"a"*40}):
            proof=f104.evaluate("a"*40)
        self.assertEqual(proof["schema"],f104.REPORT)
        self.assertEqual(proof["total_development_pairs"],144)
        self.assertEqual(proof["observation_budget_per_prediction"],1)
        self.assertTrue(proof["historical_W_F10_negative_0_of_96_preserved"])
        self.assertEqual(proof["scientific_originals_executed"],0)
        self.assertEqual(proof["accepted_ref_mutations"],0)
        self.assertEqual(proof["codex_calls"],0)
        self.assertEqual(proof["paid_model_api_calls"],0)
        self.assertFalse(proof["protected_first_use_authorized"])
        self.assertFalse(proof["optimizer_promotion_authorized"])

if __name__=="__main__":
    unittest.main()
