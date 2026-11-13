"""Negative controls for the V41 native atomic-commit CLI.

This test never invokes the original commit primitive or accesses a live DB.
"""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from f139.local_controller import GitHub
from f139 import nci04_v41_native_original_install_cli as entry


class NativeOriginalInstallEntryTests(unittest.TestCase):
    def test_non_windows_cannot_enter_atomic_phase(self):
        with mock.patch.object(entry.sys, "platform", "linux"):
            with self.assertRaisesRegex(
                    entry.OriginalInstallEntryDenied,
                    "NATIVE_WINDOWS_EXACT_SOURCE_REQUIRED"):
                entry.original_atomic_commit_and_hold(
                    "a" * 40, env={}, api=GitHub())

    def test_malformed_target_fails_before_live_api(self):
        with self.assertRaises(entry.OriginalInstallEntryDenied):
            entry.original_atomic_commit_and_hold(
                "../../not-a-commit", env={}, api=GitHub())

    def test_missing_or_unqualified_wrapper_refuses_before_event(self):
        # Real Windows qualification will enforce this too; no fake live
        # GitHub comment or original-owner file is opened in these tests.
        with (mock.patch.object(entry.sys, "platform", "win32"),
              mock.patch.object(entry, "os", SimpleNamespace(name="nt"))):
            for marker in (None, "true", "dev", "preflight"):
                env = {
                    "F139_V41_INSTALL_WRAPPER": marker,
                    "GITHUB_SHA": "a" * 40,
                    "GITHUB_RUN_ATTEMPT": "1",
                    "RUNNER_NAME": "FORGE-CODEX-REMOTE",
                }
                with self.subTest(marker=marker):
                    with self.assertRaisesRegex(
                            entry.OriginalInstallEntryDenied,
                            "COMPLETE_QUALIFIED_WRAPPER_REQUIRED"):
                        entry.original_atomic_commit_and_hold(
                            "a" * 40, env=env, api=GitHub())

    def test_no_cli_route_to_mutate_task_or_policy(self):
        source = Path(entry.__file__).read_text(encoding="utf-8")
        self.assertIn("atomic.verify_install_dispatch(", source)
        self.assertIn("atomic.original_commit_after_independent_rehearsal(", source)
        self.assertIn("hold.inspect_original_postcommit_hold(", source)
        self.assertIn("original_database_rollback_authorized", source)
        for forbidden in (
            "Enable-ScheduledTask", "Start-ScheduledTask",
            "Set-ScheduledTask", "Stop-ScheduledTask",
            "Disable-ScheduledTask", "issues: write",
            "original_db.unlink", "shutil.copyfile",
        ):
            self.assertNotIn(forbidden, source)

    def test_cli_has_no_automatic_execution(self):
        source = Path(entry.__file__).read_text(encoding="utf-8")
        self.assertNotIn("workflow_dispatch", source)
        self.assertNotIn("schedule:", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("threading.", source)


if __name__ == "__main__":
    unittest.main()
