"""Static contract for the single-use original-owner V38 repair workflow.

No live comment, job, scheduler, controller, broker, issue mutation or science
is authorized by these source tests. Historical V41 owner workflow is pinned.
"""
from pathlib import Path
import re
import unittest

from f139 import nci04_v41_hybrid_forward_original_commit as commit
from f139 import nci04_v41_hybrid_forward_backup as backup
from f139 import nci04_v41_hybrid_forward_readiness as readiness


class ForwardWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        cls.workflow = (
            root / "f139-v38-original-owner-forward-recovery.yml"
        ).read_text("utf-8")
        cls.original = (
            root / "f139-v41-original-owner-live-install.yml"
        ).read_text("utf-8")

    def test_same_original_runner_and_serialization_not_new_controller(self):
        self.assertIn("name: " + commit.BACKUP_WORKFLOW, self.workflow)
        self.assertIn("group: forge-f139-v41-original-owner-live-install",
                      self.workflow)
        self.assertIn("group: forge-f139-v41-original-owner-live-install",
                      self.original)
        self.assertEqual(self.workflow.count(
            "runs-on: [self-hosted, Windows, forge-codex-isolated]"), 3)
        self.assertEqual(self.workflow.count(
            "RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'"), 3)
        self.assertEqual(self.workflow.count(
            "GITHUB_RUN_ATTEMPT -cne '1'"), 3)
        self.assertEqual(self.workflow.count(
            "persist-credentials: false"), 3)

    def test_only_three_separate_owner_issue_comment_gates(self):
        self.assertIn("issue_comment:", self.workflow)
        self.assertIn("types: [created]", self.workflow)
        for job, prefix, module in (
            ("hybrid-v38-original-forward-readiness",
             readiness.PREFIX,
             "f139.nci04_v41_hybrid_forward_readiness"),
            (commit.BACKUP_JOB, backup.PREFIX,
             "f139.nci04_v41_hybrid_forward_backup"),
            ("hybrid-v38-original-forward-commit", commit.PREFIX,
             "f139.nci04_v41_hybrid_forward_original_commit"),
        ):
            with self.subTest(job=job):
                self.assertEqual(self.workflow.count("  " + job + ":"), 1)
                self.assertIn("startsWith(github.event.comment.body, '" +
                              prefix + "')", self.workflow)
                self.assertEqual(self.workflow.count(
                    "& $match.Groups[1].Value -m " + module +
                    " --target $env:GITHUB_SHA"), 1)
        self.assertEqual(self.workflow.count(
            "github.event.issue.number == 807"), 3)
        self.assertEqual(self.workflow.count(
            "github.actor == 'spoonman136668-ai'"), 3)
        self.assertEqual(self.workflow.count(
            "GITHUB_REF -cne 'refs/heads/main'"), 3)

    def test_no_implicit_original_controller_mutation_or_extra_scheduler(self):
        for forbidden in (
            "workflow_dispatch:", "schedule:", "cron:", "push:",
            "pull_request:", "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Register-ScheduledTask", "gh workflow run",
            "gh api --method PATCH", "issues: write", "contents: write",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.workflow)
        self.assertEqual(self.workflow.count("GH_TOKEN: ${{ github.token }}"), 3)
        self.assertEqual(self.workflow.count("cancel-in-progress: false"), 1)
        self.assertEqual(self.workflow.count(
            "ORIGINAL_TASK_NOT_QUIESCED"), 3)

    def test_existing_pinned_workflow_remains_without_new_v38_jobs(self):
        self.assertNotIn("hybrid-v38-original-forward", self.original)
        self.assertNotIn(
            "f139.nci04_v41_hybrid_forward_original_commit", self.original)


if __name__ == "__main__":
    unittest.main()
