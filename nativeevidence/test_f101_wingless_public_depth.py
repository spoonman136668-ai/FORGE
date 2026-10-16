import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f101_wingless_public_depth as f101

SOURCE="e"*40
class F101Development(unittest.TestCase):
    def test_frozen_prereg_is_source_bound_and_non_authorizing(self):
        frozen,digest=f101.frozen()
        self.assertEqual(frozen["candidate_id"],"W100-C1")
        self.assertEqual(frozen["parent_f100_head_sha"],f101.PARENT_F100)
        self.assertEqual(len(digest),64)
        self.assertFalse(frozen["separations"]["scientific_acceptance_authorized"])
        self.assertFalse(frozen["separations"]["uses_codex"])
    def test_source_held_public_generator_never_reuses_old_cohort(self):
        groups=f101.dataset()
        self.assertEqual([len(g) for g in groups],[48,48,48])
        self.assertEqual(sum(len(g) for g in groups),144)
        seen=set()
        for block,group in enumerate(groups):
            for p in group:
                self.assertEqual(p.block,block)
                self.assertNotIn(p.seed,range(51100,51124))
                self.assertLessEqual(p.depth,7)
                self.assertGreaterEqual(p.depth,4)
                self.assertEqual(len(p.edges),12)
                self.assertEqual(len(set(p.edges)),12)
                self.assertEqual(p.truth,(False,True))
                # Counterfactual ground truth is independent of trained scorer.
                self.assertFalse(f101.coded_exact_depth_oracle(p.edges,p.source,p.target,p.depth-1))
                self.assertTrue(f101.coded_exact_depth_oracle(p.edges,p.source,p.target,p.depth))
            keys={(p.seed,p.depth,tuple(p.edges)) for p in group}
            self.assertEqual(len(keys),len(group))
            seen.update(keys)
        self.assertEqual(len(seen),144)
        with self.assertRaises(f101.Rejected):
            f101.generate(51100,0,0)
    def test_learned_depth_recurrence_is_not_oracle_inference(self):
        groups=f101.dataset()
        learner=f101.LearnedDepthState().fit(groups[0]+groups[1])
        self.assertEqual(learner.updates,100)
        params=(learner.gain,learner.weight,learner.bias,learner.depth_weight)
        self.assertEqual(len(params),4)
        with patch.object(f101,"coded_exact_depth_oracle",side_effect=AssertionError("oracle called from candidate")):
            p=groups[2][0]
            pred1=learner.predict(p,p.depth-1)
            pred2=learner.predict(p,p.depth)
        self.assertEqual((pred1,pred2),p.truth)
        with self.assertRaises(f101.Rejected):
            learner.fit(groups[0]+groups[1],steps=1)
    def test_precommitted_controls_and_screen_are_deterministic(self):
        a=f101.evaluate(SOURCE)
        b=f101.evaluate(SOURCE)
        self.assertEqual(a,b)
        self.assertEqual(a["development_pair_count"],144)
        self.assertEqual(a["training_pair_count"],96)
        self.assertEqual(a["public_dev_assessment_pairs"],48)
        self.assertEqual(a["training_updates"],100)
        self.assertEqual(a["control_training_updates"],100)
        scores=a["public_dev_accuracy_by_arm"]
        self.assertEqual(set(scores),{"learned_depth_conditioned","size_matched_depth_blind",
                  "depth_permuted_ablation","always_yes_shortcut",
                  "coded_exact_depth_oracle"})
        self.assertGreaterEqual(scores["learned_depth_conditioned"],0.75)
        self.assertEqual(scores["size_matched_depth_blind"],0.0)
        self.assertEqual(scores["always_yes_shortcut"],0.0)
        self.assertEqual(scores["coded_exact_depth_oracle"],1.0)
        self.assertTrue(a["public_development_screen_passed"])
        self.assertGreaterEqual(a["worst_depth_paired_accuracy"],0.6)
        self.assertGreaterEqual(a["worst_public_source_group_paired_accuracy"],0.6)
        for key in ("independently_accepted_scientific_gain","protected_first_use_authorized",
                    "fresh_scientific_original_executed","optimizer_promotion_authorized"):
            self.assertIs(a[key],False)
        for key in ("accepted_ref_mutations","codex_calls","external_model_api_calls","chatgpt_work_tasks"):
            self.assertEqual(a[key],0)
    def test_unfrozen_or_authority_flipped_quarantines_source(self):
        freeze,digest=f101.frozen()
        for field,value in (("candidate_id","W100-C2"),("lane","Yggdrasil")):
            changed=copy.deepcopy(freeze)
            changed[field]=value
            with tempfile.TemporaryDirectory() as folder:
                path=pathlib.Path(folder)/"freeze.json"
                path.write_text(json.dumps(changed),encoding="utf-8")
                with patch.object(f101,"F101",path):
                    with self.assertRaises(f101.Rejected):f101.frozen()
        changed=copy.deepcopy(freeze)
        changed["separations"]["scientific_acceptance_authorized"]=True
        with tempfile.TemporaryDirectory() as folder:
            path=pathlib.Path(folder)/"freeze.json"
            path.write_text(json.dumps(changed),encoding="utf-8")
            with patch.object(f101,"F101",path):
                with self.assertRaises(f101.Rejected):f101.frozen()
    def test_wrong_source_or_unqualified_run_fails_closed(self):
        with patch.dict("os.environ",{"GITHUB_SHA":"f"*40}):
            with self.assertRaises(f101.Rejected):
                f101.evaluate(SOURCE)
        with self.assertRaises(f101.Rejected):
            f101.evaluate("INVALID")
if __name__=="__main__":
    unittest.main()
