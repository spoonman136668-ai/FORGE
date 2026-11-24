"""Tests for Gate 13: Wingless Gen-2, TTT-Hybrid held-out OOD, and 3-lane evidence ledger."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.nci04_heldout_qualifier import HELDOUT_SEEDS
from f139.nci04_hypothesis_engine import FROZEN_SEEDS, generate_yggdrasil_hypothesis_pool
from f139.nci04_hypothesis_engine_gen2 import generate_gen2_yggdrasil_pool
from f139.nci04_scientific_evidence_report import (
    SCHEMA as EVIDENCE_SCHEMA, build_cross_architecture_evidence_report,
)
from f139.nci04_ttt_hybrid_hypothesis import (
    TTTHybridEvalDenied, qualify_ttt_hybrid_heldout,
)
from f139.nci04_wingless_gen2 import (
    WinglessGen2Denied, qualify_wingless_gen2_heldout, run_wingless_gen2_dev_eval,
)


class Gate13MultiLaneQualificationTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        fixture.setUp()
        self.fixture = fixture
        first = fixture.proposal()
        second = fixture.proposal({first["after_sha256"]})
        self.spent = {first["after_sha256"], second["after_sha256"]}
        self.last_verified = second["after_sha256"]

    def test_wingless_gen2_rejects_dev_seed_leakage_and_qualifies_reproducibly(self):
        with self.assertRaises(WinglessGen2Denied) as ctx:
            qualify_wingless_gen2_heldout(heldout_seeds=(FROZEN_SEEDS[0], 101, 131, 163, 197))
        self.assertIn("DEV_SEED_LEAKAGE_DETECTED", str(ctx.exception))

        dev1 = run_wingless_gen2_dev_eval()
        dev2 = run_wingless_gen2_dev_eval()
        self.assertEqual(dev1, dev2)
        self.assertTrue(dev1["reproducible"])

        ho1 = qualify_wingless_gen2_heldout()
        ho2 = qualify_wingless_gen2_heldout()
        self.assertEqual(ho1, ho2)
        self.assertTrue(ho1["reproducible"])
        self.assertTrue(ho1["dev_seeds_disjoint"])
        self.assertFalse(ho1["scientific_first_use"])
        self.assertFalse(ho1["auto_promote_checkpoint"])

    def test_ttt_hybrid_heldout_rejects_dev_seed_leakage_and_qualifies_reproducibly(self):
        with self.assertRaises(TTTHybridEvalDenied) as ctx:
            qualify_ttt_hybrid_heldout(heldout_seeds=(FROZEN_SEEDS[0], 101, 131, 163, 197))
        self.assertIn("DEV_SEED_LEAKAGE_DETECTED", str(ctx.exception))

        ho1 = qualify_ttt_hybrid_heldout()
        ho2 = qualify_ttt_hybrid_heldout()
        self.assertEqual(ho1, ho2)
        self.assertTrue(ho1["reproducible"])
        self.assertTrue(ho1["dev_seeds_disjoint"])
        self.assertFalse(ho1["scientific_first_use"])
        self.assertFalse(ho1["auto_promote_checkpoint"])
        self.assertIn("trust_region_slow_fast_assimilation", ho1["qualified_policies"])

    def test_cross_architecture_evidence_report_seals_all_three_distinct_lanes(self):
        with patch("f139.nci04_hypothesis_engine.ACCEPTED_NATIVE_BLOB", self.fixture.blob):
            g1 = generate_yggdrasil_hypothesis_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=self.fixture.seed,
                consumed_after=self.spent,
                last_verified_after=self.last_verified,
            )
        with patch("f139.nci04_hypothesis_engine_gen2.ACCEPTED_NATIVE_BLOB", self.fixture.blob):
            g2 = generate_gen2_yggdrasil_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=self.fixture.seed,
                consumed_after=self.spent,
                last_verified_after=self.last_verified,
            )
        rep1 = build_cross_architecture_evidence_report(
            yggdrasil_gen1_pool=g1[:4], yggdrasil_gen2_pool=g2[:4],
            heldout_seeds=HELDOUT_SEEDS[:5],
        )
        rep2 = build_cross_architecture_evidence_report(
            yggdrasil_gen1_pool=g1[:4], yggdrasil_gen2_pool=g2[:4],
            heldout_seeds=HELDOUT_SEEDS[:5],
        )
        self.assertEqual(rep1, rep2)
        self.assertEqual(rep1["schema"], EVIDENCE_SCHEMA)
        self.assertEqual(rep1["distinct_architecture_count"], 3)
        self.assertEqual(set(rep1["lanes"].keys()), {"Yggdrasil", "Wingless", "TTT-Hybrid"})
        self.assertEqual(rep1["paid_model_calls"], 0)
        self.assertFalse(rep1["scientific_first_use"])
        self.assertFalse(rep1["auto_promote_checkpoint"])
        self.assertEqual(len(rep1["evidence_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
