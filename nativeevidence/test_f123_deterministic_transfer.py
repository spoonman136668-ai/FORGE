"""F123 adversarial source-only integer and hard-transfer qualification."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f123_deterministic_transfer as m
from test_f120_generated_environment import advisory

SRC = "a" * 40
VECTOR = [1, 1, 2]

class F123Qualification(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = SRC

    def tearDown(self):
        if self.old is None:
            os.environ.pop("GITHUB_SHA", None)
        else:
            os.environ["GITHUB_SHA"] = self.old

    def test_preregistration_frozen_before_implementation(self):
        self.assertEqual(m.f120.blob(m.FREEZE.read_bytes().replace(b"\r\n", b"\n")),
                         m.FREEZE_BLOB)
        self.assertEqual(len(m.frozen()), 64)
        self.assertEqual(m.PARENT, "2e183a5c8d5df68f644a4a06f0ef689b88c9e223")

    def test_graph_pair_counterfactual_source_and_oracle(self):
        for phase in ("TRAIN", "CONFIRM"):
            for lane in ("Wingless", "Yggdrasil"):
                for seed in (list(m.SEEDS[lane][phase])[:2] +
                             list(m.SEEDS[lane][phase])[-2:]):
                    g = m.graph(seed, VECTOR, lane, phase)
                    topo = lambda es: sorted(tuple(e[:3]) for e in es)
                    vals = lambda es: sorted(v for e in es for v in e[3:])
                    self.assertEqual(topo(g["positive"]), topo(g["negative"]))
                    self.assertEqual(vals(g["positive"]), vals(g["negative"]))
                    self.assertTrue(m.f120.binding_solver(g, g["positive"]))
                    self.assertFalse(m.f120.binding_solver(g, g["negative"]))
                    self.assertTrue(m.f120.role_only(g, g["negative"]))
                    self.assertEqual(len(m.raw_junctions(g, g["positive"])),
                                     g["hops"] - 1)

    def test_structural_novelty_and_longer_chains(self):
        a = m.graph(96000, VECTOR, "Wingless", "TRAIN")
        b = m.graph(96100, VECTOR, "Wingless", "CONFIRM")
        self.assertEqual(a["hops"], 2)
        self.assertEqual(b["hops"], 7)
        self.assertTrue(set(a["roles"]).isdisjoint(set(b["roles"])))
        self.assertGreater(len(b["positive"]), len(a["positive"]))
        self.assertTrue(any("cycle-unseen" in e[2] for e in b["positive"]))
        self.assertTrue(any("false-merge" in e[2] for e in b["positive"]))

    def test_raw_pair_inputs_do_not_contain_equality_label(self):
        g = m.graph(96000, VECTOR, "Wingless", "TRAIN")
        d = m.encodings(g)
        pair = m.encode_pair(m.raw_junctions(g, g["positive"])[0], d)
        self.assertEqual(len(pair), 2)
        self.assertEqual(len(pair[0]), 24)
        self.assertEqual(len(pair[1]), 24)
        self.assertTrue(set(pair[0] + pair[1]).issubset({0, 1}))
        self.assertEqual(len(m.features(pair)), 25)

    def test_even_confirmation_near_collision_exactly_one_bit(self):
        for lane in ("Wingless", "Yggdrasil"):
            seed = m.SEEDS[lane]["CONFIRM"].start
            g = m.graph(seed, VECTOR, lane, "CONFIRM")
            d = m.encodings(g)
            self.assertNotEqual(g["hard_symbol"], g["near_to_symbol"])
            self.assertEqual(sum(x != y for x, y in
                                 zip(d[g["hard_symbol"]], d[g["near_to_symbol"]])), 1)
            odd = m.graph(seed + 1, VECTOR, lane, "CONFIRM")
            self.assertFalse(m.make_rows({"vector":VECTOR}, lane, "CONFIRM")[1]["hard"])

    def test_projection_collision_quarantines(self):
        g = m.graph(96000, VECTOR, "Wingless", "TRAIN")
        with mock.patch.object(m, "token", return_value=(0,) * 24):
            with self.assertRaisesRegex(m.Invalid, "TOKEN_COLLISION"):
                m.encodings(g)

    def test_integer_training_and_prediction_reproducibility(self):
        rows = m.make_rows({"vector": VECTOR}, "Wingless", "TRAIN")
        samples = m.train_samples(rows) + m.train_samples(rows)
        w1, n1 = m.train(samples)
        w2, n2 = m.train(samples)
        self.assertEqual((w1, n1), (w2, n2))
        self.assertEqual(m.sha(w1), m.sha(w2))
        self.assertGreater(n1, 0)
        self.assertTrue(all(type(v) is int for v in w1))
        self.assertEqual(len(w1), 25)

    def test_full_both_lane_report_is_byte_identical_on_repeat(self):
        a = m.execute(advisory(), SRC, 123, "pull_request")
        b = m.execute(advisory(), SRC, 123, "pull_request")
        self.assertEqual(m.canonical(a), m.canonical(b))
        self.assertEqual(a["schema"], m.SCHEMA)
        self.assertEqual(a["training_pairs_total"], 96)
        self.assertEqual(a["confirmation_pairs_total"], 192)
        self.assertTrue(a["integer_training_and_inference_only"])
        self.assertFalse(a["external_challenge_witness"])
        self.assertFalse(a["scientific_first_use_authorized"])
        self.assertEqual(a["accepted_ref_mutations"], 0)
        for lane in a["lanes"]:
            self.assertEqual(lane["hard_confirmation_pairs"], 48)
            self.assertEqual(lane["all_confirmation_pairs"], 96)
            self.assertEqual(lane["exact_symbolic_control_paired_correct"], 96)
            self.assertEqual(lane["train_only_model"], "I")
            self.assertFalse(lane["independent_witnessed_scientific_transfer"])
            self.assertFalse(lane["heldout_was_used_for_selection_or_training"])

    def test_source_identity_and_advisory_negative_cases(self):
        with self.assertRaisesRegex(m.Invalid, "CURRENT_SOURCE_IDENTITY_MISMATCH"):
            m.execute(advisory(), "b" * 40, 123, "pull_request")
        bad = copy.deepcopy(advisory())
        bad["lanes"][0]["public_environment_artifacts"][0]["vector"] = [999,0,0]
        with self.assertRaises(m.f120.Invalid):
            m.execute(bad, SRC, 123, "pull_request")

if __name__ == "__main__":
    unittest.main()
