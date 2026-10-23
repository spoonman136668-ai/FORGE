"""Source-only Q21N-01 generator checks; no frozen role episodes sampled."""
import hashlib
from pathlib import Path
import unittest
from unittest import mock

import generator as g
import prereg_guard as p


class Q21N01SourceOnlyTests(unittest.TestCase):
    def test_preflight_avoids_episode_birth(self):
        with mock.patch.object(g, "generate",
                               side_effect=AssertionError("UNAUTHORIZED_ROLE_BIRTH")):
            outcome = g.preflight()
        self.assertEqual(outcome["episodes_generated"], 0)
        self.assertEqual(outcome["scientific_admission"], "NOT_GRANTED")
        self.assertEqual(outcome["status"],
                         "Q21N01_NATIVE_GENERATOR_SOURCE_ONLY_PASS")

    def test_all_role_seeds_use_a_disjoint_domain_without_generating(self):
        for role, count in g.ROLE_COUNTS.items():
            for family in g.FAMILIES:
                seeds = [g.seed_for(role, family, n) for n in (0, count//2, count-1)]
                self.assertEqual(len(seeds), len(set(seeds)))
                for n, seed in zip((0, count//2, count-1), seeds):
                    legacy = "forge-q21-v1:" + role + ":" + family + ":" + str(n)
                    q21 = int.from_bytes(hashlib.sha256(legacy.encode()).digest()[:8],
                                         "big")
                    self.assertNotEqual(seed, q21)

    def test_first_use_without_real_fsa_is_refused_before_any_rng(self):
        with mock.patch.object(g.random, "Random",
                               side_effect=AssertionError("NO_DRAW_ALLOWED")):
            with self.assertRaisesRegex(p.ProtocolRefused,
                                        "EXTERNAL_FSA_ADMISSION_NOT_PRESENT"):
                g.generate("FIT_TRAIN", g.FAMILIES[0], 0)
            with self.assertRaisesRegex(p.ProtocolRefused,
                                        "EXTERNAL_FSA_ADMISSION_NOT_PRESENT"):
                g.generate("DEV", g.FAMILIES[1], 0,
                           authenticated_fsa_worker=False)

    def test_protected_roles_or_out_of_range_are_refused_before_rng(self):
        for bad_role in ("Q21_DEV", "HELD", "ORIGINAL", "Q20_FIT", "", "FIT_train"):
            with self.subTest(role=bad_role), self.assertRaisesRegex(
                    p.ProtocolRefused, "UNKNOWN_ROLE"):
                g.seed_for(bad_role, g.FAMILIES[0], 0)
        for n in (-1, 128, 1.0, True):
            with self.subTest(index=n), self.assertRaisesRegex(
                    p.ProtocolRefused, "EPISODE_INDEX_DRIFT"):
                g.seed_for("DEV", g.FAMILIES[0], n)

    def test_exact_original_transition_laws_without_generator_execution(self):
        a = g.family_parameters(g.FAMILIES[0])
        b = g.family_parameters(g.FAMILIES[1])
        self.assertEqual(g.flip_probability(g.FAMILIES[0], 0, 0, 0, a), 1/32)
        self.assertEqual(g.flip_probability(g.FAMILIES[0], 1, 0, 0, a), 3/4)
        self.assertEqual(g.flip_probability(g.FAMILIES[1], 1, 1, 0, b), 1/32)
        self.assertEqual(g.flip_probability(g.FAMILIES[1], 1, 1, 2, b), 31/32)
        self.assertEqual(g.flip_probability(g.FAMILIES[1], 0, 1, 2, b), 1/32)
        with self.assertRaisesRegex(p.ProtocolRefused, "NO_CAUSAL_TRANSITION_IN_NULL"):
            g.flip_probability(g.FAMILIES[2], 1, 1, 2, b)

    def test_public_triples_are_strict_and_never_return_private_metadata(self):
        # Handwritten four-step fixture, NOT a Q21N-01 seeded episode.
        a = g.make_public_row(g.FAMILIES[0],
                              [(0, 0), (0, 1), (1, 0), (1, 1)], [0, 1, 0])
        self.assertEqual(len(a), 3)
        self.assertEqual(len(a[1]), 4)
        self.assertEqual(g.public_rows([a]), [a])
        for bad in (a + ({"responsive_slot": 1},),
                    {"family": g.FAMILIES[0], "private_state": 1}):
            with self.assertRaises(p.ProtocolRefused):
                g.public_rows([bad])

    def test_protected_public_obs_types_do_not_sneak_into_models(self):
        for bad_actions in ([True], [-1], [2], ["0"]):
            with self.subTest(actions=bad_actions), self.assertRaises(p.ProtocolRefused):
                g.make_public_row(g.FAMILIES[0], [(0, 0), (0, 1)],
                                  bad_actions)
        for bad_observation in ([(False, 0), (0, 1)], [(0, 2), (0, 1)]):
            with self.assertRaises(p.ProtocolRefused):
                g.make_public_row(g.FAMILIES[1], bad_observation, [1])

    def test_both_protocols_preserved_and_no_external_controller_imports(self):
        frozen, previous = p.read_protocol()
        p.validate(frozen, previous)
        source = Path(g.__file__).read_text(encoding="utf-8")
        self.assertNotIn("cross_repository_authentication", source)
        self.assertNotIn("github.com/spoonman136668-ai/ckb-plane", source)
        self.assertNotIn("workflow_dispatch", source)
        self.assertNotIn("execute_development(", source)
        self.assertNotIn("original_firstuse", source)


if __name__ == "__main__":
    unittest.main()
