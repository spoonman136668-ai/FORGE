"""Frozen C1 read-identity negative enforcement, no scientific execution."""
import unittest
from c1_independent_fidelity import BASELINE, sensor_identity_delta


class C1FidelityQualification(unittest.TestCase):
    def test_native_observation_schedule_is_permutation(self):
        schedule = [list(p) for p in BASELINE]
        self.assertTrue(sensor_identity_delta(schedule)["preserves_existing_address_multiset"])
        self.assertEqual(sensor_identity_delta(schedule)["new_physical_addresses"], [])

    def test_true_reordering_preserves_physical_read_multiset(self):
        schedule = [[4, 2], [1, 0], [0, 1], [1, 0], [4, 2]]
        self.assertTrue(sensor_identity_delta(schedule)["preserves_existing_address_multiset"])

    def test_positive_development_candidate_is_not_a_permutation(self):
        schedule = [[0, 1], [0, 1], [0, 1], [8, 11], [0, 1]]
        observation = sensor_identity_delta(schedule)
        self.assertFalse(observation["preserves_existing_address_multiset"])
        self.assertEqual(observation["new_physical_addresses"], [8, 11])

    def test_repeated_anchor_reads_are_not_a_permutation(self):
        schedule = [[0, 1] for _ in range(5)]
        observed = sensor_identity_delta(schedule)
        self.assertFalse(observed["preserves_existing_address_multiset"])
        self.assertEqual(observed["new_physical_addresses"], [])

    def test_invalid_addresses_and_quota_rejected(self):
        for invalid in (
            [[0, 1]],
            [[0, 1]] * 4 + [[3, 3]],
            [[0, 1]] * 4 + [[0, 16]],
            [[0, 1]] * 4 + [[0, True]],
            [[0, 1]] * 4 + [0, 1],
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    sensor_identity_delta(invalid)


if __name__ == "__main__":
    unittest.main()
