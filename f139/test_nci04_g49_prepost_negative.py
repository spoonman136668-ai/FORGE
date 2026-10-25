"""G49 isolated deterministic pre-POST negative certificate tests.

No original Windows owner database, GitHub POST, task or production file touch.
"""
from __future__ import annotations

import json
import sqlite3
import unittest

from f139.nci04_g49_prepost_negative import (
    CLAIM_SEQ, CLAIM_SHA, DEFECT, G49Denied, ISSUE, KIND, REASON,
    SCHEMA, SOURCE_V7, TICKET, settle_g49_original_prepost,
    verify_g49_custody,
)


class FakeLedger:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE events(seq INTEGER PRIMARY KEY, sha TEXT, "
            "kind TEXT, payload TEXT)")
        self.conn.execute(
            "CREATE TABLE tasks(ticket TEXT, source_sha TEXT, stage TEXT, "
            "quarantine_reason TEXT, run_id INTEGER, "
            "evidence_sha TEXT, evidence_dir TEXT)")
        self.conn.execute(
            "INSERT INTO tasks VALUES(?,?,?, ?,NULL,NULL,NULL)",
            (TICKET, SOURCE_V7, "QUARANTINED", REASON))
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (CLAIM_SEQ, CLAIM_SHA, "BEFORE_DISPATCH_INTENT",
             json.dumps({"ticket": TICKET})))
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (CLAIM_SEQ+1, "b"*64, "ATTEMPT_QUARANTINED",
             json.dumps({"ticket": TICKET, "reason": REASON})))
        self.receipt = {
            "schema": SCHEMA, "ticket": TICKET, "source_sha": SOURCE_V7,
            "issue_number": ISSUE, "claim_seq": CLAIM_SEQ,
            "claim_sha": CLAIM_SHA, "quarantine_seq": CLAIM_SEQ+1,
            "quarantine_sha": "b"*64,
            "provider_result": "ABSENT_AT_ORIGINAL_OWNER_PREPOST_BOUNDARY",
            "defect": DEFECT, "new_dispatches": 0,
            "scientific_first_use": False,
        }

    def append(self):
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (CLAIM_SEQ+2, "c"*64, KIND, json.dumps(self.receipt)))

    def close(self):
        self.conn.close()


class G49OriginalPrepostTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeLedger()
        self.addCleanup(self.db.close)

    def test_no_certificate_does_not_change_existing_history(self):
        self.assertFalse(verify_g49_custody(self.db))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events").fetchone()[0], 2)

    def test_exact_original_negative_is_read_only_verified(self):
        self.db.append()
        self.assertTrue(verify_g49_custody(self.db))
        self.assertEqual(self.db.conn.execute(
            "SELECT stage FROM tasks WHERE ticket=?", (TICKET,)).fetchone()[0],
            "QUARANTINED")

    def test_signer_failure_cannot_be_rewritten_as_provider_receipt(self):
        self.db.receipt["provider_result"] = "FAILED_PROVIDER"
        self.db.append()
        with self.assertRaisesRegex(G49Denied, "RECORD_IDENTITY"):
            verify_g49_custody(self.db)

    def test_unauthorized_retry_or_post_rejected(self):
        self.db.append()
        self.db.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (CLAIM_SEQ+3, "d"*64, "DISPATCH_POST_RETURNED",
             json.dumps({"ticket": TICKET})))
        with self.assertRaisesRegex(G49Denied, "PROVIDER_POST"):
            verify_g49_custody(self.db)

    def test_source_negative_ticket_cannot_be_relabelled_as_ready(self):
        self.db.append()
        self.db.conn.execute(
            "UPDATE tasks SET stage='READY' WHERE ticket=?", (TICKET,))
        with self.assertRaisesRegex(G49Denied, "TASK_CUSTODY"):
            verify_g49_custody(self.db)

    def test_fake_owner_cannot_mutate_anything(self):
        self.assertEqual(
            self.db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            2)
        with self.assertRaisesRegex(G49Denied, "CANONICAL_OWNER_ONLY"):
            settle_g49_original_prepost(
                self.db, object(), owner_quiesced=True)
        self.assertEqual(
            self.db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            2)

    def test_exact_original_one_time_boundary_is_frozen(self):
        self.assertEqual(SOURCE_V7,
                         "72301da157c27fc6fa7d22edce6842c7e4b2a432")
        self.assertEqual(CLAIM_SEQ, 225)
        self.assertEqual(CLAIM_SHA,
                         "daac64effe3c1422449e44b0250786d4cd1a0e24fc40d3e248743d59fcc01129")
        self.assertFalse(self.db.receipt["scientific_first_use"])
        self.assertEqual(self.db.receipt["new_dispatches"], 0)


if __name__ == "__main__":
    unittest.main()
