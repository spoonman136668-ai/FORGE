import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f102_yggdrasil_public_roles as f102

SHA=os.environ.get("GITHUB_SHA") or "f"*40

class F102PublicRoleComposition(unittest.TestCase):
    def test_first_commit_prereg_and_denied_authority(self):
        c,digest=f102.frozen()
        self.assertEqual(c["parent_f101_sha"],f102.PARENT_F101)
        self.assertEqual(c["candidate_id"],"Y100-C1")
        self.assertEqual(c["learned_mechanism"]["total_trainable_parameters"],18)
        self.assertEqual(len(digest),64)
        self.assertTrue(c["guards"]["preregistration_committed_before_executable_code"])
        self.assertTrue(c["guards"]["no_first_use_authorization"])
    def test_all_new_public_role_swap_pairs_and_oracle_control(self):
        groups=f102.public_groups()
        self.assertEqual([len(g) for g in groups],[48,48,48])
        ids=set()
        for block,cohort in enumerate(groups):
            for case in cohort:
                self.assertEqual(case.block,block)
                self.assertNotIn(case.seed,range(51400,51448))
                self.assertEqual(len(case.edges),len(set(case.edges)))
                self.assertEqual(len(case.edges),12)
                self.assertEqual(len(case.query_roles),4)
                self.assertEqual(sum(a!=b for a,b in zip(case.positive_roles,case.negative_roles)),1)
                self.assertTrue(f102.coded_typed_role_oracle(case,case.positive_roles))
                self.assertFalse(f102.coded_typed_role_oracle(case,case.negative_roles))
                ids.add((case.seed,case.specimen))
        self.assertEqual(len(ids),144)
        with self.assertRaises(f102.Rejected):
            f102.generate(51400,0,0)
    def test_actual_gradient_fit_keeps_candidate_isolated_from_coded_oracle(self):
        groups=f102.public_groups()
        model=f102.LearnedRoleComposer()
        with patch.object(f102,"coded_typed_role_oracle",side_effect=AssertionError("ORACLE_IN_CANDIDATE")):
            model.fit(groups[0]+groups[1])
            example=groups[2][0]
            self.assertTrue(model.predicts(example,example.positive_roles))
            self.assertFalse(model.predicts(example,example.negative_roles))
        self.assertEqual(model.training_updates,100)
        self.assertEqual(len(model.compatibility)+2,18)
        with self.assertRaises(f102.Rejected):
            model.fit(groups[0]+groups[1])
        with self.assertRaises(f102.Rejected):
            f102.LearnedRoleComposer().fit(groups[0]+groups[1],steps=101)
    def test_report_is_deterministic_and_public_only_even_when_successful(self):
        a=f102.evaluate(SHA)
        b=f102.evaluate(SHA)
        self.assertEqual(a,b)
        self.assertEqual(a["total_public_development_pairs"],144)
        self.assertEqual(a["training_pairs"],96)
        self.assertEqual(a["public_development_assessment_pairs"],48)
        self.assertEqual(a["learned_training_updates"],100)
        self.assertEqual(a["blind_control_training_updates"],100)
        s=a["paired_public_dev_accuracy"]
        self.assertEqual(set(s),{"learned_typed_role_composer","size_matched_role_blind",
                    "query_role_permuted_ablation","always_yes_shortcut",
                    "coded_typed_role_oracle"})
        self.assertGreaterEqual(s["learned_typed_role_composer"],0.75)
        self.assertEqual(s["size_matched_role_blind"],0)
        self.assertEqual(s["always_yes_shortcut"],0)
        self.assertEqual(s["coded_typed_role_oracle"],1)
        self.assertLessEqual(s["query_role_permuted_ablation"],s["learned_typed_role_composer"])
        self.assertGreaterEqual(a["worst_role_family_accuracy"],0.6)
        self.assertEqual(a["node_renaming_prediction_agreement"],1)
        self.assertTrue(a["public_development_screen_passed"])
        self.assertTrue(a["historical_Y_F9_zero_of_192_negative_preserved"])
        for key in ("first_use_authorized","optimizer_promotion_authorized","ckb_plane_accessed"):
            self.assertFalse(a[key])
        for key in ("codex_invocations","external_model_api_calls","chatgpt_work_tasks",
                    "accepted_ref_mutations","scientific_originals_executed",
                    "independent_scientific_results_accepted"):
            self.assertEqual(a[key],0)
    def test_generator_source_and_graph_mutation_cannot_fake_results(self):
        g=f102.public_groups()
        p=g[2][0]
        self.assertEqual(f102.remap_nodes(p).positive_roles,p.positive_roles)
        self.assertEqual(f102.remap_nodes(p).query_roles,p.query_roles)
        altered=f102.Pair(p.seed,p.block,p.specimen,p.edges,p.negative_roles,p.negative_roles,
                          p.query_roles,p.source,p.target)
        self.assertFalse(f102.coded_typed_role_oracle(altered,altered.positive_roles))
        with patch.dict("os.environ",{"GITHUB_SHA":"0"*40}):
            with self.assertRaises(f102.Rejected):
                f102.evaluate("f"*40)
    def test_frozen_controls_historical_finding_or_budget_cannot_be_retuned(self):
        original,_=f102.frozen()
        for change in ("historical_gain","delete_control","paid_model",
                       "raise_budget","replay_seed","post_result_tuning"):
            altered=copy.deepcopy(original)
            if change=="historical_gain":
                altered["frozen_historical_negative"]["learned_paired_correct"]=192
            if change=="delete_control":altered["controls"].pop()
            if change=="paid_model":altered["guards"]["no_model_api_calls"]=False
            if change=="raise_budget":altered["learned_mechanism"]["maximum_training_updates"]=100000
            if change=="replay_seed":altered["public_development"]["seed_blocks"][0]=[51400,51415]
            if change=="post_result_tuning":altered["metrics"]["screen_only_thresholds"]["minimum_paired_accuracy"]=0.1
            with tempfile.TemporaryDirectory() as d:
                path=pathlib.Path(d)/"frozen.json"
                path.write_text(json.dumps(altered),encoding="utf-8")
                with patch.object(f102,"FROZEN",path),self.subTest(change=change):
                    with self.assertRaises(f102.Rejected):
                        f102.frozen()
if __name__=="__main__":unittest.main()
