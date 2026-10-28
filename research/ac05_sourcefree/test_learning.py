"""AC-05 independent source-visible assertions; no real scientific first-use."""
import json
import unittest

import learning as m

class TestAC05(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.run()
    def test_six_real_development_mechanism_probes_exist(self):
        self.assertEqual(set(self.report["results"]),{"AC-D"+str(i) for i in range(1,7)})
        self.assertEqual(self.report["source_free_mechanism_count"],6)
    def test_delta_learned_dependency_with_counterexample(self):
        r=self.report["results"]["AC-D1"]
        self.assertEqual(r["learned_dependency_count"],3)
        self.assertEqual(r["observed_incremental_errors"],0)
        self.assertLess(r["incremental_outcome_computations"],r["full_outcome_computations"])
        self.assertGreater(r["fit_outcome_queries"],r["evaluation_events"])
        self.assertTrue(r["undercovered_fit_unseen_interaction_failure"])
    def test_decision_assumption_violation(self):
        r=self.report["results"]["AC-D2"]
        self.assertTrue(r["fit_action_parity"])
        self.assertEqual(r["certified_action"],r["full_fitted_action"])
        self.assertTrue(r["observed_stationarity_shift_failure"])
    def test_memory_fusion_reversible_but_misses_unobserved_future(self):
        r=self.report["results"]["AC-D3"]
        self.assertEqual(r["fit_group_count"],1)
        self.assertLess(r["fit_group_serialized_bytes"],r["fit_full_serialized_bytes"])
        self.assertGreater(r["unobserved_future_error_count"],0)
        self.assertEqual(r["post_counterexample_groups"],2)
        self.assertTrue(r["cold_restart_history_roundtrip"])
    def test_program_search_does_not_beat_fitted_control(self):
        r=self.report["results"]["AC-D4"]
        self.assertGreater(r["candidate_count_evaluated"],2)
        self.assertEqual(r["fitted_rule"],r["fitted_linear_control"])
        self.assertFalse(r["advantage_over_fitted_control"])
    def test_local_credit_preserves_strong_ema_parity_and_shift_negative(self):
        r=self.report["results"]["AC-D5"]
        self.assertTrue(r["matched_fitted_ema_parity"])
        self.assertLess(r["shifted_family_action_reward_exact"],r["fit_action_reward_exact"])
        self.assertTrue(r["confounded_noncausal_credit_risk"])
    def test_renamed_structure_does_not_count_as_unfamiliar_transfer(self):
        r=self.report["results"]["AC-D6"]
        self.assertTrue(r["renamed_familiar_classified_as_known"])
        self.assertTrue(r["unfamiliar_graph_abstained"])
        self.assertTrue(r["typed_graph_control_two_step_success"])
        self.assertFalse(r["verified_unfamiliar_transfer"])
    def test_strict_negative_evidence_and_no_acceptance(self):
        report=self.report
        self.assertEqual(report["scope"],"SYNTHETIC_DEVELOPMENT_ONLY")
        self.assertFalse(report["scientific_first_use"])
        self.assertFalse(report["independent_consequence_source_verified"])
        self.assertFalse(report["native_model_changed"])
        self.assertFalse(report["accepted_science"])
        self.assertFalse(report["new_controller_or_scheduler"])
        self.assertTrue(report["all_36_ideas_retained_in_portfolio"])
        self.assertIsInstance(report["measurement"]["total_wall_ns"],int)
        self.assertTrue(json.loads(json.dumps(report))["results"]["AC-D6"]["unfamiliar_graph_abstained"])
if __name__=="__main__":
    unittest.main()
