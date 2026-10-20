"""Bilateral source-only analytic coverage; no independently born causal sources."""
from __future__ import annotations
import unittest
import lcrm01e_identifiability as e


class AffinePublicCausalFeasibility(unittest.TestCase):
    def test_model_space_complete(self):
        self.assertEqual(len(e.MODELS), 512)
        self.assertEqual(len(e.QUERIES), 8)

    def test_all_models_binary_and_observable(self):
        for model in e.MODELS:
            obs=e.observations(model)
            self.assertEqual(len(obs), 2)
            self.assertTrue(all(v in (0, 1) for row in obs for v in row))

    def test_distinct_structures_indistinguishable(self):
        self.assertNotEqual(e.WITNESS_DIRECT, e.WITNESS_COMMON)
        self.assertEqual(e.observations(e.WITNESS_DIRECT), e.observations(e.WITNESS_COMMON))

    def test_intervention_discriminates_chain_confounded(self):
        self.assertEqual(e.scm(e.WITNESS_DIRECT, 0, ('X', 1)), (1, 1, 1))
        self.assertEqual(e.scm(e.WITNESS_COMMON, 0, ('X', 1)), (1, 0, 0))

    def test_observation_only_version_set_contains_both(self):
        v=e.versions(e.observations(e.WITNESS_DIRECT))
        self.assertIn(e.WITNESS_DIRECT, v)
        self.assertIn(e.WITNESS_COMMON, v)
        self.assertEqual(len(v), 8)

    def test_no_unidentified_effect_admission(self):
        a=e.predict(e.observations(e.WITNESS_DIRECT), (0, 'X', 1))
        self.assertFalse(a['admitted'])
        self.assertIsNone(a['outcome'])

    def test_public_observed_effect_shrinks_version_space(self):
        obs=e.observations(e.WITNESS_DIRECT)
        row=(0, 'X', 1, e.scm(e.WITNESS_DIRECT, 0, ('X', 1)))
        smaller=e.versions(obs, (row,))
        self.assertIn(e.WITNESS_DIRECT, smaller)
        self.assertNotIn(e.WITNESS_COMMON, smaller)
        self.assertLess(len(smaller), 8)

    def test_identifiable_observational_control_query(self):
        # do(X) to its already observed value cannot create a novel causal
        # contrast, but its observed state is uniquely known.
        o=e.observations(e.WITNESS_DIRECT)
        q=e.predict(o, (0, 'X', o[0][0]))
        self.assertTrue(q['admitted'])
        self.assertEqual(q['outcome'], o[0])
        self.assertFalse(q['scientific_admitted'])

    def test_contradictory_do_receipt_does_not_admit(self):
        o=e.observations(e.WITNESS_DIRECT)
        bad=(0, 'X', 1, (0,0,0))
        self.assertEqual(e.versions(o, (bad,)), ())
        self.assertFalse(e.predict(o, (0, 'X', 1), (bad,))['admitted'])

    def test_does_not_train_or_claim_protected_firstuse(self):
        result=e.evaluate()
        self.assertFalse(result['trained_lcrm_model_qualified'])
        self.assertEqual(result['protected_scientific_first_use'], 0)
        self.assertFalse(result['independent_real_public_do_witness_present'])

    def test_all_observation_classes_nonunique(self):
        d=e.evaluate()
        self.assertEqual(d['observational_signature_count'], 64)
        self.assertEqual(d['observational_classes_with_multiple_scm'], 64)
        self.assertEqual(d['max_observational_equivalence_class'], 8)

    def test_intervention_reduces_but_does_not_remove_ambiguity(self):
        d=e.evaluate()
        self.assertEqual(d['ambiguous_changed_target_pairs'], 2048)
        self.assertEqual(d['remaining_ambiguous_changed_target_pairs_after_one_public_do'], 1536)
        self.assertEqual(d['model_cases_whose_compatible_set_shrinks_with_do_X_1_at_U_0'], 256)

    def test_invalid_public_inputs_fail_closed(self):
        with self.assertRaises(ValueError): e.scm(512,0)
        with self.assertRaises(ValueError): e.scm(1,True)
        with self.assertRaises(ValueError): e.scm(1,0, ('Z',1))
        with self.assertRaises(ValueError): e.predict(e.observations(1), (0, 'Z', 1))

    def test_missing_public_history_rejected(self):
        with self.assertRaises(ValueError): e.versions(())
        with self.assertRaises(ValueError): e.versions(((0,0,2),(1,1,1)))

    def test_invalid_public_do_receipt_rejected(self):
        with self.assertRaises(ValueError): e.versions(e.observations(1), ((0,'X',2,(1,1,1)),))


if __name__ == '__main__':
    unittest.main()
