"""Hybrid owner admission: explicit SQLite migration and negative preservation."""
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.hybrid_owner_admission import (
    OLD_CHECK, NEW_CHECK, audit_hybrid_lane, is_migrated, migrate_hybrid_lane,
    QUALIFIED_HYBRID_WORKER_BLOB, require_qualified_worker_blob,
)


class HybridOwnerMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"original.db"
        self.db=Database.initialize(self.path,"a"*40)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        self.db.enable_native_two_slots()

    def test_original_source_and_event_bytes_preserved_after_owner_upgrade(self):
        before=[tuple(r) for r in self.db.conn.execute(
            "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq")]
        self.assertFalse(is_migrated(self.db))
        with patch("f139.nci04_owner_ledger.verify_native_activation",return_value=True):
            self.assertTrue(migrate_hybrid_lane(self.db))
            self.assertFalse(migrate_hybrid_lane(self.db))
        self.assertTrue(is_migrated(self.db))
        self.assertTrue(audit_hybrid_lane(self.db))
        self.assertEqual(before,[tuple(r) for r in self.db.conn.execute(
            "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"
            " LIMIT ?",(len(before),))])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='HYBRID_LANE_SCHEMA_ADMITTED'"
        ).fetchone()[0],1)
        self.db.verify()
        # Actual SQLite CHECK now admits only the exact native lane identity.
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,?,?)",
            ("f139-nci04-i42-aaaaaaaaaaaa-01234567","TTT-Hybrid","a"*40,
             "QUARANTINED","b"*64))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
                "VALUES(?,?,?,?,?)",("f139-native-science","Science","a"*40,
                                    "READY","b"*64))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute("DELETE FROM tasks")
        # Unbacked Hybrid task is NEVER accepted as authentic owner admission.
        with self.assertRaises(Exception):
            self.db.verify()

    def test_worker_not_qualified_never_unlocks_original_owner_migration(self):
        for candidate in ("8eab7972ba1b30eabf1e38477aff60b598cdeb2f",
                          "0" * 40, "", None):
            with self.subTest(value=candidate), self.assertRaisesRegex(
                    ValueError, "QUALIFIED_WORKER_NOT_RELEASED"):
                require_qualified_worker_blob(candidate)
        require_qualified_worker_blob(QUALIFIED_HYBRID_WORKER_BLOB)

    def test_no_implicit_source_migration_or_unapproved_owner(self):
        self.assertFalse(audit_hybrid_lane(self.db))
        with self.assertRaisesRegex(ValueError,"NATIVE_ORIGINAL_OWNER_NOT_ACTIVE"):
            migrate_hybrid_lane(self.db)
        self.assertIn(OLD_CHECK,self.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='tasks'").fetchone()[0])
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
                "VALUES(?,?,?,?,?)",("f139-hybrid-noowner","TTT-Hybrid","a"*40,
                                    "READY","b"*64))

    def test_extra_schema_trigger_blocks_before_mutation(self):
        self.db.conn.execute(
            "CREATE TRIGGER rogue_guard BEFORE INSERT ON tasks "
            "BEGIN SELECT RAISE(ABORT,'FORBIDDEN'); END")
        with patch("f139.nci04_owner_ledger.verify_native_activation",return_value=True):
            with self.assertRaisesRegex(ValueError,"INDEX_OR_TRIGGER_IDENTITY_DRIFT"):
                migrate_hybrid_lane(self.db)
        self.assertFalse(is_migrated(self.db))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='HYBRID_LANE_SCHEMA_ADMITTED'"
        ).fetchone()[0],0)

    def test_migration_tamper_detected_on_cold_reopen(self):
        with patch("f139.nci04_owner_ledger.verify_native_activation",return_value=True):
            self.assertTrue(migrate_hybrid_lane(self.db))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(
                "UPDATE events SET payload='{}' "
                "WHERE kind='HYBRID_LANE_SCHEMA_ADMITTED'")
        self.db.verify()
