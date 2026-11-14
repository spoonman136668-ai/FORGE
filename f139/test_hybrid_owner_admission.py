"""Hybrid owner admission: explicit SQLite migration and negative preservation."""
import sqlite3
import tempfile
from pathlib import Path
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.hybrid_owner_admission import (
    OLD_CHECK, NEW_CHECK, audit_hybrid_lane, is_migrated, migrate_hybrid_lane,
    _qualified_v41_postcommit_source_hold,
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

    def test_only_exact_committed_v37_hold_exempts_source_bound_activation(self):
        # Boundary check: full ledger verification is still performed by CLI.
        from f139.nci04_v41_hybrid_source_transition import (
            ACTIVATED_SEQ, ACTIVATED_HASH, FROM_V41, SCHEMA, PURPOSE,
        )
        from f139.nci04_owner_ledger import ACTIVATION_KIND
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY,kind TEXT,"
            "sha TEXT,prior_sha TEXT,payload TEXT)")
        target = "c611c4362e3cc867984448a03ecdf3be923d2ef1"
        head = "a" * 64
        activation = {"source_sha": FROM_V41}
        transition = {
            "schema": SCHEMA, "purpose": PURPOSE,
            "from_source_sha": FROM_V41, "to_source_sha": target,
            "original_head_seq": ACTIVATED_SEQ,
            "original_head_sha256": ACTIVATED_HASH,
            "hybrid_admission": False, "scientific_first_use": False,
            "new_dispatches": 0,
        }
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
            ACTIVATED_SEQ, ACTIVATION_KIND, ACTIVATED_HASH,
            "0" * 64, json.dumps(activation)))
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
            ACTIVATED_SEQ + 1, "SOURCE_TRANSITION_ADMITTED", head,
            ACTIVATED_HASH, json.dumps(transition)))
        meta = {"head_seq": ACTIVATED_SEQ + 1,
                "head_hash": head, "source_sha": target}
        held = SimpleNamespace(conn=conn, meta=lambda: meta)
        self.assertTrue(_qualified_v41_postcommit_source_hold(held))
        for field, bad in (
            ("to_source_sha", FROM_V41),
            ("from_source_sha", target),
            ("schema", "forge.f139.source-transition.v36"),
            ("hybrid_admission", True),
            ("new_dispatches", 1),
        ):
            with self.subTest(field=field):
                tampered = dict(transition, **{field: bad})
                conn.execute("UPDATE events SET payload=? WHERE seq=?", (
                    json.dumps(tampered), ACTIVATED_SEQ + 1))
                self.assertFalse(_qualified_v41_postcommit_source_hold(held))
        conn.execute("UPDATE events SET payload=? WHERE seq=?", (
            json.dumps(transition), ACTIVATED_SEQ + 1))
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
            ACTIVATED_SEQ + 2, "SOURCE_TRANSITION_ADMITTED",
            "b" * 64, head, json.dumps(transition)))
        meta["head_seq"] += 1
        self.assertFalse(_qualified_v41_postcommit_source_hold(held))
        conn.execute("DELETE FROM events WHERE seq=?", (ACTIVATED_SEQ + 2,))
        meta["head_seq"] -= 1
        conn.execute("DELETE FROM events WHERE seq=?", (ACTIVATED_SEQ,))
        self.assertFalse(_qualified_v41_postcommit_source_hold(held))

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
