"""Proof that V19 original readiness never opens original SQLite as a writer.

Disposable SQLite only; no real owner task, token, issue, or provider.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_release_readonly_preflight import (
    SOURCE, V19ReleasePreflightDenied, _original_state)


class OriginalV19ReadOnlySqliteTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="f139-v19-sqlite-ro-")
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "original-disposable.sqlite"
        self.db = Database.initialize(self.path, SOURCE)
        self.addCleanup(self.db.close)

    def test_readonly_connection_cold_verifies_without_sqlite_writer_privilege(self):
        self.db.close()
        original = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with SingleOwner(self.path.with_suffix(".lock")):
            db = Database.open_readonly(self.path)
            try:
                self.assertIs(type(db), Database)
                self.assertIs(db._readonly_opened, True)
                self.assertEqual(db.conn.execute("PRAGMA query_only").fetchone()[0], 1)
                self.assertEqual(db.meta()["source_sha"], SOURCE)
                db.verify()
                for sql in (
                    "UPDATE meta SET source_sha='0000000000000000000000000000000000000000' WHERE id=1",
                    "CREATE TABLE must_never_exist(id INTEGER)",
                    "PRAGMA journal_mode=DELETE",
                ):
                    with self.subTest(sql=sql):
                        with self.assertRaises(sqlite3.OperationalError):
                            db.conn.execute(sql)
                self.assertEqual(db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)
            finally:
                db.close()
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),
                         original)

    def test_ordinary_writable_constructor_is_rejected_for_original_witness(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(
                    V19ReleasePreflightDenied, "SQLITE_MODE_RO_REQUIRED"):
                _original_state(self.db)
        self.assertFalse(getattr(self.db, "_readonly_opened", False))

    def test_single_owner_mutex_remains_mandatory_in_readonly_path(self):
        self.db.close()
        db = Database.open_readonly(self.path)
        try:
            with self.assertRaisesRegex(
                    V19ReleasePreflightDenied, "MUTEX_REQUIRED"):
                _original_state(db)
        finally:
            db.close()

    def test_missing_original_never_creates_database(self):
        missing = self.path.with_name("missing-original.sqlite")
        with self.assertRaises(Exception):
            Database.open_readonly(missing)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
