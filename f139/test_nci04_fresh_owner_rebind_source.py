"""Source-only safety controls for one existing disabled-task F139 fresh rebind.

No original Windows host, task, worker, SQLite or GitHub API mutation occurs
during tests. Runtime authority requires a separate owner-authenticated run.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "f139/nci04_fresh_owner_rebind.ps1"
WORKFLOW = ROOT / ".github/workflows/f139-fresh-original-owner-rebind.yml"
ORIGINAL = "c06403c8b6035c6c7013866a7ea08cef1244b507"
ORIGINAL_TREE = "b7abf26f618654f330b55f510bfcc34d8916848a"
FRESH = "408139c0a10fd4836a22422c8df041aa64dfa001"
FRESH_TREE = "4f35d3965bfd2d8688586600926445008e16f5b9"
HEAD4 = "b099aba6750a4ae323ffd5291ea0ae940b1403b4063aa89f34521fe513383337"


class OriginalFreshRebindSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_reuses_only_original_task_and_frozen_custody(self):
        for term in (
            "FORGE-F139-UnifiedController", ORIGINAL, ORIGINAL_TREE,
            FRESH, FRESH_TREE, HEAD4, "$FreshRun=44831323193",
            "f139-fresh-dev-", "issues/807",
            "f139-owner-release-", "release.protected",
            "Get-ScheduledTask", "Get-CimInstance Win32_Process",
            "OWNER_ADMIN_REQUIRED", "ORIGINAL_TASK_SID_DRIFT",
            "F139OriginalOwnerMutex", "Database.open_readonly",
            "audit_frozen_original_readonly",
            "FRESH_DEVELOPMENT_INTAKE_READY_DISPATCH_BLOCKED",
            "original_sqlite_mutations=0", "worker_dispatched=$false",
            "scientific_first_use=$false", "paid_model_calls=0",
            "F139_FRESH_EXISTING_DISABLED_TASK_REBIND=PASS",
        ):
            with self.subTest(term=term):
                self.assertIn(term, self.script)
        self.assertIn("new_database_path", self.script)

    def test_rebind_is_once_only_and_no_autostart_or_dispatch(self):
        script = self.script
        self.assertEqual(
            script.count("Set-ScheduledTask -TaskName $TaskName -Action $newAction"), 1)
        self.assertLess(
            script.index("COLD_DB_CUSTODY_OR_TASK_NOT_READY"),
            script.index("Set-ScheduledTask -TaskName $TaskName"))
        self.assertLess(
            script.index("IMMUTABLE_WORKER_RELEASE_NOT_PRESENT"),
            script.index("Set-ScheduledTask -TaskName $TaskName"))
        self.assertLess(
            script.index("REBINDED_OR_UNKNOWN_ATTEMPT_NO_REPLAY"),
            script.index("Set-ScheduledTask -TaskName $TaskName"))
        self.assertLess(
            script.index("Set-ScheduledTask -TaskName $TaskName"),
            script.index("F139_FRESH_EXISTING_DISABLED_TASK_REBIND=PASS"))
        for forbidden in (
            "Enable-ScheduledTask", "Start-ScheduledTask",
            "Register-ScheduledTask", "Unregister-ScheduledTask",
            "Disable-ScheduledTask", "Stop-ScheduledTask",
            "gh api --method POST", "gh api --method PATCH",
            "workflow_dispatch", "sqlite3.connect(", "OPENAI_API_KEY=",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    def test_owner_workflow_is_exact_comment_and_same_runner_only(self):
        text = self.workflow
        self.assertEqual(text.count("\non:\n  issue_comment:\n    types: [created]\n"), 1)
        for term in (
            "github.repository == 'spoonman136668-ai/FORGE'",
            "github.actor == 'spoonman136668-ai'",
            "github.event.issue.number == 1830",
            "github.event.comment.author_association == 'OWNER'",
            "F139-FRESH-DEV-TASK-REBIND ",
            "runs-on: [self-hosted, Windows, forge-codex-isolated]",
            "group: forge-f139-v54-original-owner",
            "cancel-in-progress: false",
            "persist-credentials: false",
            "fetch-depth: 0",
            "GH_TOKEN:", "nci04_fresh_owner_rebind.ps1",
            "F139_WORKER_DISPATCH_AUTHORIZED=FALSE",
            "F139_SCIENTIFIC_FIRST_USE=FALSE",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)
        for forbidden in (
            "\n  workflow_dispatch:", "\n  schedule:", "\n  push:",
            "\n  pull_request:", "contents: write", "issues: write",
        ):
            self.assertNotIn(forbidden, text)

    def test_exact_g145_source_scope_has_negative_controls(self):
        from scripts import check_rar_g145_pr_scope as scope
        head = "b" * 40
        base = scope.FRESH_REBIND_BASE
        request = {
            "number": scope.FRESH_REBIND_PR,
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {
                "ref": scope.FRESH_REBIND_BRANCH,
                "sha": head,
                "repo": {"full_name": scope.REPO},
            },
            "base": {
                "ref": "main", "sha": base,
                "repo": {"full_name": scope.REPO},
            },
        }

        def git(*args):
            if args == ("merge-base", base, head):
                return base
            if args == ("rev-parse", base + "^{tree}"):
                return scope.FRESH_REBIND_TREE
            if args == ("diff", "--no-renames", "--name-only", base, head):
                return "\n".join(sorted(scope.FRESH_REBIND_FILES))
            if args[0] == "rev-parse" and args[1].startswith(head + ":"):
                return scope.FRESH_REBIND_BLOBS.get(
                    args[1][len(head) + 1:], "0" * 40)
            raise AssertionError("unexpected git call")

        self.assertEqual(scope.admit_fresh_original_rebind(
            head, base, request, git),
            "EXACT_PR1851_F139_FRESH_DISABLED_TASK_REBIND_CI_ONLY")
        for override in (
            {"number": 1850},
            {"author_association": "CONTRIBUTOR"},
            {"user": {"login": "foreign"}},
            {"head": {**request["head"], "ref": "foreign"}},
            {"base": {**request["base"], "sha": "f" * 40}},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    scope.admit_fresh_original_rebind(
                        head, base, {**request, **override}, git)

        def moved(*args):
            if args == ("rev-parse", head + ":" + scope.FRESH_REBIND_SCRIPT):
                return "0" * 40
            return git(*args)

        with self.assertRaisesRegex(ValueError, "SOURCE_OR_BLOB_DRIFT"):
            scope.admit_fresh_original_rebind(
                head, base, request, moved)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell AST only")
    def test_actual_powershell_ast_parses_without_execution(self):
        ps = shutil.which("powershell.exe") or shutil.which("pwsh")
        self.assertIsNotNone(ps)
        expr = (
            "$ErrorActionPreference='Stop';$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:F139_PS_SOURCE,[ref]$t,[ref]$e)|Out-Null;"
            "if($null -ne $e -and @($e).Count -gt 0){"
            "$e|ForEach-Object{Write-Output $_.Message};exit 1}"
        )
        result = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", expr],
            env={**os.environ, "F139_PS_SOURCE": str(SCRIPT)},
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[:2000])


if __name__ == "__main__":
    unittest.main()
