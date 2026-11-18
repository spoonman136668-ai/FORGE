"""V54 synthetic read-only negatives; NOT a real Windows owner readback."""
from __future__ import annotations

import json
import sqlite3
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.nci04_v54_original_owner_readonly_preflight import (
    SOURCE, ANCHOR_SEQ, ANCHOR_SHA, PREVIOUS_SCHEMA,
    ReadonlyPreflightDenied, inspect_owner,
)

TARGET = "a" * 40


class V54Preflight(unittest.TestCase):
    def setUp(self):
        self.db = object.__new__(Database)
        self.db._readonly_opened = True
        c = sqlite3.connect(":memory:", isolation_level=None)
        c.row_factory = sqlite3.Row
        self.db.conn = c
        c.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY,"
                  "kind TEXT,sha TEXT,payload TEXT)")
        c.execute("CREATE TABLE tasks(ticket TEXT,lane TEXT,source_sha TEXT,"
                  "stage TEXT,manifest_sha TEXT,run_id INTEGER,"
                  "evidence_dir TEXT,evidence_sha TEXT,"
                  "quarantine_reason TEXT,started_at TEXT)")
        c.execute("INSERT INTO events VALUES(1840,'SOURCE_TRANSITION_ADMITTED',?,?)",
                  ("b"*64, json.dumps({
                      "schema":PREVIOUS_SCHEMA,
                      "from_source_sha":"2ea68f93cbe6323aa6b0cbe99e47a32f0717b04c",
                      "to_source_sha":SOURCE})))
        c.execute("INSERT INTO events VALUES(1847,'PROVIDER_VERIFIED_TERMINAL',?,?)",
                  (ANCHOR_SHA,"{}"))
        c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                  ("t1","Wingless",SOURCE,"VERIFIED","c"*64,2,"sealed","d"*64,None,None))
        c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                  ("t2","Yggdrasil",SOURCE,"QUARANTINED","e"*64,None,
                   None,None,"retained",None))
        c.execute("PRAGMA query_only=ON")
        self.meta = dict(source_sha=SOURCE,enabled=1,legacy_suspended=1,
                         head_seq=ANCHOR_SEQ,head_hash=ANCHOR_SHA)
        for item in (
            patch.object(Database,"verify",return_value=None),
            patch.object(Database,"meta",side_effect=lambda:dict(self.meta)),
            patch("f139.nci04_v54_original_owner_readonly_preflight.verify_native_activation",
                  return_value=True),
            patch("f139.nci04_v54_original_owner_readonly_preflight.custodied_ids",
                  return_value=frozenset()),
        ):
            item.start()
            self.addCleanup(item.stop)
        self.addCleanup(c.close)

    def test_advisory_pure_idempotent_snapshot(self):
        before = self.db.conn.total_changes
        first = inspect_owner(self.db,proposed_source=TARGET)
        second = inspect_owner(self.db,proposed_source=TARGET)
        self.assertEqual(first,second)
        self.assertEqual(first["verified_ancestor_seq"],ANCHOR_SEQ)
        self.assertEqual(first["quarantined_task_count"],1)
        self.assertFalse(first["release_authorized"])
        self.assertEqual(first["owner_mutations"],0)
        self.assertEqual(before,self.db.conn.total_changes)
        self.assertFalse(self.db.conn.in_transaction)

    def test_valid_later_source_stable_history_is_not_stale(self):
        self.meta["head_seq"] = ANCHOR_SEQ+1
        self.meta["head_hash"] = "f"*64
        got = inspect_owner(self.db,proposed_source=TARGET)
        self.assertEqual(got["observed_event_head_seq"],ANCHOR_SEQ+1)
        self.assertEqual(got["verified_ancestor_sha256"],ANCHOR_SHA)

    def test_wrong_source_head_or_replay_denied(self):
        for field,other in (
            ("source_sha","f"*40),("enabled",0),
            ("legacy_suspended",0),("head_seq",1846),
        ):
            prior = self.meta[field]
            self.meta[field] = other
            with self.subTest(field=field), self.assertRaises(ReadonlyPreflightDenied):
                inspect_owner(self.db,proposed_source=TARGET)
            self.meta[field] = prior
        for proposed in (SOURCE,
                         "2ea68f93cbe6323aa6b0cbe99e47a32f0717b04c",
                         "bad"):
            with self.subTest(proposed=proposed), self.assertRaises(ReadonlyPreflightDenied):
                inspect_owner(self.db,proposed_source=proposed)

    def test_corrupt_event_and_open_task_denied(self):
        c=self.db.conn
        c.execute("PRAGMA query_only=OFF")
        c.execute("UPDATE events SET sha=? WHERE seq=?",("0"*64,ANCHOR_SEQ))
        c.execute("PRAGMA query_only=ON")
        with self.assertRaises(ReadonlyPreflightDenied):
            inspect_owner(self.db,proposed_source=TARGET)
        c.execute("PRAGMA query_only=OFF")
        c.execute("UPDATE events SET sha=? WHERE seq=?",(ANCHOR_SHA,ANCHOR_SEQ))
        c.execute("UPDATE tasks SET stage='READY' WHERE ticket='t2'")
        c.execute("PRAGMA query_only=ON")
        with self.assertRaises(ReadonlyPreflightDenied):
            inspect_owner(self.db,proposed_source=TARGET)

    def test_readonly_connection_and_fresh_transaction_required(self):
        self.db._readonly_opened=False
        with self.assertRaises(ReadonlyPreflightDenied):
            inspect_owner(self.db,proposed_source=TARGET)
        self.db._readonly_opened=True
        c=self.db.conn
        c.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ReadonlyPreflightDenied):
            inspect_owner(self.db,proposed_source=TARGET)
        c.execute("PRAGMA query_only=ON")
        c.execute("BEGIN")
        try:
            with self.assertRaises(ReadonlyPreflightDenied):
                inspect_owner(self.db,proposed_source=TARGET)
        finally:
            c.execute("ROLLBACK")

    def test_unsealed_model_attempt_and_unreviewed_transition_denied(self):
        c=self.db.conn
        c.execute("PRAGMA query_only=OFF")
        c.execute("INSERT INTO events VALUES(1,'MODEL_DRAFT_ATTEMPTED',?,?)",
                  ("f"*64,"{}"))
        c.execute("PRAGMA query_only=ON")
        with self.assertRaises(ReadonlyPreflightDenied):
            inspect_owner(self.db,proposed_source=TARGET)
        c.execute("PRAGMA query_only=OFF")
        c.execute("DELETE FROM events WHERE seq=1")
        c.execute("UPDATE events SET payload=? WHERE seq=1840",
                  (json.dumps({"schema":"unreviewed",
                               "to_source_sha":SOURCE}),))
        c.execute("PRAGMA query_only=ON")
        with self.assertRaises(ReadonlyPreflightDenied):
            inspect_owner(self.db,proposed_source=TARGET)

    def test_current_original_event1847_154_verified_56_negatives(self):
        """Today's 210 real terminal-task counts must remain readable on V54.

        Older V51's exact 153/56 assumption is obsolete. Positive and negative
        original custody must not be inferred from synthetic fixtures: the real
        owner still requires Database.verify() against its immutable events.
        """
        conn = self.db.conn
        conn.execute("PRAGMA query_only=OFF")
        positives = [
            (f"v{i:03d}", "Wingless", SOURCE, "VERIFIED", "c"*64,
             2000+i, "sealed", "d"*64, None, None)
            for i in range(153)
        ]
        negatives = [
            (f"q{i:03d}", "Yggdrasil", SOURCE, "QUARANTINED",
             "e"*64, None, None, None, "preserved", None)
            for i in range(55)
        ]
        conn.executemany("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                         positives + negatives)
        conn.execute("PRAGMA query_only=ON")
        report = inspect_owner(self.db, proposed_source=TARGET)
        self.assertEqual(report["verified_ancestor_seq"], 1847)
        self.assertEqual(report["verified_task_count"], 154)
        self.assertEqual(report["quarantined_task_count"], 56)
        self.assertEqual(report["terminal_task_count"], 210)
        self.assertFalse(report["release_authorized"])
        self.assertEqual(report["owner_mutations"], 0)

    def test_no_live_owner_write_or_new_scheduler_interface(self):
        import inspect
        from f139 import nci04_v54_original_owner_readonly_preflight as m
        source=inspect.getsource(m)
        for forbidden in ("Register-ScheduledTask", "Set-ScheduledTask",
                          "UPDATE meta SET", "gh api --method POST",
                          "def release(", "def install(", "def publish("):
            self.assertNotIn(forbidden,source)
        self.assertIn('conn.execute("BEGIN")',source)
        self.assertIn('conn.execute("ROLLBACK")',source)


if __name__ == "__main__":
    unittest.main()
