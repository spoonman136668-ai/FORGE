"""Tests for the paired, deterministic synthetic memory benchmark."""
import unittest
from unittest.mock import patch

from scripts import two_tier_synthetic_benchmark as b


class TwoTierSyntheticBenchmarkTests(unittest.TestCase):
    def test_result_is_deterministic_and_explicitly_non_scientific(self):
        first = b.run_benchmark()
        self.assertEqual(first, b.run_benchmark())
        self.assertEqual(first["classification"], "SYNTHETIC_ENGINEERING_DIAGNOSTIC")
        self.assertFalse(first["authenticated_source"])
        self.assertFalse(first["scientific_first_use"])
        self.assertFalse(first["scientific_gain_verified"])
        self.assertFalse(first["deployment_authorized"])
        self.assertEqual(first["model_calls"], 0)
        self.assertEqual(first["paid_api_calls"], 0)

    def test_four_arms_receive_paired_identical_observations(self):
        result = b.run_benchmark()
        self.assertEqual(set(result["arms"]), set(b.ARMS))
        self.assertEqual(result["steps"], 48)
        self.assertEqual(result["reversal_at"], 24)
        for name in b.ARMS:
            row = result["arms"][name]
            self.assertEqual(row["learned_bytes"], 194)
            self.assertEqual(row["checkpoint_bytes"], 230)
            self.assertEqual(sum(row["lifetime_counts_context0_action0"]), 48)
            self.assertEqual(sum(row["lifetime_counts_context0_action1"]), 48)

    def test_recent_and_two_tier_adapt_faster_than_lifetime_only(self):
        arms = b.run_benchmark()["arms"]
        lifetime_delay = arms["lifetime-only"]["context0_adaptation_delay_steps"]
        recent_delay = arms["recent-only"]["context0_adaptation_delay_steps"]
        two_tier_delay = arms["two-tier"]["context0_adaptation_delay_steps"]
        self.assertIsNotNone(lifetime_delay)
        self.assertIsNotNone(recent_delay)
        self.assertIsNotNone(two_tier_delay)
        self.assertLess(two_tier_delay, lifetime_delay)
        self.assertLessEqual(two_tier_delay, 2)
        self.assertGreater(
            arms["two-tier"]["context0_post_reversal_accuracy"],
            arms["lifetime-only"]["context0_post_reversal_accuracy"])
        self.assertGreater(
            arms["two-tier"]["context1_stationary_accuracy"], 0.9)

    def test_context_isolation_prevents_cross_context_reversal(self):
        arms = b.run_benchmark()["arms"]
        self.assertGreater(arms["two-tier"]["context1_stationary_accuracy"], 0.9)
        self.assertGreater(
            arms["two-tier"]["context1_stationary_accuracy"],
            arms["no-memory"]["context1_stationary_accuracy"])

    def test_no_filesystem_or_network_is_required(self):
        with patch("builtins.open", side_effect=AssertionError("I/O forbidden")), \
             patch("builtins.input", side_effect=AssertionError("prompt forbidden")):
            result = b.run_benchmark()
        self.assertEqual(result["classification"], "SYNTHETIC_ENGINEERING_DIAGNOSTIC")


if __name__ == "__main__":
    unittest.main()
