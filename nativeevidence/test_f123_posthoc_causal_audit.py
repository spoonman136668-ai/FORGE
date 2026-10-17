"""F123 post-hoc route attribution is diagnostic only and never touches CONFIRM."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f123_posthoc_causal_audit as m
import f123_multipath_environment as env

W = [-1.2] + [0.17]*16 + [.05, 3., .5]

class CausalAuditBoundary(unittest.TestCase):
    def graphs(self):
        return env.build(96000, [1,1,2], "Wingless", "TRAIN")

    def test_pinned_unchanged_training_sources(self):
        m.sources()
        self.assertEqual(m.PARENT_HEAD, "7882849a59964f412a87589be653114e7bf64d52")
        self.assertEqual(m.TRAIN_REPORT_SHA,
                         "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d")

    def test_reconstructed_attention_equals_recurrent_inference(self):
        positive, negative = self.graphs()
        for obs in (positive, negative):
            value, paths = m.route_witness(obs, W)
            self.assertGreaterEqual(len(paths), 2)
            self.assertAlmostEqual(value,
                                   m.learned.predict_b(obs, W)[0], places=12)
            self.assertEqual(sum(bool(x["symbolic_valid_posthoc"]) for x in paths),
                             m.env.symbolic_routes(obs))
            self.assertTrue(all(len(x["route_sha256"]) == 64 for x in paths))

    def test_posthoc_route_id_and_probability_permutation_invariance(self):
        positive, _ = self.graphs()
        reversed_obs = copy.deepcopy(positive)
        reversed_obs["edges"].reverse()
        p, paths = m.route_witness(positive, W)
        q, reversed_paths = m.route_witness(reversed_obs, W)
        self.assertAlmostEqual(p, q, places=12)
        self.assertEqual(paths[0]["route_sha256"],
                         reversed_paths[0]["route_sha256"])

    def test_edge_ablations_only_change_model_visible_raw_bits(self):
        pos, neg = self.graphs()
        result = m.paired_audit(pos, neg, W)
        self.assertEqual(result["intervention_changed_edges"], 2)
        self.assertGreater(result["cost"]["b_public_edge_scans"], 0)
        self.assertGreater(result["cost"]["b_feature_multiply_adds"], 0)
        self.assertEqual(result["negative_top_route_symbolically_valid"], False)
        self.assertGreaterEqual(result["max_nonprivileged_edge_ablation_delta"], 0)
        self.assertEqual(len(m.edge_ablation(pos, W)) >= 1, True)

    def test_invalid_tampering_quarantined(self):
        pos, neg = self.graphs()
        damaged = copy.deepcopy(pos)
        damaged["oracle_edge_index"] = 1
        with self.assertRaises(env.Invalid):
            m.route_witness(damaged, W)
        with self.assertRaises(env.Invalid):
            m.paired_audit(damaged, neg, W)
        with self.assertRaises(env.Invalid):
            m.route_witness(pos, W[:-1])

    def test_train_only_seed_and_cost_upper_bounds(self):
        for lane, seed in (("Wingless", 96001), ("Yggdrasil", 97001)):
            positive, negative = env.build(seed, [2,2,1], lane, "TRAIN")
            p = m.paired_audit(positive, negative, W)
            self.assertGreater(p["cost"]["fixed_raw_bit_comparisons_upper"], 0)
            self.assertLessEqual(p["cost"]["public_route_count"], 256)
            self.assertEqual(len(m.env.COHORTS[lane]["TRAIN"]), 24)
            self.assertTrue(all(x not in m.env.COHORTS[lane]["TRAIN"]
                                for x in m.env.COHORTS[lane]["CONFIRM"]))

if __name__ == "__main__":
    unittest.main()
