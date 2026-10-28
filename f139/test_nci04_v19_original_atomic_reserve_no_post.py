"""Qualify V19 ORIGINAL SQLite atomic pre-POST intent with no model requests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_attempt_schema import KIND
from f139.nci04_v19_original_atomic_reserve_no_post import (
    ShadowDenied, reserve_original_intent_without_post,
)
from test_nci04_v19_original_attempt_schema import (
    OriginalRequestColdVerifierTests,
)


class OriginalAtomicNoPostTests(unittest.TestCase):
    def setUp(self):
        fixture = OriginalRequestColdVerifierTests(
            "test_no_new_events_original_behavior_and_original_head_unchanged")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = fixture.mutex

    def native(self):
        return self.fixture.real_native()

    def reserve(self, *, lane="Wingless", day="2026-10-28",
                witness=None, inject_fault=False):
        if witness is None:
            witness = lambda: True
        return reserve_original_intent_without_post(
            self.db, lane=lane, utc_day=day,
            owner_witness=witness,
            fault_after_append=inject_fault)

    def count(self):
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)
        ).fetchone()[0]

    def test_original_sqlite_atomic_pre_post_event_cold_reopens(self):
        issue = self.native()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            report = self.reserve()
            self.assertEqual(report["disposition"],
                             "ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST")
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"] + 1)
            self.assertEqual(report["original_request_attempt_event_seq"],
                             self.db.meta()["head_seq"])
            self.assertEqual(report["original_request_attempt_event_sha256"],
                             self.db.meta()["head_hash"])
            self.assertEqual(self.count(), 1)
            for name in ("original_owner_request_authorized", "worker_dispatched",
                         "scientific_first_use"):
                self.assertIs(report[name], False)
            for name in ("provider_requests", "paid_model_calls",
                         "accepted_ref_mutations"):
                self.assertEqual(report[name], 0)
            row = self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)
            ).fetchone()
            self.assertIn(issue.ticket, row["payload"])
            cold = Database(self.db.filename)
            try:
                cold.verify()
                self.assertEqual(cold.meta()["head_hash"],
                                 self.db.meta()["head_hash"])
            finally:
                cold.close()

    def test_second_same_native_terminal_is_spent_even_next_utc_day(self):
        self.native()
        with SingleOwner(self.mutex):
            first = self.reserve()
            frozen = self.db.meta().copy()
            for day in ("2026-10-28", "2026-10-29", "2026-11-12"):
                with self.subTest(day=day):
                    second = self.reserve(day=day)
                    self.assertEqual(second["disposition"],
                                     "BLOCKED_ALREADY_CONSUMED")
                    self.assertIsNone(second["original_request_attempt_event_seq"])
                    self.assertEqual(self.count(), 1)
                    self.assertEqual(self.db.meta(), frozen)
            self.assertNotEqual(first["original_request_attempt_event_sha256"],
                                frozen["source_sha"])

    def test_original_transaction_rollback_after_precommit_fault(self):
        self.native()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(
                    ShadowDenied, "INJECTED_AFTER_APPEND_PRECOMMIT_ROLLBACK"):
                self.reserve(inject_fault=True)
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(self.count(), 0)
            self.db.verify()
            self.assertEqual(self.reserve()["disposition"],
                             "ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST")
            self.assertEqual(self.count(), 1)

    def test_lost_post_commit_receipt_never_replays_on_cold_reopen(self):
        self.native()
        with SingleOwner(self.mutex):
            _discarded_receipt = self.reserve()
            cold = Database(self.db.filename)
            try:
                cold.verify()
                # Existing original mutex remains held by the same owner;
                # a lost response does not justify another provider call.
                repeat = reserve_original_intent_without_post(
                    cold, lane="Wingless", utc_day="2026-10-28",
                    owner_witness=lambda: True)
                self.assertEqual(repeat["disposition"],
                                 "BLOCKED_ALREADY_CONSUMED")
                self.assertEqual(cold.meta(), self.db.meta())
            finally:
                cold.close()

    def test_no_native_terminal_means_no_original_event(self):
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            r = self.reserve()
            self.assertEqual(r["disposition"],
                             "BLOCKED_NO_AUTHENTIC_NATIVE_TERMINAL")
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(self.count(), 0)

    def test_owner_mutex_and_witness_are_not_optional(self):
        self.native()
        before = self.db.meta().copy()
        with self.assertRaisesRegex(ShadowDenied, "MUTEX_NOT_HELD"):
            self.reserve()
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(ShadowDenied, "WITNESS_NOT_ATTESTED"):
                self.reserve(witness=lambda: False)
            with self.assertRaisesRegex(ShadowDenied, "WITNESS_NOT_ATTESTED"):
                self.reserve(witness=lambda: None)
        self.assertEqual(self.count(), 0)
        self.assertEqual(self.db.meta(), before)

    def test_original_old_free_attempt_spends_same_day_budget(self):
        self.fixture.original_spent_free_request()
        self.native()  # newer actual native evidence after old free request
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            r = self.reserve()
            self.assertEqual(
                r["disposition"], "BLOCKED_COMBINED_ORIGINAL_AND_V19_BUDGET")
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(self.count(), 0)
            self.db.verify()

    def test_original_free_attempt_after_terminal_blocks_stale_witness(self):
        self.native()
        self.fixture.original_spent_free_request()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            r = self.reserve()
            self.assertEqual(
                r["disposition"], "BLOCKED_NO_NEW_TERMINAL_AFTER_ORIGINAL_ATTEMPT")
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), before)

    def test_unauthorized_lane_or_utc_day_rejected_before_original_transaction(self):
        self.native()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_DB_OR_LANE"):
                self.reserve(lane="Invalid")
            with self.assertRaises(ShadowDenied):
                self.reserve(day="2026-02-30")
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(self.count(), 0)

    def test_no_network_or_external_provider_invoked(self):
        self.native()
        with SingleOwner(self.mutex):
            with patch(
                "f139.nci04_owner_free_reasoner_proposal.infer_free_once",
                side_effect=AssertionError("NEVER external provider")
            ), patch(
                "f139.local_controller.GitHub",
                side_effect=AssertionError("NEVER GitHub client")
            ):
                report = self.reserve()
            self.assertEqual(report["provider_requests"], 0)
            self.assertFalse(report["original_owner_request_authorized"])
            self.assertEqual(self.count(), 1)

    def test_corrupt_original_head_cannot_reserve(self):
        self.native()
        self.db.conn.execute(
            "UPDATE meta SET head_hash=? WHERE id=1", ("f" * 64,))
        with SingleOwner(self.mutex):
            with self.assertRaises(Exception):
                self.reserve()
            self.assertEqual(self.count(), 0)

    def test_current_original_owner_disabled_denies_but_does_not_insert(self):
        self.native()
        self.db.conn.execute("UPDATE meta SET enabled=0 WHERE id=1")
        with SingleOwner(self.mutex):
            r = self.reserve()
            self.assertEqual(r["disposition"],
                             "BLOCKED_ORIGINAL_OWNER_DISABLED_OR_BUSY")
            self.assertEqual(self.count(), 0)


if __name__ == "__main__":
    unittest.main()
