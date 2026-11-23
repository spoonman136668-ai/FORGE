"""Synthetic V41 copy-integrity adversarial tests (never original owner)."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_cold_copy_verifier as v41
from f139.nci04_v41_catalog_recovery_preflight import (
    OWNER_SOURCE as FROM, V41ReadOnlyDenied as RecoveryPreflightDenied)

TARGET = "7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595"


class OriginalCopyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.origin = self.root / "state.sqlite"
        with closing(Database.initialize(self.origin, FROM)):
            pass
        self.run_id = 71234
        self.backup = self.root / ("f139-v41-before-" + str(self.run_id)) / "state.sqlite"
        self.backup.parent.mkdir()
        with closing(sqlite3.connect(str(self.origin))) as src:
            with closing(sqlite3.connect(str(self.backup))) as dst:
                src.backup(dst)

    def hash(self):
        return hashlib.sha256(self.backup.read_bytes()).hexdigest()

    def proof(self, original):
        meta = original.meta()
        return {
            "source_sha": FROM,
            "original_head_seq": meta["head_seq"],
            "original_head_sha256": meta["head_hash"],
            "verified_historical_tasks": 153,
            "quarantined_historical_tasks": 56,
            "source_transition_authorized": False, "scientific_first_use": False,
        }

    def attempt(self, *, sha=None, path=None, run_id=None, fake=None, archives=None,
                generation=None, locked=True):
        with SingleOwner(self.origin.with_suffix(".lock")):
            with closing(Database.open_readonly(self.origin)) as db:
                with patch.object(v41.SingleOwner, "held", return_value=locked), \
                     patch.object(v41, "original_ledger_preflight",
                                  side_effect=(fake if fake is not None else self.proof)), \
                     patch.object(v41, "source_preflight",
                                  side_effect=lambda get, target: {
                                      "original_source_sha": FROM,
                                      "target_source_sha": TARGET,
                                      "unique_eligible_issues": 200,
                                      "source_transition_authorized": False,
                                      "scientific_first_use": False}), \
                     patch.object(v41, "copy_provider_archives",
                                  side_effect=archives or (lambda *a, **k: {"provider": "1"*64})), \
                     patch.object(v41, "copy_generation_executable",
                                  side_effect=generation or (lambda *a, **k: {"binary": "2"*64})):
                    return v41.verify_cold_copy(
                        db, path if path is not None else self.backup,
                        lambda _: None, target=TARGET,
                        run_id=self.run_id if run_id is None else run_id,
                        expected_backup_sha256=self.hash() if sha is None else sha)

    def test_actual_sqlite_cold_copy_passes_with_zero_effects(self):
        proof = self.attempt()
        self.assertEqual(proof["schema"],
                         "forge.f139.v41.original-owner-cold-copy-readonly.v1")
        self.assertEqual(proof["backup_sha256"], self.hash())
        # Reading a valid WAL-format standalone DB must not generate SHM/WAL.
        for suffix in ("-wal", "-shm", "-journal"):
            self.assertFalse(Path(str(self.backup) + suffix).exists())
        self.assertEqual(proof["preserved_quarantined_tasks"], 56)
        self.assertFalse(proof["source_transition_authorized"])
        self.assertFalse(proof["scientific_first_use"])
        self.assertEqual(proof["original_owner_mutations"], 0)

    def test_backup_byte_digest_and_bound_directory_are_mandatory(self):
        with self.assertRaises(RecoveryPreflightDenied):
            self.attempt(sha="0"*64)
        with self.assertRaises(RecoveryPreflightDenied):
            self.attempt(sha="INVALID")
        with self.assertRaises(RecoveryPreflightDenied):
            self.attempt(run_id=9999)
        with self.assertRaises(RecoveryPreflightDenied):
            self.attempt(path=self.origin)

    def test_valid_sqlite_backup_with_extra_table_cannot_be_reported_identical(self):
        with closing(sqlite3.connect(str(self.backup))) as conn:
            conn.execute("CREATE TABLE forged_user_table (item TEXT)")
            conn.commit()
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "COLD_ALL_TABLE_LOGICAL_DRIFT"):
            self.attempt()

    def test_committed_wal_only_data_cannot_pass_main_file_sha(self):
        # This is the actual reviewed P1: a committed WAL contains a table
        # absent from the hashed main SQLite file. Keep the writer open to
        # prevent connection-close checkpoint from hiding the failure.
        with closing(sqlite3.connect(str(self.backup), isolation_level=None)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA wal_autocheckpoint=0")
            conn.execute("CREATE TABLE wal_only_verified (value TEXT)")
            self.assertTrue(Path(str(self.backup) + "-wal").exists())
            with self.assertRaisesRegex(RecoveryPreflightDenied,
                                        "COLD_BACKUP_SQLITE_SIDECAR_PRESENT"):
                self.attempt()

    def test_empty_or_dangling_backup_sidecars_are_denied(self):
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.backup) + suffix)
            sidecar.write_bytes(b"")
            with self.subTest(suffix=suffix), self.assertRaisesRegex(
                    RecoveryPreflightDenied, "COLD_BACKUP_SQLITE_SIDECAR_PRESENT"):
                self.attempt()
            sidecar.unlink()

    def test_backup_changed_after_logical_verification_is_denied(self):
        def change_backup(*args, **kwargs):
            # Test-side mutation of disposable backup only; original is ro.
            with self.backup.open("ab") as stream:
                stream.write(b"postcopy-tamper")
            return {"provider": "1"*64}
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "COLD_BACKUP_CHANGED_DURING_VERIFICATION"):
            self.attempt(archives=change_backup)

    def test_aba_swap_of_backup_path_cannot_change_hashed_query_snapshot(self):
        # Reproduce reviewed P2: the external file has stale bytes at both
        # checks, but is replaced by the correct original during SQL open.
        # The verifier-owned isolated snapshot MUST remain stale and fail
        # full logical parity instead of trusting the mutable pathname.
        with closing(sqlite3.connect(str(self.origin))) as conn:
            conn.execute("CREATE TABLE original_only_for_aba (value TEXT)")
            conn.commit()
        old_bytes = self.backup.read_bytes()
        current_bytes = self.origin.read_bytes()
        real_open = v41._open_immutable_hashed_backup
        seen_private = []
        def swap_backing_file(private):
            self.assertNotEqual(private.resolve(), self.backup.resolve())
            seen_private.append(private)
            self.backup.write_bytes(current_bytes)
            try:
                return real_open(private)
            finally:
                self.backup.write_bytes(old_bytes)
        with patch.object(v41, "_open_immutable_hashed_backup",
                          side_effect=swap_backing_file):
            with self.assertRaisesRegex(RecoveryPreflightDenied,
                                        "COLD_ALL_TABLE_LOGICAL_DRIFT"):
                self.attempt()
        self.assertEqual(len(seen_private), 1)
        self.assertEqual(self.backup.read_bytes(), old_bytes)
        self.assertFalse(seen_private[0].exists())

    def test_private_snapshot_is_proven_to_match_supplied_backup_hash(self):
        receipt = self.attempt()
        self.assertEqual(receipt["verified_isolated_snapshot_sha256"], self.hash())

    def test_cold_copy_head_drift_is_not_hidden_by_matching_bytes(self):
        with closing(sqlite3.connect(str(self.backup))) as con:
            con.execute("UPDATE meta SET source_sha=? WHERE id=1", ("3"*40,))
            con.commit()
        with self.assertRaises(Exception):
            self.attempt()

    def test_original_mutex_cannot_be_simulated_by_backup(self):
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "ORIGINAL_MUTEX_READONLY_REQUIRED"):
            self.attempt(locked=False)

    def test_readonly_copy_cannot_be_substituted_or_symlinked(self):
        alias = self.backup.with_name("alias.sqlite")
        try:
            alias.symlink_to(self.backup)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on runner")
        with self.assertRaises(RecoveryPreflightDenied):
            self.attempt(path=alias)

    def test_missing_archive_or_generation_custody_denied(self):
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "ORIGINAL_ARCHIVE_OR_BINARY_MISSING"):
            self.attempt(archives=lambda *a, **k: {})
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "ORIGINAL_ARCHIVE_OR_BINARY_MISSING"):
            self.attempt(generation=lambda *a, **k: {})
        def missing(*args, **kwargs):
            raise FileNotFoundError("original provider ZIP absent")
        with self.assertRaises(FileNotFoundError):
            self.attempt(archives=missing)

    def test_preflight_must_pin_exact_original_head_and_never_authorize(self):
        def incorrect(db):
            state = self.proof(db)
            state["source_transition_authorized"] = True
            return state
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "ORIGINAL_PREFLIGHT_NOT_AUTHENTIC"):
            self.attempt(fake=incorrect)
        def wrong(db):
            state = self.proof(db)
            state["original_head_seq"] += 1
            return state
        with self.assertRaisesRegex(RecoveryPreflightDenied,
                                    "ORIGINAL_PREFLIGHT_NOT_AUTHENTIC"):
            self.attempt(fake=wrong)

    def test_only_exact_original_readonly_database_accepted(self):
        with SingleOwner(self.origin.with_suffix(".lock")):
            with closing(Database(self.origin)) as db:
                with self.assertRaises(RecoveryPreflightDenied):
                    v41.verify_cold_copy(
                        db, self.backup, lambda _: None, target=TARGET,
                        run_id=self.run_id, expected_backup_sha256=self.hash())

    def test_no_controller_start_or_source_transition_from_verifier(self):
        import inspect
        code = inspect.getsource(v41)
        for prohibited in ("db.transition_source(", "db.event(",
                           "Disable-ScheduledTask", "Start-ScheduledTask",
                           'get("POST"', "create_ref(", "workflow_dispatch("):
            self.assertNotIn(prohibited, code)


if __name__ == "__main__":
    unittest.main()
