"""F56 original Acrobot source-only causal-proxy diagnostics.

Only already-consumed original `book` F51 FIT roots may be recollected.
No policy rollouts on fresh transfer/retention or scientific first use.
"""
import ast
import inspect
import math
import unittest

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f54_original_acrobot_fit_quantile_action_audit as f54
import f55_original_acrobot_oof_fit_action as f55
import f56_original_acrobot_fit_ips_proxy as f56


class F56OriginalLoggedBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=f56.score()

    def test_source_and_original_fit_custody(self):
        r=self.report
        self.assertEqual(r["original_source"]["upstream_commit"],f51.ORIGINAL_COMMIT)
        self.assertEqual(r["original_source"]["acrobot_git_blob"],f51.ORIGINAL_FILE_BLOB)
        self.assertEqual(r["original_fit_sha256"],f55.ORIGINAL_FIT_SHA256)
        self.assertEqual(r["original_fit_steps"],8974)
        self.assertEqual(r["original_fit_episodes"],48)
        self.assertEqual(tuple(r["roots"]),f55.ROOTS)
        self.assertEqual(r["recollected_historical_fit_resets"],48)
        self.assertEqual(r["new_scored_or_unfamiliar_reset_seeds"],0)

    def test_analytical_behavior_probabilities_positive_and_normalized(self):
        obs_far_up=[1.,0.,1.,0.,0.,0.2]
        obs_far_dn=[1.,0.,1.,0.,0.,-.2]
        obs_near_up=[1.,0.,1.,0.,0.,0.]
        obs_near_dn=[1.,0.,1.,0.,0.,-.1]
        np.testing.assert_allclose(f56.behavior_probs(obs_far_up),[.2,.2,.6])
        np.testing.assert_allclose(f56.behavior_probs(obs_far_dn),[.6,.2,.2])
        np.testing.assert_allclose(f56.behavior_probs(obs_near_up),[.2,.24,.56])
        np.testing.assert_allclose(f56.behavior_probs(obs_near_dn),[.56,.24,.2])
        for x in (obs_far_up,obs_far_dn,obs_near_up,obs_near_dn):
            probabilities=f56.behavior_probs(x)
            self.assertAlmostEqual(float(sum(probabilities)),1.0)
            self.assertGreaterEqual(float(min(probabilities)),.2-1e-12)
        with self.assertRaises(ValueError):
            f56.behavior_probs([float("nan")]*6)
        with self.assertRaises(ValueError):
            f56.behavior_probs([0.]*5)

    def test_real_end_effector_height_uses_only_public_state(self):
        bottom=[1.,0.,1.,0.,0.,0.]
        top=[-1.,0.,1.,0.,0.,0.]
        self.assertAlmostEqual(f56.tip_height(bottom),-2.)
        self.assertAlmostEqual(f56.tip_height(top),2.)
        delta,prob=f56.recorded_one_step([bottom,2,-1.,top,False,False])
        self.assertAlmostEqual(delta,4.)
        self.assertAlmostEqual(float(prob[2]),.56)
        with self.assertRaises(ValueError):
            f56.tip_height([0.,0.,1.,0.,0.,0.])
        with self.assertRaises(ValueError):
            f56.recorded_one_step([bottom,99,-1.,top,False,False])

    def test_six_folds_are_disjoint_original_roots_only(self):
        r=self.report
        self.assertEqual(r["root_count"],6)
        self.assertEqual(sum(f["excluded_steps"] for f in r["folds"]),8974)
        self.assertEqual(sum(f["excluded_episodes"] for f in r["folds"]),48)
        self.assertEqual(tuple(f["excluded_root"] for f in r["folds"]),f55.ROOTS)
        for f in r["folds"]:
            self.assertNotIn(f["excluded_root"],f["train_roots"])
            self.assertEqual(len(set(f["train_roots"])),5)
            self.assertEqual(f["excluded_episodes"],8)
            self.assertEqual(f["train_steps"]+f["excluded_steps"],8974)
            self.assertTrue(f["cold_replay_exact"])
            self.assertTrue(math.isfinite(f["calibrated_q_margin"]))
            self.assertGreater(f["calibrated_q_margin"],0)

    def test_ips_matched_counts_weights_ess_and_control_contrasts(self):
        r=self.report
        for f in r["folds"]:
            a=f["audit"]
            self.assertEqual(set(a["arms"]),set(f54.ARMS))
            self.assertEqual(a["recorded_steps"],f["excluded_steps"])
            for k,x in a["arms"].items():
                self.assertEqual(sum(x["actions"]),f["excluded_steps"])
                self.assertLessEqual(x["matched_count"],f["excluded_steps"])
                self.assertGreater(x["matched_count"],0)
                self.assertGreater(x["weight_sum"],0)
                self.assertLessEqual(x["weight_sum"],5*x["matched_count"]+1e-8)
                self.assertGreater(x["ess"],0)
                self.assertLessEqual(x["ess"],x["matched_count"]+1e-8)
                self.assertTrue(math.isfinite(x["ht_ips_mean"]))
            c=a["paired_contrasts"]
            for baseline in ("momentum-rule","frozen-fqi","rotated-credit"):
                self.assertAlmostEqual(c[baseline],a["arms"]["quantile-supported"]["ht_ips_mean"]-a["arms"][baseline]["ht_ips_mean"],places=12)
        self.assertTrue(all(x["ess"]>0 for x in r["aggregate_diagnostic_ess"].values()))

    def test_fixed_exhaustive_six_root_cluster_bootstrap(self):
        interval=f56.exhaustive_root_interval([.25]*6)
        self.assertEqual(interval["resamples"],46656)
        self.assertAlmostEqual(interval["lower_025"],.25)
        self.assertAlmostEqual(interval["upper_975"],.25)
        interval2=f56.exhaustive_root_interval([-1.,-1.,-1.,1.,1.,1.])
        self.assertLess(interval2["lower_025"],0.)
        self.assertGreater(interval2["upper_975"],0.)
        for c in self.report["root_cluster_exhaustive_intervals"].values():
            self.assertEqual(c["resamples"],46656)
            self.assertLessEqual(c["lower_025"],c["upper_975"])

    def test_no_fresh_physics_or_original_scientific_execution(self):
        code=ast.parse(inspect.getsource(f56))
        calls=set()
        for node in ast.walk(code):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name):
                calls.add(node.func.value.id+"."+node.func.attr)
        forbidden={"gym.make","f51.evaluate","f51.score","f51.collect_fit","f51.new_real_env",
                   "f53.evaluate","f53.score","f55.score","f54.score",
                   "env.reset","env.step"}
        self.assertFalse(calls & forbidden)
        self.assertIn("f55.source_and_root_groups",calls)
        r=self.report
        self.assertFalse(r["scientific_first_use"])
        self.assertFalse(r["scientific_accepted"])
        self.assertFalse(r["episodic_policy_return_proven"])
        self.assertFalse(r["unfamiliar_physics_transfer_proven"])
        self.assertEqual(r["fresh_scored_episodes"],0)

    def test_prespecified_classification_and_report_digest(self):
        r=self.report
        self.assertEqual(r["cold_exact_roots"],6)
        self.assertEqual(r["frozen_thresholds"],{
            "min_height_difference":.001,
            "min_positive_roots":5,
            "min_diagnostic_ess":100.,
            "bootstrap_draws":46656})
        self.assertIn(r["strongest_conventional_arm"],f56.CONTROL)
        d=r["root_equal_candidate_contrasts"]
        positive=(all(r["aggregate_diagnostic_ess"][k]["ess"]>=100
                      for k in ("quantile-supported",*f56.CONTROL)) and
                  d["momentum-rule"]>=.001 and
                  d[r["strongest_conventional_arm"]]>=.001 and
                  r["momentum_positive_root_count"]>=5 and
                  r["root_cluster_exhaustive_intervals"]["momentum-rule"]["lower_025"]>0 and
                  d["rotated-credit"]>0)
        self.assertEqual(r["classification"],"F56_FIT_ONE_STEP_PROXY_SIGNAL_UNVERIFIED" if positive else "F56_FIT_ONE_STEP_NO_GO")
        self.assertEqual(r["report_sha256"],f51.digest({k:v for k,v in r.items() if k!="report_sha256"}))


if __name__=="__main__":
    unittest.main()
