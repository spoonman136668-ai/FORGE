"""Exact source-free Q21N-01 information identity checks. No role seeds."""
import math
from unittest import TestCase, mock

import generator
import population_witness as w


class ExactPublicInformation(TestCase):
    def test_two_real_families_match_independent_true_law_calculation(self):
        known = {
            generator.FAMILIES[0]: (
                0.6421760370743884,
                0.6075551028331725,
                0.03462093424121593,
                0.030293317461063937,
            ),
            generator.FAMILIES[1]: (
                0.6391875086627814,
                0.5798182437178361,
                0.05936926494494532,
                0.051948106826827156,
            ),
        }
        for family, expected in known.items():
            with self.subTest(family=family):
                r = w.exact_window(family)
                actual = (
                    r["current_public_entropy_nats_per_bit"],
                    r["four_observation_history_entropy_nats_per_bit"],
                    r["stationary_public_history_gain_nats_per_bit"],
                    r["whole_episode_32_step_information_gain_lower_bound"],
                )
                for got, want in zip(actual, expected):
                    self.assertAlmostEqual(got, want, delta=1e-11)
                self.assertAlmostEqual(r["mass"], 1, delta=1e-12)
                self.assertFalse(r["hidden_state_or_slot_exposed"])
                self.assertEqual(r["role_episodes_generated"], 0)

    def test_iid_null_history_information_is_identically_zero(self):
        # Null bits are iid Bernoulli(1/2), independent of public actions,
        # slot and past observations. Entropy per bit is log(2) under either
        # conditioning; exact Bayes information gain is identically zero.
        h = w.bernoulli_entropy(0.5)
        self.assertAlmostEqual(h, math.log(2), delta=1e-15)
        self.assertAlmostEqual(h - h, 0.0, delta=1e-15)
        with self.assertRaisesRegex(Exception, "TRUE_LAW_FAMILY_REQUIRED"):
            w.exact_window(generator.FAMILIES[2])

    def test_never_generate_a_seeded_episode_or_fit_model(self):
        with mock.patch.object(generator, "generate",
                               side_effect=AssertionError("ROLE_BIRTH")), \
             mock.patch.object(generator, "seed_for",
                               side_effect=AssertionError("FROZEN_SEED_USED")):
            result = w.witness()
        self.assertEqual(result["role_episodes_generated"], 0)
        self.assertEqual(result["models_trained"], 0)
        self.assertEqual(result["native_fsa_admission"], "NOT_REQUESTED")
        self.assertFalse(result["claimed_empirical_significance"])
        self.assertEqual(result["iid_null_exact_history_advantage_nats_per_bit"],
                         0.0)
        self.assertEqual(result["qualification"],
                         "THEORETICAL_INFORMATION_AVAILABLE_NOT_LEARNABILITY")
        self.assertGreater(
            min(x["whole_episode_32_step_information_gain_lower_bound"]
                for x in result["bounds"]),
            result["threshold_nats_per_bit"]
        )

    def test_genuine_history_is_better_without_private_state(self):
        for family in generator.FAMILIES[:2]:
            row = w.exact_window(family)
            self.assertGreater(
                row["current_public_entropy_nats_per_bit"],
                row["four_observation_history_entropy_nats_per_bit"]
            )
            self.assertFalse(row["hidden_state_or_slot_exposed"])
            self.assertTrue(0 < row[
                "whole_episode_32_step_information_gain_lower_bound"] < 0.6932)


if __name__ == "__main__":
    import unittest
    unittest.main()
