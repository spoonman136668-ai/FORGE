"""R11 original-ledger lifetime one-shot: cold denial and no side effects.

Unit tests deliberately NEVER forge original 23-event source authority or
claim that a fake mocked GitHub failure is real owner authorization.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner, canonical, hash_bytes
from f139.nci04_owner_ledger import SEALED_OWNER_PREFIX_HEAD
from f139.rsi_r11_owner_once import (
    KIND, SCHEMA, FIELDS, SCOPE, OriginalOnceDenied,
    audit_owner_once, reserve_original_owner_once,
)
from f139.rsi_r10_self_scope import AFTER_RUN

SOURCE = "d" * 40


class OriginalLifetimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "state.sqlite"
        self.db = Database.initialize(self.path, SOURCE)
        self.addCleanup(lambda: self.db.close())

    def owner_event(self):
        """Audit-only synthetic payload; NOT a native original event."""
        return {
            "schema": SCHEMA, "owner_source_sha": SOURCE,
            "original_owner_prefix_sha256": SEALED_OWNER_PREFIX_HEAD,
            "failed_head_sha": "e" * 40,
            "failed_run_id": AFTER_RUN + 1,
            "failed_job_id": 128880000001,
            "failed_log_sha256": "a" * 64,
            "source_git_blob_sha": "b" * 40,
            "target_path": "f139/diagnostic.py",
            "before_sha256": "c" * 64,
            "candidate_sha256": "d" * 64,
            "task_scope_sha256": "e" * 64,
            "failure_class": "WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP",
            "mechanism": "r16-direct",
            "prior_event_head_sha256": self.db.meta()["head_hash"],
            "operator_scope": SCOPE, "development_only": True,
            "new_worker_created": False,
            "owner_self_worker_admitted": False,
            "worker_dispatched": False, "source_promoted": False,
            "scientific_first_use": False, "paid_model_calls": 0,
            "autonomous_rsi_proven": False,
        }

    def test_empty_original_database_has_no_reservation(self):
        self.assertEqual(audit_owner_once(self.db), ())
        self.db.verify()

    def test_disposable_scope_cannot_reserve_as_original(self):
        from f139.test_rsi_r10_self_scope import fresh, FRESH, JOB, PATH, HEAD
        from f139.rsi_r8_owner_custody import observe_disabled_development
        from f139.rsi_r10_self_scope import reserve_disabled_development
        provider = fresh()
        with SingleOwner(self.path.with_suffix(".lock")):
            observe_disabled_development(
                db=self.db, provider=provider, run_id=FRESH,
                job_id=JOB, path=PATH, failed_head=HEAD)
            reserve_disabled_development(
                db=self.db, provider=provider, failed_run_id=FRESH,
                failed_job_id=JOB, target_path=PATH)
            self.assertEqual(audit_owner_once(self.db), ())
            with self.assertRaisesRegex(OriginalOnceDenied,
                                        "ORIGINAL_OWNER_INSTANCE|ORIGINAL_GITHUB_ADAPTER_DRIFT|WINDOWS_ORIGINAL|ORIGINAL_DATABASE_PATH"):
                reserve_original_owner_once(
                    db=self.db, provider=provider, target_path=PATH)
        self.assertEqual(self.db.meta()["enabled"], 0)

    def test_forged_original_event_rejected_despite_recomputed_hash(self):
        doc = self.owner_event()
        self.db.event(KIND, doc)
        # Original historical foundation is absent; a guessed source/event
        # cannot turn a disposable DB into a signed original owner.
        with self.assertRaises(Exception):
            self.db.verify()

    def test_original_audit_rejects_false_worker_or_science_claims(self):
        for key, value in (
            ("worker_dispatched", True), ("owner_self_worker_admitted", True),
            ("scientific_first_use", True), ("autonomous_rsi_proven", True),
            ("new_worker_created", True), ("paid_model_calls", 1),
            ("operator_scope", "another-scope"),
            ("failed_run_id", AFTER_RUN),
        ):
            with self.subTest(key=key):
                # Independent simulated SQLite database per case.
                doc = self.owner_event()
                doc[key] = value
                self.db.event(KIND, doc)
                with self.assertRaisesRegex(
                        OriginalOnceDenied, "ORIGINAL_RESERVATION_FIELDS"):
                    audit_owner_once(self.db)
                self.db.conn.execute("DROP TRIGGER IF EXISTS prevent_event_delete")
                self.db.conn.execute("DELETE FROM events")
                self.db.conn.execute(
                    "UPDATE meta SET head_seq=0,head_hash=? WHERE id=1",
                    ("0" * 64,))
                self.db.conn.executescript(
                    "CREATE TRIGGER IF NOT EXISTS prevent_event_delete "
                    "BEFORE DELETE ON events BEGIN SELECT RAISE("
                    "ABORT,'F139_APPEND_ONLY'); END;")

    def test_lifetime_duplicate_rejected_even_with_different_failure(self):
        first = self.owner_event()
        self.db.event(KIND, first)
        # A later source epoch must not reset the original ledger's one-use.
        self.db.event("SOURCE_TRANSITION_ADMITTED", {
            "from_source_sha": SOURCE, "to_source_sha": "f" * 40,
        })
        self.db.conn.execute(
            "UPDATE meta SET source_sha=? WHERE id=1", ("f" * 40,))
        second = self.owner_event()
        second["owner_source_sha"] = "f" * 40
        second["failed_run_id"] += 1
        second["prior_event_head_sha256"] = self.db.meta()["head_hash"]
        self.db.event(KIND, second)
        with self.assertRaisesRegex(OriginalOnceDenied,
                                    "LIFETIME_RESERVATION_EXHAUSTED"):
            audit_owner_once(self.db)

    def test_untrusted_original_single_use_never_activates_worker_lanes(self):
        from f139.local_controller import LANES as ORIGINAL_LANES
        from f139.verify_ticket import LANES as WORKER_LANES
        self.assertNotIn("FORGE-self", ORIGINAL_LANES)
        self.assertNotIn("FORGE-self", WORKER_LANES)
        tasks = self.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table'"
            "AND name='tasks'").fetchone()[0]
        self.assertNotIn("'FORGE-self'", tasks)
        self.assertEqual(FIELDS, frozenset(self.owner_event()))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM tasks").fetchone()[0], 0)

    def test_original_repair_writer_denied_without_verified_owner(self):
        class FakeGitHub:
            pass
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(OriginalOnceDenied,
                                        "ORIGINAL_OWNER_INSTANCE"):
                reserve_original_owner_once(
                    db=self.db, provider=FakeGitHub(),
                    target_path="f139/diagnostic.py")


if __name__ == "__main__":
    unittest.main()
