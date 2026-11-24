"""Tests for Gate 12: Independent held-out OOD qualifier, TTT-Hybrid eval, and Gen-2 escalation."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.nci04_heldout_qualifier import (
    HELDOUT_SEEDS, SCHEMA as HELDOUT_SCHEMA, HeldoutQualificationDenied,
    qualify_hypothesis_heldout, qualify_pool_heldout,
)
from f139.nci04_hypothesis_engine import FROZEN_SEEDS
from f139.nci04_hypothesis_engine_gen2 import generate_gen2_yggdrasil_pool
from f139.nci04_receipt_feedback import (
    parse_hypothesis_recipe, rank_pool_with_receipt_feedback,
)
from f139.nci04_ttt_hybrid_hypothesis import (
    SCHEMA as TTT_SCHEMA, run_ttt_hybrid_preregistered_eval,
)


class Gate12HeldoutAndTTTHybridTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        fixture.setUp()
        self.fixture = fixture
        first = fixture.proposal()
        second = fixture.proposal({first["after_sha256"]})
        self.spent = {first["after_sha256"], second["after_sha256"]}
        self.last_verified = second["after_sha256"]

    def _gen2_pool(self):
        with patch("f139.nci04_hypothesis_engine_gen2.ACCEPTED_NATIVE_BLOB",
                   self.fixture.blob):
            return generate_gen2_yggdrasil_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=self.fixture.seed,
                consumed_after=self.spent,
                last_verified_after=self.last_verified,
            )

    def test_heldout_qualifier_rejects_dev_seed_leakage_fail_closed(self):
        pool = self._gen2_pool()
        self.assertTrue(set(HELDOUT_SEEDS).isdisjoint(set(FROZEN_SEEDS)))
        leaked_seeds = (FROZEN_SEEDS[0], 101, 131, 163, 197)
        with self.assertRaises(HeldoutQualificationDenied) as ctx:
            qualify_hypothesis_heldout(pool[0], heldout_seeds=leaked_seeds)
        self.assertIn("DEV_SEED_LEAKAGE_DETECTED", str(ctx.exception))

    def test_heldout_qualifier_runs_reproducibly_with_164_byte_invariance(self):
        pool = self._gen2_pool()
        summary1 = qualify_pool_heldout(pool[:4])
        summary2 = qualify_pool_heldout(pool[:4])
        self.assertEqual(summary1, summary2)
        self.assertEqual(summary1["schema"], HELDOUT_SCHEMA)
        self.assertEqual(summary1["evaluated_count"], 4)
        self.assertFalse(summary1["scientific_first_use"])
        self.assertFalse(summary1["auto_promote_checkpoint"])
        self.assertEqual(summary1["paid_model_calls"], 0)
        for rep in summary1["reports"]:
            self.assertTrue(rep["dev_seeds_disjoint"])
            self.assertTrue(rep["reproducible"])
            self.assertTrue(rep["candidate"]["checkpoint_164_byte_invariance"])
            self.assertEqual(len(rep["paired_seed_deltas"]), len(HELDOUT_SEEDS))
            self.assertEqual(
                rep["seed_wins"] + rep["seed_ties"] + rep["seed_losses"],
                len(HELDOUT_SEEDS),
            )

    def test_ttt_hybrid_preregistered_eval_is_reproducible_and_bounded(self):
        rep1 = run_ttt_hybrid_preregistered_eval()
        rep2 = run_ttt_hybrid_preregistered_eval()
        self.assertEqual(rep1, rep2)
        self.assertEqual(rep1["schema"], TTT_SCHEMA)
        self.assertEqual(rep1["lane"], "TTT-Hybrid")
        self.assertTrue(rep1["reproducible"])
        self.assertFalse(rep1["scientific_first_use"])
        self.assertFalse(rep1["auto_promote_checkpoint"])
        self.assertEqual(rep1["paid_model_calls"], 0)
        self.assertEqual(len(rep1["report_sha256"]), 64)
        for stats in rep1["results"].values():
            self.assertTrue(stats["bounded_norm_ok"])

    def test_receipt_feedback_parses_gen2_recipes_and_pivots_on_negative(self):
        axes = parse_hypothesis_recipe("ygg-gen2-z_5_4-min2-least_observed-v1")
        self.assertEqual(axes, {
            "estimator": "z_5_4",
            "support_gate": "min2",
            "tie_policy": "least_observed",
        })
        pool = self._gen2_pool()
        entries = [{
            "stage": "NEGATIVE",
            "negative": {"reason": "synthetic_fail"},
            "record": {"after_sha256": "0" * 64},
            "publication_attempt": {"recipe": "ygg-gen2-z_5_4-min2-least_observed-v1"},
        }]
        decision = rank_pool_with_receipt_feedback(pool, entries)
        self.assertIsNotNone(decision["selected_hypothesis_id"])
        self.assertNotEqual(
            decision["selected_hypothesis_id"],
            "ygg-gen2-z_5_4-min2-least_observed-v1",
        )


if __name__ == "__main__":
    unittest.main()
