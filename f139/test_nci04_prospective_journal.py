"""Real SQLite ordering/rollback/restart; reused untrusted owner fixtures only."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from f139 import test_nci04_owner_ledger as owner_fixture
from f139.local_controller import Database, run_once
from f139.nci04_owner_ledger import admit_native_issue, activate_native
from f139.nci04_prospective_journal import (
    KIND, journal_native_assignment, audit_assignment_event,
)
from test_nci04_owner_issue import MAIN, HMAC, TARGET, TREE, issue, inspect

NOW = "2026-11-03T12:00:00.123456Z"


class ProspectiveJournalTests(unittest.TestCase):
    def setUp(self):
        fixture = owner_fixture.LedgerTests(
            "test_admit_exactly_once_and_verify_original_ledger")
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        self.fixture = fixture
        self.db, self.path, self.native = fixture.db, fixture.path, fixture.native
        activate_native(self.db, fixture.approval())
        admit_native_issue(self.db, self.native, NOW)

    def capture(self):
        self.db.claim(self.native.ticket, NOW, archive_native_decision=True)
        return self.db.conn.execute(
            "SELECT * FROM events WHERE kind=?", (KIND,)).fetchone()

    def test_atomic_order_survives_real_cold_reopen(self):
        row = self.capture()
        result = audit_assignment_event(self.db, row)
        self.assertTrue(result["local_prestart_order_verified"])
        self.assertFalse(result["decision_time_independently_proven"])
        self.assertFalse(result["optimizer_training_authorized"])
        self.assertFalse(result["dispatch_authorized"])
        with sqlite3.connect(self.path) as other:
            self.assertEqual(other.execute(
                "SELECT stage FROM tasks WHERE ticket=?",
                (self.native.ticket,)).fetchone()[0], "START_RISK")
        reopened = Database(self.path)
        self.addCleanup(reopened.close)
        reopened.verify()
        self.assertEqual(reopened.meta(), self.db.meta())

    def test_claim_failure_rolls_back_assignment_and_start(self):
        before = self.db.meta()
        original = self.db.event
        def fail_claim(kind, payload):
            if kind == "BEFORE_DISPATCH_INTENT":
                raise RuntimeError("injected claim failure")
            return original(kind, payload)
        with patch.object(self.db, "event", side_effect=fail_claim):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.capture()
        self.assertEqual(self.db.meta(), before)
        self.assertEqual(self.db.ready()["ticket"], self.native.ticket)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)).fetchone()[0], 0)

    def test_reclaim_does_not_duplicate_or_replay(self):
        self.capture()
        before = self.db.meta()
        with self.assertRaises(Exception):
            self.capture()
        self.assertEqual(self.db.meta(), before)

    def test_no_standalone_journal_write(self):
        with self.assertRaisesRegex(ValueError, "TRANSACTION_REQUIRED"):
            journal_native_assignment(self.db, self.native.ticket, NOW)

    def test_started_candidate_excluded_from_successor_menu(self):
        self.capture()
        raw = issue("Yggdrasil")
        raw["number"], raw["id"] = 703, raw["id"] + 1
        second = inspect(raw)
        admit_native_issue(self.db, second, NOW)
        self.db.claim(second.ticket, NOW, archive_native_decision=True)
        row = self.db.conn.execute(
            "SELECT * FROM events WHERE kind=? ORDER BY seq DESC LIMIT 1", (KIND,)).fetchone()
        payload = json.loads(row["payload"])
        self.assertEqual([r["ticket"] for r in payload["eligible_native_ready"]],
                         [second.ticket])
        self.assertEqual(payload["assignment"]["selection_probability_bp"], 10000)
        self.assertEqual(payload["assignment"]["lane"], "Yggdrasil")
        audit_assignment_event(self.db, row)
        self.db.verify()

    def test_wrong_order_or_unjournaled_ready_fails_closed(self):
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,'READY',?)",
            ("f139-nci04-aaa", "Wingless", MAIN, "a"*64))
        before = self.db.meta()
        with self.assertRaisesRegex(ValueError, "SELECTION_ORDER"):
            self.capture()
        self.assertEqual(self.db.meta(), before)

    def test_historical_menu_tampering_rejected_even_with_rehashed_payload(self):
        row = dict(self.capture())
        payload = json.loads(row["payload"])
        payload["eligible_native_ready"][0]["candidate_sha256"] = "f"*64
        row["payload"] = json.dumps(payload)
        with self.assertRaisesRegex(ValueError, "HISTORICAL_MENU_OR_POLICY_DRIFT"):
            audit_assignment_event(self.db, row)

    def test_missing_adjacent_start_is_rejected(self):
        row = dict(self.capture())
        row["seq"] += 20
        with self.assertRaises(ValueError):
            audit_assignment_event(self.db, row)

    def test_ordinary_tick_commits_journal_before_provider_callback(self):
        observed = []
        outer = self
        class Provider:
            def protected_main(self): return MAIN
            def dispatch_native(self, fields, record):
                with sqlite3.connect(outer.path) as conn:
                    kinds = [r[0] for r in conn.execute(
                        "SELECT kind FROM events ORDER BY seq DESC LIMIT 2")]
                outer.assertEqual(kinds, ["BEFORE_DISPATCH_INTENT", KIND])
                outer.assertFalse(outer.db.conn.in_transaction)
                observed.append(record.ticket)
        result = run_once(self.db, Provider(), self.path, HMAC, now=NOW)
        self.assertEqual(result["disposition"], "DEVELOPMENT_DISPATCHED_ONCE")
        self.assertEqual(observed, [self.native.ticket])


if __name__ == "__main__":
    unittest.main()
