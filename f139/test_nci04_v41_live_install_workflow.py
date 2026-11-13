"""Static negative controls for one-shot V41 original-owner installation route.

Unit qualification proves source/wiring restrictions only. Actual original
Windows owner execution and post-install research acceptance remain separate.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v41-original-owner-live-install.yml"
WRAPPER = ROOT / "f139/v41_original_owner_live_install.ps1"


class OriginalOwnerV41InstallWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.wrapper = WRAPPER.read_text(encoding="utf-8")

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
