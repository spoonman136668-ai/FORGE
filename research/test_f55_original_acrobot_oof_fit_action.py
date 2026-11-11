"""F55 original-FIT-only deterministic, held-root-out source qualification.

Only consumed F51 book FIT actions; no F51/F53 scored episodes.
"""
import ast
import inspect
import math
import unittest

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f53_original_acrobot_supported_residual_dev as f53
import f54_original_acrobot_fit_quantile_action_audit as f54
import f55_original_acrobot_oof_fit_action as f55


class OriginalF55RootOutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=f55.score()

    def test_original_farama_source_still_exact(self):
        r=self.result
        self.assertEqual(r["original_source"]["upstream_commit"],f51.ORIGINAL_COMMIT)
        self.assertEqual(r["original_source"]["acrobot_git_blob"],f51.ORIGINAL_FILE_BLOB)
        self.assertEqual(r["original_fit_sha256"],f55.ORIGINAL_FIT_SHA256)
        self.assertEqual(r["old_fit_observations"],8974)
        self.assertEqual(r["old_fit_episodes"],48)
        self.assertEqual(f55.ROOTS,tuple(f51.FIT))

    def test_six_folds_exactly_one_whole_root_out(self):
        r=self.result
        self.assertEqual(r["fold_count"],6)
        self.assertEqual(tuple(x["excluded_root"] for x in r["folds"]),f55.ROOTS)
        self.assertEqual(sum(x["excluded_steps"] for x in r["folds"]),8974)
        for fold in r["folds"]:
            self.assertEqual(fold["excluded_episode_count"],8)
            self.assertEqual(len(fold["train_roots"]),5)
            self.assertNotIn(fold["excluded_root"],fold["train_roots"])
            self.assertEqual(len(set(fold["train_roots"])),5)
            self.assertEqual(fold["train_steps"]+fold["excluded_steps"],8974)
            self.assertEqual(len(fold["excluded_episode_metadata"]),8)
            self.assertEqual([e["episode"] for e in fold["excluded_episode_metadata"]],list(range(8)))
            self.assertEqual(sum(fold["excluded_action_counts"]),fold["excluded_steps"])

    def test_numeric_parameters_frozen_inside_five_root_training_only(self):
        for fold in self.result["folds"]:
            self.assertGreater(fold["positive_train_gaps"],0)
            self.assertTrue(math.isfinite(fold["training_q_margin"]))
            self.assertGreater(fold["training_q_margin"],0)
            self.assertEqual(sum(fold["training_action_counts"]),fold["train_steps"])
            self.assertTrue(all(x>0 for x in fold["training_action_counts"]))
            for key in ("trained_model_sha256","training_source_sha256",
                        "excluded_source_sha256","support_sha256"):
                self.assertRegex(fold[key],r"^[a-f0-9]{64}$")

    def test_each_arm_has_exact_root_action_counts(self):
        for fold in self.result["folds"]:
            audit=fold["action_audit"]
            self.assertEqual(set(audit["arms"]),set(f54.ARMS))
            for name,stats in audit["arms"].items():
                self.assertEqual(sum(stats["actions"]),fold["excluded_steps"],name)
                self.assertGreaterEqual(stats["behavior_matches"],0)
                self.assertLessEqual(stats["behavior_matches"],fold["excluded_steps"])
                self.assertGreaterEqual(stats["deviations"],0)
                self.assertLessEqual(stats["deviations"],fold["excluded_steps"])
            self.assertEqual(audit["arms"]["momentum-rule"]["deviations"],0)

    def test_support_control_is_subset_of_margin_only(self):
        for fold in self.result["folds"]:
            a=fold["action_audit"]
            s=a["support"]
            self.assertEqual(s["margin_eligible"],sum(s[k] for k in (
                "both_supported","only_g_supported","only_h_supported",
                "neither_supported")))
            self.assertEqual(a["arms"]["quantile-margin-only"]["deviations"],s["margin_eligible"])
            self.assertEqual(a["arms"]["quantile-supported"]["deviations"],s["both_supported"])
            self.assertLessEqual(s["both_supported"],s["margin_eligible"])

    def test_cold_actions_replayed_all_six_roots(self):
        self.assertEqual(self.result["cold_replay_verified_folds"],6)
        for fold in self.result["folds"]:
            self.assertTrue(fold["cold_action_replay_matches"])
            self.assertEqual(len(fold["action_audit"]["action_trace_sha256"]),len(f54.ARMS))
            for v in fold["action_audit"]["action_trace_sha256"].values():
                self.assertRegex(v,r"^[a-f0-9]{64}$")

    def test_scored_seeds_and_environment_evaluation_inaccessible(self):
        tree=ast.parse(inspect.getsource(f55))
        calls=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                fn=node.func
                if isinstance(fn,ast.Attribute) and isinstance(fn.value,ast.Name):
                    calls.add(fn.value.id+"."+fn.attr)
        self.assertFalse(calls & {
            "f51.evaluate","f53.evaluate","f53.score","f54.score",
            "f51.new_real_env","f53.new_real_env","gym.make",
            "env.reset","env.step"})
        self.assertIn("f51.collect_fit",calls)
        self.assertIn("f51.fit_fqi",calls)
        self.assertTrue(set((*f53.TRANSFER,*f53.RETENTION)) .isdisjoint(f55.ROOTS))
        self.assertFalse(self.result["original_first_use_consumed"])
        self.assertEqual(self.result["external_transfer_evaluations"],0)
        self.assertEqual(self.result["new_retention_evaluations"],0)
        self.assertEqual(self.result["physically_scored_excluded_episodes"],0)

    def test_frozen_disposition_and_exact_report_digest(self):
        r=self.result
        self.assertEqual(r["supported_oof_action_overrides"],sum(
            x["action_audit"]["arms"]["quantile-supported"]["deviations"]
            for x in r["folds"]))
        self.assertEqual(r["active_excluded_roots"],sum(
            x["action_audit"]["arms"]["quantile-supported"]["deviations"]>0
            for x in r["folds"]))
        self.assertEqual(r["required_min_oof_overrides"],90)
        self.assertEqual(r["required_min_active_roots"],4)
        positive=(r["supported_oof_action_overrides"]>=90 and
                  r["active_excluded_roots"]>=4)
        self.assertEqual(r["classification"],
            "F55_FIT_OOF_ACTIVATION_UNVERIFIED" if positive else "F55_FIT_OOF_NO_GO")
        self.assertFalse(r["science_accepted"])
        self.assertFalse(r["real_value_gain_proven"])
        self.assertFalse(r["unfamiliar_physics_transfer_proven"])
        self.assertEqual(f51.digest({k:v for k,v in r.items() if k!="report_sha256"}),
                         r["report_sha256"])


if __name__=="__main__":
    unittest.main()
