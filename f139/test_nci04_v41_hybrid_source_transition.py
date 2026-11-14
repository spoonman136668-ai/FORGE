"""Inert V41->Hybrid v37 predecessor, real SQL and rollback rehearsal tests."""
import json
import unittest
from unittest import mock

from f139 import nci04_v41_hybrid_source_transition as successor


class HybridV41SuccessorTests(unittest.TestCase):
    def test_no_live_owner_without_lease_witness(self):
        with self.assertRaisesRegex(
                successor.HybridSourceDenied,
                "SEPARATELY_APPROVED_ORIGINAL_OWNER_REQUIRED"):
            successor.commit_transition(
                None, {},
                disabled_owner_witness=lambda: True,
                verified_release_witness=lambda: True)

    def test_preview_cannot_use_unqualified_database(self):
        with self.assertRaisesRegex(
                successor.HybridSourceDenied, "EXISTING_OWNER_MUTEX_REQUIRED"):
            successor.build_proof(
                None, "a" * 40, 1, 43591751557, "f" * 64)

    def test_cold_event_rejects_foreign_and_missing_fields(self):
        row = {"seq": 1830, "prior_sha": successor.ACTIVATED_HASH}
        for altered in (
            {}, {"schema": successor.SCHEMA},
            {"schema": "forge.f139.source-transition.v36"},
        ):
            with self.subTest(doc=altered):
                with self.assertRaisesRegex(
                        successor.HybridSourceDenied,
                        "EVENT_FIELDS_OR_AUTHORITY_DRIFT"):
                    successor.verify_cold_event(None, row, altered, [])

    def test_forged_predecessor_rejected(self):
        row = {"seq": 1830, "prior_sha": successor.ACTIVATED_HASH}
        with self.assertRaisesRegex(
                successor.HybridSourceDenied,
                "UNIQUE_V41_PREDECESSOR_REQUIRED"):
            successor.snapshot(None, row, [])

    def test_source_has_no_execution_route(self):
        from pathlib import Path
        text = Path(successor.__file__).read_text(encoding="utf-8")
        self.assertNotIn("if __name__ == ", text)
        self.assertNotIn("workflow_dispatch", text)
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask",
                          "Disable-ScheduledTask", "Enable-ScheduledTask",
                          "gh api --method PATCH", "requests.post("):
            self.assertNotIn(forbidden, text)
        self.assertIn("bundle.verify_detached_restore(", text)
        self.assertIn("db.event(\"SOURCE_TRANSITION_ADMITTED\", proof)", text)

    def test_backup_readback_is_proposal_not_dispatch(self):
        self.assertEqual(successor.FROM_V41,
                         "1a40fe4e3ec6e93a1631d59863b95e90981d734e")
        self.assertEqual(successor.ACTIVATED_SEQ, 1829)
        self.assertEqual(successor.ACTIVATED_HASH,
                         "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8")
        self.assertEqual(successor.SCHEMA,
                         "forge.f139.source-transition.v37")



