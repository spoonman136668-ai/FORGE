"""Source-only negative controls for V59 original-host read-only process census.

No Windows owner task, original SQLite, runner or GitHub provider is invoked.
This static contract guards the original owner read-only workflow; only a
separate genuine Windows-host receipt can verify live process population.
"""
from pathlib import Path
import unittest


WORKFLOW = (
    Path(__file__).resolve().parents[1] /
    ".github/workflows/f139-v59-original-owner-readonly.yml"
)


class OriginalV59ProcessSnapshotSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_existing_owner_event_and_readonly_policy_preserved(self):
        src = self.source
        for required in (
            "F139-V59-ORIGINAL-READONLY ",
            "github.event.issue.number == 807",
            "runs-on: [self-hosted, Windows, forge-codex-isolated]",
            "RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE'",
            "F139_V59_ORIGINAL_READONLY=PASS",
            "F139_V59_SOURCE_TRANSITION_AUTHORIZED=FALSE",
            "F139_V59_OWNER_TASK_MUTATIONS=ZERO",
            "audit_frozen_original_readonly",
            "Database.open_readonly",
        ):
            with self.subTest(required=required):
                self.assertIn(required, src)

    def test_process_counts_fresh_before_and_after_ledger_audit(self):
        src = self.source
        self.assertEqual(src.count("Get-CimInstance Win32_Process"), 1)
        self.assertIn("Name='python.exe' OR Name='pythonw.exe'", src)
        self.assertIn("-ErrorAction Stop", src)
        self.assertIn("'f139[.]local_controller'", src)
        self.assertIn("OrdinalIgnoreCase", src)
        self.assertIn("$members.Count -eq $matched.Count", src)
        self.assertIn("$matched.Count -le 1", src)
        self.assertIn("DUPLICATE_OR_FOREIGN_CONTROLLER_PROCESS", src)
        self.assertEqual(src.count("$processesBefore=OriginalControllerCount"), 1)
        self.assertEqual(src.count("$processesAfter=OriginalControllerCount"), 1)
        self.assertLess(src.index("$processesBefore=OriginalControllerCount"),
                        src.index("Database.open_readonly"))
        self.assertGreater(src.index("$processesAfter=OriginalControllerCount"),
                           src.index("Database.open_readonly"))

    def test_observation_cannot_be_mistaken_for_host_release(self):
        src = self.source
        for required in (
            "F139_V59_ORIGINAL_PROCESS_SNAPSHOT=",
            "schema='forge.f139.v59.original-owner-process-snapshot.v1'",
            "task_state=[string]$after.State",
            "task_enabled=[bool]$after.Settings.Enabled",
            "matching_original_database_controllers_before=$processesBefore",
            "matching_original_database_controllers_after=$processesAfter",
            "owner_task_release_authorized=$false",
            "fresh_activation_authorized=$false",
            "worker_dispatch_authorized=$false",
            "scientific_first_use=$false",
            "new_controller=$false",
            "new_scheduler=$false",
            "original_task_mutations=0",
        ):
            with self.subTest(required=required):
                self.assertIn(required, src)
        for forbidden in (
            "Stop-ScheduledTask", "Start-ScheduledTask",
            "Disable-ScheduledTask", "Enable-ScheduledTask",
            "Set-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "Stop-Process",
            "Start-Process", "Remove-Item", "Invoke-RestMethod",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)


    @staticmethod
    def _powershell_from_workflow(source: str) -> str:
        """Extract the real run block with its YAML indentation removed."""
        marker = "        run: |\n"
        if source.count(marker) != 1:
            raise AssertionError("Expected exactly one original owner run block")
        block = source.split(marker, 1)[1]
        rows = block.splitlines()
        return "\n".join(row[10:] if row.startswith("          ") else ""
                         for row in rows).strip() + "\n"

    @staticmethod
    def _parse_powershell(script: str):
        import shutil
        import subprocess

        pwsh = shutil.which("pwsh")
        if pwsh is None:
            raise AssertionError("Native Windows qualification requires pwsh")
        parse = (
            "$text=[Console]::In.ReadToEnd();"
            "$tokens=$null;$errors=$null;"
            "[void][System.Management.Automation.Language.Parser]::ParseInput("
            "$text,[ref]$tokens,[ref]$errors);"
            "if($errors.Count -gt 0){"
            "[Console]::Error.WriteLine(($errors|ForEach-Object "
            "{ $_.ErrorId }) -join ',');exit 1};exit 0"
        )
        return subprocess.run(
            [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive",
             "-Command", parse],
            input=script, capture_output=True, text=True,
            timeout=45, check=False,
        )

    def test_real_workflow_powershell_parses_and_detects_old_regression(self):
        import sys

        if sys.platform != "win32":
            self.skipTest("Actual PowerShell AST parse runs on native Windows")
        script = self._powershell_from_workflow(self.source)
        safe = self._parse_powershell(script)
        self.assertEqual(safe.returncode, 0, safe.stderr[-1000:])
        one_line = ("Get-CimInstance Win32_Process -Filter "
                    "\"Name='python.exe' OR Name='pythonw.exe'\" "
                    "-ErrorAction Stop |")
        self.assertIn(one_line, script)
        # The previous merged release passed static tests but PowerShell
        # rejected this exact broken linebreak on the genuine owner runner.
        broken = script.replace(
            one_line,
            "Get-CimInstance Win32_Process -Filter\n"
            "  \"Name='python.exe' OR Name='pythonw.exe'\" "
            "-ErrorAction Stop |",
            1,
        )
        self.assertNotEqual(broken, script)
        rejected = self._parse_powershell(broken)
        self.assertNotEqual(rejected.returncode, 0,
                            "Regression fixture must remain parser-invalid")

    def test_output_never_prints_process_command_line_or_pid(self):
        src = self.source
        output = src[src.index("          $witness=@{"):
                     src.index("          Write-Output 'F139_V59_ORIGINAL_READONLY=PASS'")]
        self.assertNotIn("CommandLine", output)
        self.assertNotIn("ProcessId", output)
        self.assertNotIn("$db", output)
        self.assertNotIn("$root", output)
        self.assertNotIn("$python", output)


if __name__ == "__main__":
    unittest.main()
