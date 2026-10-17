"""F123 graph-source qualification; no model selection or held-out scoring."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f123_multipath_environment as m

class F123EnvironmentQualification(unittest.TestCase):
    def test_contract_identity(self):
        self.assertEqual(len(m.frozen()), 64)
        self.assertEqual(m.FREEZE_BLOB, "9663e453051642bd798f9647df9993c3470c8672")

    def test_frozen_seed_and_input_boundaries(self):
        for seed in (94000, 96024, 96148, 97000, 97100):
            with self.subTest(seed=seed):
                with self.assertRaises(m.Invalid):
                    m.build(seed, [1, 2, 0], "Wingless", "TRAIN")
        with self.assertRaises(m.Invalid):
            m.build(96000, [4, 1, 2], "Wingless", "TRAIN")

    def test_competing_routes_are_not_privileged_features(self):
        for lane, train_seed, confirm_seed in (("Wingless", 96000, 96100),
                                                ("Yggdrasil", 97000, 97100)):
            for seed, phase in ((train_seed, "TRAIN"), (train_seed + 1, "TRAIN"),
                                (confirm_seed, "CONFIRM"), (confirm_seed + 1, "CONFIRM")):
                with self.subTest(lane=lane, seed=seed):
                    pos, neg = m.build(seed, [1, 2, 0], lane, phase)
                    self.assertEqual(len(pos["roles"]), 2 + seed % 2 if phase == "TRAIN"
                                     else 5 + seed % 2)
                    self.assertEqual(m.symbolic_routes(pos), 1)
                    self.assertEqual(m.symbolic_routes(neg), 0)
                    self.assertGreaterEqual(m.symbolic_routes(pos, role_only=True),
                                            2 if phase == "TRAIN" else 3)
                    self.assertEqual(set(pos), m.FIELDS)
                    self.assertEqual(set(pos["edges"][0]), m.EDGE_FIELDS)
                    self.assertTrue(m.admit(pos, neg))

    def test_edge_order_reversal_does_not_change_truth(self):
        pos, neg = m.build(96101, [0, 3, 1], "Wingless", "CONFIRM")
        for graph, expected in ((pos, 1), (neg, 0)):
            swapped = copy.deepcopy(graph)
            swapped["edges"].reverse()
            self.assertEqual(m.symbolic_routes(swapped), expected)

    def test_replay_and_lane_phase_separation(self):
        first = m.build(96002, [2, 1, 3], "Wingless", "TRAIN")
        self.assertEqual(first, m.build(96002, [2, 1, 3], "Wingless", "TRAIN"))
        held = m.build(96102, [2, 1, 3], "Wingless", "CONFIRM")
        self.assertTrue(set(first[0]["roles"]).isdisjoint(held[0]["roles"]))
        self.assertNotEqual(first[0]["start"], held[0]["start"])

    def test_privileged_markers_and_nonraw_tokens_quarantined(self):
        pos, neg = m.build(96002, [0, 0, 0], "Wingless", "TRAIN")
        for marker in ("oracle_path", "seed", "label", "correct_junction", "equality"):
            bad = copy.deepcopy(pos)
            bad[marker] = 1
            with self.subTest(marker=marker), self.assertRaises(m.Invalid):
                m.validate_observation(bad)
        bad = copy.deepcopy(pos)
        bad["edges"][0]["equality"] = True
        with self.assertRaises(m.Invalid):
            m.validate_observation(bad)
        bad = copy.deepcopy(pos)
        bad["edges"][0]["src_bits"] = [1] * 15 + [True]
        with self.assertRaises(m.Invalid):
            m.validate_observation(bad)
        with self.assertRaises(m.Invalid):
            m.admit(pos, pos)
        with self.assertRaises(m.Invalid):
            m.admit(neg, pos)

    def test_full_frozen_split_admission_without_confirmation_training(self):
        for lane in m.COHORTS:
            for phase in ("TRAIN", "CONFIRM"):
                for seed in m.COHORTS[lane][phase]:
                    for vector in ([1, 1, 2], [3, 2, 0]):
                        with self.subTest(lane=lane, phase=phase, seed=seed, vector=vector):
                            pos, neg = m.build(seed, vector, lane, phase)
                            self.assertEqual(m.symbolic_routes(pos), 1)
                            self.assertEqual(m.symbolic_routes(neg), 0)

if __name__ == "__main__":
    unittest.main()
