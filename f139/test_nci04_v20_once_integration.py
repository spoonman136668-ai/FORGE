"""Isolated original V20 terminal once-only integration contract.

No real SQLite, owner credential, Windows task or GitHub provider calls.
Verifies correct V3 run identity and fail-closed behavior at the *helper* layer.
"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from f139 import nci04_v20_original_terminal_once as once


class FakeConn:
    def __init__(self, db):
        self.db = db

    def execute(self, query, args=()):
        if "json_extract" in query:
            return [("prior",)] if self.db.already_terminal else []
        if "SELECT stage,run_id,completed_at" in query:
            return [{"stage": self.db.stage, "run_id": self.db.run_id,
                     "completed_at": self.db.completed_at}]
        if "SELECT kind FROM events" in query:
            return ([{"kind": "PROVIDER_VERIFIED_TERMINAL"},
                     {"kind": "NATIVE_V_THREE_PROVIDER_CUSTODY"}]
                    if self.db.completed_at else [])
        raise AssertionError("Unanticipated query in fake original DB: " + query)


class FakeDatabase:
    last = None

    def __init__(self, filename):
        self.filename = Path(filename)
        self.stage = "WAIT_PROVIDER"
        self.run_id = None
        self.completed_at = None
        self.already_terminal = False
        self.head_seq = once.HEAD_SEQ
        self.head_hash = once.HEAD_HASH
        self.conn = FakeConn(self)
        FakeDatabase.last = self

    def verify(self):
        return None

    def meta(self):
        return {"source_sha": once.SOURCE, "head_seq": self.head_seq,
                "head_hash": self.head_hash, "enabled": 1,
                "legacy_suspended": 1}

    def actives(self):
        if self.stage != "WAIT_PROVIDER":
            return []
        return [{"ticket": once.TICKET, "lane": "Yggdrasil",
                 "stage": self.stage, "source_sha": once.SOURCE,
                 "started_at": once.STARTED, "run_id": None}]

    def ready(self):
        return None

    def close(self):
        return None


class OneShotOriginalIntegration(unittest.TestCase):
    def test_reuses_exact_prior_worker_and_original_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            path.write_bytes(b"synthetic marker, not a real sqlite file")
            lock = MagicMock()
            lock.held.return_value = True
            def settled(db, api, db_path, **fields):
                self.assertEqual(db_path, path)
                self.assertEqual(fields, {
                    "ticket": once.TICKET, "run_id": 40969568784,
                    "started_at": once.STARTED,
                    "owner_key": "x" * 32,
                })
                db.stage = "VERIFIED"
                db.run_id = once.RUN_ID
                db.completed_at = "2026-10-29T23:01:00Z"
                db.head_seq += 2
                db.head_hash = "f" * 64
                return {"original_sqlite_terminal_verified": True,
                        "scientific_first_use": False}
            with patch.object(once, "Database", FakeDatabase), \
                 patch.object(once, "SingleOwner", lock), \
                 patch.object(once, "GitHub", MagicMock()), \
                 patch.object(once, "verify_release_worker_branch",
                              return_value="f139-owner-release-"+once.SOURCE), \
                 patch.object(once, "verify_native_activation", return_value=True), \
                 patch.object(once, "settle_original_v3",
                              side_effect=settled) as consumer, \
                 patch.object(once, "audit_v3_original_custody") as audit:
                result = once.settle_one_original(path, "x" * 32)
            self.assertEqual(result["original_v20_terminal"], "PASS")
            self.assertEqual(result["run_id"], once.RUN_ID)
            self.assertEqual(result["event_seq"], once.HEAD_SEQ + 2)
            self.assertEqual(consumer.call_count, 1)
            audit.assert_called_once()
            self.assertEqual(lock.call_count, 1)
            lock.held.assert_called_once_with(path.with_suffix(".lock"))

    def test_provider_denial_never_reports_a_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            path.touch()
            lock = MagicMock()
            lock.held.return_value = True
            with patch.object(once, "Database", FakeDatabase), \
                 patch.object(once, "SingleOwner", lock), \
                 patch.object(once, "GitHub", MagicMock()), \
                 patch.object(once, "verify_release_worker_branch",
                              return_value="f139-owner-release-"+once.SOURCE), \
                 patch.object(once, "verify_native_activation", return_value=True), \
                 patch.object(once, "settle_original_v3",
                              side_effect=ValueError("signed receipt denied")), \
                 patch.object(once, "audit_v3_original_custody") as audit:
                with self.assertRaisesRegex(ValueError, "signed receipt denied"):
                    once.settle_one_original(path, "x" * 32)
            audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
