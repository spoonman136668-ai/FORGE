"""Atomic V19 free-request reservation rehearsal; no actual provider calls."""
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139.nci04_v19_atomic_reservation_rehearsal import (
    ShadowDenied, new_rehearsal, reserve_simulated, rows,
)
from test_nci04_v19_original_terminal_witness import OriginalWitnessTests


class V19AtomicRehearsalTests(unittest.TestCase):
    def setUp(self):
        source = OriginalWitnessTests(
            "test_empty_history_is_no_request_and_no_event_changes")
        source.setUp()
        self.addCleanup(source.doCleanups)
        self.source = source
        self.db = source.db
        self.mutex = self.db.filename.with_suffix(".lock")
        self.lab = new_rehearsal()
        self.addCleanup(self.lab.close)

    def genuine_terminal(self):
        activate_native(self.db, self.source.fixture.approval())
        issue = self.source.fixture.native
        self.assertEqual(issue.lane, "Wingless")
        self.assertTrue(admit_native_issue(
            self.db, issue, "2026-10-28T09:00:00Z"))
        self.db.claim(issue.ticket, "2026-10-28T09:01:00Z")
        self.db.dispatch_observed(issue.ticket)
        self.db.terminal(issue.ticket, 98012345678,
                         "/tmp/f139-v19-test-only-evidence", "e" * 64)

    def reserve(self, *, day="2026-10-28", lane="Wingless", abort=False):
        return reserve_simulated(
            self.db, self.lab, lane=lane, utc_day=day,
            abort_before_commit=abort)

    def test_authenticated_terminal_yields_one_atomic_simulation_only(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            report = self.reserve()
            self.assertEqual(report["disposition"],
                             "IN_MEMORY_ATOMIC_RESERVATION_ONLY_NO_POST")
            self.assertTrue(report["simulated_in_memory_reservation"])
            self.assertEqual(report["simulation_attempt_count"], 1)
            self.assertEqual(len(report["scope_sha256"]), 64)
            self.assertFalse(report["original_owner_request_authorized"])
            self.assertFalse(report["scientific_first_use"])
            self.assertFalse(report["worker_dispatched"])
            self.assertEqual(report["provider_requests"], 0)
            self.assertEqual(report["paid_model_calls"], 0)
            self.assertEqual(report["real_original_ledger_events_written"], 0)
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(len(rows(self.lab, self.db)), 1)
            self.assertEqual(rows(self.lab, self.db)[0]["ticket"],
                             self.source.fixture.native.ticket)

    def test_duplicate_terminal_and_utc_rollover_cannot_replay(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            self.reserve()
            before = self.db.meta()["head_hash"]
            second = self.reserve()
            self.assertEqual(second["disposition"],
                             "BLOCKED_ALREADY_CONSUMED")
            tomorrow = self.reserve(day="2026-10-29")
            self.assertEqual(tomorrow["disposition"],
                             "BLOCKED_ALREADY_CONSUMED")
            self.assertEqual(len(rows(self.lab, self.db)), 1)
            self.assertEqual(self.db.meta()["head_hash"], before)

    def test_failed_precommit_simulation_rolls_back_without_partial_record(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            original = self.db.meta()["head_hash"]
            with self.assertRaisesRegex(ShadowDenied,
                                         "INJECTED_PRECOMMIT_ROLLBACK"):
                self.reserve(abort=True)
            self.assertEqual(len(rows(self.lab, self.db)), 0)
            self.assertFalse(self.lab.in_transaction)
            self.assertEqual(self.db.meta()["head_hash"], original)
            self.assertTrue(self.reserve()["simulated_in_memory_reservation"])
            self.assertEqual(len(rows(self.lab, self.db)), 1)

    def test_append_only_attempts_refuse_update_and_delete(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            self.reserve()
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "V19_REHEARSAL_APPEND_ONLY"):
                self.lab.execute("UPDATE attempts SET day='2026-11-01'")
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "V19_REHEARSAL_APPEND_ONLY"):
                self.lab.execute("DELETE FROM attempts")
            self.assertEqual(len(rows(self.lab, self.db)), 1)

    def test_original_owner_sqlite_connection_never_accepts_rehearsal_writes(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied, "WRONG_CONNECTION"):
                reserve_simulated(
                    self.db, self.db.conn, lane="Wingless",
                    utc_day="2026-10-28")
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(len(rows(self.lab, self.db)), 0)

    def test_other_file_backed_sqlite_rejected_even_if_controller_is_locked(self):
        self.genuine_terminal()
        with tempfile.TemporaryDirectory(prefix="v19-other-db-") as root:
            other = sqlite3.connect(str(Path(root) / "unsafe.sqlite"),
                                    isolation_level=None)
            try:
                with SingleOwner(self.mutex):
                    with self.assertRaisesRegex(
                            ShadowDenied, "PERSISTENT_OR_ATTACHED_DATABASE_FORBIDDEN"):
                        reserve_simulated(self.db, other, lane="Wingless",
                                          utc_day="2026-10-28")
            finally:
                # On Windows, close the SQLite file before TemporaryDirectory
                # tries to remove it; do not mask the actual gate outcome.
                other.close()

    def test_mutex_required_and_original_disabled_is_not_eligibility(self):
        self.genuine_terminal()
        with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_MUTEX_REQUIRED"):
            self.reserve()
        self.db.conn.execute("UPDATE meta SET enabled=0 WHERE id=1")
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_OWNER_DISABLED"):
                self.reserve()
        self.assertEqual(len(rows(self.lab, self.db)), 0)

    def test_no_terminal_or_busy_owner_never_reserves(self):
        with SingleOwner(self.mutex):
            r = self.reserve()
            self.assertEqual(r["disposition"],
                             "BLOCKED_NO_AUTHENTIC_NATIVE_TERMINAL")
            self.assertFalse(r["simulated_in_memory_reservation"])
            self.assertEqual(len(rows(self.lab, self.db)), 0)
        activate_native(self.db, self.source.fixture.approval())
        admit_native_issue(self.db, self.source.fixture.native,
                           "2026-10-28T09:00:00Z")
        with SingleOwner(self.mutex):
            r = self.reserve()
            self.assertEqual(r["disposition"],
                             "BLOCKED_ORIGINAL_WORK_IN_FLIGHT")
            self.assertEqual(len(rows(self.lab, self.db)), 0)

    def test_no_network_transport_needed_or_permitted(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            with patch("f139.local_controller.GitHub",
                       side_effect=AssertionError("no provider/network")):
                report = self.reserve()
        self.assertEqual(report["provider_requests"], 0)
        self.assertFalse(report["original_owner_request_authorized"])

    def test_owner_chain_corruption_blocks_atomic_reservation(self):
        self.genuine_terminal()
        self.db.conn.execute(
            "UPDATE meta SET head_hash=? WHERE id=1", ("f" * 64,))
        with SingleOwner(self.mutex):
            with self.assertRaises(Exception):
                self.reserve()
            self.assertEqual(len(rows(self.lab, self.db)), 0)

    def test_missing_or_invalid_utc_day_does_not_open_transaction(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            for day in ("2026-02-30", "2026-10-28abc", "2026-2-8"):
                with self.subTest(day=day), self.assertRaises(ShadowDenied):
                    self.reserve(day=day)
            self.assertFalse(self.lab.in_transaction)

    def test_simulation_digest_has_no_hidden_authority(self):
        self.genuine_terminal()
        with SingleOwner(self.mutex):
            self.reserve()
            record = rows(self.lab, self.db)[0]
            self.assertEqual(len(record["event_sha256"]), 64)
            self.assertEqual(record["prior_sha256"], "0" * 64)
            self.assertEqual(record["scope_sha256"],
                             self.reserve()["scope_sha256"])
        self.assertFalse(self.lab.in_transaction)


if __name__ == "__main__":
    unittest.main()
