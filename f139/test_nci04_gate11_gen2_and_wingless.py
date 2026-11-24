"""Tests for Gate 11: Gen-2 Yggdrasil hypotheses & Wingless causal-binding evaluator."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.nci04_hypothesis_engine_gen2 import (
    GEN2_ESTIMATORS, GEN2_SUPPORT_GATES, GEN2_TIE_POLICIES,
    SCHEMA as GEN2_SCHEMA, generate_gen2_yggdrasil_pool,
)
from f139.nci04_scientific_evaluator import evaluate_and_rank_pool
from f139.nci04_wingless_hypothesis import (
    SCHEMA as WINGLESS_SCHEMA, run_wingless_preregistered_eval,
)


class Gate11Gen2AndWinglessTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        fixture.setUp()
        self.fixture = fixture
        first = fixture.proposal()
        second = fixture.proposal({first["after_sha256"]})
        self.spent = {first["after_sha256"], second["after_sha256"]}
        self.last_verified = second["after_sha256"]

    def test_gen2_generates_18_unique_hypotheses_and_evaluates_reproducibly(self):
        with patch("f139.nci04_hypothesis_engine_gen2.ACCEPTED_NATIVE_BLOB",
                   self.fixture.blob):
            pool = generate_gen2_yggdrasil_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=self.fixture.seed,
                consumed_after=self.spent,
                last_verified_after=self.last_verified,
            )
        expected = len(GEN2_ESTIMATORS) * len(GEN2_SUPPORT_GATES) * len(GEN2_TIE_POLICIES)
        self.assertEqual(expected, 18)
        self.assertEqual(len(pool), 18)
        self.assertEqual(len({p["plan"]["after_sha256"] for p in pool}), 18)
        self.assertTrue(all(p["plan"]["schema"] == GEN2_SCHEMA for p in pool))
        summary = evaluate_and_rank_pool(pool)
        self.assertEqual(summary["evaluated_count"], 18)
        self.assertTrue(all(e["reproducible"] for e in summary["evaluations"]))
        self.assertTrue(all(e["candidate"]["checkpoint_164_byte_invariance"]
                            for e in summary["evaluations"]))

    def test_wingless_preregistered_causal_binding_eval_is_reproducible(self):
        rep1 = run_wingless_preregistered_eval()
        rep2 = run_wingless_preregistered_eval()
        self.assertEqual(rep1, rep2)
        self.assertEqual(rep1["schema"], WINGLESS_SCHEMA)
        self.assertEqual(rep1["lane"], "Wingless")
        self.assertTrue(rep1["reproducible"])
        self.assertFalse(rep1["scientific_first_use"])
        self.assertFalse(rep1["auto_promote_checkpoint"])
        self.assertEqual(len(rep1["report_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
