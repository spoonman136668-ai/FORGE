"""Tests for paired synthetic two-tier benchmark with explicit abstention."""
import unittest
from unittest.mock import patch
from scripts import two_tier_synthetic_benchmark as b

class TwoTierSyntheticBenchmarkTests(unittest.TestCase):
    def test_result_is_deterministic_and_explicitly_non_scientific(self):
        first=b.run_benchmark()
        self.assertEqual(first,b.run_benchmark())
        self.assertEqual(first["classification"],"SYNTHETIC_ENGINEERING_DIAGNOSTIC")
        self.assertFalse(first["authenticated_source"])
        self.assertFalse(first["scientific_first_use"])
        self.assertFalse(first["scientific_gain_verified"])
        self.assertFalse(first["deployment_authorized"])
        self.assertEqual(first["model_calls"],0)
        self.assertEqual(first["paid_api_calls"],0)

    def test_four_arms_receive_paired_identical_observations_and_real_costs(self):
        result=b.run_benchmark()
        self.assertEqual(set(result["arms"]),set(b.ARMS))
        self.assertEqual(result["steps"],48)
        self.assertEqual(result["warmup_pairs"],6)
        self.assertEqual(result["reversal_at"],24)
        self.assertEqual(result["contexts"],2)
        for name in ("lifetime-only","recent-only","two-tier"):
            self.assertEqual(result["arms"][name]["context0_pre_reversal"]["decision_accuracy_all_steps"],1.0)
            self.assertEqual(result["arms"][name]["context0_pre_reversal"]["decision_coverage"],1.0)
        self.assertEqual(result["arms"]["lifetime-only"]["active_packed_state_bytes"],128)
        self.assertEqual(result["arms"]["recent-only"]["active_packed_state_bytes"],64)
        self.assertEqual(result["arms"]["two-tier"]["active_packed_state_bytes"],194)
        self.assertEqual(result["arms"]["no-memory"]["active_packed_state_bytes"],0)
        self.assertEqual(result["arms"]["two-tier"]["declared_checkpoint_bytes"],230)

    def test_abstention_is_not_scored_as_a_correct_default(self):
        row=b.run_benchmark()["arms"]["no-memory"]
        self.assertEqual(row["context0_pre_reversal"]["decision_coverage"],0.0)
        self.assertEqual(row["context0_pre_reversal"]["decision_accuracy_all_steps"],0.0)
        self.assertIsNone(row["context0_pre_reversal"]["accuracy_when_decided"])
        self.assertEqual(row["context1_stationary"]["abstentions"],48)

    def test_recent_and_two_tier_adapt_after_recent_window_turnover(self):
        arms=b.run_benchmark()["arms"]
        self.assertIsNone(arms["lifetime-only"]["context0_adaptation_delay_steps"])
        self.assertEqual(arms["recent-only"]["context0_adaptation_delay_steps"],2)
        self.assertEqual(arms["two-tier"]["context0_adaptation_delay_steps"],2)
        self.assertIsNone(arms["no-memory"]["context0_adaptation_delay_steps"])
        self.assertGreater(
            arms["two-tier"]["context0_post_reversal"]["decision_accuracy_all_steps"],
            arms["lifetime-only"]["context0_post_reversal"]["decision_accuracy_all_steps"])
        self.assertEqual(arms["two-tier"]["context1_stationary"]["decision_accuracy_all_steps"],1.0)

    def test_context_isolation_preserves_stationary_context_during_other_reversal(self):
        arms=b.run_benchmark()["arms"]
        self.assertEqual(arms["two-tier"]["context1_stationary"]["decision_accuracy_all_steps"],1.0)
        self.assertEqual(arms["two-tier"]["context1_stationary"]["decision_coverage"],1.0)
        self.assertEqual(arms["no-memory"]["context1_stationary"]["decision_coverage"],0.0)

    def test_cost_benefit_is_reported_not_hidden(self):
        arms=b.run_benchmark()["arms"]
        self.assertGreater(arms["two-tier"]["active_packed_state_bytes"],
                           arms["recent-only"]["active_packed_state_bytes"])
        self.assertEqual(
            arms["two-tier"]["context0_post_reversal"]["decision_accuracy_all_steps"],
            arms["recent-only"]["context0_post_reversal"]["decision_accuracy_all_steps"])

    def test_sparse_fallback_preserves_prior_then_adapts_with_support(self):
        result=b.run_sparse_fallback()
        before=result["decision_after_one_reversal_pair"]
        self.assertEqual(result["recent_counts_after_one_reversal_pair"]["two-tier"],[[1,1],[1,1]])
        self.assertEqual(before["lifetime-only"],1)
        self.assertEqual(before["two-tier"],1)
        self.assertIsNone(before["recent-only"])
        self.assertIsNone(before["no-memory"])
        after=result["decision_after_two_reversal_pairs"]
        self.assertEqual(after["lifetime-only"],1)
        self.assertEqual(after["two-tier"],0)
        self.assertEqual(after["recent-only"],0)
        self.assertIsNone(after["no-memory"])
        self.assertEqual(result["abstention_after_one_pair"]["two-tier"],False)
        self.assertEqual(result["abstention_after_one_pair"]["recent-only"],True)
        self.assertEqual(result["state_bytes"]["two-tier"],194)
        self.assertEqual(result["state_bytes"]["recent-only"],64)

    def test_no_filesystem_or_interactive_execution(self):
        with patch("builtins.open",side_effect=AssertionError("I/O forbidden")), \
             patch("builtins.input",side_effect=AssertionError("prompt forbidden")):
            result=b.run_benchmark()
        self.assertEqual(result["classification"],"SYNTHETIC_ENGINEERING_DIAGNOSTIC")

if __name__=="__main__":
    unittest.main()
