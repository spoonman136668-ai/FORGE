"""Original SQLite owner fixture; synthetic provider only, no live effects."""
from __future__ import annotations

import unittest

from f139.local_controller import SingleOwner
from f139.nci04_fresh_curriculum import CurriculumDenied
from f139.nci04_fresh_curriculum_owner import select_cold_owner_dev_candidate
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


if __name__ == "__main__":
    unittest.main()
