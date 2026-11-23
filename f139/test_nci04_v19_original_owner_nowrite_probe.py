"""Original V19 owner witness contract: no production task or network writes."""
from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database
import f139.nci04_v19_original_owner_nowrite_probe as probe


class ReadOnlyOwnerProbeTests(unittest.TestCase):
    def test_non_original_runner_rejected_before_any_owner_or_remote_calls(self):
        with tempfile.TemporaryDirectory(prefix="f139-nowrite-negative-") as tmp:
            with patch.dict(probe.os.environ, {"RUNNER_NAME":"NOT-ORIGINAL"}, clear=True):
                with self.assertRaisesRegex(probe.OwnerReadOnlyDenied,
                                            "ORIGINAL_WINDOWS_RUNNER_REQUIRED"):
                    probe.owner_witness(Path(tmp) / "absent.sqlite")

    def test_probe_never_mutates_task_controller_or_remote_git(self):
        source = inspect.getsource(probe)
        for forbidden in (
            "Disable-ScheduledTask", "Enable-ScheduledTask", "Stop-ScheduledTask",
            "Start-ScheduledTask", "Set-ScheduledTask", "Register-ScheduledTask",
            "transition_source(", "db.event(", "db.conn.execute(\"UPDATE ",
            "issues/807", "git push", "git checkout", "gh api -X",
            "requests.post", "activate_native(", "run_once(",
        ):
            self.assertNotIn(forbidden, source, forbidden)
        self.assertIn("Get-ScheduledTask", source)
        self.assertIn("RUNNER_NAME", source)
        self.assertIn("F139_V19_PROBE_DB", source)
        self.assertIn("GetFullPath", source)
        self.assertIn("GetCurrent()", source)
        self.assertIn("Database.open_readonly(db_path)", source)
        self.assertIn("with SingleOwner(db_path.with_suffix(\".lock\")):", source)
        self.assertIn("v19_original_release_readonly_preflight(", source)

    def test_action_route_contract_is_present(self):
        source = probe._TASK_PROBE
        self.assertIn("V19_ACTION_ROUTE_BEGIN", source)
        self.assertIn("V19_ACTION_ROUTE_END", source)
        self.assertIn("GetFileName([string]$action.Execute)", source)
        self.assertIn("powershell.exe", source)
        self.assertIn("$wrapper=Field 'File'", source)
        self.assertIn("Run-FORGE-F139.ps1", source)
        self.assertIn("IsPathRooted($wrapper)", source)
        self.assertIn("Test-Path -LiteralPath $wrapper -PathType Leaf", source)

    @unittest.skipUnless(probe.os.name == "nt", "Windows PowerShell 5.1 required")
    def test_action_route_accepts_only_original_executable_and_existing_wrapper(self):
        source = probe._TASK_PROBE
        guard = source.split("# V19_ACTION_ROUTE_BEGIN\n", 1)[1].split(
            "# V19_ACTION_ROUTE_END", 1)[0]
        powershell = probe.shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        with tempfile.TemporaryDirectory(prefix="f139-v19-action-route-") as td:
            original = Path(td) / "Run-FORGE-F139.ps1"
            alternate = Path(td) / "Other-Launcher.ps1"
            original.write_text("# test-only wrapper\n", encoding="utf-8")
            alternate.write_text("# test-only alternate\n", encoding="utf-8")
            def options(path):
                return f'-File "{path}" -PollSeconds 300'

            cases = (
                ("authentic", "powershell.exe", options(original), 0),
                ("wrong-executable", "cmd.exe", options(original), 37),
                ("wrong-wrapper", "powershell.exe", options(alternate), 38),
                ("missing-wrapper", "powershell.exe",
                 options(Path(td) / "missing" / original.name), 38),
                ("relative-wrapper", "powershell.exe", options(original.name), 38),
            )
            script = (
                "$ErrorActionPreference='Stop';\n"
                "$t=[pscustomobject]@{Actions=@([pscustomobject]@{"
                "Execute=$env:F139_TEST_ACTION_EXECUTE;"
                "Arguments=$env:F139_TEST_ACTION_ARGUMENTS})};\n"
                + guard + "\nWrite-Output 'ACTION_ROUTE_OK'\n"
            )
            for name, executable, arguments, expected in cases:
                with self.subTest(name=name):
                    environment = {
                        **probe.os.environ,
                        "F139_TEST_ACTION_EXECUTE": executable,
                        "F139_TEST_ACTION_ARGUMENTS": arguments,
                    }
                    result = subprocess.run(
                        [powershell, "-NoProfile", "-NonInteractive",
                         "-Command", script],
                        env=environment, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=15, check=False,
                    )
                    self.assertEqual(result.returncode, expected,
                                     result.stderr.decode(errors="replace")[:400])
                    if expected == 0:
                        self.assertEqual(result.stdout.strip(), b"ACTION_ROUTE_OK")

    def test_probe_output_cannot_authorize_source_cutover(self):
        with tempfile.TemporaryDirectory(prefix="f139-nowrite-proof-") as td:
            db_path = Path(td) / "fixture.sqlite"
            db = Database.initialize(db_path, probe.SOURCE)
            db.close()
            readonly = {
                "schema":"forge.f139.v19.original-owner-release-readiness-nowrite.v1",
                "read_only":True,
                "runtime_cutover_authorized":False,
                "original_sqlite_writes":0,
                "github_writes":0,
            }
            with patch.object(probe, "owner_witness", return_value=True), patch.object(
                    probe, "v19_original_release_readonly_preflight",
                    return_value=readonly) as preflight:
                proof = probe.inspect_original_owner(db_path)
                self.assertEqual(preflight.call_count, 1)
                _, kwargs = preflight.call_args
                self.assertTrue(callable(kwargs["owner_witness"]))
                self.assertTrue(callable(kwargs["original_get"]))
                self.assertEqual(kwargs["owner_witness"](), True)
            self.assertEqual(proof, readonly)

    def test_foreign_authority_proof_rejected(self):
        with tempfile.TemporaryDirectory(prefix="f139-nowrite-reject-") as td:
            db_path = Path(td) / "fixture.sqlite"
            db = Database.initialize(db_path, probe.SOURCE)
            db.close()
            for broken in (
                {"read_only":True, "runtime_cutover_authorized":True,
                 "original_sqlite_writes":0, "github_writes":0},
                {"read_only":True, "runtime_cutover_authorized":False,
                 "original_sqlite_writes":1, "github_writes":0},
                {"read_only":False, "runtime_cutover_authorized":False,
                 "original_sqlite_writes":0, "github_writes":0},
            ):
                with self.subTest(broken=broken), patch.object(
                        probe, "owner_witness", return_value=True), patch.object(
                        probe, "v19_original_release_readonly_preflight",
                        return_value=broken):
                    with self.assertRaisesRegex(
                            probe.OwnerReadOnlyDenied, "UNEXPECTED_RELEASE_AUTHORITY"):
                        probe.inspect_original_owner(db_path)


if __name__ == "__main__":
    unittest.main()
