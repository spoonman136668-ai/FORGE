"""Fail-closed AC-06 source-free assertions, not scientific acceptance."""
import json
import unittest
import restricted as m

class AC06RestrictedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.run()
        cls.by={(o["family"],o["seed"]):o["result"] for o in cls.report["observations"]}

    def test_all_seven_restricted_family_probes_and_fixed_seeds(self):
        self.assertEqual(set(m.CASES),{
            "vsa_interference","reservoir_readout","finite_state_rule",
            "local_automata","rank_one_factor","graph_program","unusual_math"})
        self.assertEqual(len(self.report["observations"]),21)
        self.assertEqual(set(k[1] for k in self.by),set(m.SEEDS))
        self.assertEqual(self.report["proposals_original_total"],30)
        self.assertEqual(
            set(self.report["experiment_claim_ids"])|
            set(self.report["unmeasured_original_ids"]),
            set(m.ALL_ORIGINAL))
        self.assertFalse(set(self.report["experiment_claim_ids"])&
                         set(self.report["unmeasured_original_ids"]))

    def test_vsa_ideal_one_entry_and_recall_interference_is_visible(self):
        for seed in m.SEEDS:
            r=self.by["vsa_interference",seed]
            self.assertEqual(r["dimensions"],256)
            self.assertEqual([v["bundle_entries"] for v in r["capacity_rows"]],
                             [1,4,16,32])
            self.assertEqual(r["capacity_rows"][0]["correct"],1)
            for row in r["capacity_rows"]:
                self.assertGreaterEqual(row["correct"],0)
                self.assertLessEqual(row["correct"],row["tested"])
                self.assertTrue(row["candidate_inventory_required"])

    def test_reservoir_readout_is_actually_fitted_not_just_recurrent(self):
        for seed in m.SEEDS:
            r=self.by["reservoir_readout",seed]
            self.assertLess(r["fit_mse_after"],r["fit_mse_before"])
            self.assertEqual(r["heldout_explicit_previous_bit_mse"],0.0)
            self.assertTrue(r["readout_trainable"])

    def test_saturating_state_machine_vs_correct_fitted_control(self):
        for seed in m.SEEDS:
            r=self.by["finite_state_rule",seed]
            self.assertEqual(r["fit_updates"],400)
            self.assertTrue(r["observed_all_16_patterns"])
            self.assertEqual(r["source_visible_holdout_pattern_accuracy"],1.0)
            self.assertEqual(r["fitted_tabular_control_accuracy"],1.0)
            self.assertLess(r["flipped_rule_accuracy"],1.0)

    def test_ca_rule_learned_and_changed_rule_negative(self):
        for seed in m.SEEDS:
            r=self.by["local_automata",seed]
            self.assertEqual(r["learned_local_table_entries"],8)
            self.assertEqual(r["new_length_accuracy"],1.0)
            self.assertLess(r["changed_rule110_accuracy"],1.0)

    def test_lowrank_compression_requires_lowrank_data(self):
        for seed in m.SEEDS:
            r=self.by["rank_one_factor",seed]
            self.assertLess(r["rank1_holdout_mse"],1e-20)
            self.assertGreater(r["fullrank_holdout_mse"],0.1)
            self.assertLess(r["factor_floats"],r["dense_floats"])
            self.assertEqual(r["fitted_observed_entries"],35)

    def test_graph_rule_fitted_but_does_not_transfer_new_depth(self):
        for seed in m.SEEDS:
            r=self.by["graph_program",seed]
            self.assertEqual(r["fitted_program"],"typed-two")
            self.assertEqual(r["renamed_same_structure_correct"],
                             r["renamed_same_structure_total"])
            self.assertFalse(r["unfamiliar_threehop_correct"])
            self.assertTrue(r["unfamiliar_strong_typed_reference_correct"])

    def test_unusual_math_has_real_bounds_and_restricted_parity(self):
        for seed in m.SEEDS:
            r=self.by["unusual_math",seed]
            self.assertTrue(r["ntt_matches_naive_mod17"])
            self.assertTrue(r["spectral_magnitude_loses_order"])
            self.assertEqual(r["distinct_inputs_probed"],257)
            self.assertEqual(r["eight_bit_value_count"],256)
            self.assertTrue(r["finite_state_chaos_cycle_detected"])
            self.assertTrue(r["t_gate_non_stabilizer_relative_phase"])

    def test_no_protected_science_or_architectural_mutation(self):
        r=self.report
        self.assertEqual(r["scope"],"SYNTHETIC_DEVELOPMENT_ONLY")
        self.assertFalse(r["native_learning_or_transfer_superiority"])
        self.assertFalse(r["independent_consequence_source_verified"])
        self.assertFalse(r["scientific_first_use"])
        self.assertFalse(r["accepted_science"])
        self.assertFalse(r["new_controller_or_scheduler"])
        self.assertTrue(r["all_30_original_and_six_new_remain_advisory"])
        self.assertEqual(json.loads(json.dumps(r))["schema"],m.SCHEMA)

if __name__=="__main__":
    unittest.main()
