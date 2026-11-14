"""Read-only uncertainty classification on disposable SQLite, no owner admission.

Historical 1829-event verifier and external provider archives are simulated.
These are real SQL query-only tests, NOT genuine original-host cold acceptance.
"""
from contextlib import closing
from pathlib import Path
import unittest
from unittest import mock

from f139 import nci04_v41_hybrid_held_recovery as recovery
from f139 import nci04_v41_hybrid_original_commit as commit
from f139 import nci04_v41_hybrid_source_transition as source
from f139.local_controller import Database, SingleOwner
from f139 import test_nci04_v41_hybrid_source_transition as fixture_tests


class HeldReadOnlyRecoveryFixtureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_tests.HybridSyntheticSqlTransactionTests(
            "test_atomic_source_commit_keeps_history_and_new_dispatches_zero")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.cold = self.fixture.simulated_external_qualification()
        self.req = {
            "target_source_sha": self.fixture.target,
            "original_head_seq": source.ACTIVATED_SEQ,
            "original_head_sha256": source.ACTIVATED_HASH,
            "backup_run_id": 800001,
            "backup_manifest_sha256": "5" * 64,
            "readiness_comment_id": 31,
        }

    def inspect(self):
        with closing(Database.open_readonly(self.fixture.file)) as db:
            return recovery.inspect_held_ledger(db, self.req)

    def commit(self):
        f = self.fixture
        proof = source.build_proof(
            f.db, f.target, 31, 800001, "5" * 64)
        receipt = source.commit_transition(
            f.db, proof,
            disabled_owner_witness=lambda: True,
            verified_release_witness=lambda: True)
        return proof, receipt

    def test_uncommitted_exact_preimage_is_classified_without_mutation(self):
        with SingleOwner(self.fixture.file.with_suffix(".lock")):
            before = self.fixture.state()
            view = self.inspect()
            self.assertEqual(self.fixture.state(), before)
            self.assertEqual(view["classification"], "PRECOMMIT_UNCHANGED_HOLD")
            self.assertFalse(view["source_commit_recorded"])
            self.assertFalse(view["source_commit_retry_authorized"])
            self.assertFalse(view["restore_older_sqlite_authorized"])
            self.assertFalse(view["original_task_resume_authorized"])
            self.assertEqual(view["readback_database_mutations"], 0)
            self.cold.assert_called_with(
                self.fixture.file.parent / "f139-hybrid-before-800001",
                expected_manifest_sha256="5" * 64,
                target_sha=self.fixture.target, run_id=800001,
                expected_head_seq=source.ACTIVATED_SEQ,
                expected_head_sha256=source.ACTIVATED_HASH)

    def test_commit_receipt_lost_but_exact_v37_event_still_identifiable(self):
        with SingleOwner(self.fixture.file.with_suffix(".lock")):
            self.commit()
            before = self.fixture.state()
            result = self.inspect()
            self.assertEqual(self.fixture.state(), before)
            self.assertEqual(result["classification"], "COMMITTED_SOURCE_HOLD")
            self.assertTrue(result["source_commit_recorded"])
            self.assertEqual(result["event_seq"], source.ACTIVATED_SEQ + 1)
            self.assertFalse(result["source_commit_retry_authorized"])
            self.assertFalse(result["original_task_resume_authorized"])
            self.assertFalse(result["hybrid_admission"])
            self.assertFalse(result["scientific_first_use"])

    def test_wrong_preimage_head_or_backup_fails_closed(self):
        with SingleOwner(self.fixture.file.with_suffix(".lock")):
            for key, bad in (
                    ("original_head_seq", source.ACTIVATED_SEQ+1),
                    ("original_head_sha256", "f"*64),
                    ("readiness_comment_id", 0)):
                old = self.req[key]
                self.req[key] = bad
                try:
                    with self.subTest(key=key), self.assertRaises(
                            recovery.HeldRecoveryDenied):
                        self.inspect()
                finally:
                    self.req[key] = old

    def test_wrong_postcommit_source_backup_or_owner_identity_denied(self):
        with SingleOwner(self.fixture.file.with_suffix(".lock")):
            self.commit()
            for key, bad in (
                    ("original_head_seq", source.ACTIVATED_SEQ+1),
                    ("original_head_sha256", "f"*64),
                    ("target_source_sha", "e"*40),
                    ("backup_run_id", 800002),
                    ("backup_manifest_sha256", "f"*64),
                    ("readiness_comment_id", 32)):
                old = self.req[key]
                self.req[key] = bad
                try:
                    with self.subTest(key=key), self.assertRaises(
                            recovery.HeldRecoveryDenied):
                        self.inspect()
                finally:
                    self.req[key] = old

    def test_absent_original_lock_or_wrong_connection_denied(self):
        with self.assertRaisesRegex(
                recovery.HeldRecoveryDenied,
                "AUTHENTICATED_READONLY_OR_FROZEN_REQUEST_REQUIRED"):
            recovery.inspect_held_ledger(self.fixture.db, self.req)
        with closing(Database.open_readonly(self.fixture.file)) as db:
            with self.assertRaisesRegex(
                    recovery.HeldRecoveryDenied,
                    "AUTHENTICATED_READONLY_OR_FROZEN_REQUEST_REQUIRED"):
                recovery.inspect_held_ledger(db, self.req)

    def test_bad_cold_restore_is_not_recovery_authority(self):
        self.cold.return_value = {
            "independent_detached_restore_verified": False,
            "provider_archives_bytes_verified": True,
            "generation_binary_bytes_verified": True,
            "original_owner_mutations": 0,
            "source_transition_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
            "logical_all_tables_sha256": "4"*64}
        with SingleOwner(self.fixture.file.with_suffix(".lock")):
            with self.assertRaisesRegex(
                    recovery.HeldRecoveryDenied,
                    "FROZEN_FULL_COLD_BUNDLE_REQUIRED"):
                self.inspect()

    def test_new_readonly_route_never_replays_or_controls_owner(self):
        program = Path(recovery.__file__).read_text("utf-8")
        for forbidden in (
                "commit_transition(", "Disable-ScheduledTask",
                "Start-ScheduledTask", "Stop-ScheduledTask",
                "Enable-ScheduledTask", "Set-ScheduledTask",
                "UPDATE meta SET", "workflow_dispatch(",
                "gh api --method PATCH"):
            self.assertNotIn(forbidden, program)
        with self.assertRaisesRegex(
                recovery.HeldRecoveryDenied, "ORIGINAL_WINDOWS_NATIVE_PROVIDER_REQUIRED"):
            recovery.inspect_original(
                Path("/tmp/untrusted.sqlite"), {}, {}, object())


if __name__ == "__main__":
    unittest.main()
