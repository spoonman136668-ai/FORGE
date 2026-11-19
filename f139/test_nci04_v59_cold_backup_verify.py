"""V59 source-bound cold backup path/authority negative controls.

Synthetic private files are not original-owner scientific or source receipts.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v59_cold_backup_verify as v59


class V59ColdBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "FORGE-F139"
        self.root.mkdir()
        self.original = self.root / "state.sqlite"
        self.original.write_bytes(b"x"*2048)
        self.run = v59.MIN_RUN + 4
        self.folder = self.root / ("f139-v59-before-"+str(self.run))
        self.folder.mkdir()
        self.backup = self.folder / "state.sqlite"
        self.backup.write_bytes(b"x"*2048)

    def bound(self, original=None, backup=None, run=None):
        return v59.frozen_backup_destination(
            original or self.original, backup or self.backup,
            self.run if run is None else run)

    def test_canonical_path(self):
        self.assertEqual(self.bound(), self.backup)

    def test_reject_older_or_untyped_owner_run(self):
        for run in (v59.MIN_RUN, v59.MIN_RUN-1, True, str(self.run)):
            with self.subTest(run=run):
                with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                            "OWNER_RUN_INVALID"):
                    self.bound(run=run)

    def test_reject_wrong_path_and_too_small_copy(self):
        other = self.root / "outside"
        other.mkdir()
        file = other / "state.sqlite"
        file.write_bytes(b"x"*2048)
        with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                    "BACKUP_PATH_OR_SIZE_INVALID"):
            self.bound(backup=file)
        self.backup.write_bytes(b"tiny")
        with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                    "BACKUP_PATH_OR_SIZE_INVALID"):
            self.bound()

    def test_original_absent_fail_closed(self):
        self.original.unlink()
        with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                    "ORIGINAL_OR_BACKUP_FILE_INVALID"):
            self.bound()

    def test_reject_symlinked_backup_folder(self):
        alias = self.root / ("f139-v59-before-"+str(self.run+1))
        try:
            alias.symlink_to(self.folder, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(v59.V59ColdBackupDenied):
            self.bound(backup=alias/"state.sqlite",run=self.run+1)

    def test_counterfeit_database_rejected_before_any_backup_io(self):
        with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                    "ORIGINAL_READONLY_REQUIRED"):
            v59.verify_original_cold_backup(
                object(), self.backup,owner_run_id=self.run,target="a"*40,
                expected_backup_sha256="a"*64)

    def test_refuse_missing_mutex_and_unsafe_target(self):
        class FakeResult:
            def fetchone(self):
                return (1,)
        class FakeConn:
            def execute(self, cmd):
                return FakeResult()
        class FakeDb:
            def __init__(self, filename):
                self.filename=filename
                self.conn=FakeConn()
                self._readonly_opened=True
        db=FakeDb(self.original)
        with patch.object(v59, "Database", FakeDb), \
             patch.object(v59.SingleOwner, "held", return_value=False):
            with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                        "ORIGINAL_MUTEX_REQUIRED"):
                v59.verify_original_cold_backup(
                    db,self.backup,owner_run_id=self.run,target="a"*40,
                    expected_backup_sha256="a"*64)
        with patch.object(v59, "Database", FakeDb), \
             patch.object(v59.SingleOwner, "held", return_value=True):
            for target,digest in (("a"*39,"a"*64),
                                  (v59.SOURCE,"a"*64),
                                  ("a"*40,"private"),
                                  ("a"*40,"G"*64)):
                with self.subTest(target=target):
                    with self.assertRaisesRegex(v59.V59ColdBackupDenied,
                                                "TARGET_OR_SHA_INVALID"):
                        v59.verify_original_cold_backup(
                            db,self.backup,owner_run_id=self.run,
                            target=target,expected_backup_sha256=digest)

    def test_module_is_readonly_not_a_release_route(self):
        source=Path(__file__).with_name("nci04_v59_cold_backup_verify.py").read_text()
        self.assertNotIn("sqlite3.connect",source)
        self.assertNotIn("Register-ScheduledTask",source)
        self.assertNotIn("gh api",source)
        self.assertNotIn("UPDATE meta",source)
        self.assertNotIn("db.event(",source)
        self.assertIn('"source_transition_authorized": False',source)


if __name__=="__main__":
    unittest.main()
