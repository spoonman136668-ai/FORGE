"""F123 bounded TRAIN-only control and evidence-custody qualification."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f123_controls as m
import f123_multipath_environment as env
from test_f120_generated_environment import advisory

SRC = "a" * 40
VECTORS = [[1, 1, 2], [2, 2, 1]]

class FrozenControlsQualification(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = SRC

    def tearDown(self):
        if self.saved is None:
            os.environ.pop("GITHUB_SHA", None)
        else:
            os.environ["GITHUB_SHA"] = self.saved

    def test_all_frozen_control_types_distinct_and_reportable(self):
        self.assertEqual(set(m.ARMS), {
            "CTRL_F122_NO_ROUTING", "CTRL_FIXED_SOFT_PATH",
            "CTRL_ROLE_ONLY", "CTRL_QUERY_ONLY", "CTRL_EXACT_SYMBOLIC"})
        p, n = env.build(96000, VECTORS[0], "Wingless", "TRAIN")
        rows = [(p, 1), (n, 0)]
        foundation = [.2] + [.5] * 16
        query = [0.] * 20
        outcomes = {}
        for name in m.ARMS:
            result = m.paired_score(rows, lambda o, arm=name:
                                    m.predict_control(o, arm, foundation, query))
            self.assertEqual(result["pairs"], 1)
            outcomes[name] = result
        self.assertEqual(outcomes["CTRL_EXACT_SYMBOLIC"]["paired_correct"], 1)
        self.assertEqual(outcomes["CTRL_ROLE_ONLY"]["paired_correct"], 0)
        self.assertEqual(outcomes["CTRL_FIXED_SOFT_PATH"]["paired_correct"], 1)

    def test_query_only_stats_cannot_read_token_values(self):
        positive, negative = env.build(96001, VECTORS[0], "Wingless", "TRAIN")
        self.assertEqual(m.topology_features(positive),
                         m.topology_features(negative))
        reversed_positive = copy.deepcopy(positive)
        reversed_positive["edges"].reverse()
        self.assertEqual(m.topology_features(positive),
                         m.topology_features(reversed_positive))
        changed = copy.deepcopy(positive)
        changed["edges"][0]["dst_bits"] = [1 - x for x in changed["edges"][0]["dst_bits"]]
        self.assertEqual(m.topology_features(positive), m.topology_features(changed))

    def test_shuffle_intervention_is_graph_only_and_deterministic(self):
        positive, negative = env.build(96002, VECTORS[0], "Wingless", "TRAIN")
        x = m.shuffled_token_control(positive)
        self.assertNotEqual(x, positive)
        self.assertEqual(x, m.shuffled_token_control(positive))
        self.assertEqual(set(x), env.FIELDS)
        self.assertEqual(m.topology_features(x), m.topology_features(positive))
        self.assertEqual(set(x["edges"][0]), env.EDGE_FIELDS)
        # Must not rely on changed-edge coordinate or gold label.
        self.assertNotEqual(m.shuffled_token_control(positive),
                            m.shuffled_token_control(negative))

    def test_paired_score_does_not_overstate_balanced_accuracy(self):
        positive, negative = env.build(96000, VECTORS[0], "Wingless", "TRAIN")
        r = m.paired_score([(positive, 1), (negative, 0)], lambda _: True)
        self.assertEqual(r["paired_correct"], 0)
        self.assertEqual(r["balanced_accuracy"], 0.5)
        self.assertEqual(r["positive_correct"], 1)
        self.assertEqual(r["negative_correct"], 0)
        with self.assertRaisesRegex(env.Invalid, "LABEL_PAIR_DRIFT"):
            m.paired_score([(positive, 0), (negative, 1)], lambda _: False)

    def test_train_only_two_lane_custody_and_authentic_vector_binding(self):
        actual_build = env.build
        phases = []
        def guarded(seed, vector, lane, phase):
            phases.append(phase)
            if phase != "TRAIN":
                raise AssertionError("F123_CONFIRM_WAS_READ")
            return actual_build(seed, vector, lane, phase)
        with mock.patch.object(env, "build", side_effect=guarded):
            report = m.train_evidence(advisory(), SRC, 1234, "push")
        self.assertEqual(set(phases), {"TRAIN"})
        self.assertEqual(report["source_sha"], SRC)
        self.assertEqual(report["schema"], m.SCHEMA)
        self.assertEqual(report["cohorts"], "TRAIN_ONLY")
        self.assertEqual(report["freeze_git_blob"], env.FREEZE_BLOB)
        self.assertEqual(report["confirmation_inputs_generated"], 0)
        self.assertEqual(len(report["lanes"]), 2)
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(report["originals_dispatched"], 0)
        self.assertEqual(report["optimizer_promotions"], 0)
        for lane in report["lanes"]:
            self.assertEqual(len(lane["advisory_candidate_source_shas"]), 2)
            self.assertEqual(set(lane["train_control_scores"]), set(m.ARMS))
            self.assertEqual(lane["train_control_scores"]["CTRL_EXACT_SYMBOLIC"]["paired_correct"], 48)
            self.assertEqual(lane["train_control_scores"]["CTRL_ROLE_ONLY"]["paired_correct"], 0)
            self.assertEqual(lane["selected_model_weights_sha256"],
                             m.learned.digest(lane["train_frozen_weights"][
                                 lane["train_source_only_selection"]]))
            self.assertEqual(lane["confirmation_inputs_generated"], 0)

    def test_source_and_advisory_tamper_fail_closed(self):
        with self.assertRaisesRegex(env.Invalid, "SOURCE_IDENTITY_UNQUALIFIED"):
            m.train_evidence(advisory(), "b" * 40, 4, "push")
        bad = advisory()
        bad["lanes"][0]["public_environment_artifacts"][0]["vector"] = [9, 0, 0]
        with self.assertRaises(m.f120.Invalid):
            m.train_evidence(bad, SRC, 4, "push")

if __name__ == "__main__":
    unittest.main()
