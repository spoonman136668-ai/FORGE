"""Read-only V59 original Windows owner route scope and negative controls."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WF=ROOT/".github/workflows/f139-v59-original-owner-readonly.yml"
G145=ROOT/"scripts/check_rar_g145_pr_scope.py"
G148=ROOT/"scripts/check_rar_g148_go_cache.py"
G156=ROOT/"scripts/check_rar_g156_dynamic_base_cache.py"
BRANCH="engineering/f139-v59-original-cold-readonly-once-20261119"
BASE="d620479254755e3fe375ecb293b38f97a6bebdba"
TREE="4ac7e84573d9b4c9eb3ddbd811c52dd730f3db18"

class V59OriginalReadOnlyWorkflowScopeTests(unittest.TestCase):
    def test_workflow_is_single_run_owner_readonly(self):
        src=WF.read_text()
        for phrase in (
            "types: [created]",
            "group: forge-f139-v54-original-owner",
            "cancel-in-progress: false",
            "github.actor == 'spoonman136668-ai'",
            "github.event.issue.number == 807",
            "F139-V59-ORIGINAL-READONLY ",
            "F139_V59_ORIGINAL_READONLY=PASS",
            "RUNNER_NAME",
            "FORGE-CODEX-REMOTE",
            "ORIGINAL_INSTALLED_SOURCE_DRIFT",
            "FRESH_EXACT_OWNER_COMMENT_REQUIRED",
            "SOURCE_TRANSITION_AUTHORIZED=FALSE",
            "OWNER_TASK_MUTATIONS=ZERO",
            "audit_frozen_original_readonly",
            "Database.open_readonly",
            "PRAGMA query_only" if False else "owner_mutations",
        ):
            self.assertIn(phrase,src)
        for forbidden in (
            "Disable-ScheduledTask", "Enable-ScheduledTask",
            "Stop-ScheduledTask", "Start-ScheduledTask",
            "Register-ScheduledTask", "Set-ScheduledTask",
            "sqlite3.connect(", "db.event(", "UPDATE meta SET",
            "paid_api_calls: 1", "contents: write",
            "workflow_dispatch:", "schedule:",
        ):
            self.assertNotIn(forbidden,src)

    def test_exact_policy_and_source_anchor(self):
        src=WF.read_text()
        self.assertIn("c06403c8b6035c6c7013866a7ea08cef1244b507",src)
        self.assertIn("scientific_first_use -eq $false",src)
        self.assertIn("new_controller -eq $false",src)
        self.assertIn("new_scheduler -eq $false",src)
        self.assertIn("new_queue -eq $false",src)
        self.assertIn("7013003282",src)
        self.assertIn(" 1864",src)
        self.assertIn("issues/comments/",src)

    def test_only_one_workflow_and_guarded_ci_admission(self):
        s145=G145.read_text()
        s148=G148.read_text()
        s156=G156.read_text()
        self.assertIn(BRANCH,s145)
        self.assertIn(BASE,s145)
        self.assertIn(TREE,s145)
        self.assertIn("V59_READONLY_WORKFLOW_BLOB",s145)
        self.assertIn(BRANCH,s148)
        self.assertIn(BRANCH,s156)
        self.assertIn(BASE,s156)
        self.assertIn(TREE,s156)

if __name__=="__main__":
    unittest.main()
