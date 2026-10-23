"""F139 bounded 24/7 native-development throughput, isolated original DB fixture.

Tests never touch real original owner SQLite, GitHub dispatch, protected
science source, paid APIs, controller process or active scheduler.
"""
import sqlite3
import unittest

from f139.local_controller import F139Error
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_owner_ledger import (
    NativeLedgerDenied, admit_native_issue, native_recent_starts,
    MAX_DAILY, MAX_STARTS_PER_WINDOW)
from test_nci04_owner_issue import issue as make_issue, MAIN, TARGET, TREE
from test_nci04_owner_ledger import LedgerTests


class CadenceTests(unittest.TestCase):
    def setUp(self):
        # The established native ledger test fixture has six authentic sealed
        # historical development-task identities and no LIVE controller.
        self.owner = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.db = self.owner.db

    def issue(self, n):
        raw = make_issue()
        raw["number"] = n
        raw["id"] = 5951234500 + n
        return inspect_owner_issue(
            raw, protected_main=MAIN,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TREE)

    def complete(self, n, timestamp):
        record = self.issue(n)
        self.assertTrue(admit_native_issue(self.db, record, timestamp))
        self.db.claim(record.ticket, timestamp)
        self.db.dispatch_observed(record.ticket)
        self.db.terminal(record.ticket, 50000000000+n,
                         "/fixture-only/never-prod", "d"*64)
        self.db.verify()
        return record

    def test_two_starts_per_rolling_ten_minutes_and_no_silent_abort(self):
        self.complete(810, "2026-10-22T10:00:00Z")
        self.complete(811, "2026-10-22T10:04:00Z")
        before = self.db.meta()["head_hash"]
        # Third admission must defer, NOT throw, consume an issue, alter the
        # event ledger, or accidentally dispatch a duplicate worker.
        self.assertFalse(admit_native_issue(
            self.db, self.issue(812), "2026-10-22T10:09:59Z"))
        self.assertEqual(self.db.meta()["head_hash"], before)
        self.assertEqual(native_recent_starts(
            self.db, "2026-10-22T10:09:59Z"), 2)
        self.complete(812, "2026-10-22T10:10:00Z")
        self.assertEqual(native_recent_starts(
            self.db, "2026-10-22T10:10:00Z"), 2)
        self.assertEqual(MAX_STARTS_PER_WINDOW, 2)
        self.assertEqual(MAX_DAILY, 288)

    def test_no_twenty_total_expiration_and_day_boundary(self):
        # A previously consumed, old-source historical native ledger should
        # not permanently cap all future owner development intake at 20.
        for n in range(810, 831):
            self.complete(n, "2026-10-21T00:00:00Z" if n==810
                          else "2026-10-21T%02d:00:00Z" % (n-810))
        self.assertEqual(len([
            row for row in self.db.conn.execute(
                "SELECT ticket FROM tasks WHERE ticket LIKE 'f139-nci04-%'")]),21)
        self.complete(900, "2026-10-22T00:00:01Z")
        self.assertEqual(native_recent_starts(
            self.db,"2026-10-22T00:00:01Z"),1)

    def test_clock_reversal_fails_closed(self):
        self.complete(810, "2026-10-22T10:03:00Z")
        with self.assertRaisesRegex(
                NativeLedgerDenied,"NATIVE_CADENCE_CLOCK_MOVED_BACKWARD"):
            native_recent_starts(self.db,"2026-10-22T10:02:59Z")

    def test_existing_claim_guards_cannot_start_a_third(self):
        self.complete(810,"2026-10-22T10:01:00Z")
        self.complete(811,"2026-10-22T10:02:00Z")
        # If another caller inserts an authenticated pending READY ticket,
        # the claim limiter still independently rejects a third start.
        work=self.issue(812)
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,'READY',?)",
            (work.ticket,work.lane,work.source_sha,"a"*64))
        with self.assertRaisesRegex(
                F139Error,"NATIVE_TWO_PER_TEN_MINUTES_LIMIT"):
            self.db.claim(work.ticket,"2026-10-22T10:05:00Z")
        rec=self.db.conn.execute(
            "SELECT stage,started_at FROM tasks WHERE ticket=?",
            (work.ticket,)).fetchone()
        self.assertEqual(rec["stage"],"READY")
        self.assertIsNone(rec["started_at"])


if __name__ == "__main__":
    unittest.main()
