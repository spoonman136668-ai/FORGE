"""Source-bound negative controls for the inert V3 original-host cold CLI."""
from __future__ import annotations

import base64
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from f139.local_controller import F139Error, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_v3_original_cold_host_cli import (
    FRESH_DIR, V3HostColdDenied, inspect_cold_host, main,
)
from f139.test_nci04_v3_remote_readonly_preflight import (
    HEAD, MERGE, PR, RUNS, TREE,
)


class V3OriginalHostColdCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "FORGE-F139" / FRESH_DIR
        self.folder.mkdir(parents=True)
        self.dbpath = self.folder / "state.sqlite"
        self.dbpath.write_bytes(b"read-only-test-fixture")
        self.lock = self.dbpath.with_suffix(".lock")
        self.lock.write_bytes(b"L")
        self.key = "synthetic-owner-HMAC-key-longer-than-32-characters"
        self.params = {
            "owner_source_sha": MERGE,
            "owner_source_tree": TREE,
            "pr_number": PR,
            "pr_head_sha": HEAD,
            **RUNS,
        }
        self.encoded = base64.b64encode(canonical(self.params)).decode("ascii")
        self.db = Mock()
        self.db._readonly_opened = True
        self.db.conn.total_changes = 0
        self.db.conn.execute.return_value.fetchone.return_value = (1,)
        self.proof = {
            "remote_evidence": "VERIFIED_READ_ONLY",
            "signed_v1_cold_history": "VERIFIED_READ_ONLY",
            "verified_terminal_tasks": 3,
            "source_commit": MERGE,
            "source_tree": TREE,
            "original_windows_sid_and_task": "NOT_CHECKED",
            "installed_checkout": "NOT_CHECKED",
            "source_forward_authorized": False,
            "safe_to_disable_task": False,
            "signed_v3_certificate": False,
            "sqlite_mutations": 0,
            "worker_dispatches": 0,
            "scientific_first_use": False,
        }

    def audit(self, *, encoded=None, dbpath=None, folder=None, key=None,
              proof=None, sqlite=None):
        if sqlite is not None:
            self.db._readonly_opened = sqlite
        with patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
            return_value=self.db,
        ) as opener, patch(
            "f139.nci04_v3_original_cold_host_cli.inspect_original_owner_cold_readonly",
            return_value=self.proof if proof is None else proof,
        ) as cold:
            result = inspect_cold_host(
                self.encoded if encoded is None else encoded,
                dbpath=self.dbpath if dbpath is None else dbpath,
                folder=self.folder if folder is None else folder,
                key=self.key if key is None else key,
                api=object(),
            )
            return result, opener, cold

    def test_existing_lock_and_readonly_probe_never_grant_authority(self):
        old_db = self.dbpath.read_bytes()
        old_lock = self.lock.read_bytes()
        report, opener, cold = self.audit()
        self.assertEqual(report["cold_history"], "VERIFIED_READ_ONLY")
        self.assertEqual(report["owner_windows_sid_dpapi"], "NOT_CHECKED")
        for name in ("source_forward_authorized", "task_mutation_authorized",
                     "scientific_first_use"):
            self.assertIs(report[name], False)
        opener.assert_called_once_with(self.dbpath)
        self.assertEqual(cold.call_count, 1)
        self.assertEqual(cold.call_args.kwargs, self.params)
        self.db.close.assert_called_once()
        self.assertEqual(self.dbpath.read_bytes(), old_db)
        self.assertEqual(self.lock.read_bytes(), old_lock)
        self.assertFalse(SingleOwner.held(self.lock))

    def test_invalid_encoded_request_denied_before_lock_or_sqlite(self):
        with patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
        ) as opener:
            with self.assertRaises(Exception):
                self.audit(encoded="non-canonical-!!")
            opener.assert_not_called()

    def test_wrong_or_relative_owner_path_denied(self):
        for bad in (
            {"dbpath": Path("state.sqlite")},
            {"dbpath": self.folder / "other.sqlite"},
            {"folder": self.folder.parent},
        ):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                    V3HostColdDenied, "INPUT_OR_OWNER_PATH_INVALID"
                ):
                    self.audit(**bad)

    def test_missing_or_empty_existing_lock_denied(self):
        self.lock.unlink()
        with self.assertRaisesRegex(
            V3HostColdDenied, "OWNER_SOURCE_OR_EXISTING_LOCK_INVALID"
        ):
            self.audit()
        self.assertFalse(self.lock.exists())
        self.lock.write_bytes(b"")
        with self.assertRaisesRegex(
            V3HostColdDenied, "OWNER_SOURCE_OR_EXISTING_LOCK_INVALID"
        ):
            self.audit()
        self.assertEqual(self.lock.stat().st_size, 0)

    def test_lock_disappears_at_acquire_never_recreated(self):
        real_open = Path.open
        def lose_before_open(path, *args, **kwargs):
            if path == self.lock and args and args[0] == "r+b":
                path.unlink()
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", lose_before_open), patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
        ) as opener:
            with self.assertRaises(FileNotFoundError):
                inspect_cold_host(self.encoded, dbpath=self.dbpath,
                                  folder=self.folder, key=self.key, api=object())
            opener.assert_not_called()
        self.assertFalse(self.lock.exists())

    def test_existing_lock_truncated_during_acquire_not_repaired(self):
        real_open = Path.open
        def truncate_before_open(path, *args, **kwargs):
            if path == self.lock and args and args[0] == "r+b":
                with real_open(path, "wb"):
                    pass
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", truncate_before_open), patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
        ) as opener:
            with self.assertRaises(F139Error):
                inspect_cold_host(self.encoded, dbpath=self.dbpath,
                                  folder=self.folder, key=self.key, api=object())
            opener.assert_not_called()
        self.assertEqual(self.lock.read_bytes(), b"")

    def test_default_controller_lock_creation_unchanged(self):
        other = self.folder / "fresh-controller-lock.lock"
        self.assertFalse(other.exists())
        with SingleOwner(other):
            self.assertTrue(SingleOwner.held(other))
            self.assertTrue(other.is_file())
        self.assertFalse(SingleOwner.held(other))

    def test_reparse_database_denied_before_open(self):
        real = Path.is_symlink
        with patch.object(
            Path, "is_symlink", lambda p: p == self.dbpath or real(p)
        ), patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
        ) as opener:
            with self.assertRaisesRegex(
                V3HostColdDenied, "OWNER_SOURCE_OR_EXISTING_LOCK_INVALID"
            ):
                inspect_cold_host(self.encoded, dbpath=self.dbpath,
                                  folder=self.folder, key=self.key, api=object())
            opener.assert_not_called()

    def test_unavailable_kernel_lock_does_not_open_sqlite(self):
        with patch.object(
            SingleOwner, "__enter__", side_effect=F139Error("LOCK_HELD")
        ), patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
        ) as opener:
            with self.assertRaisesRegex(F139Error, "LOCK_HELD"):
                inspect_cold_host(self.encoded, dbpath=self.dbpath,
                                  folder=self.folder, key=self.key, api=object())
            opener.assert_not_called()

    def test_writable_database_denied_and_closed(self):
        with self.assertRaisesRegex(V3HostColdDenied, "SQLITE_READONLY_REQUIRED"):
            self.audit(sqlite=False)
        self.db.close.assert_called_once()

    def test_disabled_sqlite_query_only_denied(self):
        self.db.conn.execute.return_value.fetchone.return_value = (0,)
        with self.assertRaisesRegex(V3HostColdDenied, "SQLITE_READONLY_REQUIRED"):
            self.audit()
        self.db.close.assert_called_once()

    def test_unsafe_positive_flags_denied_and_closed(self):
        for key, value in (
            ("source_forward_authorized", True),
            ("safe_to_disable_task", True),
            ("signed_v3_certificate", True),
            ("scientific_first_use", True),
            ("owner_windows_sid_dpapi", "VERIFIED"),
            ("sqlite_mutations", 1),
        ):
            with self.subTest(key=key):
                altered = dict(self.proof)
                altered[key if key != "owner_windows_sid_dpapi"
                        else "original_windows_sid_and_task"] = value
                self.db.close.reset_mock()
                with self.assertRaisesRegex(
                    V3HostColdDenied, "UNEXPECTED_CUSTODY_OR_AUTHORITY"
                ):
                    self.audit(proof=altered)
                self.db.close.assert_called_once()

    def test_cold_failure_closes_database_and_does_not_print_secret(self):
        with patch(
            "f139.nci04_v3_original_cold_host_cli.Database.open_readonly",
            return_value=self.db,
        ), patch(
            "f139.nci04_v3_original_cold_host_cli.inspect_original_owner_cold_readonly",
            side_effect=ValueError("sensitive-key-must-not-be-printed"),
        ):
            with self.assertRaises(ValueError):
                inspect_cold_host(self.encoded, dbpath=self.dbpath,
                                  folder=self.folder, key=self.key, api=object())
        self.db.close.assert_called_once()

    def test_cli_non_windows_is_denied_without_files_or_network(self):
        output = StringIO()
        with patch(
            "f139.nci04_v3_original_cold_host_cli._native_windows",
            return_value=False,
        ), patch(
            "f139.nci04_v3_original_cold_host_cli.inspect_cold_host",
        ) as cold, redirect_stderr(output):
            code = main([self.encoded])
        self.assertEqual(code, 2)
        self.assertEqual(output.getvalue().strip(),
                         "F139_V3_ORIGINAL_COLD_HISTORY=DENIED")
        cold.assert_not_called()

    def test_cli_success_outputs_no_secrets_or_task_authority(self):
        output, errors = StringIO(), StringIO()
        with patch(
            "f139.nci04_v3_original_cold_host_cli._native_windows",
            return_value=True,
        ), patch.dict(os.environ, {
            "LOCALAPPDATA": self.temp.name,
            "F139_WORKER_HMAC_KEY": self.key,
        }), patch(
            "f139.nci04_v3_original_cold_host_cli.inspect_cold_host",
            return_value={"cold_history": "VERIFIED_READ_ONLY"},
        ) as cold, redirect_stdout(output), redirect_stderr(errors):
            code = main([self.encoded])
        self.assertEqual(code, 0)
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(cold.call_args.kwargs["dbpath"], self.dbpath)
        self.assertIn("F139_V3_ORIGINAL_COLD_HISTORY=READ_ONLY_PASS",
                      output.getvalue())
        self.assertIn("F139_V3_TASK_MUTATION_AUTHORIZED=FALSE",
                      output.getvalue())
        self.assertNotIn(self.key, output.getvalue())
        self.assertNotIn(self.temp.name, output.getvalue())

    def test_source_contains_no_owner_or_provider_write_path(self):
        code = Path(__file__).with_name(
            "nci04_v3_original_cold_host_cli.py").read_text()
        for forbidden in (
            "Set-ScheduledTask", "Stop-ScheduledTask", "Enable-ScheduledTask",
            "Register-ScheduledTask", "api.post(", "api.patch(",
            "os.system(", "subprocess.run(", "sign-cert",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
