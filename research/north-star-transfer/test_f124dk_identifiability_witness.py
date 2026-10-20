"""Non-scientific source-only mathematical verification for F124-DK."""
from __future__ import annotations

import unittest

import f124dk_identifiability_witness as w


class SourceFreeSymmetryIdentifiabilityTests(unittest.TestCase):
    def test_full_domain_matches_frozen_five_nibble_contract(self):
        self.assertEqual(w.DOMAIN, 1_048_576)
        self.assertEqual(w.NIBBLES, 5)
        self.assertEqual(w.WIDTH, 4)

    def test_bit_rotation_is_a_nibble_bijection(self):
        self.assertEqual(sorted(w.rotate_nibble(x) for x in range(16)), list(range(16)))
        self.assertEqual(w.rotate_nibble(1), 2)

    def test_rotating_a_vector_performs_simultaneous_bit_action(self):
        values = (1, 2, 3, 4, 5)
        x = sum(v << (4 * k) for k, v in enumerate(values))
        expected = sum(w.rotate_nibble(v) << (4 * k) for k, v in enumerate(values))
        self.assertEqual(w.rotate_input(x), expected)

    def test_zero_law_is_equivariant_on_sampled_domain(self):
        for x in (0, 1, 15, 16, 255, 9123, w.DOMAIN - 1):
            self.assertEqual(w.all_zero_law(w.rotate_input(x)),
                             w.rotate_nibble(w.all_zero_law(x)))

    def test_declared_192_input_witness(self):
        c = w.source_neutral_witness(range(192))
        self.assertEqual(c.witness_input, 192)
        self.assertEqual(c.unique_observed_inputs, 192)
        self.assertTrue(c.non_equivariance_proved)
        self.assertIn(c.modified_lhs, (0, 1))
        self.assertEqual(c.modified_rhs, 2)

    def test_witness_when_unseen_x_is_fixed_under_rotation(self):
        c = w.source_neutral_witness(range(1, 20))
        self.assertEqual(c.witness_input, 0)
        self.assertEqual((c.modified_lhs, c.modified_rhs), (1, 2))

    def test_witness_when_unseen_x_is_not_fixed_under_rotation(self):
        c = w.source_neutral_witness([0])
        self.assertEqual(c.witness_input, 1)
        self.assertEqual((c.modified_lhs, c.modified_rhs), (0, 2))

    def test_duplicates_do_not_fake_coverage(self):
        c = w.source_neutral_witness([0, 0, 1, 1, 2])
        self.assertEqual((c.unique_observed_inputs, c.witness_input), (3, 3))

    def test_unsorted_sparse_rows_still_supply_proof(self):
        c = w.source_neutral_witness([999, 3, 1, 0])
        self.assertEqual(c.witness_input, 2)
        self.assertTrue(c.non_equivariance_proved)

    def test_reject_out_of_domain_and_boolean_values(self):
        for values in ([w.DOMAIN], [-1], [True], ["0"]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                w.source_neutral_witness(values)

    def test_reject_nonzero_observed_label_instead_of_overclaiming(self):
        with self.assertRaisesRegex(ValueError, "ZERO_LABELS"):
            w.validate_labeled_observations([(0, 0), (1, 2)])

    def test_partial_zero_labels_are_validated(self):
        c = w.validate_labeled_observations([(0, 0), (1, 0)])
        self.assertEqual(c.witness_input, 2)

    def test_absence_of_any_rows_still_cannot_certify_symmetry(self):
        c = w.source_neutral_witness([])
        self.assertEqual(c.witness_input, 0)
        self.assertTrue(c.non_equivariance_proved)

    def test_preflight_contract_reports_no_first_use(self):
        receipt = w.declared_preflight()
        self.assertEqual(receipt["maximum_public_FIT_events"], 192)
        self.assertEqual(receipt["unobserved_input_count_at_least"], 1_048_384)
        self.assertFalse(receipt["arbitrary_nonzero_label_coverage_claim"])
        self.assertEqual(receipt["protected_scientific_sources_consumed"], 0)
        self.assertEqual(receipt["F124_DK_reserved_seeds_consumed"], 0)
        self.assertFalse(receipt["external_original_science_acceptance"])


if __name__ == "__main__":
    unittest.main()
