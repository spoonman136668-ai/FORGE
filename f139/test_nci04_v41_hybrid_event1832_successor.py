"""Synthetic only: original held event 1831 -> inert source successor v39.

These disposable fixtures do NOT impersonate a genuine original Windows
owner, independently restored backup or release; no workflow is registered.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical
from f139 import nci04_v41_hybrid_source_transition as v37
from f139 import nci04_v41_hybrid_forward_repair as v38
from f139 import nci04_v41_hybrid_event1832_successor as v39


class Event1832SourceSuccessorTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path = Path(t.name) / "synthetic.sqlite"
        self.db = Database.initialize(self.path, v39.SOURCE)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        self.db.enable_native_two_slots()
        self.target = "b" * 40
        self.v37 = {
            "schema": v37.SCHEMA,
            "from_source_sha": v37.FROM_V41,
            "to_source_sha": v38.FROM,
            "original_head_seq": v37.ACTIVATED_SEQ,
            "original_head_sha256": v37.ACTIVATED_HASH,
            "backup_manifest_sha256": "c" * 64,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "new_dispatches": 0,
        }
        self.db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha,sha)"
            " VALUES(?,?,?,?,?)",
            (1830, "SOURCE_TRANSITION_ADMITTED", json.dumps(self.v37),
             v37.ACTIVATED_HASH, v38.V37_HEAD))
        for n in range(153):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,?,?,?,?,?)",
                (f"mock-verified-{n:03}", "Wingless", v37.FROM_V41,
                 "VERIFIED", "d" * 64, n+1, "synthetic", "e" * 64))
        for n in range(56):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "quarantine_reason) VALUES(?,?,?,?,?,?)",
                (f"mock-negative-{n:03}", "Yggdrasil", v37.FROM_V41,
                 "QUARANTINED", "d" * 64, "synthetic"))
        legacy = v38.snapshot(
            self.db, {"seq": 1831, "prior_sha": v38.V37_HEAD}, [self.v37])
        self.v38 = {
            "schema": v38.SCHEMA,
            "from_source_sha": v38.FROM,
            "to_source_sha": v39.SOURCE,
            "original_head_seq": v38.V37_SEQ,
            "original_head_sha256": v38.V37_HEAD,
            "terminal_tasks_sha256": legacy["terminal_tasks_sha256"],
            "qualified_worker_blob": v39.WORKER_BLOB,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "task_resume_authorized": False,
            "owner_policy_update_authorized": False,
            "new_dispatches": 0,
        }
        self.db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha,sha)"
            " VALUES(?,?,?,?,?)",
            (v39.PREDECESSOR_SEQ, "SOURCE_TRANSITION_ADMITTED",
             json.dumps(self.v38), v38.V37_HEAD, v39.PREDECESSOR_SHA))
        self.db.conn.execute(
            "UPDATE meta SET source_sha=?,head_seq=?,head_hash=? WHERE id=1",
            (v39.SOURCE, v39.PREDECESSOR_SEQ, v39.PREDECESSOR_SHA))
        # Only synthetic unit mechanics, never a real full-history acceptance.
        verify_patch = patch.object(self.db, "verify", return_value=None)
        verify_patch.start()
        self.addCleanup(verify_patch.stop)
        self.cold = {
            "schema": v39.COLD_SCHEMA,
            "original_source_sha": v39.SOURCE,
            "original_head_seq": v39.PREDECESSOR_SEQ,
            "original_head_sha256": v39.PREDECESSOR_SHA,
            "target_source_sha": self.target,
            "backup_run_id": 6789,
            "backup_manifest_sha256": "f" * 64,
            "backup_logical_all_tables_sha256": "a" * 64,
            "independent_detached_restore_verified": True,
            "provider_archives_bytes_verified": True,
            "generation_binary_bytes_verified": True,
            "negative_custody_bytes_verified": True,
            "original_owner_mutations": 0,
            "new_dispatches": 0,
            "scientific_first_use": False,
        }

    def proof(self):
        return v39.build_proof(
            self.db, target=self.target, owner_event_id=4567,
            backup_run_id=6789, backup_manifest_sha256="f" * 64,
            backup_logical_all_tables_sha256="a" * 64)

    def action(self, proof, **overrides):
        kwargs = dict(
            disabled_owner_witness=lambda: True,
            release_witness=lambda: True,
            detached_cold_witness=lambda: self.cold.copy(),
        )
        kwargs.update(overrides)
        return v39.commit_transition(self.db, proof, **kwargs)

    def test_single_source_successor_and_original_task_rows_unchanged(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            before = [tuple(row) for row in self.db.conn.execute(
                "SELECT * FROM tasks ORDER BY ticket")]
            proof = self.proof()
            self.assertEqual(self.db.meta()["head_seq"], 1831)
            self.assertEqual(proof["terminal_tasks_sha256"],
                             self.v38["terminal_tasks_sha256"])
            self.assertEqual(proof["verified_historical_tasks"], 153)
            self.assertEqual(proof["custodied_negative_tasks"], 56)
            self.assertFalse(proof["task_resume_authorized"])
            receipt = self.action(proof)
            self.assertEqual(receipt["event_seq"], 1832)
            self.assertEqual(receipt["source_sha"], self.target)
            self.assertFalse(receipt["scientific_first_use"])
            self.assertEqual([tuple(row) for row in self.db.conn.execute(
                "SELECT * FROM tasks ORDER BY ticket")], before)
            row = self.db.conn.execute(
                "SELECT seq,payload,sha,prior_sha FROM events WHERE seq=1832"
            ).fetchone()
            self.assertEqual(row["prior_sha"], v39.PREDECESSOR_SHA)
            v39.verify_cold_event(
                self.db, row, json.loads(row["payload"]),
                [self.v37, self.v38])
            with self.assertRaisesRegex(
                    v39.SuccessorDenied,
                    "ORIGINAL_COMMITTED_EVENT1831_HOLD_REQUIRED"):
                self.action(proof)

    def test_modified_cold_receipt_refuses_without_source_write(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            proof = self.proof()
            for delta in (
                {"negative_custody_bytes_verified": False},
                {"original_head_sha256": "0" * 64},
                {"backup_manifest_sha256": "1" * 64},
                {"scientific_first_use": True},
            ):
                with self.subTest(delta=delta):
                    self.cold.update(delta)
                    with self.assertRaisesRegex(
                            v39.SuccessorDenied,
                            "DETACHED_COLD_RECEIPT_OR_PROVENANCE_REQUIRED"):
                        self.action(proof)
                    self.cold.update({
                        "negative_custody_bytes_verified": True,
                        "original_head_sha256": v39.PREDECESSOR_SHA,
                        "backup_manifest_sha256": "f" * 64,
                        "scientific_first_use": False,
                    })
                    self.assertEqual(self.db.meta()["head_seq"], 1831)

    def test_forged_source_or_missing_original_mutex_refused(self):
        with self.assertRaisesRegex(
                v39.SuccessorDenied, "EXISTING_SINGLE_OWNER_MUTEX_REQUIRED"):
            self.proof()
        with SingleOwner(self.path.with_suffix(".lock")):
            proof = self.proof()
            for wrong in (
                {**proof, "to_source_sha": v39.SOURCE},
                {**proof, "scientific_first_use": True},
                {**proof, "owner_policy_update_authorized": True},
                {**proof, "original_head_sha256": "0" * 64},
                {**proof, "terminal_tasks_sha256": "0" * 64},
            ):
                with self.subTest(bad=wrong):
                    with self.assertRaises(v39.SuccessorDenied):
                        self.action(wrong)
            self.assertEqual(self.db.meta()["head_seq"], 1831)

    def test_missing_negative_predecessor_or_witness_loss_refuses(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            proof = self.proof()
            broken = [self.v37, {**self.v38,
                                   "terminal_tasks_sha256": "0" * 64}]
            with self.assertRaises(v39.SuccessorDenied):
                v39.verify_cold_event(
                    self.db, {"seq": 1832,
                              "prior_sha": v39.PREDECESSOR_SHA},
                    proof, broken)
            with self.assertRaisesRegex(
                    v39.SuccessorDenied,
                    "DISABLED_OWNER_OR_RELEASE_NOT_AUTHENTIC"):
                self.action(proof, release_witness=lambda: False)
            calls = [0]
            def only_initial():
                calls[0] += 1
                return calls[0] < 4
            with self.assertRaisesRegex(
                    v39.SuccessorDenied,
                    "DISABLED_OWNER_OR_RELEASE_NOT_AUTHENTIC"):
                self.action(proof, disabled_owner_witness=only_initial)
            self.assertEqual(self.db.meta()["head_seq"], 1831)
            self.assertEqual(self.db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE seq=1832").fetchone()[0], 0)

    def test_no_native_workflow_or_implicit_scientific_dispatch(self):
        import inspect
        src=inspect.getsource(v39)
        self.assertNotIn("if __name__",src)
        self.assertNotIn("issue_comment",src)
        self.assertNotIn("Start-ScheduledTask",src)
        self.assertNotIn("workflow_dispatch",src)
        self.assertNotIn("scientific_first_use\": True",src)
        self.assertNotIn("github.com/",src)
        self.assertIn("SingleOwner.held(",src)
        self.assertIn("UPDATE meta SET source_sha",src)
        self.assertIn("db.event(\"SOURCE_TRANSITION_ADMITTED\", proof)",src)


if __name__ == "__main__":
    unittest.main()
