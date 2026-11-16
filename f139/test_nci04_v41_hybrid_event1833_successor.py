"""Disposable mechanics only; no live event1832 evidence is forged as qualified.

Exact original event1832 hash/proof/cold backup require native original owner.
Synthetic fixtures patch only the *external historical proof digest* and full
database verify; production code never accepts the patched synthetic evidence.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner, canonical as event_canonical
from f139 import nci04_v41_hybrid_event1832_successor as v39
from f139 import nci04_v41_hybrid_event1833_successor as v40
from f139.test_nci04_v41_hybrid_event1832_successor import (
    Event1832SourceSuccessorTests as Synthetic1831Fixture)


class Event1833InertSourceTests(unittest.TestCase):
    def setUp(self):
        Synthetic1831Fixture.setUp(self)
        self.target = "c" * 40
        prior = v39.snapshot(
            self.db,
            {"seq": 1832, "prior_sha": v39.PREDECESSOR_SHA},
            [self.v37, self.v38])
        self.v39 = {
            "schema": v39.SCHEMA,
            "from_source_sha": v39.SOURCE,
            "to_source_sha": v40.SOURCE,
            "owner_event_id": v40.PREDECESSOR_OWNER_EVENT_ID,
            "prior_event_head_sha256": v39.PREDECESSOR_SHA,
            "original_head_seq": v39.PREDECESSOR_SEQ,
            "original_head_sha256": v39.PREDECESSOR_SHA,
            "v38_event_sha256": v39.PREDECESSOR_SHA,
            "verified_historical_tasks": 153,
            "custodied_negative_tasks": 56,
            "terminal_tasks_sha256": prior["terminal_tasks_sha256"],
            "backup_run_id": v40.PREDECESSOR_BACKUP_RUN_ID,
            "backup_manifest_sha256":
                v40.PREDECESSOR_BACKUP_MANIFEST_SHA256,
            "backup_logical_all_tables_sha256":
                v40.PREDECESSOR_BACKUP_TABLES_SHA256,
            "qualified_worker_blob": v40.WORKER_BLOB,
            "purpose": v39.PURPOSE, "new_dispatches": 0,
            "scientific_first_use": False, "hybrid_admission": False,
            "task_resume_authorized": False,
            "owner_policy_update_authorized": False,
        }
        self.head = "a" * 64  # synthetic only; never claim original head
        self.db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha,sha)"
            " VALUES(?,?,?,?,?)",
            (1832, "SOURCE_TRANSITION_ADMITTED",
             event_canonical(self.v39).decode("ascii"),
             v39.PREDECESSOR_SHA, self.head))
        self.db.conn.execute(
            "UPDATE meta SET source_sha=?,head_seq=?,head_hash=? WHERE id=1",
            (v40.SOURCE, 1832, self.head))
        # A matching synthetically generated SHA256 can never stand in for
        # the original recorded owner proof. Patch just this one import for
        # algorithmic unit controls; real runtime has no such patch.
        self.digest_patch = patch.object(
            v40, "digest", return_value=v40.PREDECESSOR_PROOF_SHA256)
        self.digest_patch.start()
        self.addCleanup(self.digest_patch.stop)
        self.cold = {
            "schema": v40.COLD_SCHEMA,
            "original_source_sha": v40.SOURCE,
            "original_head_seq": 1832,
            "original_head_sha256": self.head,
            "target_source_sha": self.target,
            "backup_run_id": 6789,
            "backup_manifest_sha256": "f" * 64,
            "backup_logical_all_tables_sha256": "b" * 64,
            "independent_detached_restore_verified": True,
            "provider_archives_bytes_verified": True,
            "generation_binary_bytes_verified": True,
            "negative_custody_bytes_verified": True,
            "original_owner_mutations": 0,
            "new_dispatches": 0,
            "scientific_first_use": False,
        }

    def proof(self):
        return v40.build_proof(
            self.db, target=self.target, owner_event_id=1100,
            backup_run_id=6789, backup_manifest_sha256="f" * 64,
            backup_logical_all_tables_sha256="b" * 64)

    def action(self, proof, **overrides):
        kwargs = {
            "disabled_owner_witness": lambda: True,
            "release_witness": lambda: True,
            "detached_cold_witness": lambda: self.cold.copy(),
        }
        kwargs.update(overrides)
        return v40.commit_transition(self.db, proof, **kwargs)

    def test_one_forward_successor_preserves_entire_old_task_table(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            old = [tuple(row) for row in self.db.conn.execute(
                "SELECT * FROM tasks ORDER BY ticket")]
            proof = self.proof()
            self.assertEqual(proof["original_head_sha256"], self.head)
            self.assertEqual(proof["verified_historical_tasks"], 153)
            self.assertEqual(proof["custodied_negative_tasks"], 56)
            self.assertEqual(len(proof["custodied_negative_tickets"]), 56)
            self.assertEqual(proof["custodied_negative_tickets"],
                             sorted(proof["custodied_negative_tickets"]))
            self.assertEqual(proof["v39_predecessor_proof_sha256"],
                             v40.PREDECESSOR_PROOF_SHA256)
            result = self.action(proof)
            self.assertEqual(result["event_seq"], 1833)
            self.assertEqual(result["source_sha"], self.target)
            self.assertFalse(result["hybrid_admission"])
            self.assertFalse(result["scientific_first_use"])
            self.assertEqual(old, [tuple(row) for row in self.db.conn.execute(
                "SELECT * FROM tasks ORDER BY ticket")])
            event = self.db.conn.execute(
                "SELECT seq,sha,prior_sha,payload FROM events WHERE seq=1833"
            ).fetchone()
            self.assertEqual(event["prior_sha"], self.head)
            v40.verify_cold_event(
                self.db, event, json.loads(event["payload"]),
                [self.v37, self.v38, self.v39])
            with self.assertRaisesRegex(
                    v40.SuccessorDenied, "HELD_ORIGINAL_EVENT1832_REQUIRED"):
                self.action(proof)

    def test_old_event_proof_mismatch_fails_closed_before_any_write(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            with patch.object(v40, "digest", return_value="0" * 64):
                with self.assertRaisesRegex(
                        v40.SuccessorDenied,
                        "FROZEN_EVENT1832_EVENT_OR_CANONICAL_PROOF_DRIFT"):
                    self.proof()
            self.assertEqual(self.db.meta()["head_seq"], 1832)

    def test_no_source_event_replay_or_mutated_negative_history(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            old = [self.v37, self.v38, self.v39]
            with self.assertRaises(v40.SuccessorDenied):
                v40.snapshot(self.db, {"seq": 1833,
                                      "prior_sha": "0" * 64}, old)
            wrong = old[:-1] + [
                {**self.v39, "backup_run_id": 1234}]
            with self.assertRaises(v40.SuccessorDenied):
                v40.snapshot(self.db, {"seq": 1833,
                                      "prior_sha": self.head}, wrong)
            doc = self.proof()
            for delta in (
                {"scientific_first_use": True},
                {"task_resume_authorized": True},
                {"owner_policy_update_authorized": True},
                {"terminal_tasks_sha256": "0" * 64},
                {"custodied_negative_tickets": []},
                {"v39_predecessor_proof_sha256": "0" * 64},
            ):
                with self.subTest(delta=delta):
                    with self.assertRaises(v40.SuccessorDenied):
                        self.action({**doc, **delta})
            self.assertEqual(self.db.meta()["head_seq"], 1832)

    def test_cold_owner_witness_and_lock_required(self):
        with self.assertRaisesRegex(
                v40.SuccessorDenied, "EXISTING_ORIGINAL_OWNER_MUTEX_REQUIRED"):
            self.proof()
        with SingleOwner(self.path.with_suffix(".lock")):
            proof = self.proof()
            for changed in (
                {"independent_detached_restore_verified": False},
                {"negative_custody_bytes_verified": False},
                {"original_head_sha256": "0" * 64},
                {"backup_manifest_sha256": "0" * 64},
            ):
                self.cold.update(changed)
                with self.assertRaisesRegex(
                        v40.SuccessorDenied,
                        "REAL_EVENT1832_COLD_CUSTODY_REQUIRED"):
                    self.action(proof)
                self.cold.update({
                    "independent_detached_restore_verified": True,
                    "negative_custody_bytes_verified": True,
                    "original_head_sha256": self.head,
                    "backup_manifest_sha256": "f" * 64,
                })
            with self.assertRaisesRegex(
                    v40.SuccessorDenied,
                    "DISABLED_ORIGINAL_OWNER_AND_RELEASE_REQUIRED"):
                self.action(proof, release_witness=lambda: False)
            self.assertEqual(self.db.meta()["head_seq"], 1832)

    def test_inert_mechanism_not_native_execution_authority(self):
        import inspect
        code = inspect.getsource(v40)
        self.assertNotIn("if __name__", code)
        self.assertNotIn("workflow_dispatch", code)
        self.assertNotIn("Register-ScheduledTask", code)
        self.assertNotIn("Start-ScheduledTask", code)
        self.assertNotIn("github.com/", code)
        self.assertIn("SingleOwner.held(", code)
        self.assertIn("UPDATE meta SET source_sha=?", code)


if __name__ == "__main__":
    unittest.main()
