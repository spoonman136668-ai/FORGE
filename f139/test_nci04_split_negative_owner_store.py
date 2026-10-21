"""A8E2A2 isolated synthetic owner-custody filesystem/SQLite tests.

No owner profile, actual #706 provider ZIP, HMAC or historic records consumed.
The existing full F139 tests independently verify original event-chain logic.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from f139.local_controller import Database
from f139.nci04_split_negative_owner_store import (
    KIND, ARTIFACT_BYTES, ARTIFACT_SHA256, RUN_ID, SOURCE, TICKET,
    SplitOwnerCustodyDenied,
    admit_second_negative_custody, check_path, paths,
    records, verify_second_negative_custody, write_original_zip,
)

REASON = "TEST_ONLY_REJECTED"


class SecondNegativeSyntheticOwnerTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix="f139-a8e2a2-synthetic-")
        self.addCleanup(td.cleanup)
        self.path = Path(td.name) / "state.sqlite"
        self.db = Database.initialize(self.path, SOURCE)
        self.addCleanup(self.db.close)
        # The fixture is NOT the original owner's 55-event evidence. Tests
        # bypass the already-independently-qualified historic chain verifier.
        self.db.verify = lambda: None
        self.db.conn.execute(
            "UPDATE meta SET enabled=1, legacy_suspended=1 WHERE id=1")
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
            "quarantine_reason) VALUES(?,?,?,'QUARANTINED',?,?)",
            (TICKET, "Wingless", SOURCE, "a"*64, REASON))
        for ix in range(54):
            with self.db.transaction():
                self.db.event("SYNTHETIC_ONLY", {"synthetic_index": ix})
        with self.db.transaction():
            self.db.event("ATTEMPT_QUARANTINED", {
                "ticket": TICKET, "reason": REASON})
        self.assertEqual(self.db.meta()["head_seq"], 55)
        self.head = self.db.meta()["head_hash"]
        self.owner_issue = SimpleNamespace(
            ticket=TICKET, source_sha=SOURCE,
            issue_body_sha256="b"*64,
            native_intent_sha256="c"*64)
        self.archive = b"synthetic-not-provider-zip:" + b"x" * (ARTIFACT_BYTES - 27)
        self.assertEqual(len(self.archive), ARTIFACT_BYTES)
        expected = ARTIFACT_SHA256
        real_archive = self.archive
        def synthetic_digest(data):
            if data == real_archive:
                return expected
            return hashlib.sha256(data).hexdigest()
        self.mock_digest = mock.patch(
            "f139.nci04_split_negative_owner_store.digest",
            side_effect=synthetic_digest)
        self.mock_digest.start()
        self.addCleanup(self.mock_digest.stop)
        self.mock_head = mock.patch(
            "f139.nci04_split_negative_owner_store.OWNER_HEAD_55", self.head)
        self.mock_head.start()
        self.addCleanup(self.mock_head.stop)
        self.mock_orig = mock.patch(
            "f139.nci04_split_negative_owner_store.verify_original_negative_custody",
            return_value=True)
        self.mock_orig.start()
        self.addCleanup(self.mock_orig.stop)
        self.mock_frozen = mock.patch(
            "f139.nci04_split_negative_owner_store.frozen_native_issue",
            return_value=self.owner_issue)
        self.mock_frozen.start()
        self.addCleanup(self.mock_frozen.stop)
        self.mock_provider = mock.patch(
            "f139.nci04_split_negative_owner_store.verify_706_split_provider_original",
            return_value={
                "whole_run_qualified": False,
                "original_owner_durable_custody": False,
                "successor_source_transition_authorized": False,
            })
        self.mock_provider.start()
        self.addCleanup(self.mock_provider.stop)
        self.original_task = dict(self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?", (TICKET,)).fetchone())
        self.original_events = [dict(r) for r in self.db.conn.execute(
            "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq")]

    def admit(self):
        return admit_second_negative_custody(
            self.db, run={}, jobs=[], artifacts=[],
            archive=self.archive,
            owner_hmac_key="test-not-real-owner-HMAC", epoch=1)

    def test_custody_appends_event_56_and_preserves_every_previous_byte(self):
        receipt = self.admit()
        self.assertEqual(receipt["second_negative_custody"], "PASS")
        self.assertEqual(self.db.meta()["head_seq"], 56)
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["source_transition_authorized"])
        self.assertTrue(verify_second_negative_custody(self.db))
        self.assertEqual([dict(x) for x in self.db.conn.execute(
            "SELECT seq,kind,payload,prior_sha,sha FROM events WHERE seq<=55 ORDER BY seq")],
            self.original_events)
        self.assertEqual(dict(self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?", (TICKET,)).fetchone()),
            self.original_task)
        _, _, path = paths(self.db)
        self.assertEqual(path.read_bytes(), self.archive)

    def test_original_archive_bytes_survive_cold_restart(self):
        self.admit()
        self.db.close()
        self.db = Database(self.path)
        self.db.verify = lambda: None
        self.assertTrue(verify_second_negative_custody(self.db))
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def test_tampered_missing_and_broken_original_archive_rejected(self):
        self.admit()
        _, _, path = paths(self.db)
        path.write_bytes(b"forged")
        with self.assertRaisesRegex(SplitOwnerCustodyDenied, "SECOND_CUSTODY_ZIP_TAMPERED"):
            verify_second_negative_custody(self.db)
        path.write_bytes(self.archive)
        path.unlink()
        with self.assertRaisesRegex(SplitOwnerCustodyDenied, "SECOND_CUSTODY_ZIP_TAMPERED"):
            verify_second_negative_custody(self.db)

    def test_double_original_admission_never_appends_again(self):
        self.admit()
        with self.assertRaisesRegex(SplitOwnerCustodyDenied, "ORIGINAL_55_HEAD_OR_OWNER_DRIFT"):
            self.admit()
        self.assertEqual(len(records(self.db)), 1)
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def test_provider_failure_must_leave_disk_and_sql_unchanged(self):
        with mock.patch(
            "f139.nci04_split_negative_owner_store.verify_706_split_provider_original",
            side_effect=ValueError("FAKE_PROVIDER_REJECTED")):
            with self.assertRaisesRegex(ValueError, "FAKE_PROVIDER_REJECTED"):
                self.admit()
        _, _, path = paths(self.db)
        self.assertFalse(path.exists())
        self.assertEqual(self.db.meta()["head_seq"], 55)

    def test_orphan_file_recovers_only_identical_original_bytes(self):
        with mock.patch.object(self.db, "event", side_effect=OSError("SIMULATED_CRASH")):
            with self.assertRaisesRegex(OSError, "SIMULATED_CRASH"):
                self.admit()
        self.assertEqual(self.db.meta()["head_seq"], 55)
        _, _, path = paths(self.db)
        self.assertEqual(path.read_bytes(), self.archive)
        self.assertEqual(self.admit()["second_negative_custody"], "PASS")
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def test_existing_untrusted_file_is_not_overwritten(self):
        _, directory, path = paths(self.db)
        directory.mkdir(parents=True)
        path.write_bytes(b"untrusted")
        with self.assertRaisesRegex(SplitOwnerCustodyDenied,
                                    "EXISTING_ORIGINAL_ZIP_CONFLICT"):
            self.admit()
        self.assertEqual(path.read_bytes(), b"untrusted")
        self.assertEqual(self.db.meta()["head_seq"], 55)

    def test_partial_untrusted_file_cannot_be_silently_recovered(self):
        _, directory, path = paths(self.db)
        directory.mkdir(parents=True)
        (directory / "ubuntu-latest.zip.partial").write_bytes(b"partial")
        with self.assertRaisesRegex(SplitOwnerCustodyDenied,
                                    "PARTIAL_ORIGINAL_REQUIRES_REVIEW"):
            self.admit()
        self.assertFalse(path.exists())
        self.assertEqual(self.db.meta()["head_seq"], 55)

    def test_quarantine_event_reason_or_head_drift_denied(self):
        self.db.conn.execute(
            "UPDATE tasks SET quarantine_reason=? WHERE ticket=?",
            ("CHANGED_REASON", TICKET))
        with self.assertRaisesRegex(SplitOwnerCustodyDenied, "ORIGINAL_EVENT_55_DRIFT"):
            self.admit()
        self.db.conn.execute(
            "UPDATE tasks SET quarantine_reason=? WHERE ticket=?",
            (REASON, TICKET))
        with mock.patch(
            "f139.nci04_split_negative_owner_store.OWNER_HEAD_55", "f"*64):
            with self.assertRaisesRegex(SplitOwnerCustodyDenied,
                                        "ORIGINAL_55_HEAD_OR_OWNER_DRIFT"):
                self.admit()
        self.assertEqual(self.db.meta()["head_seq"], 55)

    def test_event_or_original_custody_tamper_fails_closed(self):
        self.admit()
        with mock.patch(
            "f139.nci04_split_negative_owner_store.verify_original_negative_custody",
            return_value=False):
            with self.assertRaisesRegex(SplitOwnerCustodyDenied, "FIRST_NEGATIVE_LOST"):
                verify_second_negative_custody(self.db)
        row = self.db.conn.execute(
            "SELECT payload FROM events WHERE seq=56").fetchone()
        doc = json.loads(row["payload"])
        doc["whole_run_qualified"] = True
        # Real F139 SQLite explicitly prohibits historical event mutation.
        # Assert append-only enforcement rather than weakening the trigger
        # just to synthetically exercise a forged custody document.
        with self.assertRaisesRegex(sqlite3.IntegrityError, "F139_APPEND_ONLY"):
            self.db.conn.execute("UPDATE events SET payload=? WHERE seq=56",
                                 (json.dumps(doc),))
        self.assertTrue(verify_second_negative_custody(self.db))

if __name__ == "__main__":
    unittest.main()
