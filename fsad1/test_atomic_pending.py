"""FSA D1 atomic SQL protocol tests against real SQLite, not a fake D1 implementation.

These tests establish single-database concurrent write semantics. They are
NOT independent FSA credential custody, remote backup, D1 deployment,
cross-failure-domain authentication, signed receipts or science permission.
"""
from __future__ import annotations

import concurrent.futures
from contextlib import closing
import pathlib
import sqlite3
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
SCHEMA = (ROOT / "schema.sql").read_text(encoding="utf-8")
RESERVE = (ROOT / "reserve_pending.sql").read_text(encoding="utf-8")
READBACK = (ROOT / "readback.sql").read_text(encoding="utf-8")
H = lambda letter: letter * 64
CLAIM = (H("a"), H("b"), H("c"), "Wingless", H("d"), H("e"), 7, 11, H("f"))


class AtomicPendingFirstUse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(pathlib.Path(self.tmp.name) / "fsa.sqlite")
        with closing(self.open()) as db:
            db.executescript(SCHEMA)
            # TEST FIXTURE ONLY: these identities are not production attestations.
            db.execute(
                "INSERT INTO authority_state "
                "(singleton,archive_id,head_sha256,owner_epoch,"
                "ledger_generation,ledger_sha256,reservation_open)"
                " VALUES (1,?,?,?,?,?,1)", (H("d"), H("e"), 7, 11, H("f"))
            )

    def open(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def attempt(self, claim=CLAIM):
        with closing(self.open()) as db:
            try:
                return db.execute(RESERVE, claim).fetchall()
            except sqlite3.IntegrityError:
                return "INTEGRITY_CONFLICT_NO_RETRY"

    def test_exact_single_pending_reservation_and_non_authorizing_readback(self):
        rows = self.attempt()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][-1], "RESERVED_PENDING_INDEPENDENT_WITNESS")
        self.assertEqual(self.attempt(), [])
        with closing(self.open()) as db:
            row = db.execute(READBACK, (H("a"),)).fetchone()
            self.assertEqual(row, rows[0])
            self.assertEqual(
                db.execute("SELECT reservation_open,reservation_sequence "
                           "FROM authority_state").fetchone(), (0, 1)
            )

    def test_global_slot_prevents_other_lane_on_stale_ledger(self):
        self.assertEqual(len(self.attempt()), 1)
        other = (H("1"), H("2"), H("3"), "Yggdrasil", *CLAIM[4:])
        self.assertEqual(self.attempt(other), [])
        with closing(self.open()) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM original_firstuse").fetchone()[0], 1)

    def test_frozen_authority_drift_never_reserves(self):
        for index, value in (
            (4, H("0")), (5, H("0")), (6, 8),
            (7, 12), (8, H("0"))
        ):
            with self.subTest(parameter=index):
                c = list(CLAIM)
                c[index] = value
                self.assertEqual(self.attempt(tuple(c)), [])
        with closing(self.open()) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM original_firstuse").fetchone()[0], 0)
            self.assertEqual(db.execute(
                "SELECT reservation_open,reservation_sequence "
                "FROM authority_state").fetchone(), (1, 0))

    def test_concurrent_claims_across_both_lanes_only_one_wins(self):
        barrier = threading.Barrier(16)
        def competitor(i):
            claim = (f"{i + 1:064x}", f"{i + 40:064x}", f"{i + 80:064x}",
                     "Wingless" if i % 2 else "Yggdrasil", *CLAIM[4:])
            barrier.wait(timeout=10)
            return self.attempt(claim)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            outcomes = list(pool.map(competitor, range(16)))
        self.assertEqual(sum(isinstance(x, list) and len(x) == 1
                             for x in outcomes), 1)
        self.assertEqual(sum(x == [] for x in outcomes), 15)
        with closing(self.open()) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM original_firstuse").fetchone()[0], 1)
            self.assertEqual(db.execute(
                "SELECT reservation_sequence FROM authority_state").fetchone()[0], 1)

    def test_reopening_with_new_test_epoch_cannot_reuse_consumed_cohort(self):
        self.assertEqual(len(self.attempt()), 1)
        with closing(self.open()) as db:
            # TEST FIXTURE ONLY. Actual state refresh requires independent FSA
            # authentication and external signed ledger reconciliation.
            db.execute(
                "UPDATE authority_state SET reservation_open=1,"
                "ledger_generation=12,head_sha256=?,ledger_sha256=?",
                (H("1"), H("2"))
            )
        replay = list(CLAIM)
        replay[5], replay[7], replay[8] = H("1"), 12, H("2")
        self.assertEqual(self.attempt(tuple(replay)),
                         "INTEGRITY_CONFLICT_NO_RETRY")
        with closing(self.open()) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM original_firstuse").fetchone()[0], 1)
            self.assertEqual(db.execute(
                "SELECT reservation_open FROM authority_state").fetchone()[0], 1)

    def test_unknown_lane_or_bad_identity_is_never_committed(self):
        for change in [
            (3, "Qualification"), (0, "not-a-hash"), (6, 0)
        ]:
            modified = list(CLAIM)
            modified[change[0]] = change[1]
            self.assertEqual(self.attempt(tuple(modified)),
                             "INTEGRITY_CONFLICT_NO_RETRY")
        with closing(self.open()) as db:
            self.assertEqual(db.execute(
                "SELECT reservation_open,reservation_sequence "
                "FROM authority_state").fetchone(), (1, 0))

    def test_reopened_file_preserves_pending_claim_after_disconnect(self):
        self.assertEqual(len(self.attempt()), 1)
        with closing(self.open()) as db:
            self.assertEqual(db.execute(
                "SELECT state FROM original_firstuse WHERE cohort_sha256=?",
                (H("a"),)).fetchone()[0],
                "RESERVED_PENDING_INDEPENDENT_WITNESS")
        self.assertEqual(self.attempt(), [])


if __name__ == "__main__":
    unittest.main()
