"""Windows original-owner task read-only guard; no live task manipulation."""
from pathlib import Path
import base64
import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v41_native_preinstall_profile as pre
from f139 import nci04_v41_source_transition as source


TARGET = "8" * 40


class NativePreinstallWitnessTests(unittest.TestCase):
    def test_inert_module_and_win_only_guard(self):
        text = inspect.getsource(pre)
        for token in ("Get-ScheduledTask", "F139_EXPECTED_V40_SOURCE",
                      "F139_EXPECTED_CANDIDATE_ROOT", "F139_CANDIDATE_PID",
                      "git -C $oldRoot rev-parse HEAD",
                      "Get-CimInstance Win32_Process",
                      "F139_V41_OLD_TASK_DISABLED_STAGED_CANDIDATE=PASS"):
            self.assertIn(token, text)
        for forbidden in ("Disable-ScheduledTask", "Enable-ScheduledTask",
                          "Register-ScheduledTask", "Unregister-ScheduledTask",
                          "Set-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Set-Content", "Add-Content",
                          "gh api --method", "F139_WORKER_HMAC_KEY"):
            self.assertNotIn(forbidden, pre.SCRIPT)
        self.assertIn('t.State -cne \'Disabled\'', pre.SCRIPT)
        self.assertIn('t.Settings.Enabled -ne $false', pre.SCRIPT)

    def test_nonwindows_and_invalid_target_never_call_shell(self):
        with patch.object(pre.sys, "platform", "linux"), \
             patch.object(pre.subprocess, "run") as called:
            with self.assertRaisesRegex(pre.NativePreinstallDenied,
                                        "WINDOWS_EXACT_CANDIDATE_REQUIRED"):
                pre.verify_original_task_disabled_for_staged_candidate(
                    Path("/tmp/f139-state.sqlite"), Path("/tmp/forge"), TARGET)
            called.assert_not_called()
        with patch.object(pre.subprocess, "run") as called:
            with self.assertRaises(pre.NativePreinstallDenied):
                pre.verify_original_task_disabled_for_staged_candidate(
                    Path("/tmp/f139-state.sqlite"), Path("/tmp/forge"), "bad")
            called.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "native Windows PowerShell parser")
    def test_native_preinstall_powershell_ast_and_broken_filter_negative(self):
        # Parse, but NEVER execute, the genuine owner-task witness. Its earlier
        # two-line -Filter command failed on the original Windows host before
        # any V41 SQLite event was written. Do not mock the PowerShell parser.
        ps = shutil.which("powershell.exe")
        self.assertIsNotNone(ps)
        checker = (
            "$tokens=$null;$syntaxErrors=$null;"
            "[System.Management.Automation.Language.Parser]::ParseInput("
            "$env:F139_READONLY_PS_SOURCE,[ref]$tokens,[ref]$syntaxErrors)"
            "|Out-Null;"
            "if(@($syntaxErrors).Count -ne 0){exit 15};exit 0"
        )
        args = [ps, "-NoProfile", "-NonInteractive", "-EncodedCommand",
                base64.b64encode(checker.encode("utf-16le")).decode("ascii")]
        bad_filter = (
            "-Filter \"Name='python.exe' OR Name='pythonw.exe'\" -ErrorAction"
        )
        self.assertIn(bad_filter, pre.SCRIPT)
        malformed = pre.SCRIPT.replace(
            bad_filter,
            "-Filter\\n    \"Name='python.exe' OR Name='pythonw.exe'\" -ErrorAction"
        )
        for script, valid in ((pre.SCRIPT, True), (malformed, False)):
            with self.subTest(valid=valid):
                ran = subprocess.run(
                    args, capture_output=True, check=False, timeout=20,
                    stdin=subprocess.DEVNULL,
                    env=dict(os.environ, F139_READONLY_PS_SOURCE=script),
                )
                if valid:
                    self.assertEqual(ran.returncode, 0)
                else:
                    self.assertNotEqual(ran.returncode, 0)

    @unittest.skipUnless(sys.platform == "win32", "native Windows witness")
    def test_windows_canonical_path_binary_git_task_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as scratch:
            db = Path(scratch) / "FORGE-F139" / "state.sqlite"
            db.parent.mkdir(parents=True)
            db.write_bytes(b"read-only test fixture; never opened")
            root = Path(__file__).resolve().parents[1]
            calls = []
            def run(argv, **kwargs):
                calls.append((argv, kwargs))
                if argv[0] == "git":
                    if argv[-2:] == ["rev-parse", "HEAD"]:
                        stdout = (TARGET + "\n").encode("ascii")
                    else:
                        self.assertEqual(argv[-2:],
                                         ["--porcelain", "--untracked-files=all"])
                        stdout = b""
                    return subprocess.CompletedProcess(argv, 0, stdout, b"")
                self.assertIn("-NoProfile", argv)
                self.assertIn("Get-ScheduledTask", argv[-1])
                self.assertEqual(
                    kwargs["env"]["F139_EXPECTED_ORIGINAL_DATABASE"],
                    str(db.resolve()))
                self.assertEqual(kwargs["env"]["F139_EXPECTED_V40_SOURCE"],
                                 source.FROM_V40)
                self.assertEqual(
                    kwargs["env"]["F139_EXPECTED_CANDIDATE_ROOT"],
                    str(root))
                self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
                return subprocess.CompletedProcess(
                    argv, 0,
                    b"F139_V41_OLD_TASK_DISABLED_STAGED_CANDIDATE=PASS\n",
                    b"")
            with patch.dict(os.environ, {"LOCALAPPDATA": scratch}), \
                 patch.object(pre.subprocess, "run", side_effect=run), \
                 patch.object(pre.shutil, "which", return_value="powershell.exe"):
                self.assertTrue(pre.verify_original_task_disabled_for_staged_candidate(
                    db, root, TARGET))
                self.assertEqual(len(calls), 3)
                self.assertEqual(db.read_bytes(), b"read-only test fixture; never opened")

                def denied(argv, **kwargs):
                    if argv[0] == "git":
                        return run(argv, **kwargs)
                    return subprocess.CompletedProcess(argv, 43, b"", b"")
                with patch.object(pre.subprocess, "run", side_effect=denied):
                    with self.assertRaisesRegex(pre.NativePreinstallDenied,
                                                "TASK_SID_ROOT_QUIESCENCE_DRIFT"):
                        pre.verify_original_task_disabled_for_staged_candidate(
                            db, root, TARGET)
                with patch.object(pre.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(pre.NativePreinstallDenied,
                                                "NATIVE_POWERSHELL_UNAVAILABLE"):
                        pre.verify_original_task_disabled_for_staged_candidate(
                            db, root, TARGET)
                with self.assertRaisesRegex(pre.NativePreinstallDenied,
                                            "CANONICAL_ORIGINAL_SQLITE_ONLY"):
                    pre.verify_original_task_disabled_for_staged_candidate(
                        root / "nonowner.sqlite", root, TARGET)


if __name__ == "__main__":
    unittest.main()
