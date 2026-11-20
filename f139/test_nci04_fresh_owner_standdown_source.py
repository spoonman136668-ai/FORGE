"""Source-only controls for a single, original-Windows-task standdown.

The suite does not stop any task, launch controller, or admit research.
Successful tests are engineering evidence only, never native owner approval.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "f139/nci04_fresh_owner_standdown.ps1"
WORKFLOW = ROOT / ".github/workflows/f139-fresh-original-owner-standdown.yml"
SOURCE = "c06403c8b6035c6c7013866a7ea08cef1244b507"
HEAD = "e10be7151e19f2104ef2659ae04bef89b2711eea1659decb1477fd7354ff24ec"
TOKEN = "F139-FRESH-DEV-OWNER-STANDDOWN "


class OriginalStanddownSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_existing_owner_and_frozen_original_custody(self):
        script = self.script
        for required in (
            "FORGE-F139-UnifiedController", SOURCE, HEAD,
            "$env:GITHUB_SHA", "$env:GITHUB_EVENT_PATH",
            "$env:GITHUB_WORKFLOW_REF", "OWNER_ISSUE_PROVIDER_DRIFT",
            "$env:GITHUB_RUN_ATTEMPT -ceq '1'",
            "$env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE'",
            "comment.author_association -ceq 'OWNER'",
            "issues/comments/", "branches/main", "issues/807",
            "Get-ScheduledTask", "Get-CimInstance Win32_Process",
            "ORIGINAL_TASK_IDENTITY", "OWNER_SID_DRIFT" if False else
            "OWNER_ADMIN_REQUIRED",
            "F139OriginalOwnerMutex", "Database.open_readonly",
            "audit_frozen_original_readonly", "head_seq",
            "OriginalExecute", "OriginalPrincipal",
            "ORIGINAL_LEDGER_CHANGED", "$OriginalArguments",
            "ORIGINAL_EVENT1864_PRESERVED=PASS",
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)
        self.assertLess(script.index("audit_frozen_original_readonly"),
                        script.index("Disable-ScheduledTask -TaskName $Name"))
        self.assertLess(script.index("Disable-ScheduledTask -TaskName $Name"),
                        script.index("ORIGINAL_LEDGER_CHANGED"))
        self.assertLess(script.index("Disable-ScheduledTask -TaskName $Name"),
                        script.index("F139_ORIGINAL_CONTROLLER_PROCESSES=ZERO"))

    def test_only_exact_one_shot_owner_comment_can_enter_runner(self):
        workflow = self.workflow
        self.assertEqual(workflow.count("\non:\n  issue_comment:\n    types: [created]\n"), 1)
        for required in (
            "github.actor == 'spoonman136668-ai'",
            "github.event.issue.number == 1830",
            "github.event.comment.author_association == 'OWNER'",
            "startsWith(github.event.comment.body, '" + TOKEN + "')",
            "runs-on: [self-hosted, Windows, forge-codex-isolated]",
            "group: forge-f139-v54-original-owner",
            "cancel-in-progress: false", "persist-credentials: false",
            "nci04_fresh_owner_standdown.ps1", "GH_TOKEN:",
            "F139_WORKER_DISPATCH_AUTHORIZED=FALSE",
            "F139_SCIENTIFIC_FIRST_USE=FALSE",
        ):
            with self.subTest(required=required):
                self.assertIn(required, workflow)
        for forbidden in ("\n  workflow_dispatch:", "\n  schedule:",
                          "\n  push:", "\n  pull_request:",
                          "contents: write", "issues: write"):
            self.assertNotIn(forbidden, workflow)

    def test_standdown_never_installs_or_dispatches_another_owner(self):
        script = self.script
        for forbidden in (
            "Register-ScheduledTask", "Unregister-ScheduledTask",
            "New-ScheduledTask", "Set-ScheduledTask",
            "Enable-ScheduledTask", "Start-ScheduledTask",
            "workflow_dispatch", "gh api --method POST",
            "gh api --method PATCH", "OPENAI_API_KEY=",
            "new scheduler", "sqlite3.connect(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)
        self.assertEqual(script.count("Disable-ScheduledTask -TaskName $Name"), 1)
        self.assertEqual(script.count("Stop-ScheduledTask -TaskName $Name"), 1)
        self.assertIn("F139_FRESH_DEV_OWNER_STANDDOWN=PASS", script)

    def test_exact_g145_owner_branch_and_blob_negative_controls(self):
        from scripts import check_rar_g145_pr_scope as scope
        head = "b" * 40
        base = scope.FRESH_STANDDOWN_BASE
        request = {
            "number": 1848, "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {
                "ref": scope.FRESH_STANDDOWN_BRANCH,
                "sha": head,
                "repo": {"full_name": scope.REPO},
            },
            "base": {
                "ref": "main", "sha": base,
                "repo": {"full_name": scope.REPO},
            },
        }

        def provider(*args):
            if args == ("merge-base", base, head):
                return base
            if args == ("rev-parse", base + "^{tree}"):
                return scope.FRESH_STANDDOWN_TREE
            if args == ("diff", "--no-renames", "--name-only", base, head):
                return "\n".join(sorted(scope.FRESH_STANDDOWN_FILES))
            if args[0] == "rev-parse" and args[1].startswith(head + ":"):
                return scope.FRESH_STANDDOWN_BLOBS.get(
                    args[1][len(head) + 1:], "0" * 40)
            raise AssertionError("unrecognized git request")

        self.assertEqual(
            scope.admit_fresh_original_standdown(head, base, request, provider),
            "EXACT_PR1848_F139_STANDDOWN_SOURCE_CI_ONLY",
        )
        for override in (
            {"number": 1849},
            {"author_association": "CONTRIBUTOR"},
            {"user": {"login": "foreign"}},
            {"head": {**request["head"], "ref": "foreign"}},
            {"head": {**request["head"], "sha": "0" * 40}},
            {"base": {**request["base"], "sha": "f" * 40}},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    scope.admit_fresh_original_standdown(
                        head, base, {**request, **override}, provider)

        def moved(*args):
            if args == ("rev-parse", head + ":" +
                        scope.FRESH_STANDDOWN_SCRIPT):
                return "c" * 40
            return provider(*args)

        with self.assertRaisesRegex(
            ValueError, "SOURCE_OR_BLOB_DRIFT"
        ):
            scope.admit_fresh_original_standdown(
                head, base, request, moved)

    @unittest.skipUnless(os.name == "nt", "Native Windows PowerShell AST only")
    def test_windows_ast_parses_source_without_executing(self):
        ps = shutil.which("powershell.exe") or shutil.which("pwsh")
        self.assertIsNotNone(ps, "native Windows parser is required")
        program = (
            "$ErrorActionPreference='Stop';$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:F139_PS_SOURCE,[ref]$t,[ref]$e)|Out-Null;"
            "if($null -ne $e -and @($e).Count -gt 0){"
            "$e|ForEach-Object{Write-Output $_.Message};exit 1}"
        )
        result = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", program],
            env=dict(os.environ, F139_PS_SOURCE=str(SCRIPT)),
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0,
                         (result.stdout + "\n" + result.stderr)[:2000])


if __name__ == "__main__":
    unittest.main()
