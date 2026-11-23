"""Scoped read-only original-task profile for the actual postcommit V37 hold.

A failed activation may have retargeted the disabled original task to the
new V37 checkout; neither arbitrary source nor additional task is accepted.
No Windows task commands are executed by the test runner mocks.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_forward_backup as backup
from f139 import nci04_v41_hybrid_forward_original_commit as commit


class HeldOriginalTaskSourceTests(unittest.TestCase):
    def test_exactly_two_historically_bound_checkout_sources(self):
        self.assertEqual(profile.ALLOWED_ACTION_SOURCE_SHAS, {
            "1a40fe4e3ec6e93a1631d59863b95e90981d734e",
            "c611c4362e3cc867984448a03ecdf3be923d2ef1",
        })
        source = Path(profile.__file__).read_text("utf-8")
        for proof in ("Principal.UserId", "@($t.Triggers).Count -ne 3",
                      "@($t.Actions).Count -ne 1", "RepositoryRoot",
                      "PythonExe", "Run-FORGE-F139.ps1",
                      "$t.Settings.Enabled -ne $false",
                      "Get-CimInstance Win32_Process",
                      "git -C $root status --porcelain --untracked-files=all",
                      "-not($allow -ccontains $now)"):
            with self.subTest(proof=proof):
                self.assertIn(proof, source)
        for forbidden in ("Set-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Enable-ScheduledTask",
                          "Disable-ScheduledTask", "Register-ScheduledTask",
                          "gh api --method PATCH", "workflow_dispatch"):
            self.assertNotIn(forbidden, source)

    def test_no_weakening_of_precommit_v41_reader(self):
        older = (Path(__file__).resolve().parent /
                 "nci04_v41_hybrid_owner_maintenance.py").read_text("utf-8")
        self.assertIn('"F139_EXPECTED_SOURCE_SHA": pair.V41_SOURCE', older)
        for module in (readiness, backup, commit):
            text = Path(module.__file__).read_text("utf-8")
            self.assertIn("profile.readback(", text)
            self.assertNotIn("owner._task_readback(", text)

    @unittest.skipUnless(os.name == "nt", "Native Windows profile parser test")
    def test_exact_original_guard_parses_under_windows_powershell_51(self):
        """Parse the real fixed read-only guard without touching Task Scheduler."""
        with tempfile.TemporaryDirectory() as root:
            db = Path(root) / "state.sqlite"
            db.write_bytes(b"synthetic-not-a-real-database")
            exe = profile.shutil.which("powershell.exe")
            self.assertTrue(exe, "WIN_POWERSHELL_51_UNAVAILABLE")
            parse_result = []
            def verify_source(argv, **params):
                self.assertEqual(argv[:3],
                                 [exe, "-NoProfile", "-NonInteractive"])
                self.assertEqual(params["check"], False)
                self.assertEqual(params["timeout"], 25)
                # Only run the Windows PowerShell parser, not the script.
                env = {**params["env"], "F139_TEST_GUARD_BODY": argv[4]}
                parser = (
                    "$tokens=$null; $errors=$null; "
                    "[void][System.Management.Automation.Language.Parser]::ParseInput("
                    "$env:F139_TEST_GUARD_BODY,[ref]$tokens,[ref]$errors); "
                    "if($errors.Count){"
                    "Write-Output ('PARSE_ERROR_LINE='+$errors[0].Extent.StartLineNumber); "
                    "exit 42}; Write-Output 'PARSE_OK'"
                )
                check = subprocess.run(
                    [exe, "-NoProfile", "-NonInteractive", "-Command", parser],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=20, stdin=subprocess.DEVNULL, check=False)
                sanitized = check.stdout.decode("ascii", errors="replace").strip()
                parse_result.append(sanitized)
                self.assertEqual(check.returncode, 0,
                                 "ORIGINAL_GUARD_" + sanitized[:65])
                self.assertEqual(sanitized, "PARSE_OK")
                return subprocess.CompletedProcess(argv, 0,
                      stdout=profile.PROOF + b"\n", stderr=b"")
            self.assertTrue(profile.readback(db, runner=verify_source))
            self.assertEqual(parse_result, ["PARSE_OK"])

    @unittest.skipUnless(os.name == "nt", "Native Windows profile test")
    def test_fake_readonly_task_proof_has_exact_allowlist(self):
        with tempfile.TemporaryDirectory() as root:
            original = Path(root) / "state.sqlite"
            original.write_bytes(b"fixture-not-original")
            calls = []
            def stub(argv, **kwargs):
                calls.append((argv, kwargs))
                return subprocess.CompletedProcess(
                    argv, 0, stdout=profile.PROOF + b"\n",
                    stderr=b"")
            with patch.object(profile.shutil, "which",
                              return_value="powershell.exe"):
                self.assertTrue(profile.readback(original, runner=stub))
            self.assertEqual(len(calls), 1)
            argv, params = calls[0]
            self.assertEqual(argv[1:3],
                             ["-NoProfile", "-NonInteractive"])
            self.assertEqual(
                set(params["env"]["F139_V38_ALLOWED_ACTION_SOURCE_SHAS"].split(";")),
                profile.ALLOWED_ACTION_SOURCE_SHAS)
            self.assertEqual(
                params["env"]["F139_V38_EXPECTED_DATABASE"],
                str(original.resolve()))

    @unittest.skipUnless(os.name == "nt", "Native Windows profile test")
    def test_missing_sid_or_quiescence_receipt_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            original = Path(root) / "state.sqlite"
            original.write_bytes(b"fixture-not-original")
            def failed(argv, **kwargs):
                return subprocess.CompletedProcess(
                    argv, 51, stdout=b"", stderr=b"")
            with patch.object(profile.shutil, "which",
                              return_value="powershell.exe"):
                with self.assertRaisesRegex(
                        profile.HeldTaskIdentityDenied,
                        "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED"):
                    profile.readback(original, runner=failed)


if __name__ == "__main__":
    unittest.main()
