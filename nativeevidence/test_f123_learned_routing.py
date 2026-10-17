"""F123 learned-routing qualification: TRAIN only, no confirmation touch."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f123_multipath_environment as env
import f123_learned_routing as m

VECTORS = [[1, 1, 2], [3, 2, 0]]

class F123LearnedRoutingQualification(unittest.TestCase):
    def sample(self):
        return env.build(96000, VECTORS[0], "Wingless", "TRAIN")

    def test_query_uses_public_graph_only_and_no_oracle(self):
        positive, negative = self.sample()
        routes = m.public_paths(positive)
        self.assertGreaterEqual(len(routes), 2)
        self.assertTrue(all(len(route) == len(positive["roles"]) for route in routes))
        for marker in ("truth", "oracle", "selected_path", "changed_edge", "equality"):
            bad = copy.deepcopy(positive)
            bad[marker] = True
            with self.assertRaises(env.Invalid):
                m.public_paths(bad)
                m.predict_b(bad, [-1.2] + [.17] * 16 + [.05, 3.0, .5])

    def test_recurrent_prediction_is_edge_order_invariant(self):
        positive, negative = self.sample()
        w = [-1.2] + [.17] * 16 + [.05, 3., .5]
        for obs in (positive, negative):
            flipped = copy.deepcopy(obs)
            flipped["edges"].reverse()
            self.assertAlmostEqual(m.predict_b(obs, w)[0],
                                   m.predict_b(flipped, w)[0], places=12)

    def test_query_role_mask_changes_reachable_paths(self):
        positive, _ = self.sample()
        damaged = copy.deepcopy(positive)
        damaged["roles"][1] = "new-role-not-in-graph"
        with self.assertRaisesRegex(env.Invalid, "NO_PUBLIC_QUERY_ROUTES"):
            m.public_paths(damaged)
        with self.assertRaisesRegex(env.Invalid, "NO_PUBLIC_QUERY_ROUTES"):
            m.predict_b(damaged, [-1.2] + [.17] * 16 + [.05, 3., .5])

    def test_b_analytic_gradient_matches_numeric_training_graph(self):
        positive, _ = self.sample()
        weights = [-1.2] + [.17] * 16 + [.05, 3.0, .5]
        _, grad = m.predict_b(positive, weights)
        delta = 1e-5
        for i in (0, 3, 10, 17, 18, 19):
            plus, minus = list(weights), list(weights)
            plus[i] += delta
            minus[i] -= delta
            numeric = (m.predict_b(positive, plus)[0] -
                       m.predict_b(positive, minus)[0]) / (2. * delta)
            # Analytic returns logit gradient, so sigmoid'(logit) scales it.
            probability = m.predict_b(positive, weights)[0]
            analytic = probability * (1. - probability) * grad[i]
            self.assertAlmostEqual(analytic, numeric, places=5)

    def test_a_analytic_gradient_matches_numeric_training_graph(self):
        positive, _ = self.sample()
        frozen = [.04] + [.1] * 16
        w = [-1.2, .4, .4]
        prob, grad = m.predict_a(positive, w, frozen)
        delta = 1e-5
        for i in range(len(w)):
            plus, minus = list(w), list(w)
            plus[i] += delta
            minus[i] -= delta
            numeric = (m.predict_a(positive, plus, frozen)[0] -
                       m.predict_a(positive, minus, frozen)[0]) / (2. * delta)
            self.assertAlmostEqual(prob * (1. - prob) * grad[i], numeric, places=5)

    def test_train_only_dual_lane_and_immutable_model_selection(self):
        original_build = env.build
        seen_phases = []
        def training_only(seed, vector, lane, phase):
            seen_phases.append(phase)
            if phase != "TRAIN":
                raise AssertionError("F123_CONFIRM_READ_FORBIDDEN")
            return original_build(seed, vector, lane, phase)
        with mock.patch.object(env, "build", side_effect=training_only):
            for lane in ("Wingless", "Yggdrasil"):
                result = m.train_lane(lane, VECTORS)
                self.assertEqual(result["phase"], "TRAIN_ONLY")
                self.assertIn(result["train_selected_arm"], ("A", "B"))
                self.assertEqual(set(result["model_arms"]), {"A", "B"})
                self.assertEqual(result["confirmation_inputs_generated"], 0)
                self.assertTrue(all(x["movement"] > 0. for x in result["model_arms"].values()))
                self.assertTrue(all(x["parameters"] <= 768 for x in result["model_arms"].values()))
                self.assertEqual(result["originals_dispatched"], 0)
        self.assertTrue(seen_phases)
        self.assertEqual(set(seen_phases), {"TRAIN"})

if __name__ == "__main__":
    unittest.main()
