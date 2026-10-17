"""F122 prospective adversarial qualification, source-only research development."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f122_raw_transfer as m
from test_f120_generated_environment import advisory

SRC = "a" * 40
VEC = [1, 1, 2]

class RawTransferQualification(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = SRC

    def tearDown(self):
        if self.old is None:
            os.environ.pop("GITHUB_SHA", None)
        else:
            os.environ["GITHUB_SHA"] = self.old

    def test_preimplementation_freeze_identity_and_denied_authority(self):
        self.assertEqual(m.f120.blob(m.FREEZE.read_bytes().replace(b"\r\n", b"\n")),
                         m.FREEZE_BLOB)
        self.assertEqual(m.PARENT_F121, "57e54e98e223406e19dc8be5d73d309413250a85")
        self.assertEqual(len(m.frozen()), 64)

    def test_matched_pairs_preserve_global_marginals_but_not_binding(self):
        for phase, seeds in (("TRAIN", [94000, 94023, 95000]),
                             ("CONFIRM", [94100, 94147, 95147])):
            for lane in ("Wingless", "Yggdrasil"):
                for seed in seeds:
                    if seed not in m.SEEDS[lane][phase]:
                        continue
                    c = m.graph(seed, VEC, lane, phase)
                    topo = lambda es: sorted(e[:3] for e in es)
                    slots = lambda es: sorted(v for e in es for v in e[3:])
                    self.assertEqual(topo(c["positive"]), topo(c["negative"]))
                    self.assertEqual(slots(c["positive"]), slots(c["negative"]))
                    self.assertTrue(m.f120.binding_solver(c, c["positive"]))
                    self.assertFalse(m.f120.binding_solver(c, c["negative"]))
                    self.assertTrue(m.f120.role_only(c, c["negative"]))

    def test_unseen_role_family_and_longer_relation_chain(self):
        tr = m.graph(94000, VEC, "Wingless", "TRAIN")
        cf = m.graph(94100, VEC, "Wingless", "CONFIRM")
        self.assertEqual(tr["hops"], 2)
        self.assertEqual(cf["hops"], 5)
        self.assertTrue(set(tr["roles"]).isdisjoint(cf["roles"]))
        self.assertFalse(set(tr["positive"]) & set(cf["positive"]))
        self.assertGreater(len(cf["positive"]), len(tr["positive"]))

    def test_raw_features_are_paired_symbols_not_precomputed_equality(self):
        c = m.graph(94000, VEC, "Wingless", "TRAIN")
        lookup = m.encodings(c)
        raw_pos = m.raw_junctions(c, c["positive"])
        raw_neg = m.raw_junctions(c, c["negative"])
        p = m.encode_pair(*raw_pos[0], lookup)
        n = m.encode_pair(*raw_neg[0], lookup)
        self.assertEqual(len(p), 2)
        self.assertEqual(len(p[0]), 16)
        self.assertTrue(set(p[0]).issubset({0, 1}))
        self.assertTrue(set(p[1]).issubset({0, 1}))
        self.assertNotIsInstance(p, int)
        self.assertNotIsInstance(p, bool)
        self.assertNotEqual(p, n)
        self.assertEqual(len(m.model_a(m.initialize("A"), p)[1]), 17)

    def test_edge_order_and_offpath_order_do_not_leak_answer(self):
        case = m.graph(94101, VEC, "Wingless", "CONFIRM")
        order_a = m.raw_junctions(case, case["positive"])
        order_b = m.raw_junctions(case, list(reversed(case["positive"])))
        self.assertEqual(order_a, order_b)
        negative = m.raw_junctions(case, case["negative"])
        reversed_negative = m.raw_junctions(case, list(reversed(case["negative"])))
        self.assertEqual(negative, reversed_negative)
        self.assertNotEqual(order_a, negative)

    def test_collision_fail_closed(self):
        c = m.graph(94000, VEC, "Wingless", "TRAIN")
        with mock.patch.object(m, "token_bits", return_value=(0,) * 16):
            with self.assertRaisesRegex(m.Invalid, "PROJECTION_COLLISION"):
                m.encodings(c)

    def test_separate_training_and_confirmation_frozen_seeds(self):
        for lane in ("Wingless", "Yggdrasil"):
            self.assertTrue(set(m.SEEDS[lane]["TRAIN"]).isdisjoint(
                set(m.SEEDS[lane]["CONFIRM"])))
            self.assertEqual(len(m.SEEDS[lane]["TRAIN"]), 24)
            self.assertEqual(len(m.SEEDS[lane]["CONFIRM"]), 48)

    def test_two_learned_arms_have_real_updates_and_are_bounded(self):
        rows = m.build_rows({"vector": VEC}, "Wingless", "TRAIN")
        samples = m.train_samples(rows) + m.train_samples(rows)
        for arm in ("A", "B"):
            w, count = m.train(samples, arm)
            self.assertLessEqual(count, 409)
            self.assertNotEqual(w, m.initialize(arm))
        self.assertEqual(len(samples), 96)

    def test_full_source_only_two_lane_cohort_and_controls(self):
        report = m.execute(advisory(), SRC, 122, "pull_request")
        self.assertEqual(report["schema"], m.SCHEMA)
        self.assertEqual(report["training_pairs_total"], 96)
        self.assertEqual(report["confirmation_pairs_total"], 192)
        self.assertEqual(report["model_arms"], 2)
        self.assertTrue(report["actual_learned_parameter_updates"])
        self.assertFalse(report["scientific_first_use_authorized"])
        self.assertEqual(report["accepted_ref_mutations"], 0)
        self.assertEqual(report["optimizer_promotions"], 0)
        for lane in report["lanes"]:
            self.assertEqual(set(lane["confirmation_scores"]), {"A", "B"})
            self.assertEqual(lane["frozen_controls"]["CTRL_EXACT_SYMBOLIC"][0]["paired_correct"], 48)
            self.assertEqual(len(lane["candidate_source_sha256"]), 2)
            self.assertTrue(lane["train_and_confirm_source_isolated"])
            self.assertFalse(lane["engineered_equality_bit_given_to_model"])
            self.assertFalse(lane["confirmation_used_for_training_or_selection"])
            self.assertFalse(lane["independent_scientific_transfer_established"])

    def test_source_mismatch_quarantines(self):
        with self.assertRaisesRegex(m.Invalid, "SOURCE_NOT_PINNED"):
            m.execute(advisory(), "b" * 40, 1, "pull_request")

    def test_advisory_mismatch_quarantines(self):
        bad = copy.deepcopy(advisory())
        bad["lanes"][0]["public_environment_artifacts"][0]["vector"] = [999, 0, 0]
        with self.assertRaises(m.f120.Invalid):
            m.execute(bad, SRC, 122, "pull_request")

if __name__ == "__main__":
    unittest.main()
