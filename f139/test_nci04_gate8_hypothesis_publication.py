"""Tests for Gate 8: live V3 hypothesis publication seam & multi-lane isolation."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_lifecycle as native_fixture
from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.local_controller import SingleOwner
from f139.nci04_fresh_curriculum_owner import (
    HYPOTHESIS_V3_BUDGET_CEILING, remaining_hypothesis_v3_budget,
)
from f139.nci04_fresh_lifecycle import (
    PUBLISH_HYPOTHESIS_V3_RECIPES, PUBLISH_KIND, PUBLISH_SCHEMA_HYPOTHESIS_V3,
    read_lifecycle, reserve_claim, settle_provider,
)
from f139.nci04_fresh_successor_publication import (
    preflight_hypothesis_v3_plan, publish_one,
)
from f139.nci04_hypothesis_engine import generate_yggdrasil_hypothesis_pool
from f139.nci04_multi_lane_targets import (
    LANES, LaneRegistryDenied, get_lane_contract, validate_lane_isolation,
)
from f139.nci04_native_contract import canonical, digest


class Gate8HypothesisPublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = native_fixture.FreshLifecycleTests(
            "test_original_inert_prefix_stays_valid_but_cannot_claim_without_release")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.install_synthetic_release()
        self.fixture = fixture

        prop = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        prop.setUp()
        first = prop.proposal()
        second = prop.proposal({first["after_sha256"]})
        spent = {first["after_sha256"], second["after_sha256"]}
        with patch("f139.nci04_hypothesis_engine.ACCEPTED_NATIVE_BLOB", prop.blob):
            pool = generate_yggdrasil_hypothesis_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=prop.seed,
                consumed_after=spent,
                last_verified_after=second["after_sha256"],
            )
        self.plan = pool[0]["plan"]

    def terminal(self):
        fixture = self.fixture
        claim, raw = reserve_claim(
            fixture.db, fixture, fixture.key, now=fixture.now)
        fixture.prepare_provider(claim, raw)
        settle_provider(
            fixture.db, fixture, fixture.key,
            run_id=fixture.rid, now=fixture.finished)

    def test_v3_hypothesis_recipes_count_and_preflight_validation(self):
        self.assertEqual(len(PUBLISH_HYPOTHESIS_V3_RECIPES), 32)
        preflight_hypothesis_v3_plan(self.plan)
        for key, value in (
            ("recipe", "ygg-unknown-min1-abstain-v1"),
            ("title", "wrong title"),
            ("after_sha256", "f" * 64),
            ("preregistration_sha256", "not-a-sha"),
            ("scientific_first_use", True),
            ("paid_model_calls", 1),
        ):
            with self.subTest(key=key):
                bad = dict(self.plan, **{key: value})
                with self.assertRaises(ValueError):
                    preflight_hypothesis_v3_plan(bad)

    def test_publish_one_falls_through_to_v3_hypothesis_and_cold_reopens(self):
        fixture = self.fixture
        n_posts = []
        def lost_ack(**kwargs):
            n_posts.append(kwargs)
            raise OSError("V3 SYNTHETIC LOST ACK")
        fixture.create_native_feed_issue = lost_ack
        with SingleOwner(fixture.path.with_suffix(".lock")):
            self.terminal()
            before = fixture.db.meta()["head_seq"]
            with patch(
                "f139.nci04_fresh_successor_publication.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_successor_publication.propose_from_original_owner",
                return_value=None,
            ), patch(
                "f139.nci04_fresh_successor_publication.plan_next_structured_dev_from_original_owner",
                return_value=None,
            ), patch(
                "f139.nci04_fresh_successor_publication.plan_next_hypothesis_v3_from_original_owner",
                return_value=self.plan,
            ) as v3_planner:
                with self.assertRaisesRegex(OSError, "V3 SYNTHETIC LOST ACK"):
                    publish_one(fixture.db, fixture, fixture.key)
                self.assertEqual(fixture.db.meta()["head_seq"], before + 1)
                _, entries = read_lifecycle(fixture.db, fixture.key)
                self.assertEqual(entries[-1]["publication_attempt"]["schema"],
                                 PUBLISH_SCHEMA_HYPOTHESIS_V3)
                self.assertEqual(entries[-1]["publication_attempt"]["recipe"],
                                 self.plan["recipe"])
                self.assertEqual(
                    remaining_hypothesis_v3_budget(entries, HYPOTHESIS_V3_BUDGET_CEILING),
                    HYPOTHESIS_V3_BUDGET_CEILING - 2,
                )
                # Idempotent guard: second call returns None without re-posting
                self.assertIsNone(publish_one(fixture.db, fixture, fixture.key))
                self.assertEqual(len(n_posts), 1)
                self.assertEqual(v3_planner.call_count, 1)
        fixture.reopen()
        with SingleOwner(fixture.path.with_suffix(".lock")):
            _, entries = read_lifecycle(fixture.db, fixture.key)
            self.assertEqual(entries[-1]["publication_attempt"]["schema"],
                             PUBLISH_SCHEMA_HYPOTHESIS_V3)
            self.assertEqual(fixture.db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind=?", (PUBLISH_KIND,)
            ).fetchone()[0], 1)

    def test_multi_lane_registry_enforces_isolation_and_blocks_contamination(self):
        self.assertEqual(set(LANES), {"Yggdrasil", "Wingless", "TTT-Hybrid"})
        for lane in ("Yggdrasil", "Wingless", "TTT-Hybrid"):
            c = get_lane_contract(lane)
            self.assertEqual(len(c["contract_sha256"]), 64)
        validate_lane_isolation(
            lane="Yggdrasil",
            candidate_text="def choose_hyp_se_margin(self): return 0",
            target_repo="spoonman136668-ai/Yggdrasil",
        )
        with self.assertRaisesRegex(LaneRegistryDenied, "CROSS_REPO_OR_LANE"):
            validate_lane_isolation(
                lane="Wingless",
                candidate_text="def step(self): return 0",
                target_repo="spoonman136668-ai/Yggdrasil",
            )
        with self.assertRaisesRegex(LaneRegistryDenied, "FORBIDDEN_CONTAMINATION"):
            validate_lane_isolation(
                lane="Yggdrasil",
                candidate_text="import ktrade",
                target_repo="spoonman136668-ai/Yggdrasil",
            )
        with self.assertRaisesRegex(LaneRegistryDenied, "FORBIDDEN_CONTAMINATION"):
            validate_lane_isolation(
                lane="TTT-Hybrid",
                candidate_text="class TransformerBlock: pass",
                target_repo="spoonman136668-ai/FORGE",
            )


if __name__ == "__main__":
    unittest.main()
