"""Tests for the paired, deterministic synthetic memory benchmark."""
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

    def test_four_arms_receive_paired_identical_observations(self):
        result=b.run_benchmark()
        self.assertEqual(set(result["arms"]),set(b.ARMS))
        self.assertEqual(result["steps"],48)
        self.assertEqual(result["reversal_at"],24)
        self.assertEqual(result["contexts"],2)
        for row in result["arms"].values():
            self.assertEqual(row["context0_pre_reversal_accuracy"],1.0)
        self.assertEqual(result["arms"]["lifetime-only"]["active_packed_state_bytes"],128)
        self.assertEqual(result["arms"]["recent-only"]["active_packed_state_bytes"],64)
        self.assertEqual(result["arms"]["two-tier"]["active_packed_state_bytes"],194)
        self.assertEqual(result["arms"]["no-memory"]["active_packed_state_bytes"],0)
        self.assertEqual(result["arms"]["two-tier"]["declared_checkpoint_bytes"],230)

    def test_recent_and_two_tier_adapt_faster_than_lifetime_only(self):
        arms=b.run_benchmark()["arms"]
        self.assertIsNone(arms["lifetime-only"]["context0_adaptation_delay_steps"])
        self.assertEqual(arms["recent-only"]["context0_adaptation_delay_steps"],2)
        self.assertEqual(arms["two-tier"]["context0_adaptation_delay_steps"],2)
        self.assertEqual(arms["no-memory"]["context0_adaptation_delay_steps"],None)
        self.assertGreater(arms["two-tier"]["context0_post_reversal_accuracy"],
                          arms["lifetime-only"]["context0_post_reversal_accuracy"])
        self.assertGreater(arms["two-tier"]["context1_stationary_accuracy"],0.9)

    def test_context_isolation_preserves_stationary_context_during_other_reversal(self):
        arms=b.run_benchmark()["arms"]
        self.assertGreater(arms["two-tier"]["context1_stationary_accuracy"],0.9)
        self.assertGreater(arms["two-tier"]["context1_stationary_accuracy"],
                           arms["no-memory"]["context1_stationary_accuracy"])

    def test_cost_benefit_is_reported_not_hidden(self):
        arms=b.run_benchmark()["arms"]
        self.assertGreater(arms["two-tier"]["active_packed_state_bytes"],
                           arms["recent-only"]["active_packed_state_bytes"])
        self.assertEqual(arms["two-tier"]["context0_post_reversal_accuracy"],
                         arms["recent-only"]["context0_post_reversal_accuracy"])

    def test_no_filesystem_or_interactive_execution(self):
        with patch("builtins.open",side_effect=AssertionError("I/O forbidden")), \
             patch("builtins.input",side_effect=AssertionError("prompt forbidden")):
            result=b.run_benchmark()
        self.assertEqual(result["classification"],"SYNTHETIC_ENGINEERING_DIAGNOSTIC")

if __name__=="__main__":
    unittest.main()