class HybridSyntheticSqlTransactionTests(unittest.TestCase):
    """Real SQLite transaction/rollback; historic V41 replay is NOT simulated as authentic.

    Only the unavailable original 1829-event history and independently authenticated
    cold bundle are substituted. The predecessor snapshot, event grammar, database
    writes, commit, and SQL rollback run against a disposable SQLite database.
    This rehearsal is not an owner release, complete-history proof, or science gate.
    """

    def setUp(self):
        from contextlib import closing
        from pathlib import Path
        import tempfile

        from f139.local_controller import Database

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "state.sqlite"
        self.db = Database.initialize(self.file, successor.FROM_V41)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        self.db.enable_native_two_slots()
        self.target = "b" * 40
        self.predecessor = {
            "schema": successor.v41.SCHEMA,
            "from_source_sha": "c" * 40,
            "to_source_sha": successor.FROM_V41,
        }
        self.db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha,sha) "
            "VALUES(1828,'SOURCE_TRANSITION_ADMITTED',?,?,?)",
            (json.dumps(self.predecessor), "0" * 64, "1" * 64))
        self.db.conn.execute(
            "INSERT INTO events(seq,kind,payload,prior_sha,sha) "
            "VALUES(1829,'V41_ANCHOR','{}',?,?)",
            ("1" * 64, successor.ACTIVATED_HASH))
        self.db.conn.execute(
            "UPDATE meta SET head_seq=?,head_hash=? WHERE id=1",
            (successor.ACTIVATED_SEQ, successor.ACTIVATED_HASH))
        for index in range(153):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,?,?,?,?,?)",
                ("synthetic-positive-%03d" % index, "Wingless",
                 successor.FROM_V41, "VERIFIED", "2" * 64,
                 index + 1, "synthetic-only", "3" * 64))
        for index in range(56):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "quarantine_reason) VALUES(?,?,?,?,?,?)",
                ("synthetic-negative-%03d" % index, "Yggdrasil",
                 successor.FROM_V41, "QUARANTINED", "2" * 64,
                 "synthetic-only"))
        self.before = self.state()

    def state(self):
        return (
            self.db.meta().copy(),
            [tuple(row) for row in self.db.conn.execute(
                "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq")],
            [tuple(row) for row in self.db.conn.execute(
                "SELECT ticket,lane,source_sha,stage,manifest_sha,run_id,"
                "evidence_dir,evidence_sha,quarantine_reason "
                "FROM tasks ORDER BY ticket")],
        )

    def simulated_external_qualification(self, detached=None):
        from contextlib import ExitStack
        from f139.local_controller import Database
        from f139 import nci04_v41_hybrid_cold_bundle as cold

        if detached is None:
            detached = {
                "independent_detached_restore_verified": True,
                "provider_archives_bytes_verified": True,
                "generation_binary_bytes_verified": True,
                "original_owner_mutations": 0,
                "source_transition_authorized": False,
                "hybrid_admission": False,
                "scientific_first_use": False,
                "logical_all_tables_sha256": "4" * 64,
            }
        stack = ExitStack()
        self.addCleanup(stack.close)
        # No synthetic proof can make the historical Database.verify() pass.
        # Only the original historical replay is substituted here.
        stack.enter_context(mock.patch.object(Database, "verify", return_value=None))
        stack.enter_context(mock.patch.object(
            successor, "verify_native_activation", return_value=True))
        stack.enter_context(mock.patch.object(
            successor, "is_migrated", return_value=False))
        detached_mock = stack.enter_context(mock.patch.object(
            cold, "verify_detached_restore", return_value=detached))
        return detached_mock

    def test_atomic_source_commit_keeps_history_and_new_dispatches_zero(self):
        import json
        from f139.local_controller import SingleOwner

        cold = self.simulated_external_qualification()
        with SingleOwner(self.file.with_suffix(".lock")):
            proof = successor.build_proof(
                self.db, self.target, 31, 800001, "5" * 64)
            self.assertEqual(self.state(), self.before)
            cold.assert_called_with(
                self.file.parent / "f139-hybrid-before-800001",
                expected_manifest_sha256="5" * 64,
                target_sha=self.target, run_id=800001,
                expected_head_seq=successor.ACTIVATED_SEQ,
                expected_head_sha256=successor.ACTIVATED_HASH)
            receipt = successor.commit_transition(
                self.db, proof, disabled_owner_witness=lambda: True,
                verified_release_witness=lambda: True)
            with self.assertRaisesRegex(
                    successor.HybridSourceDenied, "IDLE_ORIGINAL_V41_REQUIRED"):
                successor.commit_transition(
                    self.db, proof, disabled_owner_witness=lambda: True,
                    verified_release_witness=lambda: True)
        after_meta, after_events, after_tasks = self.state()
        self.assertEqual(after_meta["source_sha"], self.target)
        self.assertEqual(after_meta["head_seq"], successor.ACTIVATED_SEQ + 1)
        self.assertEqual(after_tasks, self.before[2])
        self.assertEqual(after_events[:len(self.before[1])], self.before[1])
        self.assertEqual(len(after_events), len(self.before[1]) + 1)
        row = self.db.conn.execute(
            "SELECT seq,prior_sha,payload,sha FROM events "
            "WHERE seq=?", (successor.ACTIVATED_SEQ + 1,)).fetchone()
        self.assertEqual(row["prior_sha"], successor.ACTIVATED_HASH)
        self.assertEqual(json.loads(row["payload"]), proof)
        self.assertEqual(row["sha"], receipt["event_head_sha256"])
        self.assertFalse(receipt["task_resume_authorized"])
        self.assertFalse(receipt["hybrid_admission"])
        self.assertFalse(receipt["scientific_first_use"])
        self.assertEqual(receipt["new_dispatches"], 0)

    def test_postwrite_disabled_witness_loss_rolls_back_entire_sql_transaction(self):
        from f139.local_controller import SingleOwner

        self.simulated_external_qualification()
        count = [0]

        def task_disabled():
            count[0] += 1
            return count[0] != 3

        with SingleOwner(self.file.with_suffix(".lock")):
            proof = successor.build_proof(
                self.db, self.target, 31, 800001, "5" * 64)
            with self.assertRaisesRegex(
                    successor.HybridSourceDenied, "POSTCOMMIT_OWNER_HOLD_REQUIRED"):
                successor.commit_transition(
                    self.db, proof, disabled_owner_witness=task_disabled,
                    verified_release_witness=lambda: True)
        self.assertEqual(count[0], 3)
        self.assertEqual(self.state(), self.before)

    def test_cold_bundle_fails_closed_before_any_sql_change(self):
        from f139.local_controller import SingleOwner

        self.simulated_external_qualification({
            "independent_detached_restore_verified": True,
            "provider_archives_bytes_verified": True,
            "generation_binary_bytes_verified": True,
            "original_owner_mutations": 0,
            "source_transition_authorized": False,
            "hybrid_admission": True,
            "scientific_first_use": False,
            "logical_all_tables_sha256": "4" * 64,
        })
        with SingleOwner(self.file.with_suffix(".lock")):
            with self.assertRaisesRegex(
                    successor.HybridSourceDenied,
                    "DETACHED_FULL_COLD_RESTORE_REQUIRED"):
                successor.build_proof(
                    self.db, self.target, 31, 800001, "5" * 64)
        self.assertEqual(self.state(), self.before)

    def test_negative_task_custody_drift_prevents_proof(self):
        from f139.local_controller import SingleOwner

        self.simulated_external_qualification()
        self.db.conn.execute(
            "UPDATE tasks SET stage='VERIFIED',run_id=99999,"
            "evidence_dir='synthetic-only',evidence_sha=? "
            "WHERE ticket='synthetic-negative-000'", ("3" * 64,))
        preflight = self.state()
        with SingleOwner(self.file.with_suffix(".lock")):
            with self.assertRaisesRegex(
                    successor.HybridSourceDenied,
                    "HISTORIC_TERMINAL_CUSTODY_DRIFT"):
                successor.build_proof(
                    self.db, self.target, 31, 800001, "5" * 64)
        self.assertEqual(self.state(), preflight)

if __name__ == "__main__":
    unittest.main()
