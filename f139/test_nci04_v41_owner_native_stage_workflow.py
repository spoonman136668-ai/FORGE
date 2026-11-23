"""V41 native stage workflow is a one-shot, non-deployment owner route.

The separate Python stage tests verify the canonical owner comment, remote
double-read, exact first-attempt runner, immutable release source and create-
only staging. These tests guard the GitHub workflow wiring itself.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v41-original-owner-native-stage.yml"


class V41OwnerNativeStageWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contents = WORKFLOW.read_text(encoding="utf-8")

    def test_frozen_branch_scope_matches_only_our_five_paths(self):
        from scripts import check_rar_g145_pr_scope as guard
        expected = {
            ".github/workflows/f139-v41-original-owner-native-stage.yml",
            "f139/test_nci04_v41_owner_native_stage_workflow.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        }
        self.assertEqual(
            guard.FROZEN_SCOPES["engineering/f139-v41-owner-native-stage-workflow-20261113"],
            ("2a7f2f58f829e9de9bdf47fe963d3edbf9335982", expected))

    def test_trigger_is_only_new_original_owner_issue_comment(self):
        source = self.contents
        self.assertIn("  issue_comment:\n    types: [created]", source)
        self.assertEqual(source.count("  issue_comment:"), 1)
        self.assertIn("github.actor == 'spoonman136668-ai'", source)
        self.assertIn("github.event.issue.number == 807", source)
        self.assertIn("!github.event.issue.pull_request", source)
        self.assertIn("startsWith(github.event.comment.body, 'F139-V41-NATIVE-STAGE ')", source)
        self.assertIn("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'", source)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", source)
        self.assertIn("GITHUB_REF -cne 'refs/heads/main'", source)
        for forbidden in ("workflow_dispatch:", "schedule:", "push:", "pull_request:", "repository_dispatch:"):
            self.assertNotIn("\n  " + forbidden, source)

    def test_permissions_and_source_identity_are_read_only(self):
        source = self.contents
        self.assertIn("permissions:\n  contents: read\n  issues: read\n  actions: read", source)
        self.assertNotIn("permissions: write", source)
        self.assertNotIn("  issues: write", source)
        self.assertNotIn("  contents: write", source)
        self.assertIn("persist-credentials: false", source)
        self.assertIn("fetch-depth: 0", source)
        self.assertIn("go-version: '1.23.12'", source)
        self.assertIn("cache: false", source)
        self.assertIn("GH_TOKEN: ${{ github.token }}", source)
        self.assertIn("python -B -m f139.nci04_v41_candidate_stage --target $env:GITHUB_SHA", source)
        self.assertEqual(source.count("    runs-on: [self-hosted, Windows, forge-codex-isolated]"), 1)
        for forbidden in ("Stop-ScheduledTask", "Start-ScheduledTask", "Set-ScheduledTask",
                          "Register-ScheduledTask", "Disable-ScheduledTask",
                          "Enable-ScheduledTask", "sqlite3.connect", "gh api --method",
                          "curl ", "Invoke-WebRequest", "OpenAI_API_KEY:"):
            self.assertNotIn(forbidden, source)

    def test_no_automatic_retry_or_second_controller(self):
        source = self.contents
        self.assertIn("cancel-in-progress: false", source)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", source)
        self.assertEqual(source.count("  native-candidate-stage:"), 1)
        self.assertNotIn("retry", source.lower())
        self.assertNotIn("scientific_first_use: true", source.lower())
        self.assertNotIn("hybrid_admission: true", source.lower())


if __name__ == "__main__":
    unittest.main()
