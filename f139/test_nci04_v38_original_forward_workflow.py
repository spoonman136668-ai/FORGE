"""Exact original-owner event workflow & versioned release-custody tests.

Static source only: no live owner event, SQLite writes, task starts, or science.
"""
from pathlib import Path
import unittest

from f139 import nci04_v41_hybrid_forward_readiness as readiness
from f139 import nci04_v41_hybrid_forward_backup as backup
from f139 import nci04_v41_hybrid_forward_original_commit as commit
from f139 import nci04_v41_hybrid_forward_postcommit as postcommit
from scripts import check_rar_g145_pr_scope as g145

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v38-original-forward-install.yml"

class OriginalForwardWorkflowTests(unittest.TestCase):
    def test_exact_original_owner_routes_are_distinct_and_not_scheduled(self):
        text = WORKFLOW.read_text("utf-8")
        self.assertEqual(text.count("name: FORGE F139 V38 guarded original-owner forward installation"), 1)
        self.assertIn("concurrency:\n  group: forge-f139-v38-original-forward-install-v2\n  cancel-in-progress: false", text)\n        self.assertNotIn("group: forge-f139-v41-original-owner-live-install", text)
        self.assertEqual(text.count("runs-on: [self-hosted, Windows, forge-codex-isolated]"), 4)
        self.assertEqual(text.count("github.actor == 'spoonman136668-ai'"), 4)
        self.assertEqual(text.count("github.event.issue.number == 807"), 4)
        self.assertEqual(text.count("GITHUB_RUN_ATTEMPT -cne '1'"), 4)
        self.assertEqual(text.count("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'"), 4)
        self.assertEqual(text.count("persist-credentials: false"), 4)
        self.assertEqual(text.count("GH_TOKEN: ${{ github.token }}"), 4)
        stages = (
            ("hybrid-v38-original-forward-readiness",
             "F139-HYBRID-V41-FORWARD-READINESS ",
             "f139.nci04_v41_hybrid_forward_readiness"),
            ("hybrid-v38-original-forward-backup",
             "F139-HYBRID-V41-FORWARD-BACKUP ",
             "f139.nci04_v41_hybrid_forward_backup"),
            ("hybrid-v38-original-forward-source-commit",
             "F139-HYBRID-V41-FORWARD-COMMIT ",
             "f139.nci04_v41_hybrid_forward_original_commit"),
            ("hybrid-v38-original-forward-postcommit",
             "F139-HYBRID-V41-FORWARD-POSTCOMMIT ",
             "f139.nci04_v41_hybrid_forward_postcommit"),
        )
        for name, prefix, module in stages:
            self.assertEqual(text.count("  " + name + ":\n"), 1)
            self.assertEqual(text.count("startsWith(github.event.comment.body, '" + prefix + "')"), 1)
            self.assertEqual(text.count("& python -B -m " + module + " --target $env:GITHUB_SHA"), 1)
        self.assertEqual(backup.PREFIX, stages[1][1])
        self.assertEqual(backup.SCHEMA, "forge.f139.hybrid-forward.original-backup-only.v1")
        self.assertEqual(commit.PREFIX, stages[2][1])
        self.assertEqual(commit.BACKUP_JOB, stages[1][0])
        self.assertEqual(commit.BACKUP_WORKFLOW,
                         "FORGE F139 V38 guarded original-owner forward installation")
        self.assertEqual(postcommit.PREFIX, stages[3][1])
        self.assertEqual(readiness.PREFIX, stages[0][1])
        self.assertEqual(readiness.PR, 1773)
        self.assertEqual(readiness.BRANCH, g145.V38_FORWARD_V2_BRANCH)
        for bad in (
            "\n  schedule:", "\n  workflow_dispatch:", "\n  push:",
            "workflow_call:", "Start-ScheduledTask", "Stop-ScheduledTask",
            "Register-ScheduledTask", "Enable-ScheduledTask",
            "Disable-ScheduledTask", "gh workflow run", "gh api --method",
            "contents: write", "issues: write", "actions: write",
            "Start-Process", "Set-ScheduledTask",
            "OpenAI", "CKB-plane",
        ):
            self.assertNotIn(bad, text)

    def test_source_and_owner_scopes_stay_disjoint(self):
        self.assertFalse(g145.generic_paths_safe([
            ".github/workflows/f139-v38-original-forward-install.yml"]))
        self.assertEqual(len(g145.V38_FORWARD_FILES), 8)
        self.assertIn("f139/nci04_v41_hybrid_forward_readiness.py",
                      g145.V38_FORWARD_FILES)
        self.assertNotIn(
            ".github/workflows/f139-v41-original-owner-live-install.yml",
            g145.V38_FORWARD_FILES)
        self.assertNotIn("f139/nci04_v41_hybrid_forward_original_commit.py",
                         g145.V38_FORWARD_FILES)
        g145.v38_forward_negative_controls()
        g145.v38_forward_v2_negative_controls()

if __name__ == "__main__":
    unittest.main()
