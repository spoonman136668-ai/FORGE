"""Static negative controls for one-shot V41 original-owner installation route.

Unit qualification proves source/wiring restrictions only. Actual original
Windows owner execution and post-install research acceptance remain separate.
"""
from pathlib import Path
import os
import shutil
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v41-original-owner-live-install.yml"
WRAPPER = ROOT / "f139/v41_original_owner_live_install.ps1"


class OriginalOwnerV41InstallWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.wrapper = WRAPPER.read_text(encoding="utf-8")

    def test_frozen_ci_branch_does_not_admit_arbitrary_workflow_edits(self):
        from scripts import check_rar_g145_pr_scope as scope
        self.assertEqual(
            scope.FROZEN_SCOPES[
                "engineering/f139-v41-native-original-install-entry-20261113"],
            ("98ec09b732a7764d1f2a38b98abd5927dab03dac", {
                ".github/workflows/f139-v41-original-owner-live-install.yml",
                "f139/nci04_v41_native_original_install_cli.py",
                "f139/v41_original_owner_live_install.ps1",
                "f139/test_nci04_v41_native_original_install_cli.py",
                "f139/test_nci04_v41_live_install_workflow.py",
                "scripts/check_rar_g145_pr_scope.py",
                "scripts/check_rar_g148_go_cache.py",
                "scripts/check_rar_g156_dynamic_base_cache.py",
            }))

    def test_only_original_owner_created_issue_comment_can_enter(self):
        src = self.workflow
        self.assertIn("  issue_comment:\n    types: [created]", src)
        self.assertEqual(src.count("  issue_comment:"), 1)
        self.assertIn("github.actor == 'spoonman136668-ai'", src)
        self.assertIn("github.event.issue.number == 807", src)
        self.assertIn("!github.event.issue.pull_request", src)
        self.assertIn("startsWith(github.event.comment.body, 'F139-V41-LIVE-INSTALL ')", src)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", src)
        self.assertIn("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'", src)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", src)
        self.assertIn("GITHUB_REF -cne 'refs/heads/main'", src)
        self.assertIn("persist-credentials: false", src)
        self.assertIn("cancel-in-progress: false", src)
        for forbidden in ("\n  workflow_dispatch:", "\n  schedule:",
                          "\n  push:", "\n  repository_dispatch:",
                          "\n  pull_request:"):
            self.assertNotIn(forbidden, src)

    def test_readiness_is_distinct_read_only_owner_job(self):
        src = self.workflow
        self.assertEqual(src.count("  original-owner-v41-readiness:"), 1)
        part = src.split("  original-owner-v41-readiness:", 1)[1]
        self.assertIn("startsWith(github.event.comment.body, 'F139-V41-INSTALL-READINESS ')", part)
        self.assertIn("github.actor == 'spoonman136668-ai'", part)
        self.assertIn("RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE'", part)
        self.assertIn("    permissions:\n      contents: read\n      issues: read", part)
        self.assertIn("F139_V41_READINESS_ONLY_NO_TASK_OR_SQLITE_MUTATION=PASS", part)
        for forbidden in ("Set-ScheduledTask", "Disable-ScheduledTask",
                          "Enable-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "gh api --method PATCH",
                          "sqlite3.connect(", "new controller"):
            self.assertNotIn(forbidden, part)

    def test_original_owner_single_task_and_forward_only_failure(self):
        src = self.wrapper
        self.assertIn("$name='FORGE-F139-UnifiedController'", src)
        self.assertIn("Set-ScheduledTask -TaskName $name -Action $newAction", src)
        self.assertIn("Disable-ScheduledTask -TaskName $name", src)
        self.assertIn("Enable-ScheduledTask -TaskName $name", src)
        self.assertIn("$commitEntered=$true", src)
        self.assertIn("if($disabled -and -not $commitEntered)", src)
        self.assertIn("elseif($commitEntered -and -not $activated)", src)
        self.assertIn("original_database_rollback_authorized", src)
        self.assertIn("F139_V41_POSTCOMMIT_FORWARD_REPAIR_ONLY", src)
        self.assertIn("F139_V41_SCIENTIFIC_FIRST_USE=FALSE", src)
        self.assertIn("F139_V41_HYBRID_ADMISSION=FALSE", src)
        for forbidden in ("Register-ScheduledTask", "Unregister-ScheduledTask",
                          "New-ScheduledTaskTrigger", "Copy-Item",
                          "Restore-ScheduledTask", "workflow_dispatch:",
                          "Start-Job ", "Start-ThreadJob ",
                          "OpenAI_API_KEY="):
            self.assertNotIn(forbidden, src)

    def test_no_policy_or_task_activation_before_committed_readback(self):
        src = self.wrapper
        readback = src.index("$receipt=$output[0].Substring(")
        policy = src.index("& gh api --method PATCH")
        retarget = src.index("Set-ScheduledTask -TaskName $name")
        start = src.index("Start-ScheduledTask -TaskName $name")
        self.assertLess(readback, policy)
        self.assertLess(policy, retarget)
        self.assertLess(retarget, start)
        self.assertIn("PolicyOld", src)
        self.assertIn("SourceOld", src)
        self.assertIn("Main", src)
        self.assertIn("OWNER_APPROVAL_EVENT_MISSING", src)

    @unittest.skipUnless(os.name == "nt", "Native Windows PowerShell only")
    def test_windows_powershell_parser_accepts_live_wrapper(self):
        exe = shutil.which("powershell.exe")
        self.assertIsNotNone(exe, "native Windows PowerShell is required")
        program = (
            "$ErrorActionPreference='Stop';$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:F139_CHECK_PS_SOURCE,[ref]$t,[ref]$e)|Out-Null;"
            "if(@($e).Count -ne 0){$e|ForEach-Object{Write-Output $_};exit 1}"
        )
        proc = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", program],
            env=dict(os.environ, F139_CHECK_PS_SOURCE=str(WRAPPER)),
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(proc.returncode, 0,
                         (proc.stdout + "\\n" + proc.stderr)[:3000])

    @unittest.skipUnless(os.name == "nt", "Native Windows PowerShell only")
    def test_windows_powershell_parser_accepts_readiness_step(self):
        part = self.workflow.split("  original-owner-v41-readiness:", 1)[1]
        run = textwrap.dedent(part.split("        run: |\\n", 1)[1])
        self.assertIn("F139_V41_READINESS_ONLY_NO_TASK_OR_SQLITE_MUTATION", run)
        script = (
            "$ErrorActionPreference='Stop';$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseInput("
            "$env:F139_CHECK_PS_READINESS,[ref]$t,[ref]$e)|Out-Null;"
            "if(@($e).Count -ne 0){$e|ForEach-Object{Write-Output $_};exit 1}"
        )
        exe = shutil.which("powershell.exe")
        self.assertIsNotNone(exe)
        proc = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            env=dict(os.environ, F139_CHECK_PS_READINESS=run),
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(proc.returncode, 0,
                         (proc.stdout + "\\n" + proc.stderr)[:3000])

    def test_no_second_controller_or_external_model(self):
        for src in (self.workflow, self.wrapper):
            for forbidden in (
                "python -m pip install", "openai.ChatCompletion",
                "https://api.openai.com", "gh workflow run",
                "gh run rerun", "repository_dispatch:",
                "scientific_first_use: true", "hybrid_admission: true",
            ):
                self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
