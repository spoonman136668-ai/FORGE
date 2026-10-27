"""Isolated G54 ambiguous-start custody qualification; no live owner I/O."""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import f139.nci04_g54_ambiguous_start_custody as custody
from test_nci04_owner_ledger import LedgerTests


class G54AmbiguousCustodyTests(unittest.TestCase):
    def setUp(self):
        fixture = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.db = fixture.db
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
            "started_at,quarantine_reason) VALUES(?,?,?,'QUARANTINED',?,?,?)",
            (custody.TICKET, "Yggdrasil", custody.SOURCE_SHA, "d" * 64,
             custody.STARTED_AT, custody.REASON))
        with self.db.transaction():
            self.db.event("ATTEMPT_QUARANTINED", {
                "ticket": custody.TICKET, "reason": custody.REASON})
        event = self.db.conn.execute(
            "SELECT seq,sha FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        patchers = [
            patch.object(custody, "EVENT_SEQ", event["seq"]),
            patch.object(custody, "EVENT_SHA256", event["sha"]),
            patch("f139.nci04_owner_ledger.frozen_native_issue",
                  return_value=SimpleNamespace(
                      number=989, ticket=custody.TICKET, lane="Yggdrasil",
                      source_sha=custody.SOURCE_SHA, issue_id=989001)),
        ]
        for item in patchers:
            item.start()
            self.addCleanup(item.stop)

    def test_exact_owner_negative_is_a_read_only_no_replay_witness(self):
        old = self.db.meta().copy()
        result = custody.verified_g54_ambiguous_start(self.db)
        self.assertEqual(self.db.meta(), old)
        self.assertEqual(result["quarantine_event_seq"], custody.EVENT_SEQ)
        self.assertEqual(result["quarantine_event_sha256"], custody.EVENT_SHA256)
        self.assertEqual(result["ticket"], custody.TICKET)
        self.assertIsNone(result["provider_run_id"])
        self.assertFalse(result["replay_authorized"])
        self.assertFalse(result["scientific_first_use"])

    def test_event_identity_mismatch_rejected(self):
        with patch.object(custody, "EVENT_SHA256", "0" * 64):
            with self.assertRaisesRegex(custody.G54AmbiguousCustodyDenied,
                                        "ORIGINAL_EVENT_NOT_EXACT"):
                custody.verified_g54_ambiguous_start(self.db)

    def test_quarantine_reason_or_original_source_cannot_be_rewritten(self):
        for field, bad in (("quarantine_reason", "RETRY_ALLOWED"),
                           ("source_sha", "f" * 40),
                           ("run_id", 1),
                           ("stage", "VERIFIED")):
            with self.subTest(field=field):
                self.db.conn.execute(
                    f"UPDATE tasks SET {field}=? WHERE ticket=?",
                    (bad, custody.TICKET))
                with self.assertRaisesRegex(custody.G54AmbiguousCustodyDenied,
                                            "ORIGINAL_TASK_NOT_FROZEN"):
                    custody.verified_g54_ambiguous_start(self.db)
                old = {
                    "quarantine_reason": custody.REASON,
                    "source_sha": custody.SOURCE_SHA,
                    "run_id": None, "stage": "QUARANTINED",
                }[field]
                self.db.conn.execute(
                    f"UPDATE tasks SET {field}=? WHERE ticket=?",
                    (old, custody.TICKET))

    def test_second_quarantine_cannot_be_smuggled_into_history(self):
        with self.db.transaction():
            self.db.event("ATTEMPT_QUARANTINED", {
                "ticket": custody.TICKET, "reason": custody.REASON})
        with self.assertRaisesRegex(custody.G54AmbiguousCustodyDenied,
                                    "ORIGINAL_NEGATIVE_REPLAYED"):
            custody.verified_g54_ambiguous_start(self.db)

    def test_expired_history_window_denies_retroactive_promotion(self):
        with self.assertRaisesRegex(custody.G54AmbiguousCustodyDenied,
                                    "HISTORICAL_BOUNDARY_INVALID"):
            custody.verified_g54_ambiguous_start(
                self.db, through_seq=custody.EVENT_SEQ)

    def test_unverified_owner_issue_denied(self):
        with patch("f139.nci04_owner_ledger.frozen_native_issue",
                   return_value=SimpleNamespace(
                       number=990, ticket=custody.TICKET, lane="Yggdrasil",
                       source_sha=custody.SOURCE_SHA, issue_id=990001)):
            with self.assertRaisesRegex(custody.G54AmbiguousCustodyDenied,
                                        "OWNER_ADMISSION_NOT_AUTHENTICATED"):
                custody.verified_g54_ambiguous_start(self.db)


if __name__ == "__main__":
    unittest.main()
