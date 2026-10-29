"""AC-17 negative identifiability and original-locality guard tests.

No fake source output is counted as a real original DTR episode; the samples
below only exercise pure bounded diagnostic logic.
"""
import unittest
try:
    import torch
    import ac17_identifiability_diagnosis as ac
except ModuleNotFoundError as exc:
    if exc.name!="torch":
        raise
    torch=None
    ac=None

@unittest.skipIf(torch is None,"Native AC17 tests require verified isolated CPU PyTorch venv")
class AC17Tests(unittest.TestCase):
    def test_public_context_collisions_are_explicit_negative(self):
        fit=[(0,0,0,0),(0,0,0,1),(0,1,1,1),(0,1,1,1)]
        dev=[(0,0,1,0),(0,0,0,1)]
        x=ac.public_context_evidence(fit,dev)
        self.assertEqual(x["train_unique_public_context_action"],2)
        self.assertEqual(x["train_contexts_with_both_outcomes"],1)
        self.assertEqual(x["in_sample_minority_count_lower_bound_for_deterministic_public_lookup"],1)
        self.assertEqual(x["dev_unseen_context_action_count"],1)
        self.assertGreater(x["conditional_empirical_entropy_bits"],0)

    def test_no_false_hidden_causal_state_claim(self):
        x=ac.public_context_evidence([(0,1,1,0),(0,1,1,1)],[])
        self.assertTrue(x["does_not_prove_unobservable_source_u"])
        self.assertEqual(x["in_sample_public_lookup_minimum_error_rate"],0.5)

    def test_parent_validation_rejects_unverified_source(self):
        with self.assertRaisesRegex(RuntimeError,"PARENT_REAL_SOURCE"):
            ac.fidelity({},{})

    def test_model_feature_bit_is_not_label_field(self):
        a=[(0,1,0,1),(1,0,1,0)]
        b=[(0,1,0,0),(1,0,1,1)]
        self.assertTrue(torch.equal(ac.ac16.spatial_encode(a),
                                    ac.ac16.spatial_encode(b)))

    def test_exact_fold_budget_and_protected_source(self):
        self.assertEqual(ac.N_FOLDS,8)
        self.assertEqual(ac.TOTAL_FOLD_GRADIENT_STEPS,512)
        self.assertEqual(ac.ac16.ACTIVE_YGG_SHA,
                         "92c421a5475a27015a390efb88c373eb5f15379d")
        self.assertEqual(ac.ac10.SOURCE_COMMIT,
                         "c94e9a4cd3641588b6b8507e71ccee5c27032bdf")
        self.assertTrue(set(ac.ac15.FIT).isdisjoint(ac.ac15.DEV))

    def test_fitted_baseline_does_not_use_dev_target(self):
        fit=[(0,0,0,0),(0,0,0,1),(0,0,1,1)]
        p0,_=ac.ac16.tabular_probs(fit,[(0,0,0,0)])
        p1,_=ac.ac16.tabular_probs(fit,[(0,0,0,1)])
        self.assertEqual(p0,p1)

if __name__=="__main__":
    unittest.main()
