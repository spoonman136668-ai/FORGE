"""A8E2A3 native controller v3 integration against synthetic original history only.

This is NOT owner evidence: historical original ZIP authentication is tested
separately by the A8B/A8E2A2 suites. These tests assert the production
Database source transition and cold verification actually invoke custody.
No GitHub network, no owner profile, no real worker, and no dispatch.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from f139.local_controller import Database, F139Error
from f139.nci04_negative_owner_store import (
    SOURCE_SHA as SOURCE_696, TICKET as TICKET_696)
from f139.nci04_split_negative_owner_store import (
    SOURCE as SOURCE_706, TICKET as TICKET_706, KIND as KIND_706)
from f139.nci04_owner_ledger import (
    activate_native, APPROVAL_SCHEMA, verify_native_activation)

NEW_SOURCE = "c" * 40


class TwoNegativeControllerIntegration(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="forge-a8e2a3-v3-")
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "state.sqlite"
        self.db = Database.initialize(self.path, SOURCE_706)
        self.addCleanup(self.db.close)
        self.db.conn.execute(
            "UPDATE meta SET enabled=1,legacy_suspended=1 WHERE id=1")
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
            "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,'VERIFIED',?,?,?,?)",
            ("f139-d2c-qualification-659bb1f4d751", "Qualification",
             SOURCE_696, "a" * 64, 42, "/synthetic/verified", "b" * 64))
        for ticket, source, lane in (
            (TICKET_696, SOURCE_696, "Yggdrasil"),
            (TICKET_706, SOURCE_706, "Wingless")):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "quarantine_reason) VALUES(?,?,?,'QUARANTINED',?,?)",
                (ticket, lane, source, "d" * 64, "FAILED_OR_CANCELLED_NO_REPLAY"))
        self.old = mock.patch(
            "f139.nci04_negative_owner_store.verify_original_negative_custody",
            return_value=True)
        self.second = mock.patch(
            "f139.nci04_split_negative_owner_store.verify_second_negative_custody",
            side_effect=lambda db: db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind=?", (KIND_706,)
            ).fetchone()[0] == 1)
        self.old.start()
        self.second.start()
        self.addCleanup(self.old.stop)
        self.addCleanup(self.second.stop)
        for ix in range(47):
            with self.db.transaction():
                self.db.event("SYNTHETIC_HISTORY", {"i": ix})
        with self.db.transaction():
            self.db.event("NATIVE_NEGATIVE_CUSTODIED", {"fixture": True})
        self.assertEqual(self.db.meta()["head_seq"], 48)
        prior = self.db.meta()["head_hash"]
        with self.db.transaction():
            self.db.event("SOURCE_TRANSITION_ADMITTED", {
                "schema": "forge.f139.source-transition.v2",
                "from_source_sha": SOURCE_696, "to_source_sha": SOURCE_706,
                "prior_event_head_sha256": prior,
                "verified_historical_tasks": 1,
                "new_dispatches": 0, "scientific_first_use": False,
                "custodied_negative_tasks": 1,
            })
        for ix in range(50, 55):
            with self.db.transaction():
                self.db.event("SYNTHETIC_NATIVE", {"i": ix})
        with self.db.transaction():
            self.db.event("ATTEMPT_QUARANTINED", {
                "ticket": TICKET_706, "reason": "FAILED_OR_CANCELLED_NO_REPLAY"})
        self.assertEqual(self.db.meta()["head_seq"], 55)
        self.original_55 = [dict(r) for r in self.db.conn.execute(
            "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq")]

    def append_second(self):
        with self.db.transaction():
            self.db.event(KIND_706, {"synthetic_only": True})
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def transition(self):
        self.db.transition_source(NEW_SOURCE, allow_certified_negative=True)

    def test_existing_v2_and_history_validate_without_second_custody(self):
        self.db.verify()
        self.assertEqual(self.db.meta()["head_seq"], 55)
        self.assertEqual(self.db.meta()["source_sha"], SOURCE_706)

    def test_v3_before_original_second_custody_is_forbidden(self):
        with self.assertRaises(F139Error):
            self.transition()
        self.assertEqual(self.db.meta()["head_seq"], 55)
        self.assertEqual(self.db.meta()["source_sha"], SOURCE_706)

    def test_authenticated_second_then_exact_v3(self):
        self.append_second()
        self.db.verify()
        self.transition()
        self.db.verify()
        self.assertEqual(self.db.meta()["head_seq"], 57)
        self.assertEqual(self.db.meta()["source_sha"], NEW_SOURCE)
        event = self.db.conn.execute(
            "SELECT payload FROM events WHERE seq=57").fetchone()
        doc = json.loads(event["payload"])
        self.assertEqual(doc["schema"], "forge.f139.source-transition.v3")
        self.assertEqual(doc["custodied_negative_tasks"], 2)
        self.assertEqual(doc["custodied_negative_tickets"], [TICKET_696, TICKET_706])
        retained = [dict(r) for r in self.db.conn.execute(
            "SELECT seq,kind,payload,prior_sha,sha FROM events "
            "WHERE seq<=55 ORDER BY seq")]
        self.assertEqual(retained, self.original_55)
        for ticket in (TICKET_696, TICKET_706):
            self.assertEqual(self.db.conn.execute(
                "SELECT stage FROM tasks WHERE ticket=?",
                (ticket,)).fetchone()["stage"], "QUARANTINED")

    def test_cold_restart_preserves_v3_and_both_negative_states(self):
        self.append_second()
        self.transition()
        self.db.close()
        self.db = Database(self.path)
        self.addCleanup(self.db.close)
        self.db.verify()
        self.assertEqual(self.db.meta()["head_seq"], 57)

    def test_missing_second_custody_raises_on_cold_verification(self):
        self.append_second()
        self.transition()
        with mock.patch(
            "f139.nci04_split_negative_owner_store.verify_second_negative_custody",
            return_value=False):
            with self.assertRaises(F139Error):
                self.db.verify()

    def test_missing_first_custody_raises_on_cold_verification(self):
        self.append_second()
        self.transition()
        with mock.patch(
            "f139.nci04_negative_owner_store.verify_original_negative_custody",
            return_value=False):
            with self.assertRaises(F139Error):
                self.db.verify()

    def test_unlisted_third_negative_rejects_transition(self):
        self.append_second()
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
            "quarantine_reason) VALUES(?,?,?,'QUARANTINED',?,?)",
            ("f139-d2c-wingless-659bb1f4d751", "Wingless", SOURCE_706,
             "e" * 64, "FAILED_OR_CANCELLED_NO_REPLAY"))
        with self.assertRaises(F139Error):
            self.transition()
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def test_pending_task_rejects_transition(self):
        self.append_second()
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha)"
            " VALUES(?,?,?,'READY',?)",
            ("f139-d2c-wingless-659bb1f4d751", "Wingless", SOURCE_706, "e" * 64))
        with self.assertRaises(F139Error):
            self.transition()
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def test_replay_or_subsequent_unqualified_v3_rejected(self):
        self.append_second()
        self.transition()
        with self.assertRaises(F139Error):
            self.db.transition_source("f" * 40, allow_certified_negative=True)
        self.assertEqual(self.db.meta()["head_seq"], 57)

    def test_wrong_source_rejected_without_mutation(self):
        self.append_second()
        with self.assertRaises(F139Error):
            self.db.transition_source(SOURCE_706, allow_certified_negative=True)
        self.assertEqual(self.db.meta()["head_seq"], 56)

    def test_native_activation_after_exact_v3_only(self):
        self.append_second()
        self.transition()
        meta = self.db.meta()
        approval = {
            "schema": APPROVAL_SCHEMA, "source_sha": NEW_SOURCE,
            "expected_event_head_sha256": meta["head_hash"],
            "native_development_approved": True,
            "scientific_first_use": False, "create_controller": False,
            "paid_api_calls": 0,
        }
        with mock.patch(
            "f139.nci04_owner_ledger.verified_historical_foundation",
            return_value=None):
            self.assertTrue(activate_native(self.db, approval))
        self.assertTrue(verify_native_activation(self.db))
        self.db.verify()
        self.assertEqual(self.db.meta()["head_seq"], 58)

    def test_native_activation_before_v3_rejects_two_negatives(self):
        self.append_second()
        meta = self.db.meta()
        approval = {
            "schema": APPROVAL_SCHEMA, "source_sha": SOURCE_706,
            "expected_event_head_sha256": meta["head_hash"],
            "native_development_approved": True,
            "scientific_first_use": False, "create_controller": False,
            "paid_api_calls": 0,
        }
        with mock.patch(
            "f139.nci04_owner_ledger.verified_historical_foundation",
            return_value=None):
            with self.assertRaises(ValueError):
                activate_native(self.db, approval)
        self.assertEqual(self.db.meta()["head_seq"], 56)


if __name__ == "__main__":
    unittest.main()
