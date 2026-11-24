"""Tests for preregistered scientific evaluation harness (nci04_scientific_evaluator)."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.nci04_hypothesis_engine import generate_yggdrasil_hypothesis_pool
from f139.nci04_scientific_evaluator import (
    EVAL_SCHEMA, ScientificEvalDenied, evaluate_and_rank_pool,
    evaluate_hypothesis_item,
)


class ScientificEvaluatorTests(unittest.TestCase):
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

    def test_evaluates_all_32_hypotheses_reproducibly_against_matched_controls(self):
        pool = self._pool()
        summary1 = evaluate_and_rank_pool(pool)
        summary2 = evaluate_and_rank_pool(pool)
        self.assertEqual(summary1, summary2)
        self.assertEqual(summary1["schema"], EVAL_SCHEMA)
        self.assertEqual(summary1["evaluated_count"], 32)
        self.assertFalse(summary1["scientific_first_use"])
        self.assertFalse(summary1["auto_promote_checkpoint"])
        for ev in summary1["evaluations"]:
            self.assertTrue(ev["reproducible"])
            self.assertIn("choose", ev["controls"])
            self.assertTrue(ev["candidate"]["checkpoint_164_byte_invariance"])
            self.assertEqual(len(ev["evaluation_sha256"]), 64)

    def test_negative_control_rejects_tampered_preregistration_hash(self):
        pool = self._pool()
        tampered = copy.deepcopy(pool[0])
        tampered["preregistration"]["falsifiable_claim"] = "post-hoc altered claim"
        with self.assertRaisesRegex(ScientificEvalDenied, "PREREGISTRATION_HASH_DRIFT"):
            evaluate_hypothesis_item(tampered)

    def test_negative_control_rejects_unauthorized_scientific_first_use_flag(self):
        pool = self._pool()
        bad = copy.deepcopy(pool[0])
        bad["preregistration"]["frozen_protocol"]["scientific_first_use"] = True
        with self.assertRaisesRegex(ScientificEvalDenied, "PREREGISTRATION_CONTRACT_INVALID"):
            evaluate_hypothesis_item(bad)


if __name__ == "__main__":
    unittest.main()
