"""Inert v38 forward-only source repair: synthetic SQLite and refusal controls.

The live original 1830-event history, owner authentication, protected release,
cold bundle and signed source are deliberately NOT simulated as qualified.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_hybrid_source_transition as v37
from f139 import nci04_v41_hybrid_forward_repair as repair


class ForwardSourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "held.sqlite"
        self.db = Database.initialize(self.path, repair.FROM)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        self.db.enable_native_two_slots()
        self.target = "b" * 40
        self.prev = {
            "schema": v37.SCHEMA, "from_source_sha": v37.FROM_V41,
            "to_source_sha": repair.FROM,
            "original_head_seq": v37.ACTIVATED_SEQ,
            "original_head_sha256": v37.ACTIVATED_HASH,
            "backup_manifest_sha256": "c" * 64,
            "hybrid_admission": False, "scientific_first_use": False,
            "new_dispatches": 0,
        }
        self.db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha,sha) VALUES(?,?,?,?,?)",
            (repair.V37_SEQ, "SOURCE_TRANSITION_ADMITTED",
             json.dumps(self.prev), v37.ACTIVATED_HASH, repair.V37_HEAD))
        self.db.conn.execute(
            "UPDATE meta SET source_sha=?,head_seq=?,head_hash=? WHERE id=1",
            (repair.FROM, repair.V37_SEQ, repair.V37_HEAD))
        for index in range(153):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,?,?,?,?,?)",
                ("synthetic-verified-%03d" % index, "Wingless",
                 v37.FROM_V41, "VERIFIED", "d" * 64,
                 index + 1, "synthetic", "e" * 64))
        for index in range(56):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "quarantine_reason) VALUES(?,?,?,?,?,?)",
                ("synthetic-quarantined-%03d" % index, "Yggdrasil",
                 v37.FROM_V41, "QUARANTINED", "d" * 64,
                 "synthetic"))
        # Real old history is never forged as authentic: only the snapshot
        # and atomic behavior can be exercised on a disposable fixture.
        self.verify = patch.object(self.db, "verify", return_value=None)
        self.verify.start()
        self.addCleanup(self.verify.stop)
        self.activation = patch(
            "f139.nci04_v41_hybrid_forward_repair.verify_native_activation",
            return_value=True)
        self.activation.start()
        self.addCleanup(self.activation.stop)

    def rows(self):
        return [tuple(x) for x in self.db.conn.execute(
            "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
            "evidence_dir,evidence_sha,quarantine_reason "
            "FROM tasks ORDER BY ticket")]

    def test_v38_forward_source_once_without_rewriting_old_tasks(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            previous = self.rows()
            proof = repair.build_proof(
                self.db, self.target, 9876, 34567, "f" * 64, "a" * 64)
            self.assertEqual(self.rows(), previous)
            result = repair.commit_transition(
                self.db, proof, disabled_owner_witness=lambda: True,
                release_witness=lambda: True,
                cold_bundle_witness=lambda: True)
            self.assertEqual(self.rows(), previous)
            self.assertEqual(result["event_seq"], repair.V37_SEQ + 1)
            self.assertEqual(self.db.meta()["source_sha"], self.target)
            self.assertFalse(result["task_resume_authorized"])
            self.assertFalse(result["hybrid_admission"])
            self.assertFalse(result["scientific_first_use"])
            previous_events = [self.prev]
            row = self.db.conn.execute(
                "SELECT seq,prior_sha,payload,sha FROM events WHERE seq=?",
                (repair.V37_SEQ + 1,)).fetchone()
            repair.verify_cold_event(
                self.db, row, json.loads(row["payload"]), previous_events)
            with self.assertRaisesRegex(
                    repair.ForwardRepairDenied,
                    "EXACT_UNCHANGED_ORIGINAL_V37_HOLD_REQUIRED"):
                repair.commit_transition(
                    self.db, proof, disabled_owner_witness=lambda: True,
                    release_witness=lambda: True,
                    cold_bundle_witness=lambda: True)

    def test_missing_cold_witness_fails_before_write(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            proof = repair.build_proof(
                self.db, self.target, 9876, 34567, "f" * 64, "a" * 64)
            with self.assertRaisesRegex(
                    repair.ForwardRepairDenied,
                    "SEPARATE_SOURCE_OWNER_RELEASE_AND_COLD_APPROVAL_REQUIRED"):
                repair.commit_transition(
                    self.db, proof, disabled_owner_witness=lambda: True,
                    release_witness=lambda: True,
                    cold_bundle_witness=lambda: False)
        self.assertEqual(self.db.meta()["head_seq"], repair.V37_SEQ)
        self.assertEqual(self.db.meta()["source_sha"], repair.FROM)

    def test_snapshot_rejects_missing_quarantined_record(self):
        # Live task history is immutable. Inject a filtered read-only view
        # rather than attempting to delete an existing original task.
        from types import SimpleNamespace

        class FilterOne:
            def __init__(self, connection):
                self.connection = connection
            def execute(self, sql, params=()):
                rows = self.connection.execute(sql, params)
                if "FROM tasks ORDER BY ticket" in sql:
                    return [row for row in rows
                            if row["ticket"] != "synthetic-quarantined-055"]
                return rows

        proxy = SimpleNamespace(conn=FilterOne(self.db.conn))
        before = self.rows()
        with self.assertRaisesRegex(
                repair.ForwardRepairDenied, "ORIGINAL_153_56_HISTORY_DRIFT"):
            repair.snapshot(
                proxy, {"seq": repair.V37_SEQ + 1,
                        "prior_sha": repair.V37_HEAD}, [self.prev])
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.db.meta()["head_seq"], repair.V37_SEQ)

    def test_predecessor_or_after_write_witness_loss_rolls_back(self):
        # The actual SQLite ledger forbids UPDATE of prior events. Exercise
        # a forged predecessor argument instead of tampering with live rows.
        with self.assertRaisesRegex(
                repair.ForwardRepairDenied,
                "EXACT_SINGLE_V37_PREDECESSOR_REQUIRED"):
            repair.snapshot(
                self.db,
                {"seq": repair.V37_SEQ + 1, "prior_sha": repair.V37_HEAD},
                [{**self.prev, "schema": "forge.f139.source-transition.v36"}])
        with SingleOwner(self.path.with_suffix(".lock")):
            proof = repair.build_proof(
                self.db, self.target, 9876, 34567, "f" * 64, "a" * 64)
            calls = [0]
            def disabled():
                calls[0] += 1
                return calls[0] < 3
            with self.assertRaisesRegex(
                    repair.ForwardRepairDenied, "POSTCOMMIT_OWNER_WITNESS_LOST"):
                repair.commit_transition(
                    self.db, proof, disabled_owner_witness=disabled,
                    release_witness=lambda: True,
                    cold_bundle_witness=lambda: True)
        self.assertEqual(self.db.meta()["source_sha"], repair.FROM)
        self.assertEqual(self.db.meta()["head_seq"], repair.V37_SEQ)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE seq>?", (repair.V37_SEQ,)
        ).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
