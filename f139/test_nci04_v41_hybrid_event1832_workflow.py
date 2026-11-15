"""V39 on ORIGINAL owner workflow only; no competing task or schedule."""
import unittest
from pathlib import Path
from f139 import nci04_v41_hybrid_event1832_owner as owner
from f139 import nci04_v41_hybrid_event1832_commit as committed
from f139 import nci04_v41_hybrid_event1832_postcommit as postcommit

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/f139-v39-original-source-successor.yml"
LEGACY=ROOT/".github/workflows/f139-v41-original-owner-live-install.yml"
GUARD=ROOT/"scripts/check_rar_g145_pr_scope.py"


class OriginalV39WorkflowTests(unittest.TestCase):
    def test_original_owner_comment_routes_isolate_skipped_v41_event_concurrency(self):
        s=WORKFLOW.read_text("utf-8")
        self.assertEqual(s.count(
            "group: forge-f139-v39-original-source-v2"),1)
        self.assertNotIn("group: forge-f139-v41-original-owner-live-install",s)
        self.assertIn("SingleOwner mutex",s)
        self.assertIn("cancel-in-progress: false",s)
        self.assertIn("name: FORGE F139 V39 guarded original-owner successor source-only",s)
        self.assertNotIn("hybrid-v39-original-event1831-backup:",
                         LEGACY.read_text("utf-8"))
        for name in (
            "hybrid-v39-original-event1831-readiness",
            "hybrid-v39-original-event1831-backup",
            "hybrid-v39-original-event1832-source-commit",
            "hybrid-v39-original-event1832-postcommit",
        ):
            self.assertEqual(s.count("  "+name+":"),1)
        for text in (
            owner.READINESS,owner.BACKUP,
            committed.PREFIX,postcommit.PREFIX,
            "python -B -m f139.nci04_v41_hybrid_event1832_owner",
            "python -B -m f139.nci04_v41_hybrid_event1832_commit",
            "python -B -m f139.nci04_v41_hybrid_event1832_postcommit",
            "runs-on: [self-hosted, Windows, forge-codex-isolated]",
            "github.event.issue.number == 807",
            "github.actor == 'spoonman136668-ai'",
            "github.event.comment.body",
            "github.token",
            "persist-credentials: false",
            "GITHUB_RUN_ATTEMPT -cne '1'",
            "RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",
            "GITHUB_SHA -cnotmatch '^[a-f0-9]{40}$'",
        ):
            self.assertIn(text,s)
        for forbidden in (
            "workflow_dispatch:",
            "\n  schedule:",
            "Register-ScheduledTask",
            "New-ScheduledTask -",
            "F139-NewController",
        ):
            self.assertNotIn(forbidden,s)

    def test_release_correction_preserves_exact_frozen_owner_job(self):
        s=WORKFLOW.read_bytes()
        self.assertFalse(s.endswith(b"\n\n"))
        self.assertTrue(s.endswith(b"\n"))
        scope=GUARD.read_text("utf-8")
        self.assertIn('engineering/f139-v39-postmerge-isolation-correction-20261115',scope)
        self.assertIn('request["number"] != 1775',scope)
        self.assertIn("G145_V39_POSTMERGE_OWNER_BASE_TREE_REQUIRED",scope)
        self.assertIn('"scripts/check_rar_g156_dynamic_base_cache.py"',scope)

    def test_v39_concurrency_guard_is_source_only_and_has_exact_owner_pr(self):
        src=WORKFLOW.read_text("utf-8")
        self.assertEqual(src.count("group: forge-f139-v39-original-source-v2"),1)
        self.assertIn("cancel-in-progress: false",src)
        self.assertNotIn("workflow_dispatch:",src)
        self.assertNotIn("Start-ScheduledTask",src)
        self.assertNotIn("Set-ScheduledTask",src)
        self.assertNotIn("Enable-ScheduledTask",src)
        self.assertIn("request[\"number\"] != 1776",GUARD.read_text("utf-8"))
        self.assertIn("G145_V39_V2_OWNER_BASE_TREE_REQUIRED",GUARD.read_text("utf-8"))

    def test_source_intent_commit_job_and_postcommit_remain_distinct(self):
        s=WORKFLOW.read_text("utf-8")
        start=s.index("  hybrid-v39-original-event1831-readiness:")
        stages=s[start:]
        self.assertEqual(stages.count("    runs-on:"),4)
        self.assertEqual(stages.count("      issues: read"),4)
        self.assertNotIn("      issues: write",stages)
        self.assertEqual(stages.count("    timeout-minutes:"),4)
        self.assertEqual(stages.count("  hybrid-v41-original-source-activate:"),0)
        self.assertIn("  hybrid-v41-original-source-activate:",
                      LEGACY.read_text("utf-8"))

    def test_source_scope_pin_1774_fences_privileged_workflow_changes(self):
        s=GUARD.read_text("utf-8")
        self.assertIn(
            '"engineering/f139-v38-event1831-activation-bridge-20261115": (',s)
        self.assertIn('request["number"] != 1774',s)
        self.assertIn("G145_V39_EXACT_PR1774_OWNER_BASE_TREE_REQUIRED",s)
        self.assertIn('"f139/nci04_v41_hybrid_event1832_owner.py"',s)
        self.assertIn('".github/workflows/f139-v39-original-source-successor.yml"',s)
        self.assertIn('"scripts/check_rar_g148_go_cache.py"',s)
        self.assertIn('"scripts/check_rar_g156_dynamic_base_cache.py"',s)
        self.assertIn('f139/test_nci04_v41_hybrid_event1832_workflow.py',s)

    def test_backup_route_has_no_user_self_dispatch_or_first_use(self):
        src=(ROOT/"f139/nci04_v41_hybrid_event1832_owner.py").read_text("utf-8")
        for text in (
            "if __name__ == \"__main__\"",
            'choices=("readiness", "backup")',
            "original_readiness(db, env, event, GitHub())",
            "original_backup(db, env, event, GitHub())",
        ):
            self.assertIn(text,src)
        for forbidden in (
            "Start-ScheduledTask",
            "Set-ScheduledTask",
            "Enable-ScheduledTask",
            "gh workflow run",
        ):
            self.assertNotIn(forbidden,src)


if __name__=="__main__":
    unittest.main()
