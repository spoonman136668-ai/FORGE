"""F54 genuine-Farama training-only audit controls; NEVER consumes scored seeds."""
import ast
import inspect
import math
import unittest

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f53_original_acrobot_supported_residual_dev as f53
import f54_original_acrobot_fit_quantile_action_audit as f54


class FrozenF54OriginalFitOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit, cls.records, cls.gaps, cls.threshold = f54.prepare()
        cls.result = f54.report()

    def test_authentic_source_and_original_trained_fit_custody(self):
        b = self.fit
        self.assertEqual(b["source"]["upstream_commit"], f51.ORIGINAL_COMMIT)
        self.assertEqual(b["source"]["acrobot_git_blob"], f51.ORIGINAL_FILE_BLOB)
        self.assertEqual(f51.digest(self.records), f54.FIT_SHA)
        self.assertEqual(b["fitted_sha256"], f54.MODEL_SHA)
        self.assertEqual(b["fit_action_counts"], [3604, 1824, 3546])
        self.assertEqual(len(self.records), 8974)

    def test_frozen_quantile_uses_public_fit_only(self):
        self.assertEqual(len(self.gaps), 2716)
        self.assertTrue(all(0 < x < f53.MARGIN for x in self.gaps))
        self.assertEqual(self.threshold, float(np.quantile(self.gaps, .75)))
        self.assertGreater(self.threshold, 0)
        self.assertLess(self.threshold, f53.MARGIN)
        self.assertEqual(f54.QUANTILE, .75)

    def test_supported_action_never_exceeds_margin_only(self):
        r = self.result["audit"]
        supported = r["arms"]["quantile-supported"]["deviations"]
        margin = r["arms"]["quantile-margin-only"]["deviations"]
        self.assertLessEqual(supported, margin)
        self.assertEqual(supported, r["support"]["both_supported"])
        self.assertEqual(margin, r["support"]["margin_eligible"])
        self.assertGreater(margin, 0)

    def test_f53_frozen_negative_stays_frozen(self):
        r = self.result["audit"]["arms"]
        self.assertEqual(r["f53-fixed-margin"]["deviations"], 0)
        self.assertEqual(r["momentum-rule"]["deviations"], 0)
        self.assertEqual(r["frozen-fqi"]["deviations"], 2716)
        for row in self.records[:32]:
            p = f53.SupportedPolicy("supported-residual", self.fit["theta"],
                                    self.fit["inverses"], self.fit["thresholds"])
            q = f54.Policy("f53-fixed-margin", self.fit["theta"],
                           self.fit["inverses"], self.fit["thresholds"],
                           self.threshold)
            self.assertEqual(q.action(row[0]), p.action(row[0]))

    def test_all_six_arms_are_finite_and_action_counted(self):
        self.assertEqual(len(f54.ARMS), 6)
        audit = self.result["audit"]
        for kind in f54.ARMS:
            row = audit["arms"][kind]
            self.assertEqual(sum(row["actions"]), 8974)
            self.assertGreaterEqual(row["behavior_matches"], 0)
            self.assertLessEqual(row["behavior_matches"], 8974)
            self.assertGreaterEqual(row["deviations"], 0)
            self.assertLessEqual(row["deviations"], 8974)
        for key, value in audit["support"].items():
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)

    def test_negative_credit_and_invalid_inputs_fail_closed(self):
        b = self.fit
        bad = np.zeros((3, 15))
        for kind in ("rotated-credit", "quantile-supported", "quantile-margin-only"):
            p = f54.Policy(kind, bad, b["inverses"], b["thresholds"], self.threshold)
            for obs in ([1., 0., 1., 0., 0., -.1], [1., 0., 1., 0., 0., .1]):
                self.assertEqual(p.action(obs), f51.energy_rule(obs))
        with self.assertRaises(ValueError):
            f54.Policy("invented", b["theta"], b["inverses"], b["thresholds"], self.threshold)
        with self.assertRaises(ValueError):
            f54.Policy("quantile-supported", b["theta"], b["inverses"],
                       b["thresholds"], float("nan"))
        with self.assertRaises(ValueError):
            f54.Policy("quantile-supported", b["theta"], b["inverses"],
                       b["thresholds"], self.threshold).action([float("nan")] * 6)

    def test_scored_execution_is_unreachable_from_f54_source(self):
        tree = ast.parse(inspect.getsource(f54))
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                    calls.add(fn.value.id + "." + fn.attr)
        forbidden = {"f51.evaluate", "f53.evaluate", "f53.score",
                     "f51.new_real_env", "f53.new_real_env", "gym.make"}
        self.assertFalse(calls & forbidden)
        self.assertEqual(calls & {"f51.collect_fit", "f53.frozen_fit"},
                         {"f51.collect_fit", "f53.frozen_fit"})
        f53.validate_cohorts()
        self.assertFalse(self.result["scored_seeds_accessed"])
        self.assertEqual(self.result["new_transfer_or_retention_evaluations"], 0)
        self.assertFalse(self.result["scientific_first_use"])

    def test_report_replay_digest_and_no_science_claims(self):
        r = self.result
        self.assertTrue(r["cold_audit_matches"])
        self.assertFalse(r["science_accepted"])
        self.assertEqual(r["classification"], (
            "F54_FIT_ACTIVATION_UNVERIFIED" if
            r["audit"]["arms"]["quantile-supported"]["deviations"] > 0
            else "F54_FIT_NO_ACTIVATION"))
        self.assertEqual(f51.digest({k: v for k, v in r.items()
                                     if k != "report_sha256"}), r["report_sha256"])
        for metric in ("margin_calibrated_q_units", "margin_q_gap_min",
                       "margin_q_gap_p50", "margin_q_gap_p75",
                       "margin_q_gap_p90", "margin_q_gap_max"):
            self.assertTrue(math.isfinite(r[metric]))


if __name__ == "__main__":
    unittest.main()
