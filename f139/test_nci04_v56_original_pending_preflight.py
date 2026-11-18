"""Synthetic, non-owner V56 original pending-carry preflight controls."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_v56_original_pending_preflight import (
    SOURCE, TICKET, ANCHOR_SEQ, ANCHOR_SHA,
    ADMISSION_SHA, NATIVE_ACTIVATION_SHA, READY_SOURCE_TRANSITION_SHA,
    V56ReadOnlyDenied, original_pending_snapshot,
)


class V56OriginalPendingReadOnly(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="f139-v56-carry-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "f139-v56-detached.sqlite"
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE meta (source_sha TEXT, enabled INTEGER,
                legacy_suspended INTEGER, head_seq INTEGER, head_hash TEXT);
            CREATE TABLE events (seq INTEGER, kind TEXT, sha TEXT, payload TEXT);
            CREATE TABLE tasks (ticket TEXT, lane TEXT, source_sha TEXT,
                stage TEXT, manifest_sha TEXT, run_id INTEGER,
                started_at TEXT, evidence_dir TEXT, evidence_sha TEXT,
                quarantine_reason TEXT);
            INSERT INTO meta VALUES ('1e3a3b7d63d7dce13924e279cfb61f3d975bd9aa',
                1, 1, 1855,
                '4223174995813a74a19fb89af6591dea66d12206f0c2e91600edbdb582495344');
        """)
        self.conn = conn
        self.manifest = "a" * 64
        events = [
            (1850, "SOURCE_TRANSITION_ADMITTED",
             READY_SOURCE_TRANSITION_SHA,
             {"schema": "forge.f139.source-transition.v45",
              "to_source_sha": SOURCE}),
            (1851, "NATIVE_DEVELOPMENT_ACTIVATED",
             NATIVE_ACTIVATION_SHA,
             {"source_sha": SOURCE, "scientific_first_use": False}),
            (1854, "NATIVE_DEVELOPMENT_ADMITTED",
             ADMISSION_SHA,
             {"ticket": TICKET, "lane": "Yggdrasil",
              "source_sha": SOURCE, "scientific_first_use": False,
              "manifest_sha256": self.manifest}),
            (1855, "TASK_INTAKE", ANCHOR_SHA,
             {"ticket": TICKET, "lane": "Yggdrasil",
              "manifest_sha": self.manifest}),
        ]
        for seq, kind, sha, doc in events:
            conn.execute("INSERT INTO events VALUES(?,?,?,?)",
                         (seq, kind, sha, json.dumps(doc)))
        conn.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
            (TICKET, "Yggdrasil", SOURCE, "READY", self.manifest,
             None, None, None, None, None))
        self.db = object.__new__(Database)
        self.db.filename = self.path
        self.db.conn = conn
        fake_meta = lambda obj: dict(obj.conn.execute("SELECT * FROM meta").fetchone())
        patchers = [
            patch.object(Database, "verify", return_value=None),
            patch.object(Database, "meta", new=fake_meta),
            patch("f139.nci04_v56_original_pending_preflight.verify_native_activation",
                  return_value=True),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    def snapshot(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            return original_pending_snapshot(self.db)

    def test_verified_original_pending_is_read_only_and_not_release(self):
        before = self.conn.total_changes
        result = self.snapshot()
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(result["head_sha256"], ANCHOR_SHA)
        self.assertEqual(result["ticket"], TICKET)
        self.assertEqual(result["ticket_source_sha"], SOURCE)
        self.assertEqual(len(result["ticket_identity_sha256"]), 64)
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(result["new_dispatches"], 0)

    def test_no_unlocked_preflight(self):
        with self.assertRaisesRegex(V56ReadOnlyDenied, "MUTEX"):
            original_pending_snapshot(self.db)

    def test_refuse_mutated_source_head_and_admission(self):
        scenarios = [
            ("UPDATE meta SET source_sha=?", ("f" * 40,)),
            ("UPDATE meta SET head_hash=?", ("f" * 64,)),
            ("UPDATE meta SET head_seq=?", (1856,)),
            ("UPDATE events SET sha=? WHERE seq=1854", ("f" * 64,)),
            ("UPDATE events SET sha=? WHERE seq=1855", ("f" * 64,)),
            ("UPDATE tasks SET manifest_sha=?", ("f" * 64,)),
            ("UPDATE tasks SET run_id=?", (99,)),
            ("UPDATE tasks SET stage=?", ("START_RISK",)),
            ("UPDATE tasks SET started_at=?", ("2026-11-18",)),
        ]
        for sql, args in scenarios:
            with self.subTest(sql=sql, args=args):
                self.conn.execute("SAVEPOINT testcase")
                try:
                    self.conn.execute(sql, args)
                    with self.assertRaises(V56ReadOnlyDenied):
                        self.snapshot()
                finally:
                    self.conn.execute("ROLLBACK TO testcase")
                    self.conn.execute("RELEASE testcase")

    def test_fail_on_second_ticket_or_previous_dispatch(self):
        with self.assertRaisesRegex(V56ReadOnlyDenied, "EXCLUSIVITY"):
            self.conn.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("other", "Wingless", SOURCE, "READY", self.manifest,
                 None, None, None, None, None))
            try:
                self.snapshot()
            finally:
                self.conn.execute("DELETE FROM tasks WHERE ticket='other'")
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (1840, "BEFORE_DISPATCH_INTENT", "f" * 64,
             json.dumps({"ticket": TICKET})))
        try:
            with self.assertRaisesRegex(V56ReadOnlyDenied, "SPENT"):
                self.snapshot()
        finally:
            self.conn.execute("DELETE FROM events WHERE seq=1840")

    def test_fail_on_changed_origin_event_or_intake(self):
        for seq in (1850, 1851, 1854, 1855):
            with self.subTest(seq=seq):
                self.conn.execute("SAVEPOINT testcase")
                try:
                    self.conn.execute(
                        "UPDATE events SET payload=? WHERE seq=?",
                        (json.dumps({"ticket": "wrong"}), seq))
                    with self.assertRaises(V56ReadOnlyDenied):
                        self.snapshot()
                finally:
                    self.conn.execute("ROLLBACK TO testcase")
                    self.conn.execute("RELEASE testcase")


if __name__ == "__main__":
    unittest.main()
