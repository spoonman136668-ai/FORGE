"""V41 original Windows read-only route: fail-closed source and owner checks."""
from contextlib import closing
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, F139Error, GitHub, SingleOwner
from f139 import nci04_v41_original_owner_status as route
from f139 import nci04_v41_catalog_recovery_preflight as source


class V41OriginalOwnerStatusTests(unittest.TestCase):
    def test_unapproved_event_never_calls_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.sqlite"
            with patch.object(GitHub, "native_repo_get",
                              side_effect=AssertionError("provider read")):
                for environment in ({}, {"GITHUB_REPOSITORY":source.REPO,
                                          "GITHUB_SHA":"9"*40}):
                    with self.subTest(environment=environment):
                        with self.assertRaisesRegex(
                                route.V41StatusDenied,
                                "EXACT_ORIGINAL_OWNER_RUNNER_EVENT"):
                            route.main(["--db",str(path),"--target","9"*40],
                                       environ=environment,event={})

    def test_wrong_target_or_absent_db_fails_before_get(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"state.sqlite"
            with patch.object(source, "source_preflight",
                              side_effect=AssertionError("should not GET")):
                for target in ("", "bad", source.OWNER_SOURCE, None):
                    with self.subTest(target=target):
                        with self.assertRaises(route.V41StatusDenied):
                            route.inspect_original(path,GitHub(),target=target)
                with self.assertRaises(route.V41StatusDenied):
                    route.inspect_original(path,GitHub(),target="9"*40)

    def test_mock_remote_is_not_authentic_original_sqlite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.sqlite"
            with closing(Database.initialize(path,source.OWNER_SOURCE)) as original:
                meta=original.meta().copy()
            with patch.object(source, "source_preflight",
                              return_value={"issues_per_page":[100,100,0],
                                            "unique_eligible_issues":200}):
                with self.assertRaises(source.V41ReadOnlyDenied):
                    route.inspect_original(path,GitHub(),target="9"*40)
            with closing(Database.open_readonly(path)) as readonly:
                self.assertEqual(readonly.meta(),meta)
                self.assertEqual(readonly.conn.total_changes,0)


    def test_failed_backup_forensic_inventory_reads_no_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "state.sqlite"
            db.write_bytes(b"unchanged original")
            self.assertEqual(route.inspect_failed_backup_stage(db)
                             ["classification"], "ABSENT")
            folder = root / ("f139-v41-before-" + str(route.FAILED_BACKUP_RUN))
            folder.mkdir()
            (folder / "state.sqlite").write_bytes(b"private backup")
            self.assertEqual(route.inspect_failed_backup_stage(db)
                             ["classification"], "PARTIAL_AFTER_SQLITE")
            archive = folder / "provider-custody" / "f139-nci04-example" / "7"
            archive.mkdir(parents=True)
            (archive / "manifest.json").write_bytes(b"private provider")
            self.assertEqual(route.inspect_failed_backup_stage(db)
                             ["classification"], "PARTIAL_AFTER_PROVIDER")
            gen = folder / "prior-generation-custody" / ("a" * 40)
            gen.mkdir(parents=True)
            (gen / "f139-genenv-source.exe").write_bytes(b"private binary")
            self.assertEqual(route.inspect_failed_backup_stage(db)
                             ["classification"], "PARTIAL_AFTER_PRIOR_BINARY")
            (folder / "manifest.sha256.json").write_bytes(b"not valid seal")
            with patch("builtins.open", side_effect=AssertionError("content read")):
                result = route.inspect_failed_backup_stage(db)
            self.assertEqual(result["classification"],
                             "SEALED_MARKER_PRESENT_UNVERIFIED")
            self.assertTrue(result["sealed_manifest_present"])
            self.assertEqual(result["provider_file_count"], 1)
            self.assertEqual(result["prior_binary_file_count"], 1)
            for key in ("contents_read", "original_db_written", "backup_retried"):
                self.assertFalse(result[key])
            self.assertEqual(result["task_mutations"], 0)
            self.assertEqual(db.read_bytes(), b"unchanged original")

    def test_failed_backup_forensic_deny_symlink_and_wrong_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "state.sqlite"
            db.write_bytes(b"immutable")
            folder = root / ("f139-v41-before-" + str(route.FAILED_BACKUP_RUN))
            folder.write_bytes(b"not a folder")
            self.assertEqual(route.inspect_failed_backup_stage(db)
                             ["classification"], "NON_DIRECTORY")
            folder.unlink()
            try:
                folder.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            else:
                self.assertEqual(route.inspect_failed_backup_stage(db)
                                 ["classification"], "UNTRUSTED_LINK")
            with self.assertRaises(route.V41StatusDenied):
                route.inspect_failed_backup_stage(Path("state.sqlite"))


    def test_failed_backup_inventory_resolves_previous_300_entry_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "state.sqlite"
            db.write_bytes(b"immutable-original")
            folder = base / ("f139-v41-before-" + str(route.FAILED_BACKUP_RUN))
            folder.mkdir()
            (folder / "state.sqlite").write_bytes(b"private")
            for i in range(110):
                custody = folder / "provider-custody" / ("f139-nci04-ticket-" + str(i)) / "7"
                custody.mkdir(parents=True)
                for name in ("manifest.json", "ubuntu-latest.zip", "windows-latest.zip"):
                    (custody / name).write_bytes(b"secret")
            binary = folder / "prior-generation-custody" / ("a" * 40)
            binary.mkdir(parents=True)
            (binary / "f139-genenv-source.exe").write_bytes(b"secret")
            with patch("builtins.open", side_effect=AssertionError("no file read")):
                result = route.inspect_failed_backup_stage(db)
            self.assertTrue(result["inventory_complete"])
            self.assertGreater(result["entries_scanned"], 300)
            self.assertLess(result["entries_scanned"], route.MAX_FORENSIC_ENTRIES)
            self.assertEqual(result["classification"], "PARTIAL_AFTER_PRIOR_BINARY")
            self.assertEqual(result["provider_complete_groups"], 110)
            self.assertEqual(result["provider_incomplete_groups"], 0)
            self.assertEqual(result["provider_file_count"], 330)
            self.assertEqual(result["prior_binary_file_count"], 1)
            self.assertEqual(db.read_bytes(), b"immutable-original")

    def test_failed_backup_inventory_stays_bounded_and_rejects_partial_custody(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = base / "state.sqlite"
            db.write_bytes(b"immutable-original")
            folder = base / ("f139-v41-before-" + str(route.FAILED_BACKUP_RUN))
            package = folder / "provider-custody" / "f139-nci04-missing-one" / "7"
            package.mkdir(parents=True)
            (package / "manifest.json").write_bytes(b"private")
            result = route.inspect_failed_backup_stage(db)
            self.assertTrue(result["inventory_complete"])
            self.assertEqual(result["provider_incomplete_groups"], 1)
            self.assertEqual(result["provider_complete_groups"], 0)
            with patch.object(route, "MAX_FORENSIC_ENTRIES", 2):
                denied = route.inspect_failed_backup_stage(db)
            self.assertEqual(denied["classification"], "ENTRY_LIMIT")
            self.assertFalse(denied["inventory_complete"])
            self.assertEqual(denied["entries_scanned"], 2)
            self.assertFalse(denied["contents_read"])
            self.assertEqual(db.read_bytes(), b"immutable-original")


    def test_original_live_mutex_contention_is_bounded_and_never_bypassed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            with closing(Database.initialize(path, source.OWNER_SOURCE)):
                pass
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            lock_path = path.with_suffix(".lock")
            waits = []
            with SingleOwner(lock_path):
                with patch.object(route, "OWNER_MUTEX_MAX_RETRIES", 2):
                    with self.assertRaisesRegex(
                            route.V41StatusDenied,
                            "ORIGINAL_MUTEX_STILL_BUSY"):
                        with route._read_only_owner_lease(
                                path, wait=waits.append):
                            self.fail("must not bypass original kernel lock")
                self.assertTrue(SingleOwner.held(lock_path))
            self.assertEqual(waits, [route.OWNER_MUTEX_RETRY_SECONDS] * 2)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             before)

    def test_original_mutex_release_observed_only_after_real_lock_acquired(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            with closing(Database.initialize(path, source.OWNER_SOURCE)):
                pass
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            lock_path = path.with_suffix(".lock")
            owner = SingleOwner(lock_path)
            owner.__enter__()
            waits = []
            def relinquish(delay):
                waits.append(delay)
                owner.__exit__(None, None, None)
            try:
                with route._read_only_owner_lease(path, wait=relinquish):
                    self.assertTrue(SingleOwner.held(lock_path))
                    with closing(Database.open_readonly(path)) as cold:
                        self.assertEqual(cold.conn.execute(
                            "PRAGMA query_only").fetchone()[0], 1)
                        self.assertEqual(cold.meta()["source_sha"],
                                         source.OWNER_SOURCE)
            finally:
                if owner.fd is not None:
                    owner.__exit__(None, None, None)
            self.assertEqual(waits, [route.OWNER_MUTEX_RETRY_SECONDS])
            self.assertFalse(SingleOwner.held(lock_path))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             before)

    def test_unexpected_mutex_error_or_body_failure_is_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            waits = []
            with patch.object(route, "SingleOwner") as one:
                one.return_value.__enter__.side_effect = F139Error(
                    "F139_DIFFERENT_OWNER_FAILURE")
                with self.assertRaisesRegex(
                        F139Error, "DIFFERENT_OWNER_FAILURE"):
                    with route._read_only_owner_lease(path, wait=waits.append):
                        self.fail("unexpected mutex error")
                self.assertEqual(one.return_value.__enter__.call_count, 1)
                self.assertEqual(waits, [])
            with self.assertRaisesRegex(F139Error, "ALREADY_RUNNING"):
                with route._read_only_owner_lease(path, wait=waits.append):
                    raise F139Error("F139_CONTROLLER_ALREADY_RUNNING")
            self.assertEqual(waits, [])
            self.assertFalse(SingleOwner.held(path.with_suffix(".lock")))

    def test_existing_mutation_routes_are_not_exposed(self):
        import inspect
        code=inspect.getsource(route)
        for forbidden in ("db.event(", "db.transition_source(",
                          "workflow_dispatch(", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Disable-ScheduledTask",
                          ".post(", "create_ref("):
            self.assertNotIn(forbidden,code)
        self.assertFalse(hasattr(route,"commit_transition"))
        self.assertFalse(hasattr(route,"install_release"))
        self.assertFalse(hasattr(route,"reactivate_native"))


    def test_bounded_failed_copy_probe_reports_failure_without_replay(self):
        from f139 import nci04_v41_cold_copy_verifier as cold
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "state.sqlite"
            with closing(Database.initialize(path, source.OWNER_SOURCE)):
                pass
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            folder = root / ("f139-v41-before-" + str(route.FAILED_BACKUP_RUN))
            group = folder / "provider-custody" / "f139-nci04-test" / "7"
            group.mkdir(parents=True)
            for name in ("manifest.json", "ubuntu-latest.zip", "windows-latest.zip"):
                (group / name).write_bytes(b"private")
            binary = folder / "prior-generation-custody" / (source.OWNER_SOURCE)
            binary.mkdir(parents=True)
            (binary / "f139-genenv-source.exe").write_bytes(b"private")
            (folder / "state.sqlite").write_bytes(b"private backup")
            inventory = route.inspect_failed_backup_stage(path)
            self.assertTrue(inventory["inventory_complete"])
            self.assertEqual(inventory["classification"],
                             "PARTIAL_AFTER_PRIOR_BINARY")

            with SingleOwner(path.with_suffix(".lock")):
                with closing(Database.open_readonly(path)) as original:
                    with patch.object(cold, "verify_cold_copy",
                                      side_effect=ValueError(
                                          "F139_V41_COLD_BACKUP_BYTES_DRIFT")) as check:
                        report = route.inspect_failed_backup_cold_copy(
                            original, lambda _: None, target="9"*40,
                            inventory=inventory)
                    self.assertTrue(report["attempted"])
                    self.assertTrue(report["snapshot_hash_checked"])
                    self.assertFalse(report["cold_copy_verified"])
                    self.assertEqual(report["failure_code"],
                                     "F139_V41_COLD_BACKUP_BYTES_DRIFT")
                    self.assertEqual(check.call_count, 1)
                    self.assertEqual(original.conn.total_changes, 0)

                    with patch.object(cold, "verify_cold_copy",
                                      side_effect=RuntimeError(
                                          "C:/private/secret/provider")):
                        secret = route.inspect_failed_backup_cold_copy(
                            original, lambda _: None, target="9"*40,
                            inventory=inventory)
                    self.assertEqual(secret["failure_code"],
                                     "UNCLASSIFIED_EXCEPTION")
                    self.assertNotIn("secret", str(secret))
                    self.assertFalse(secret["copied_backup_written"])
                    self.assertFalse(secret["backup_retried"])

                    with patch.object(cold, "verify_cold_copy",
                                      side_effect=AssertionError(
                                          "should not read stage")):
                        skipped = route.inspect_failed_backup_cold_copy(
                            original, lambda _: None, target="9"*40,
                            inventory={**inventory,
                                       "provider_incomplete_groups": 1})
                    self.assertFalse(skipped["attempted"])
                    self.assertEqual(skipped["failure_code"], "NOT_ELIGIBLE")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             before)
            self.assertFalse((folder / "manifest.sha256.json").exists())

    def test_untrusted_failed_backup_stage_cannot_trigger_content_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            with closing(Database.initialize(path, source.OWNER_SOURCE)):
                pass
            with SingleOwner(path.with_suffix(".lock")):
                with closing(Database.open_readonly(path)) as original:
                    report = route.inspect_failed_backup_cold_copy(
                        original, lambda _: None, target="9"*40,
                        inventory={"failed_run_id": route.FAILED_BACKUP_RUN,
                                   "classification": "UNTRUSTED_LINK",
                                   "inventory_complete": True})
                    self.assertFalse(report["attempted"])
                    self.assertFalse(report["snapshot_hash_checked"])
                    self.assertEqual(original.conn.total_changes, 0)



if __name__=="__main__":
    unittest.main()
