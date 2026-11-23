"""Original SQLite owner fixture; synthetic provider only, no live effects."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner
from f139.nci04_fresh_curriculum import CurriculumDenied
from f139.nci04_fresh_curriculum_owner import (
    select_cold_owner_dev_candidate,
    plan_next_structured_dev_from_original_owner,
    remaining_structured_dev_budget,
)
from f139.nci04_fresh_lifecycle import reserve_claim, settle_provider
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET_TREE
from f139 import test_nci04_fresh_lifecycle as fixture_module
from f139.test_nci04_fresh_curriculum import proposal


class OwnerVerifiedSelectorTests(unittest.TestCase):
    def setUp(self):
        fixture = fixture_module.FreshLifecycleTests(
            "test_original_inert_prefix_stays_valid_but_cannot_claim_without_release")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.owner = fixture
        self.candidate = proposal()
        self.candidate.update(source_sha=SOURCE, target_tree_sha=TARGET_TREE)

    def verify_one_terminal(self):
        self.owner.install_synthetic_release()
        claim, raw = reserve_claim(
            self.owner.db, self.owner, self.owner.key, now=self.owner.now)
        self.owner.prepare_provider(claim, raw)
        settle_provider(
            self.owner.db, self.owner, self.owner.key,
            run_id=self.owner.rid, now=self.owner.finished)

    def select(self, candidates=None):
        return select_cold_owner_dev_candidate(
            db=self.owner.db, owner_key=self.owner.key,
            proposals=[self.candidate] if candidates is None else candidates,
            remaining_cost_units=10)

    def test_signed_cold_terminal_selects_without_ledger_mutation(self):
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            before = (self.owner.db.meta()["head_hash"],
                      self.owner.db.conn.total_changes)
            picked = self.select()
            self.assertEqual(picked, self.candidate)
            self.assertEqual(before, (
                self.owner.db.meta()["head_hash"],
                self.owner.db.conn.total_changes))
            self.assertEqual(picked, self.select())

    def test_without_original_kernel_mutex_denied(self):
        self.owner.install_synthetic_release()
        with self.assertRaisesRegex(
                CurriculumDenied, "COLD_ORIGINAL_OWNER_MUTEX_REQUIRED"):
            self.select()

    def test_start_risk_cannot_be_treated_as_verified_history(self):
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.owner.install_synthetic_release()
            reserve_claim(
                self.owner.db, self.owner, self.owner.key, now=self.owner.now)
            with self.assertRaisesRegex(
                    CurriculumDenied, "LAST_TICKET_NOT_TERMINAL"):
                self.select()

    def test_unqualified_candidate_source_cannot_cross_original_boundary(self):
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            altered = dict(self.candidate, source_sha="0" * 40)
            with self.assertRaisesRegex(
                    CurriculumDenied, "UNQUALIFIED_OR_UNSAFE_PROPOSAL"):
                self.select([altered])

    def test_legacy_sealed_after_identity_is_always_consumed(self):
        old = self.owner.consumed["old_source_after_sha256"]
        self.assertTrue(old, "Fixture must include real-shaped historical negatives")
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            duplicated = dict(self.candidate, after_sha256=old[0])
            self.assertIsNone(self.select([duplicated]))


    def test_original_owner_plan_binds_generated_source_without_remote_post(self):
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            last = self.owner.fixture.issue.candidate.after_sha256
            candidate = dict(self.candidate, prerequisites=[last])
            plan = {
                "recipe": "support-2-v2",
                "after_sha256": candidate["after_sha256"],
                "intent_sha256": candidate["intent_sha256"],
                "scientific_first_use": False, "paid_model_calls": 0,
            }
            pool = [{"selection": candidate, "plan": plan}]
            before = (self.owner.db.meta()["head_seq"],
                      self.owner.db.meta()["head_hash"],
                      self.owner.db.conn.total_changes)
            with patch(
                "f139.nci04_fresh_lifecycle.authenticate_runtime_owner"
            ) as owner_auth, patch(
                "f139.nci04_fresh_structured_dev.generate_from_original_owner",
                return_value=pool,
            ) as author:
                actual = plan_next_structured_dev_from_original_owner(
                    db=self.owner.db, api=self.owner,
                    owner_key=self.owner.key, remaining_cost_units=2)
                self.assertEqual(actual, plan)
                owner_auth.assert_called_once()
                author.assert_called_once()
                self.assertEqual(
                    author.call_args.kwargs["last_verified_after"], last)
                self.assertIn(last, author.call_args.kwargs["consumed_after"])
                self.assertIn("9" * 64, author.call_args.kwargs["consumed_after"])
                self.assertEqual(before, (
                    self.owner.db.meta()["head_seq"],
                    self.owner.db.meta()["head_hash"],
                    self.owner.db.conn.total_changes))
                self.assertEqual(
                    self.owner.db.conn.execute(
                        "SELECT COUNT(*) FROM events WHERE kind='FRESH_SUCCESSOR_PUBLICATION_ATTEMPTED'"
                    ).fetchone()[0], 0)


    def test_cold_budget_counts_all_v2_posts_including_uncertain_attempts(self):
        from f139.nci04_fresh_lifecycle import (
            PUBLISH_SCHEMA, PUBLISH_SCHEMA_STRUCTURED,
        )
        entry = lambda attempt=None: {
            "record": {"ticket": "fixture"},
            "publication_attempt": attempt,
        }
        prior = [
            entry({"schema": PUBLISH_SCHEMA}),  # old recipes do not debit V2
            entry({"schema": PUBLISH_SCHEMA_STRUCTURED}),
            entry({"schema": PUBLISH_SCHEMA_STRUCTURED}),
            entry(),
        ]
        self.assertEqual(remaining_structured_dev_budget(prior, 16), 12)
        self.assertEqual(remaining_structured_dev_budget(prior, 4), 0)
        with self.assertRaisesRegex(
                CurriculumDenied, "STRUCTURED_BUDGET_ALREADY_EXCEEDED"):
            remaining_structured_dev_budget(prior, 3)
        # Source-validated negative/unknown outcomes remain spent; this
        # helper deliberately has no success or refund condition.
        prior[2]["negative"] = {"conclusion": "failure"}
        self.assertEqual(remaining_structured_dev_budget(prior, 16), 12)
        for bad in (None, -1, 10001, True):
            with self.subTest(bad=bad), self.assertRaises(CurriculumDenied):
                remaining_structured_dev_budget(prior, bad)
        with self.assertRaisesRegex(CurriculumDenied, "ATTEMPT_INVALID"):
            remaining_structured_dev_budget(
                [entry({"schema": "unreviewed"})], 16)

    def test_owner_planner_cannot_reset_the_structured_budget_each_tick(self):
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            last = self.owner.fixture.issue.candidate.after_sha256
            candidate = dict(self.candidate, prerequisites=[last])
            plan = {
                "recipe": "support-2-v2",
                "after_sha256": candidate["after_sha256"],
                "intent_sha256": candidate["intent_sha256"],
                "scientific_first_use": False, "paid_model_calls": 0,
            }
            pool = [{"selection": candidate, "plan": plan}]
            with patch(
                "f139.nci04_fresh_lifecycle.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_structured_dev.generate_from_original_owner",
                return_value=pool,
            ), patch(
                "f139.nci04_fresh_curriculum_owner.remaining_structured_dev_budget",
                return_value=0,
            ) as remaining:
                selected = plan_next_structured_dev_from_original_owner(
                    db=self.owner.db, api=self.owner,
                    owner_key=self.owner.key, remaining_cost_units=16)
                self.assertIsNone(selected)
                remaining.assert_called_once()
                self.assertEqual(remaining.call_args.args[1], 16)

    def test_plan_denies_without_lock_or_verified_tail(self):
        self.owner.install_synthetic_release()
        with self.assertRaisesRegex(
                CurriculumDenied, "PLANNER_ORIGINAL_MUTEX_REQUIRED"):
            plan_next_structured_dev_from_original_owner(
                db=self.owner.db, api=self.owner,
                owner_key=self.owner.key, remaining_cost_units=2)
        with SingleOwner(self.owner.path.with_suffix(".lock")), patch(
            "f139.nci04_fresh_lifecycle.authenticate_runtime_owner"
        ):
            with self.assertRaisesRegex(
                    CurriculumDenied, "PLANNER_MUST_FOLLOW_UNPUBLISHED_VERIFIED_TERMINAL"):
                plan_next_structured_dev_from_original_owner(
                    db=self.owner.db, api=self.owner,
                    owner_key=self.owner.key, remaining_cost_units=2)

    def test_plan_refuses_unauthenticated_installed_owner(self):
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            with patch(
                "f139.nci04_fresh_lifecycle.authenticate_runtime_owner",
                side_effect=ValueError("SYNTHETIC_TASK_SOURCE_DRIFT")
            ), patch(
                "f139.nci04_fresh_structured_dev.generate_from_original_owner"
            ) as author:
                with self.assertRaisesRegex(
                        ValueError, "SYNTHETIC_TASK_SOURCE_DRIFT"):
                    plan_next_structured_dev_from_original_owner(
                        db=self.owner.db, api=self.owner,
                        owner_key=self.owner.key, remaining_cost_units=2)
                author.assert_not_called()

    def test_plan_fails_closed_if_old_ledger_seal_is_modified(self):
        from f139.nci04_native_contract import canonical
        root = self.owner.path.parent
        with SingleOwner(self.owner.path.with_suffix(".lock")):
            self.verify_one_terminal()
            consumed = dict(self.owner.consumed)
            consumed["old_source_after_sha256"] = ["a" * 64]
            (root / "consumed-development-identities.json").write_bytes(
                canonical(consumed))
            with patch(
                "f139.nci04_fresh_lifecycle.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_structured_dev.generate_from_original_owner"
            ) as author:
                with self.assertRaisesRegex(
                        CurriculumDenied, "PLANNER_SEALED_CONSUMED_HISTORY_DRIFT"):
                    plan_next_structured_dev_from_original_owner(
                        db=self.owner.db, api=self.owner,
                        owner_key=self.owner.key, remaining_cost_units=2)
                author.assert_not_called()


if __name__ == "__main__":
    unittest.main()
