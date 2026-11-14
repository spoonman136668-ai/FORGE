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
        # Authentic full-chain replay remains mandatory in CLI Database.verify.
        from f139.nci04_v41_hybrid_source_transition import (
            ACTIVATED_SEQ, ACTIVATED_HASH, FROM_V41, SCHEMA, PURPOSE,
        )
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY,kind TEXT,"
            "sha TEXT,prior_sha TEXT,payload TEXT)")
        target = "c611c4362e3cc867984448a03ecdf3be923d2ef1"
        head = "a" * 64
        transition = {
            "schema": SCHEMA, "purpose": PURPOSE,
            "from_source_sha": FROM_V41, "to_source_sha": target,
            "original_head_seq": ACTIVATED_SEQ,
            "original_head_sha256": ACTIVATED_HASH,
            "hybrid_admission": False, "scientific_first_use": False,
            "new_dispatches": 0,
        }
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
            ACTIVATED_SEQ, "V41_ANCHOR", ACTIVATED_HASH,
            "0" * 64, "{}"))
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
            ACTIVATED_SEQ + 1, "SOURCE_TRANSITION_ADMITTED", head,
            ACTIVATED_HASH, json.dumps(transition)))
        meta = {"head_seq": ACTIVATED_SEQ + 1,
                "head_hash": head, "source_sha": target}
        held = SimpleNamespace(conn=conn, meta=lambda: meta)
        # An absent historical native activation is not made authentic
        # by the source transition alone.
        with patch("f139.nci04_owner_ledger.verify_native_activation",
                   return_value=False):
            self.assertFalse(_qualified_v41_postcommit_source_hold(held))
        with patch("f139.nci04_owner_ledger.verify_native_activation",
                   return_value=True) as verified:
            self.assertTrue(_qualified_v41_postcommit_source_hold(held))
            verified.assert_called_once_with(
                held, expected_source=FROM_V41)
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
                with patch("f139.nci04_owner_ledger.verify_native_activation",
                           return_value=True):
                    self.assertFalse(_qualified_v41_postcommit_source_hold(held))
        conn.execute("UPDATE events SET payload=? WHERE seq=?", (
            json.dumps(transition), ACTIVATED_SEQ + 1))
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (
            ACTIVATED_SEQ + 2, "SOURCE_TRANSITION_ADMITTED",
            "b" * 64, head, json.dumps(transition)))
        meta["head_seq"] += 1
        with patch("f139.nci04_owner_ledger.verify_native_activation",
                   return_value=True):
            self.assertFalse(_qualified_v41_postcommit_source_hold(held))
        conn.execute("DELETE FROM events WHERE seq=?", (ACTIVATED_SEQ + 2,))
        meta["head_seq"] -= 1
        conn.execute("DELETE FROM events WHERE seq=?", (ACTIVATED_SEQ,))
        with patch("f139.nci04_owner_ledger.verify_native_activation",
                   return_value=True):
            self.assertFalse(_qualified_v41_postcommit_source_hold(held))

    def test_v37_original_negative_custody_is_required_for_native_reactivation(self):
        # Source-level regression for the next authenticated owner gate.
        # This alone does NOT constitute live native-activation acceptance:
        # original 1830-event SQLite and owner readback are separately needed.
        import inspect
        from f139.nci04_owner_ledger import activate_native

        source = inspect.getsource(activate_native)
        self.assertEqual(source.count(
            '"forge.f139.source-transition.v37"'), 3)
        self.assertIn(
            "negative_successors[-1][\"to_source_sha\"]==meta[\"source_sha\"]",
            source)
        self.assertIn(
            'i1464_negative_anchor(db, db.meta()["head_seq"]+1)', source)
        self.assertIn("failed_tickets==all_certified", source)
        self.assertIn("db.verify()", source)

    def _synthetic_v37_native_activation(self, *, omit_negative=False):
        # Isolated contract test only: real 1830-event ledger is not available
        # in CI. Origin signatures and 153/56 history remain live owner gates.
        from f139.nci04_owner_ledger import activate_native, APPROVAL_SCHEMA
        from f139.nci04_negative_owner_store import TICKET as original
        from f139.nci04_split_negative_owner_store import TICKET as second
        from f139.nci04_g49_prepost_negative import TICKET as prepost
        from f139.nci04_v36_source_transition import I1464_TICKET
        from f139.nci04_v41_hybrid_source_transition import SCHEMA as V37
        from f139.local_controller import Database
        from contextlib import ExitStack
        target = "c611c4362e3cc867984448a03ecdf3be923d2ef1"
        db = Database.initialize(
            Path(self.temp.name) / ("v37-omit.db" if omit_negative else "v37-good.db"),
            target)
        self.addCleanup(db.close)
        db.enable(legacy_suspended=True)
        g54 = "synthetic-g54-frozen"
        providers = ["synthetic-provider-%02d" % i for i in range(51)]
        full = sorted({original, second, prepost, g54, I1464_TICKET, *providers})
        self.assertEqual(len(full), 56)
        rows = [ticket for ticket in full if not (omit_negative and ticket == I1464_TICKET)]
        for ticket in rows:
            db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "quarantine_reason) VALUES(?,?,?,?,?,?)",
                (ticket, "Yggdrasil", target, "QUARANTINED", "a" * 64,
                 "synthetic-negative"))
        db.event("SOURCE_TRANSITION_ADMITTED", {
            "schema": V37,
            "from_source_sha": "1a40fe4e3ec6e93a1631d59863b95e90981d734e",
            "to_source_sha": target,
            "custodied_negative_tasks": 56,
            "custodied_negative_tickets": full,
        })
        approval = {
            "schema": APPROVAL_SCHEMA, "source_sha": target,
            "expected_event_head_sha256": db.meta()["head_hash"],
            "native_development_approved": True,
            "scientific_first_use": False, "create_controller": False,
            "paid_api_calls": 0,
        }
        with ExitStack() as stack:
            stack.enter_context(patch.object(db, "verify", return_value=None))
            stack.enter_context(patch.object(
                db, "verified_native_provider_failures", return_value=providers))
            stack.enter_context(patch(
                "f139.nci04_owner_ledger.verified_historical_foundation",
                return_value=None))
            stack.enter_context(patch(
                "f139.nci04_negative_owner_store.verify_original_negative_custody",
                return_value=True))
            stack.enter_context(patch(
                "f139.nci04_split_negative_owner_store.verify_second_negative_custody",
                return_value=True))
            stack.enter_context(patch(
                "f139.nci04_g49_prepost_negative.verify_g49_custody",
                return_value=True))
            stack.enter_context(patch(
                "f139.local_controller.g54_original_canonical",
                return_value={"ticket": g54}))
            stack.enter_context(patch(
                "f139.nci04_v36_source_transition.i1464_negative_anchor",
                return_value=I1464_TICKET))
            if omit_negative:
                with self.assertRaisesRegex(
                        ValueError, "UNVERIFIED_HISTORICAL_TASK"):
                    activate_native(db, approval)
                self.assertEqual(
                    db.conn.execute("SELECT COUNT(*) FROM events WHERE "
                                    "kind='NATIVE_DEVELOPMENT_ACTIVATED'").fetchone()[0],
                    0)
            else:
                self.assertTrue(activate_native(db, approval))
                self.assertEqual(
                    db.conn.execute("SELECT COUNT(*) FROM events WHERE "
                                    "kind='NATIVE_DEVELOPMENT_ACTIVATED'").fetchone()[0],
                    1)

    def test_v37_reactivation_keeps_all_synthetic_negatives(self):
        self._synthetic_v37_native_activation()

    def test_v37_reactivation_rejects_missing_frozen_negative(self):
        self._synthetic_v37_native_activation(omit_negative=True)

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
