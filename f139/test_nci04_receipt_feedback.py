"""Tests for Gate 10: closed-loop receipt feedback and Wingless pinned lane contract."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.nci04_hypothesis_engine import generate_yggdrasil_hypothesis_pool
from f139.nci04_multi_lane_targets import get_lane_contract
from f139.nci04_receipt_feedback import (
    SCHEMA, ReceiptFeedbackDenied, parse_hypothesis_recipe,
    propose_next_generation_axes, rank_pool_with_receipt_feedback,
    summarize_receipt_ledger,
)


class ReceiptFeedbackTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        fixture.setUp()
        self.fixture = fixture
        first = fixture.proposal()
        second = fixture.proposal({first["after_sha256"]})
        self.spent = {first["after_sha256"], second["after_sha256"]}
        self.last_verified = second["after_sha256"]

    def _pool(self):
        with patch("f139.nci04_hypothesis_engine.ACCEPTED_NATIVE_BLOB",
                   self.fixture.blob):
            return generate_yggdrasil_hypothesis_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=self.fixture.seed,
                consumed_after=self.spent,
                last_verified_after=self.last_verified,
            )

    def test_parses_v3_recipes_and_summarizes_mixed_verified_and_negative_ledger(self):
        self.assertEqual(
            parse_hypothesis_recipe("ygg-se_margin-balanced2x-abstain-v1"),
            {"estimator": "se_margin", "support_gate": "balanced2x", "tie_policy": "abstain"},
        )
        self.assertIsNone(parse_hypothesis_recipe("support-4-v2"))
        entries = [
            {"stage": "VERIFIED", "publication_attempt": {"recipe": "support-4-v2"}},
            {"stage": "VERIFIED", "publication_attempt": {"recipe": "ygg-se_margin-balanced2x-abstain-v1"}},
            {"stage": "NEGATIVE", "negative": {"run_id": 999}, "publication_attempt": {"recipe": "ygg-jeffreys-min1-least_observed-v1"}},
        ]
        summary = summarize_receipt_ledger(entries)
        self.assertEqual(summary["schema"], SCHEMA)
        self.assertEqual(summary["total_verified"], 2)
        self.assertEqual(summary["total_negative"], 1)
        self.assertEqual(summary["v3_verified"], 1)
        self.assertEqual(summary["v3_negative"], 1)
        self.assertTrue(summary["retained_all_failures"])
        self.assertEqual(summary["axis_stats"]["estimator"]["se_margin"]["verified"], 1)
        self.assertEqual(summary["axis_stats"]["estimator"]["jeffreys"]["negative"], 1)

        next_gen = propose_next_generation_axes(summary)
        self.assertEqual(next_gen["clean_verified_estimators"], ["se_margin"])
        self.assertEqual(next_gen["retained_failed_estimators"], ["jeffreys"])
        families = {p["family"] for p in next_gen["next_generation_proposals"]}
        self.assertIn("rational_confidence_refinement", families)
        self.assertIn("imbalance_ratio_sweep", families)

    def test_closed_loop_ranker_pivots_away_from_failed_receipt_axes(self):
        pool = self._pool()
        entries = [
            {"stage": "NEGATIVE", "negative": {"run_id": 1},
             "publication_attempt": {"recipe": "ygg-se_margin-min1-least_observed-v1"}},
        ]
        decision = rank_pool_with_receipt_feedback(pool, entries)
        self.assertIsNotNone(decision["selected_hypothesis_id"])
        self.assertNotIn("se_margin", decision["selected_hypothesis_id"])
        self.assertNotIn("min1", decision["selected_hypothesis_id"])
        self.assertNotIn("least_observed", decision["selected_hypothesis_id"])
        self.assertFalse(decision["scientific_first_use"])
        self.assertFalse(decision["auto_promote_checkpoint"])

    def test_wingless_lane_pins_real_protected_main_commit_and_tree(self):
        w = get_lane_contract("Wingless")
        self.assertEqual(w["active_target_repo"], "spoonman136668-ai/Wingless")
        self.assertEqual(w["active_target_commit"], "9a92fcae40c811c724b4214da03fff34126f6b4f")
        self.assertEqual(w["active_target_tree"], "4d4e92af583aa66f71aa62b1cba4969dacf39453")
        self.assertEqual(w["active_target_path"], "ice/relationships.go")
        self.assertFalse(w["live_hypothesis_enabled"])

    def test_empty_entries_fail_closed(self):
        with self.assertRaisesRegex(ReceiptFeedbackDenied, "ENTRIES_INVALID"):
            summarize_receipt_ledger([])


if __name__ == "__main__":
    unittest.main()
