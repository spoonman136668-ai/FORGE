"""Negative controls for one future original-owner event1836 (no live writer)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v43_event1836_successor as v43


TARGET = "1" * 40
LAST_SOURCE_SHA = "f" * 64


class Cursor:
    def __init__(self, records):
        self.records = records

    def fetchone(self):
        return self.records[0] if self.records else None

    def __iter__(self):
        return iter(self.records)


class ColdConnection:
    def __init__(self, previous, historical):
        self.previous = previous
        self.historical = historical
        self.total_changes = 0
        self.frozen = {
            "seq": v43.PREDECESSOR_SEQ, "sha": v43.PREDECESSOR_SHA}
        self.last = {
            "seq": v43.PREDECESSOR_SEQ - 2, "sha": LAST_SOURCE_SHA,
            "payload": canonical(previous[-1]).decode("ascii")}

    def execute(self, query, params=()):
        if query.startswith("SELECT seq,sha FROM events WHERE seq=?"):
            return Cursor([self.frozen])
        if ("FROM events" in query
                and "kind='SOURCE_TRANSITION_ADMITTED'" in query
                and "ORDER BY seq DESC" in query):
            return Cursor([self.last])
        if "FROM tasks ORDER BY ticket" in query:
            return Cursor(self.historical)
        if ("FROM events" in query
                and "kind='SOURCE_TRANSITION_ADMITTED'" in query
                and "ORDER BY seq" in query):
            return Cursor([
                {"payload": canonical(p).decode("ascii")}
                for p in self.previous])
        raise AssertionError("Unexpected SQL: " + query)


class ColdDb:
    def __init__(self, previous, historical):
        self.conn = ColdConnection(previous, historical)


def fixture():
    historical = []
    for i in range(209):
        stage = "VERIFIED" if i < 153 else "QUARANTINED"
        historical.append({
            "ticket": f"historical-{i:03d}",
            "lane": "Wingless" if i % 2 else "Yggdrasil",
            "source_sha": "a" * 40,
            "stage": stage, "manifest_sha": "e" * 64,
            "run_id": i + 1 if stage == "VERIFIED" else None,
            "evidence_dir": "immutable-" + str(i) if stage == "VERIFIED" else None,
            "evidence_sha": "d" * 64 if stage == "VERIFIED" else None,
            "quarantine_reason": (
                "NEGATIVE_NO_REPLAY" if stage == "QUARANTINED" else None)})
    previous = [{
        "schema": v43.predecessor.SCHEMA,
        "from_source_sha": "a" * 40,
        "to_source_sha": v43.ORIGINAL_SOURCE,
        "terminal_tasks_sha256": digest(canonical(historical)),
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }]
    old_sha = LAST_SOURCE_SHA
    negative = sorted(t["ticket"] for t in historical
                      if t["stage"] == "QUARANTINED")
    doc = {
        "schema": v43.SCHEMA,
        "from_source_sha": v43.ORIGINAL_SOURCE,
        "to_source_sha": TARGET,
        "owner_event_id": v43.NEW_OWNER_INTENT_AFTER + 1,
        "prior_event_head_sha256": v43.PREDECESSOR_SHA,
        "original_head_seq": v43.PREDECESSOR_SEQ,
        "original_head_sha256": v43.PREDECESSOR_SHA,
        "v40_source_event_sha256": old_sha,
        "repair_ancestor_sha": v43.v42.REPAIR,
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "custodied_negative_tickets": negative,
        "terminal_tasks_sha256": previous[-1]["terminal_tasks_sha256"],
        "backup_run_id": v43.PREVIOUS_OWNER_READ_RUN + 1,
        "backup_manifest_sha256": "b" * 64,
        "backup_logical_all_tables_sha256": "c" * 64,
        "qualified_worker_blob": v43.QUALIFIED_HYBRID_WORKER_BLOB,
        "escrowed_issue_number": 1715,
        "escrow_reissue_authorized": False,
        "purpose": v43.PURPOSE,
        "new_dispatches": 0, "scientific_first_use": False,
        "hybrid_admission": False, "task_resume_authorized": False,
        "owner_policy_update_authorized": False,
    }
    row = {"seq": v43.PREDECESSOR_SEQ + 1,
           "prior_sha": v43.PREDECESSOR_SHA}
    return ColdDb(previous, historical), row, doc, previous


class Event1836SuccessorTests(unittest.TestCase):
    def check(self, db, row, doc, previous):
        with patch.object(v43, "audit_committed_escrow",
                          return_value="PAIRED_V41_TRANSITION"):
            return v43.verify_cold_event(db, row, doc, previous)

    def test_positive_replay_is_read_only_and_no_deploy_authority(self):
        db, row, doc, previous = fixture()
        self.assertTrue(self.check(db, row, doc, previous))
        self.assertEqual(set(doc), v43.FIELDS)
        self.assertEqual(db.conn.total_changes, 0)
        for key in ("scientific_first_use", "hybrid_admission",
                    "task_resume_authorized", "owner_policy_update_authorized",
                    "escrow_reissue_authorized"):
            self.assertIs(doc[key], False)
        self.assertEqual(doc["new_dispatches"], 0)
        self.assertFalse(hasattr(v43, "main"))
        self.assertFalse(hasattr(v43, "commit_transition"))
        self.assertFalse(hasattr(v43, "install"))
        self.assertFalse(hasattr(v43, "dispatch"))

    def test_source_event_and_frozen_head_fail_closed(self):
        db, row, doc, previous = fixture()
        for field, val in (
            ("seq", v43.PREDECESSOR_SEQ),
            ("prior_sha", "0" * 64)):
            with self.subTest(field=field):
                bad = dict(row, **{field: val})
                with self.assertRaises(v43.OriginalSourceSuccessorDenied):
                    self.check(db, bad, doc, previous)
        for field, value in (
            ("seq", v43.PREDECESSOR_SEQ - 1),
            ("sha", "0" * 64)):
            with self.subTest(anchor=field):
                db, row, doc, previous = fixture()
                db.conn.frozen[field] = value
                with self.assertRaises(v43.OriginalSourceSuccessorDenied):
                    self.check(db, row, doc, previous)
        db, row, doc, previous = fixture()
        db.conn.last["payload"] = json.dumps({"wrong": True})
        with self.assertRaises(v43.OriginalSourceSuccessorDenied):
            self.check(db, row, doc, previous)

    def test_prior_source_replay_and_history_is_immutable(self):
        changes = [
            ("prev_source", None), ("extra_v40", None),
            ("task_stage", None), ("new_historical_task", None),
            ("missing_negative", None), ("task_lane", None),
            ("task_evidence", None), ("unpaired_escrow", None),
        ]
        for kind, _ in changes:
            with self.subTest(kind=kind):
                db, row, doc, previous = fixture()
                if kind == "prev_source":
                    previous[-1]["to_source_sha"] = "9" * 40
                elif kind == "extra_v40":
                    previous.append(dict(previous[-1]))
                elif kind == "task_stage":
                    db.conn.historical[0]["stage"] = "QUARANTINED"
                elif kind == "new_historical_task":
                    db.conn.historical.append(dict(db.conn.historical[0],
                                                   ticket="extra"))
                elif kind == "missing_negative":
                    db.conn.historical.pop()
                elif kind == "task_lane":
                    db.conn.historical[0]["lane"] = "TTT-Hybrid"
                elif kind == "task_evidence":
                    db.conn.historical[0]["evidence_sha"] = "0" * 64
                with patch.object(v43, "audit_committed_escrow",
                                  return_value=("NO_ESCROW" if kind ==
                                                "unpaired_escrow" else
                                                "PAIRED_V41_TRANSITION")):
                    with self.assertRaises(
                            v43.OriginalSourceSuccessorDenied):
                        v43.verify_cold_event(db, row, doc, previous)

    def test_no_approval_backup_or_science_bypass(self):
        bad = [
            ("owner_event_id", v43.NEW_OWNER_INTENT_AFTER),
            ("backup_run_id", v43.PREVIOUS_OWNER_READ_RUN),
            ("backup_manifest_sha256", "f" * 63),
            ("backup_logical_all_tables_sha256", 1),
            ("to_source_sha", v43.ORIGINAL_SOURCE),
            ("to_source_sha", "a" * 40),
            ("source_sha", "9" * 40),
            ("from_source_sha", "a" * 40),
            ("original_head_seq", v43.PREDECESSOR_SEQ - 1),
            ("original_head_sha256", "0" * 64),
            ("v40_source_event_sha256", "0" * 64),
            ("repair_ancestor_sha", "0" * 40),
            ("custodied_negative_tickets", []),
            ("terminal_tasks_sha256", "0" * 64),
            ("qualified_worker_blob", "0" * 40),
            ("escrowed_issue_number", 1716),
            ("escrow_reissue_authorized", True),
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("task_resume_authorized", True),
            ("owner_policy_update_authorized", True),
            ("new_dispatches", 1),
            ("new_dispatches", False),
        ]
        for field, value in bad:
            with self.subTest(field=field, value=value):
                db, row, doc, previous = fixture()
                doc[field] = value
                with self.assertRaises(v43.OriginalSourceSuccessorDenied):
                    self.check(db, row, doc, previous)
        db, row, doc, previous = fixture()
        doc.pop("purpose")
        with self.assertRaises(v43.OriginalSourceSuccessorDenied):
            self.check(db, row, doc, previous)

    def test_proof_builder_requires_real_original_mutex(self):
        db, row, doc, previous = fixture()
        # A fake ledger object cannot be promoted into owner authority.
        with self.assertRaises(v43.OriginalSourceSuccessorDenied):
            v43.build_proof(db, target=TARGET,
                            owner_event_id=v43.NEW_OWNER_INTENT_AFTER + 1,
                            backup_run_id=v43.PREVIOUS_OWNER_READ_RUN + 1,
                            backup_manifest_sha256="b"*64,
                            backup_logical_all_tables_sha256="c"*64)

    def test_registered_in_existing_full_ledger_replay_not_execution_route(self):
        import inspect
        from f139 import local_controller
        body = inspect.getsource(local_controller.Database.verify)
        self.assertIn("from f139.nci04_v43_event1836_successor import FIELDS",
                      body)
        self.assertIn("if is_v41:", body)
        self.assertIn("from f139.nci04_v43_event1836_successor import verify_cold_event",
                      body)
        self.assertFalse(hasattr(v43, "activate"))
        self.assertFalse(hasattr(v43, "write_policy"))


if __name__ == "__main__":
    unittest.main()
