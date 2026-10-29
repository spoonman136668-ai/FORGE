"""AC-07 source-only assertions: exact 15-ID complement, matched controls, negatives."""
import unittest
import remaining as m

class AC07Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.run()
        cls.results={(r["family"],r["seed"]):r["result"] for r in cls.report["observations"]}
    def test_exact_fifteen_additional_claims_no_false_attribution(self):
        self.assertEqual(len(self.report["observations"]),27)
        self.assertEqual(len(m.CASES),9)
        self.assertEqual(len(m.SEEDS),3)
        self.assertEqual(set(self.report["restricted_new_original_ids"]),m.MISSING)
        self.assertEqual(len(m.MISSING),15)
        self.assertEqual(len(m.PREVIOUSLY_EXERCISED),15)
        self.assertFalse(m.PREVIOUSLY_EXERCISED & m.MISSING)
        self.assertEqual(self.report["combined_ac06_ac07_original_id_coverage"],30)
    def test_lossless_compression_is_conditional_and_procedural_is_not_universal(self):
        for seed in m.SEEDS:
            v=self.results["compression_procedural",seed]
            self.assertTrue(all(c["lossless"] for c in v["cases"].values()))
            self.assertLess(v["cases"]["repetitive"]["compressed_bytes"],
                            v["cases"]["repetitive"]["source_bytes"])
            self.assertGreaterEqual(v["cases"]["random"]["compressed_bytes"],
                                    v["cases"]["random"]["source_bytes"])
            self.assertTrue(v["procedural_structured_reproduced"])
            self.assertFalse(v["procedural_arbitrary_reproduced"])
            self.assertFalse(v["seed_generates_all_arbitrary_weight_arrays"])
    def test_compiled_code_has_material_storage_and_parity(self):
        for seed in m.SEEDS:
            v=self.results["compiled_constants",seed]
            self.assertTrue(v["correct_sum"])
            self.assertGreater(v["large_code_bytes"],0)
            self.assertGreater(v["source_text_bytes"],0)
            self.assertFalse(v["machine_instructions_measured"])
    def test_speculation_requires_verifier_and_preserves_errors(self):
        for seed in m.SEEDS:
            v=self.results["verified_speculation",seed]
            self.assertEqual(v["draft_accepted"]+v["draft_mismatch"],v["heldout_targets"])
            self.assertEqual(v["target_verifications"],v["heldout_targets"])
            self.assertGreater(v["draft_mismatch"],0)
            self.assertEqual(v["unguarded_mismatch_error"],v["draft_mismatch"])
            self.assertFalse(v["claimed_target_work_reduction"])
    def test_exact_cache_trades_storage_for_repeat_work(self):
        for seed in m.SEEDS:
            v=self.results["exact_cache",seed]
            self.assertTrue(v["exact_parity"])
            self.assertGreater(v["cache_hits"],0)
            self.assertEqual(v["cache_hits"]+v["computed_misses"],v["requests"])
            self.assertEqual(v["retained_record_count"],v["computed_misses"])
            self.assertTrue(v["perturbed_input_distinct"])
            self.assertFalse(v["approximate_semantic_hit_authorized"])
    def test_sharded_gradients_have_cost_and_no_network_claim(self):
        for seed in m.SEEDS:
            v=self.results["gradient_shards",seed]
            self.assertTrue(v["aggregation_parity"])
            self.assertGreater(v["minimum_topology_bytes_including_return"],0)
            self.assertFalse(v["real_network_tested"])
            self.assertFalse(v["trained_lora_adapter"])
    def test_ternary_fusion_are_software_semantic_parity_only(self):
        for seed in m.SEEDS:
            v=self.results["ternary_fusion",seed]
            self.assertTrue(v["ternary_dot_parity"])
            self.assertTrue(v["operator_fusion_parity"])
            self.assertFalse(v["native_kernel_measured"])
    def test_disk_streaming_preserves_bytes_but_not_physical_bandwidth(self):
        for seed in m.SEEDS:
            v=self.results["out_of_core",seed]
            self.assertTrue(v["source_bytes_equal"])
            self.assertEqual(v["chunk_count"]*v["stream_chunk_bytes"],v["file_bytes"])
            self.assertFalse(v["os_page_cache_controlled"])
            self.assertFalse(v["measured_physical_disk_bandwidth"])
    def test_sketch_interference_and_bounded_failed_program_search(self):
        for seed in m.SEEDS:
            v=self.results["sketch_bounded_search",seed]
            self.assertGreater(v["sketch_overcount_key_count"],0)
            self.assertEqual(v["sketch_underestimate_key_count"],0)
            self.assertEqual(v["unsolved_target_fit_checks"],v["bounded_search_budget"])
            self.assertTrue(v["unsolved_target_flag"])
            self.assertTrue(v["solved_target_flag"])
    def test_hardware_substitutes_do_not_launder_physical_claims(self):
        for seed in m.SEEDS:
            v=self.results["hardware_substitutes",seed]
            self.assertEqual(v["kind"],"SOFTWARE_SUBSTITUTE_NOT_PHYSICAL_EXPERIMENT")
            self.assertTrue(v["interleave_roundtrip"])
            self.assertTrue(v["digital_matmul_or_dot_reproducible"])
            for key in ("hbm_bandwidth_measured","numa_channel_affinity_configured",
                        "dram_in_situ_analog_arithmetic_executed","physical_claim_tested"):
                self.assertFalse(v[key])
        self.assertEqual(set(self.report["physical_substitute_not_physical_result"]),{"U03","U06"})
    def test_no_scientific_promotion_and_six_new_ideas_remain(self):
        r=self.report
        self.assertEqual(r["scope"],"SYNTHETIC_DEVELOPMENT_ONLY")
        for key in ("relevant_baseline_improvement_proven",
                    "native_model_or_architecture_changed",
                    "independent_itd02_consequence_source_verified",
                    "scientific_first_use","scientific_admission",
                    "accepted_results_updated","controller_or_queue_modified"):
            self.assertFalse(r[key])
        self.assertTrue(r["all_six_new_ac_candidates_retained"])

if __name__=="__main__":
    unittest.main()
