"""Source-free V41-to-Hybrid cold pair verification and negative controls."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_hybrid_cold_pair as cold


class HybridColdPairTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.data = Path(self.root.name)
        self.original_path = self.data / "state.sqlite"
        with closing(Database.initialize(self.original_path, cold.V41_SOURCE)):
            pass
        self.backup_dir = self.data / "f139-hybrid-before-12345"
        self.backup_dir.mkdir()
        self.backup_path = self.backup_dir / "state.sqlite"
        with closing(sqlite3.connect(self.backup_path)) as target:
            with closing(sqlite3.connect(self.original_path)) as original:
                original.backup(target)

    def run_pair(self, *, path=None, sha=None, lease=True, lower_history=True):
        # The synthetic initialized database has no 1829-event owner history.
        # Only production keeps MIN_V41_HEAD=1829; this isolates parity logic.
        with patch.object(cold, "MIN_V41_HEAD", 0 if lower_history else 1829):
            with closing(Database.open_readonly(self.original_path)) as original:
                if not lease:
                    return cold.verify_original_sqlite_pair(
                        original, path or self.backup_path,
                        target_sha=sha or cold.HYBRID_CANDIDATE)
                with SingleOwner(self.original_path.with_suffix(".lock")):
                    return cold.verify_original_sqlite_pair(
                        original, path or self.backup_path,
                        target_sha=sha or cold.HYBRID_CANDIDATE)

    def test_exact_original_and_clean_standalone_copy_match(self):
        receipt = self.run_pair()
        self.assertEqual(receipt["from_source_sha"], cold.V41_SOURCE)
        self.assertEqual(receipt["to_source_sha"], cold.HYBRID_CANDIDATE)
        self.assertEqual(receipt["original_sqlite_mutations"], 0)
        self.assertFalse(receipt["owner_release_authorized"])
        self.assertFalse(receipt["hybrid_policy_active"])
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["provider_archives_cold_restored"])

    def test_history_floor_is_not_satisfied_by_synthetic_fixture(self):
        with self.assertRaises(cold.HybridColdPairDenied):
            self.run_pair(lower_history=False)

    def test_missing_original_mutex_is_denied(self):
        with self.assertRaisesRegex(cold.HybridColdPairDenied, "MUTEX"):
            self.run_pair(lease=False)

    def test_candidate_sha_must_be_exact(self):
        with self.assertRaisesRegex(cold.HybridColdPairDenied, "CANDIDATE"):
            self.run_pair(sha="f" * 40)

    def test_stale_sqlite_backup_is_denied(self):
        with sqlite3.connect(self.backup_path) as copy:
            copy.execute("UPDATE meta SET head_seq=head_seq+1 WHERE id=1")
        with self.assertRaisesRegex(cold.HybridColdPairDenied, "PARITY"):
            self.run_pair()

    def test_sidecar_is_denied_without_opening_backup(self):
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.backup_path) + suffix)
            sidecar.write_bytes(b"unused")
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(cold.HybridColdPairDenied, "SIDECAR"):
                    self.run_pair()
            sidecar.unlink()

    def test_unscoped_backup_directory_is_denied(self):
        different = self.data / "unscoped"
        different.mkdir()
        alternate = different / "state.sqlite"
        alternate.write_bytes(self.backup_path.read_bytes())
        with self.assertRaisesRegex(cold.HybridColdPairDenied, "OWNER_SCOPED"):
            self.run_pair(path=alternate)

    def test_symlinked_backup_denied_where_platform_permits_it(self):
        destination = self.backup_dir / "real.sqlite"
        self.backup_path.replace(destination)
        try:
            self.backup_path.symlink_to(destination)
        except (NotImplementedError, OSError):
            self.skipTest("symlink creation unavailable on this platform")
        with self.assertRaisesRegex(cold.HybridColdPairDenied, "OWNER_SCOPED"):
            self.run_pair()

    def test_original_policy_and_live_admission_are_not_changed(self):
        self.run_pair()
        with closing(Database.open_readonly(self.original_path)) as original:
            self.assertEqual(original.meta()["source_sha"], cold.V41_SOURCE)
            from f139.hybrid_owner_admission import is_migrated
            self.assertFalse(is_migrated(original))


if __name__ == "__main__":
    unittest.main()
