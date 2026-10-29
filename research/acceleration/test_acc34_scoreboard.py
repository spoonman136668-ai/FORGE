"""ACC34 36 method full source-screening and native/acceleration boundary tests."""
import unittest
import acc34_scoreboard as t

class ACC34Portfolio(unittest.TestCase):
    def test_all_30_original_and_six_extra_still_registered(self):
        p=t.scoreboard()
        self.assertEqual(p["total_registered_candidates"],36)
        self.assertEqual(p["original_user_proposals"],30)
        self.assertEqual(p["additional_mechanism_hypotheses"],6)
        self.assertEqual({r["claim_id"] for r in p["rows"]},t.EXPECTED)
        self.assertEqual(len(p["rows"]),len({r["title"] for r in p["rows"]}))

    def test_no_unearned_model_science_or_substituted_physical_claim(self):
        p=t.scoreboard()
        self.assertEqual(p["stage2_qualified_native_model_speedups"],0)
        self.assertTrue(p["all_candidates_remain_eligible_for_bounded_tests"])
        self.assertFalse(p["scientific_first_use"])
        self.assertFalse(p["scientific_admission"])
        self.assertTrue(all(not r["stage2_native_model_integrated"] and
            not r["scientific_admission"] for r in p["rows"]))
        self.assertEqual({r["claim_id"] for r in p["rows"]
                          if r["stage1_scope"]=="DIGITAL_SUBSTITUTE_NOT_PHYSICAL_PROOF"},
                          {"U03","U06"})

    def test_original_stages_and_other_research_not_confused(self):
        p=t.scoreboard()
        self.assertEqual(p["native_pilot_priority_ids"],["AC-D1","AC-D5","AC-D3"])
        self.assertFalse(p["separate_native_intelligence_gates_count_as_acceleration_wins"])
        self.assertEqual([r["claim_id"] for r in p["rows"]
                         if r["stage2_performance_status"]!="NOT_QUALIFIED"],["AC-D1"])
        self.assertEqual(p["rows"][-6]["stage2_performance_status"],
                         "GO_CPU_MICROKERNEL_UNQUALIFIED_NOT_MODEL")

    def test_exact_ac08_source_register_covered_without_manual_substitution(self):
        reg=t.portfolio_module()
        self.assertEqual(reg.AC06_ORIGINAL|reg.AC07_ORIGINAL,
                         {f"U{i:02d}" for i in range(1,31)})
        self.assertEqual(set(reg.CASE_PINS),{"AC05","AC06","AC07"})
        self.assertEqual(reg.NATIVE_PILOT_ORDER[0]["claim_id"],"AC-D1")

    def test_original_source_free_empirical_negatives_still_reproduce(self):
        p=t.scoreboard(run_full_screening=True)
        self.assertTrue(p["negative_evidence_and_first_use_guards_preserved"])
        self.assertEqual(p["initial_source_free_restricted_screened"],36)

if __name__=="__main__":
    unittest.main()
