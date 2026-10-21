"""A6 original SQLite native intake/replay tests; isolated fixture only."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from f139.local_controller import Database, hash_bytes, run_once
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_owner_ledger import (
    NativeLedgerDenied, audit_native_events, admit_native_issue,
    frozen_native_issue, KIND)
from test_nci04_owner_issue import issue as make_issue, MAIN, TARGET, TREE, HMAC


class LedgerTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix="f139-a6-ledger-")
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.path = self.root / "state.sqlite"
        self.db = Database.initialize(self.path, MAIN)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        # Fixture is intentionally NOT the real historic chain. Override
        # just the sealed anchor in this isolated test; production never may.
        for i in range(39):
            with self.db.transaction():
                self.db.event("FIXTURE_UNTRUSTED", {"fixture_sequence": i})
        seq23 = self.db.conn.execute("SELECT sha FROM events WHERE seq=23").fetchone()["sha"]
        patcher = mock.patch("f139.nci04_owner_ledger.SEALED_OWNER_PREFIX_HEAD", seq23)
        patcher.start()
        self.addCleanup(patcher.stop)
        for lane, ticket in (
            ("Qualification", "f139-d2c-qualification-659bb1f4d751"),
            ("Wingless", "f139-d2c-wingless-659bb1f4d751"),
            ("Wingless", "f139-d2j-wingless-5a252f8dde24"),
            ("Yggdrasil", "f139-d2j-yggdrasil-5a252f8dde24"),
            ("Wingless", "f139-d2k-i687-5a252f8dde24-5a2ecddb"),
            ("Yggdrasil", "f139-d2k-i688-5a252f8dde24-02ded761"),
        ):
            rid = 39513293606 if "i687" in ticket else (
                39513381790 if "i688" in ticket else 42)
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,'VERIFIED',?,?,?,?)",
                (ticket, lane, MAIN, "c"*64, rid, "/dev/fixture-only", "d"*64))
        self.native = inspect_owner_issue(
            make_issue(), protected_main=MAIN,
            authenticated_target_commit=TARGET, authenticated_target_tree=TREE)
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_admit_exactly_once_and_verify_original_ledger(self):
        before = self.db.meta()["head_seq"]
        self.assertTrue(admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z"))
        self.assertEqual(self.db.meta()["head_seq"], before + 2)
        self.db.verify()
        tasks = [dict(x) for x in self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?", (self.native.ticket,))]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["stage"], "READY")
        recovered = frozen_native_issue(self.db, self.native.ticket)
        self.assertEqual(recovered.intent_raw, self.native.intent_raw)
        self.assertEqual(recovered.candidate.qualification_key,
                         self.native.qualification_key)
        self.assertFalse(admit_native_issue(self.db, self.native, "2026-10-21T10:05:00Z"))
        self.assertEqual(self.db.meta()["head_seq"], before + 2)
        reopened = Database(self.path)
        reopened.verify()
        reopened.close()

    def test_cross_source_and_same_issue_number_rejected(self):
        with self.assertRaisesRegex(NativeLedgerDenied, "SOURCE_OR_DAY_DRIFT"):
            altered = inspect_owner_issue(
                make_issue(), protected_main=MAIN,
                authenticated_target_commit=TARGET, authenticated_target_tree=TREE)
            from dataclasses import replace
            altered = replace(altered, source_sha="9"*40)
            admit_native_issue(self.db, altered, "2026-10-21T10:00:00Z")
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_original_23_event_pin_absent_fails_closed(self):
        with mock.patch("f139.nci04_owner_ledger.SEALED_OWNER_PREFIX_HEAD", "9"*64):
            with self.assertRaisesRegex(NativeLedgerDenied, "ORIGINAL_23_EVENT_PIN_DRIFT"):
                admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z")
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_original_d2k_local_runs_required(self):
        self.db.conn.execute(
            "UPDATE tasks SET run_id=999 WHERE ticket LIKE 'f139-d2k-i688-%'")
        with self.assertRaisesRegex(NativeLedgerDenied, "D2K_LOCAL_CUSTODY_NOT_VERIFIED"):
            admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z")

    def test_native_history_source_tampering_fails_closed(self):
        self.assertTrue(admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z"))
        self.db.conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket=?",
                             ("e"*64, self.native.ticket))
        with self.assertRaisesRegex(NativeLedgerDenied, "TASK_ADMISSION_MISMATCH"):
            self.db.verify()

    def test_reject_native_intent_event_deletion(self):
        self.assertTrue(admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z"))
        with self.assertRaises(Exception):
            self.db.conn.execute("DELETE FROM events WHERE kind=?", (KIND,))

    def test_owner_legacy_scheduler_keeps_native_gate_inert(self):
        class NoNativeProvider:
            def protected_main(self): return MAIN
            def d2k_eligible_issues(self, source): return []
            def native_eligible_issues(self, source):
                raise AssertionError("production must NOT inspect native issues")
        result = run_once(self.db, NoNativeProvider(), self.path, HMAC,
                          now="2026-10-21T10:00:00Z")
        self.assertEqual(result["disposition"], "QUEUE_EMPTY_NO_SCIENCE")
        self.assertEqual(self.db.meta()["head_seq"], 40)

    def test_no_second_pending_work(self):
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,'READY',?)",
            ("f139-existing-ready-task", "Wingless", MAIN, "a"*64))
        with self.assertRaisesRegex(NativeLedgerDenied, "OTHER_WORK_PENDING"):
            admit_native_issue(self.db, self.native, "2026-10-21T10:00:00Z")


if __name__ == "__main__":
    unittest.main()
