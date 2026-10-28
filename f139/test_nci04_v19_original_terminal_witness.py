"""V19 original-ledger read-only witness: authentic source-only fixture."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_terminal_witness import (
    ShadowDenied, project_original_native_terminal,
)
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from test_nci04_owner_ledger import LedgerTests


class OriginalWitnessTests(unittest.TestCase):
    def setUp(self):
        # Existing sealed-native-ledger test fixture; production original
        # SQLite is NEVER opened by the hosted CI acceptance path.
        fixture = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.lockfile = self.db.filename.with_suffix(".lock")

    def read(self, *, lane="Wingless", day="2026-10-28", attempts=None):
        if attempts is None:
            attempts = []
        return project_original_native_terminal(
            self.db, lane=lane, utc_day=day,
            hypothetical_v19_attempts=attempts)

    def test_mutex_required_even_on_empty_native_history(self):
        with self.assertRaisesRegex(ShadowDenied, "MUTEX_NOT_HELD"):
            self.read()
        self.assertFalse(SingleOwner.held(self.lockfile))

    def test_empty_history_is_no_request_and_no_event_changes(self):
        with SingleOwner(self.lockfile):
            before = self.db.meta().copy()
            result = self.read()
            self.assertEqual(result["disposition"],
                             "BLOCKED_NO_AUTHENTIC_NATIVE_TERMINAL")
            self.assertIsNone(result["shadow"])
            self.assertFalse(result["owner_request_authorized"])
            self.assertFalse(result["scientific_first_use"])
            self.assertEqual(result["provider_requests"], 0)
            self.assertEqual(result["ledger_mutations"], 0)
            self.assertEqual(result["source_mutations"], 0)
            self.assertEqual(self.db.meta()["head_hash"], before["head_hash"])
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"])

    def test_authenticated_admission_without_terminal_stays_blocked(self):
        activate_native(self.db, self.fixture.approval())
        admit_native_issue(self.db, self.fixture.native,
                           "2026-10-28T09:00:00Z")
        with SingleOwner(self.lockfile):
            before = self.db.meta()["head_hash"]
            self.assertEqual(self.read()["disposition"],
                             "BLOCKED_ORIGINAL_WORK_IN_FLIGHT")
            self.assertEqual(self.db.meta()["head_hash"], before)

    def test_reject_false_claimed_chain_by_database_type(self):
        class FakeDB:
            filename = Path("/tmp/fakedb.sqlite")
            def verify(self):
                raise AssertionError("fake db should never get verified")
        with self.assertRaisesRegex(ShadowDenied, "DATABASE_OR_LANE_INVALID"):
            project_original_native_terminal(
                FakeDB(), lane="Wingless", utc_day="2026-10-28",
                hypothetical_v19_attempts=[])

    def test_fail_closed_wrong_lane_and_corrupted_original_ledger(self):
        with SingleOwner(self.lockfile):
            with self.assertRaisesRegex(ShadowDenied, "DATABASE_OR_LANE_INVALID"):
                self.read(lane="Qualification")
            self.db.conn.execute(
                "UPDATE meta SET head_hash=? WHERE id=1", ("d"*64,))
            with self.assertRaises(Exception):
                self.read()

    def test_fresh_native_receipt_shadow_from_ledger_is_always_non_authorizing(self):
        # Real original SQLite transitions and native admission records,
        # though with fixed, isolated fixture identifiers/evidence.
        activate_native(self.db, self.fixture.approval())
        admit_native_issue(self.db, self.fixture.native,
                           "2026-10-28T09:00:00Z")
        self.db.claim(self.fixture.native.ticket, "2026-10-28T09:01:00Z")
        self.db.dispatch_observed(self.fixture.native.ticket)
        self.db.terminal(self.fixture.native.ticket, 98012345678,
                         "/tmp/f139-test-fixture-receipt", "e"*64)
        with SingleOwner(self.lockfile):
            before = self.db.meta().copy()
            r = self.read()
            self.assertEqual(r["disposition"],
                             "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED")
            self.assertIs(r["owner_request_authorized"], False)
            self.assertIs(r["worker_dispatched"], False)
            self.assertEqual(r["provider_requests"], 0)
            self.assertEqual(r["paid_model_calls"], 0)
            self.assertIs(r["scientific_first_use"], False)
            self.assertEqual(r["shadow"]["disposition"],
                             "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED")
            self.assertEqual(r["shadow"]["original_owner_request_authorized"], False)
            self.assertEqual(self.db.meta()["head_hash"], before["head_hash"])
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"])

    def test_no_silent_reuse_if_new_terminal_already_in_shadow_attempt(self):
        activate_native(self.db, self.fixture.approval())
        admit_native_issue(self.db, self.fixture.native,
                           "2026-10-28T09:00:00Z")
        self.db.claim(self.fixture.native.ticket, "2026-10-28T09:01:00Z")
        self.db.dispatch_observed(self.fixture.native.ticket)
        self.db.terminal(self.fixture.native.ticket, 98012345678,
                         "/tmp/f139-test-fixture-receipt", "e"*64)
        seq = self.db.conn.execute(
            "SELECT seq FROM events WHERE kind='PROVIDER_VERIFIED_TERMINAL' "
            "ORDER BY seq DESC LIMIT 1").fetchone()["seq"]
        attempts = [{
            "day": "2026-10-28", "lane": self.fixture.native.lane,
            "ticket": self.fixture.native.ticket,
            "terminal_seq": seq, "scope_sha256": "f"*64,
        }]
        with SingleOwner(self.lockfile):
            r = self.read(lane=self.fixture.native.lane, attempts=attempts)
            self.assertEqual(r["shadow"]["disposition"], "BLOCKED_ALREADY_CONSUMED")
            self.assertFalse(r["owner_request_authorized"])

    def test_tampered_terminal_digest_refused_before_shadow(self):
        activate_native(self.db, self.fixture.approval())
        admit_native_issue(self.db, self.fixture.native,
                           "2026-10-28T09:00:00Z")
        self.db.claim(self.fixture.native.ticket, "2026-10-28T09:01:00Z")
        self.db.dispatch_observed(self.fixture.native.ticket)
        self.db.terminal(self.fixture.native.ticket, 98012345678,
                         "/tmp/f139-test-fixture-receipt", "e"*64)
        self.db.conn.execute(
            "UPDATE tasks SET evidence_sha=? WHERE ticket=?",
            ("f"*64, self.fixture.native.ticket))
        with SingleOwner(self.lockfile):
            with self.assertRaises(Exception):
                self.read(lane=self.fixture.native.lane)

    def test_no_write_no_provider_network_even_if_shadow_says_eligible(self):
        activate_native(self.db, self.fixture.approval())
        admit_native_issue(self.db, self.fixture.native,
                           "2026-10-28T09:00:00Z")
        self.db.claim(self.fixture.native.ticket, "2026-10-28T09:01:00Z")
        self.db.dispatch_observed(self.fixture.native.ticket)
        self.db.terminal(self.fixture.native.ticket, 98012345678,
                         "/tmp/f139-test-fixture-receipt", "e"*64)
        with SingleOwner(self.lockfile):
            with patch("f139.local_controller.GitHub", side_effect=AssertionError(
                    "network transport must remain unused")):
                r=self.read(lane=self.fixture.native.lane)
            self.assertEqual(r["provider_requests"], 0)


if __name__ == "__main__":
    unittest.main()
