"""V26 original owner cutover is one-shot, dormant and fail-closed.

This test never launches a task, reads owner credentials or contacts a model.
It prevents accidental trigger/bypass as V26 moves from draft to main.
"""
from __future__ import annotations

from pathlib import Path
import unittest

WORKFLOW = (Path(__file__).resolve().parent.parent /
            ".github/workflows/f139-v26-original-owner-guarded-release.yml")


class OriginalV26ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = WORKFLOW.read_text(encoding="utf-8")

    def test_only_explicit_owner_comment_triggers_release(self):
        s = self.raw
        for x in (
            "  issue_comment:", "    types: [created]",
            "github.actor == 'spoonman136668-ai'",
            "github.event.issue.number == 807",
            "startsWith(github.event.comment.body, 'F139-V26-OWNER-CUTOVER ')",
            "github.event.comment.body",
            "$event.comment.id", 
            "$env:GITHUB_RUN_ATTEMPT -cne '1'",
            "$env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",
            "runs-on: [self-hosted, Windows, forge-codex-isolated]",
        ):
            self.assertIn(x, s)
        for unwanted in ("  schedule:", "  workflow_dispatch:", "  push:",
                         "f139.local_controller --db $dbPath tick"):
            self.assertNotIn(unwanted, s)

    def test_same_original_owner_and_v20_immutable_predecessor(self):
        s = self.raw
        for token in (
            "$old='db7a1d0f324478183c54df417624053448d6b08b'",
            "$name='FORGE-F139-UnifiedController'",
            "Get-ScheduledTask -TaskName $name",
            "WindowsIdentity]::GetCurrent()",
            "IsInRole(",
            "Field 'RepositoryRoot'", 
            "Field 'Database'", 
            "Field 'PythonExe'", 
            "$env:GITHUB_SHA",
            "Get-ScheduledTask -TaskName $name).State -cne 'Disabled'",
            "f139-owner-release-$target",
            "FORGE F139 immutable owner release refs",
            "'bypass_actors'",
            "@($rule.bypass_actors).Count -ne 0",
            "refs/heads/f139-owner-release-*",
            "if($lockTypes.Count -ne 2",
            "F139_V26_SOURCE_PINNED_OWNER_POLICY_DRIFT",
            "F139_V26_POLICY_READBACK_DRIFT",
        ):
            self.assertIn(token, s)

    def test_original_cold_backup_precedes_exactly_one_mutation(self):
        s = self.raw
        for token in (
            "from f139.nci04_v24_v20_renewable_readonly_preflight import build_v24_readonly_preflight",
            "proof=build_v24_readonly_preflight(",
            "FIRST_TICKET, RUN_ID as FIRST_RUN",
            "SECOND_TICKET, RUN_ID as SECOND_RUN",
            "shutil.copyfile(source,copied)",
            "with sqlite3.connect(str(backup)) as out:",
            "db.conn.backup(out)",
            "cold=Database.open_readonly(backup)",
            "cold.verify()",
            "assert cold.meta() == original",
            "F139_V26_BACKUP_SHA256_MISMATCH",
            "F139_V26_PRETRANSITION_BACKUP_COLLISION",
            "F139_V26_PARTIAL_CUSTODY_EXISTING_TASK_HELD_DISABLED",
            "F139_V26_ORIGINAL_TASK_NOT_RESUMED",
        ):
            self.assertIn(token, s)
        self.assertLess(s.index("cold.verify()"), s.index("$mutationPossible=$true"))
        self.assertEqual(s.count(
            "& $python -B -m f139.nci04_v25_original_owner_transition_cli "
            "--db $dbPath --approval $approval"), 1)
        self.assertNotIn("transition-qualified-native-v20", s)
        self.assertNotIn("activate-native --approval", s)

    def test_no_assumption_of_model_or_scientific_first_use(self):
        s = self.raw
        for token in (
            "F139_V26_SCIENTIFIC_FIRST_USE=FALSE",
            "F139_V26_NEW_CONTROLLER=FALSE",
            "F139_V26_PAID_API_CALLS=0",
            "$mutationPossible=$true",
            "F139_V26_ORIGINAL_SOURCE_CUTOVER=PASS",
        ):
            self.assertIn(token, s)
        self.assertNotIn("OPENROUTER_API_KEY", s)
        self.assertNotIn("MODEL_DRAFT_AUTHENTICATED=PASS", s)
        self.assertNotIn("new-scheduled-task", s.lower())
        self.assertNotIn("worker_dispatched=true", s.lower())


if __name__ == "__main__":
    unittest.main()
