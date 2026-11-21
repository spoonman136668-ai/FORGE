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

    def test_rebind_source_pr_merge_is_pinned_ancestor_not_current_head(self):
        # Current protected main necessarily advances after the rebind source PR.
        self.assertIn(
            "$SourceRebindMerge='e23b39a558b84b230f6bf9d9e37d2ade7aaf3b3a'",
            self.script)
        self.assertIn("$pr.merge_commit_sha -ceq $SourceRebindMerge", self.script)
        self.assertNotIn("$pr.merge_commit_sha -ceq $Target", self.script)
        self.assertIn(
            "& git merge-base --is-ancestor $SourceRebindMerge $Target | Out-Null",
            self.script)
        self.assertIn(
            "Need ($LASTEXITCODE -eq 0) 'QUALIFIED_OWNER_SOURCE_NOT_ANCESTOR'",
            self.script)
        self.assertLess(
            self.script.index("QUALIFIED_OWNER_SOURCE_NOT_ANCESTOR"),
            self.script.index("Set-ScheduledTask -TaskName $TaskName"))

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
            "group: forge-f139-fresh-existing-disabled-task-rebind",
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

    def test_owner_host_shell_is_builtin_powershell_not_absent_pwsh(self):
        text = self.workflow
        self.assertIn("        shell: powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File {0}\n", text)
        original, others = text.split("\n  release-existing-fresh-task:\n")
        release, audit = others.split("\n  fresh-release-readonly-audit:\n")
        self.assertEqual(original.count("        shell: powershell -NoProfile"), 1)
        self.assertEqual(release.count("        shell: powershell -NoProfile"), 1)
        self.assertEqual(audit.count("        shell: powershell -NoProfile"), 1)
        self.assertIn("F139-FRESH-DEV-RELEASE-CUSTODY-READONLY ", audit)
        self.assertNotIn("F139-FRESH-DEV-WORKER-RELEASE ", audit)
        self.assertNotIn("F139-FRESH-DEV-TASK-REBIND ", audit)
        self.assertIn("PRAGMA query_only=ON", audit)
        self.assertIn("F139_FRESH_CUSTODY_READONLY_V1=", audit)
        self.assertIn("F139_FRESH_CUSTODY_READONLY_MUTATIONS=0", audit)
        self.assertIn("44889700647", audit)
        for forbidden in ("Set-ScheduledTask", "Enable-ScheduledTask",
                          "Disable-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Register-ScheduledTask",
                          "Unregister-ScheduledTask", "F139_WORKER_HMAC_KEY",
                          "gh api --method POST", "sqlite3.connect(p)"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, audit)
        self.assertNotIn("F139-FRESH-DEV-WORKER-RELEASE ", original)
        self.assertNotIn("F139-FRESH-DEV-TASK-REBIND ", release)
        self.assertIn("nci04_fresh_owner_worker_release", release)
        self.assertIn("Import-Clixml", release)
        self.assertIn("Remove-Item Env:F139_WORKER_HMAC_KEY", release)
        self.assertNotIn("        shell: powershell\n", text)
        self.assertNotIn("        shell: powershell.exe -NoProfile", text)
        self.assertNotIn("Set-ExecutionPolicy", text)
        self.assertNotIn("        shell: pwsh", text)
        self.assertIn("powershell.exe -NoProfile -NonInteractive", text)
        self.assertIn("F139_FRESH_OWNER_TASK_REBIND_FAILED_CUSTODY_HOLD", text)



    @unittest.skipUnless(os.name == "nt", "Windows PowerShell AST only")
    def test_readonly_audit_powershell_ast_parses_without_execution(self):
        ps = shutil.which("powershell.exe")
        self.assertIsNotNone(ps)
        tail = self.workflow.split("\n  fresh-release-readonly-audit:\n", 1)[1]
        script = tail.split("        run: |\n", 1)[1]
        rows = script.splitlines()
        code = "\n".join(row[10:] if row.startswith("          ") else row
                         for row in rows)
        self.assertIn("F139_FRESH_CUSTODY_READONLY_V1", code)
        parse = ("$t=$null;$e=$null;"
                 "[System.Management.Automation.Language.Parser]::ParseInput("
                 "$env:F139_AUDIT_SOURCE,[ref]$t,[ref]$e)|Out-Null;"
                 "if(@($e).Count -gt 0){"
                 "$e|ForEach-Object{Write-Output $_.Message};exit 1}")
        result = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", parse],
            env={**os.environ, "F139_AUDIT_SOURCE": code},
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[:1800])

    def test_owner_rebind_isolated_from_all_legacy_pending_job_groups(self):
        # Real original-owner run 44844005419 was cancelled before steps:
        # unrelated issue_comment workflows shared the old pending slot.
        rebind_group = "group: forge-f139-fresh-existing-disabled-task-rebind"
        legacy_group = "group: forge-f139-v54-original-owner"
        self.assertIn(rebind_group, self.workflow)
        self.assertNotIn(legacy_group, self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertIn("F139OriginalOwnerMutex", self.script)
        self.assertIn("SINGLE_DISABLED_ORIGINAL_TASK_REQUIRED", self.script)
        self.assertIn("REBINDED_OR_UNKNOWN_ATTEMPT_NO_REPLAY", self.script)
        other_workflows = (
            ".github/workflows/f139-v59-original-owner-readonly.yml",
            ".github/workflows/f139-v54-original-owner-release.yml",
        )
        for filename in other_workflows:
            with self.subTest(filename=filename):
                original = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn(legacy_group, original)
                self.assertNotIn(rebind_group, original)

    def test_exact_g145_owner_process_policy_launcher_fix(self):
        from scripts import check_rar_g145_pr_scope as scope
        head = "e" * 40
        base = scope.FRESH_POLICY_BASE
        request = {
            "number": scope.FRESH_POLICY_PR,
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {
                "ref": scope.FRESH_POLICY_BRANCH,
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
                return scope.FRESH_POLICY_TREE
            if args == ("diff", "--no-renames", "--name-only", base, head):
                return "\n".join(sorted(scope.FRESH_POLICY_FILES))
            if args[0] == "rev-parse" and args[1].startswith(head + ":"):
                return scope.FRESH_POLICY_BLOBS.get(
                    args[1][len(head) + 1:], "0" * 40)
            raise AssertionError("unexpected git call")
        self.assertEqual(
            scope.admit_fresh_owner_process_policy_fix(
                head, base, request, git),
            "EXACT_PR1854_F139_FRESH_OWNER_PROCESS_POLICY_FIX_CI_ONLY")
        for override in (
            {"number": 1853},
            {"author_association": "CONTRIBUTOR"},
            {"user": {"login": "foreign"}},
            {"head": {**request["head"], "ref": "unrelated"}},
            {"base": {**request["base"], "sha": "0" * 40}},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    scope.admit_fresh_owner_process_policy_fix(
                        head, base, {**request, **override}, git)
        for drift_path in (scope.FRESH_POLICY_WORKFLOW, scope.FRESH_POLICY_SCRIPT):
            def changed(*args):
                if args == ("rev-parse", head + ":" + drift_path):
                    return "0" * 40
                return git(*args)
            with self.subTest(drift_path=drift_path):
                with self.assertRaisesRegex(ValueError, "SOURCE_OR_BLOB_DRIFT"):
                    scope.admit_fresh_owner_process_policy_fix(
                        head, base, request, changed)

    def test_exact_g145_fresh_rebind_concurrency_cancellation_fix(self):
        from scripts import check_rar_g145_pr_scope as scope
        head = "d" * 40
        base = scope.FRESH_REBIND_CANCEL_BASE
        request = {
            "number": scope.FRESH_REBIND_CANCEL_PR,
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {
                "ref": scope.FRESH_REBIND_CANCEL_BRANCH,
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
                return scope.FRESH_REBIND_CANCEL_TREE
            if args == ("diff", "--no-renames", "--name-only", base, head):
                return "\n".join(sorted(scope.FRESH_REBIND_CANCEL_FILES))
            if args[0] == "rev-parse" and args[1].startswith(head + ":"):
                return scope.FRESH_REBIND_CANCEL_BLOBS.get(
                    args[1][len(head) + 1:], "0" * 40)
            raise AssertionError("unexpected git call")
        self.assertEqual(
            scope.admit_fresh_rebind_pending_collision_fix(
                head, base, request, git),
            "EXACT_PR1853_F139_FRESH_OWNER_PENDING_CANCEL_FIX_CI_ONLY")
        for override in (
            {"number": 1852},
            {"author_association": "CONTRIBUTOR"},
            {"user": {"login": "foreign"}},
            {"head": {**request["head"], "ref": "unrelated"}},
            {"base": {**request["base"], "sha": "0" * 40}},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    scope.admit_fresh_rebind_pending_collision_fix(
                        head, base, {**request, **override}, git)
        def moved(*args):
            if args == ("rev-parse", head + ":" + scope.FRESH_REBIND_CANCEL_WORKFLOW):
                return "0" * 40
            return git(*args)
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_BLOB_DRIFT"):
            scope.admit_fresh_rebind_pending_collision_fix(
                head, base, request, moved)

    def test_exact_g145_owner_shell_fix_negative_controls(self):
        from scripts import check_rar_g145_pr_scope as scope
        head = "c" * 40
        base = scope.FRESH_SHELL_BASE
        request = {
            "number": scope.FRESH_SHELL_PR, "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {
                "ref": scope.FRESH_SHELL_BRANCH,
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
                return scope.FRESH_SHELL_TREE
            if args == ("diff", "--no-renames", "--name-only", base, head):
                return "\n".join(sorted(scope.FRESH_SHELL_FILES))
            if args[0] == "rev-parse" and args[1].startswith(head + ":"):
                return scope.FRESH_SHELL_BLOBS.get(
                    args[1][len(head) + 1:], "0" * 40)
            raise AssertionError("unexpected git call")
        self.assertEqual(
            scope.admit_fresh_owner_shell_fix(head, base, request, git),
            "EXACT_PR1852_F139_NATIVE_POWERSHELL_HOST_FIX_CI_ONLY")
        for override in (
            {"number": 1851},
            {"author_association": "CONTRIBUTOR"},
            {"user": {"login": "foreign"}},
            {"head": {**request["head"], "ref": "unrelated"}},
            {"base": {**request["base"], "sha": "0" * 40}},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    scope.admit_fresh_owner_shell_fix(
                        head, base, {**request, **override}, git)
        def moved(*args):
            if args == ("rev-parse", head + ":" + scope.FRESH_SHELL_WORKFLOW):
                return "0" * 40
            return git(*args)
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_BLOB_DRIFT"):
            scope.admit_fresh_owner_shell_fix(head, base, request, moved)

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
