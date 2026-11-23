"""Scope tests for the operator-approved one-shot original owner preflight.

Source-only tests; never submit a GitHub comment, start a task, change state,
read original private evidence or dispatch a runner.
"""
from pathlib import Path
import unittest

from scripts import check_rar_g145_pr_scope as guard

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "f139-v38-original-owner-readonly-once.yml"
DOC = ROOT / "docs" / "F139-V38-ONE-SHOT-ORIGINAL-OWNER-READONLY.md"


class OriginalReadonlyOwnerWorkflowTests(unittest.TestCase):
    def test_exact_no_schedule_single_owner_workflow(self):
        src = WORKFLOW.read_text("utf-8")
        self.assertTrue(src.startswith(
            "name: FORGE F139 V38 original owner one-shot read-only preflight\n"))
        self.assertIn("on:\n  issue_comment:\n    types: [created]", src)
        self.assertIn("group: forge-f139-v38-original-ledger-cold-readonly-v1", src)
        self.assertNotIn("group: forge-f139-v41-original-owner-live-install", src)
        self.assertIn("cancel-in-progress: false", src)
        self.assertEqual(src.count("  original-owner-v38-readonly-preflight:\n"), 1)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", src)
        self.assertIn("github.actor == 'spoonman136668-ai'", src)
        self.assertIn("github.event.issue.number == 807", src)
        self.assertIn("!github.event.issue.pull_request", src)
        self.assertIn("github.event.comment.body, 'F139-V38-LEDGER-COLD-READONLY-V1 '", src)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", src)
        self.assertIn("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'", src)
        self.assertIn("GH_TOKEN: ${{ github.token }}", src)
        self.assertIn("persist-credentials: false", src)
        self.assertIn("fetch-depth: 0", src)
        self.assertIn(" python -B -m f139.nci04_v38_owner_ledger_cold_readonly --target $env:GITHUB_SHA", src)
        self.assertIn("6892848524", src)
        self.assertEqual(src.count("& python -B -m f139.nci04_v38_owner_ledger_cold_readonly"), 1)
        for prohibited in (
            "\n  schedule:", "\n  workflow_dispatch:", "\n  push:",
            "permissions:\n  contents: write",
            "issues: write", "actions: write", "pull-requests: write",
            "Set-ScheduledTask", "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Set-Content", "New-ScheduledTask", "Register-ScheduledTask",
            "gh workflow run", "gh api --method", "update-ref",
            "upgrade-hybrid-lane", "commit_transition(", "CREATE TABLE",
            "Start-Process", "workflow_call:",
        ):
            self.assertNotIn(prohibited, src)

    def test_source_scoped_freeze_and_no_new_runtime(self):
        self.assertIn("one read-only original-owner", DOC.read_text("utf-8"))
        self.assertIn("c611c4362e3cc867984448a03ecdf3be923d2ef1",
                      DOC.read_text("utf-8"))
        self.assertEqual(guard.V38_READONLY_BRANCH,
                         "engineering/f139-v38-original-owner-readonly-once-20261114")
        self.assertEqual(set(guard.V38_READONLY_FILES), {
            ".github/workflows/f139-v38-original-owner-readonly-once.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
            "f139/test_v38_owner_readonly_workflow_scope.py",
            "docs/F139-V38-ONE-SHOT-ORIGINAL-OWNER-READONLY.md",
        })
        self.assertFalse(guard.generic_paths_safe([
            ".github/workflows/f139-v38-original-owner-readonly-once.yml"]))
        guard.v38_readonly_negative_controls()


if __name__ == "__main__":
    unittest.main()
