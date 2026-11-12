"""Source-only LCRM-01 feasibility and adversarial information-bound tests."""
import unittest
from itertools import product
import lcrm01_public_feasibility as p


class FeasibilityTests(unittest.TestCase):
    def setUp(self):
        self.obs = p.observed_episode((0, 1, 0, 1, 1, 0, 1, 0), p.MODELS[0])

    def test_complete_observational_equivalence(self):
        self.assertEqual(p.certificate()["all_binary_latent_histories_length_8"], 256)
        self.assertEqual(p.certificate()["public_observational_event_rows"], 2048)

    def test_public_observation_cannot_pick_causal_direction(self):
        self.assertEqual(p.consistent_models(self.obs), p.MODELS)

    def test_symbolic_must_abstain_for_underdetermined_do(self):
        for baseline in (0, 1):
            self.assertFalse(p.symbolic_counterfactual(self.obs, baseline, 1-baseline)["admitted"])

    def test_public_do_breaks_specific_model_ambiguity(self):
        for model in p.MODELS:
            case = (0, 1, p.do_x(0, 1, model))
            self.assertEqual(p.consistent_models(self.obs, (case,)), (model,))

    def test_public_noninformative_do_does_not_break_ambiguity(self):
        case = (0, 0, p.do_x(0, 0, p.MODELS[0]))
        self.assertEqual(p.consistent_models(self.obs, (case,)), p.MODELS)

    def test_two_hop_counterfactual_diverges_after_intervention(self):
        self.assertEqual(p.do_x(0, 1, "direct_chain"), (1, 1, 1))
        self.assertEqual(p.do_x(0, 1, "common_cause"), (1, 0, 0))

    def test_publicly_identified_counterfactual_is_admissible_only_in_witness_space(self):
        case = (0, 1, (1, 1, 1))
        self.assertEqual(p.symbolic_counterfactual(self.obs, 0, 1, (case,)),
                         {"admitted": True, "outcome": (1, 1, 1), "models": 1})

    def test_conflicting_intervention_is_not_success(self):
        case = (0, 1, (1, 0, 1))
        self.assertEqual(p.consistent_models(self.obs, (case,)), ())
        self.assertFalse(p.symbolic_counterfactual(self.obs, 0, 1, (case,))["admitted"])

    def test_no_observation_data_denied(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_HISTORY"):
            p.consistent_models(())

    def test_invalid_intervention_rejected(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_INTERVENTION"):
            p.do_x(0, 2, "direct_chain")

    def test_invalid_model_rejected(self):
        with self.assertRaises(ValueError):
            p.observed_episode((0,) * 8, "secret-law")

    def test_no_unauthorized_first_use_claim(self):
        rec = p.certificate()
        self.assertEqual(rec["new_scientific_firstuse"], 0)
        self.assertFalse(rec["learned_relational_transfer_accepted"])
        self.assertFalse(rec["protected_case_access"])


if __name__ == "__main__":
    unittest.main()
