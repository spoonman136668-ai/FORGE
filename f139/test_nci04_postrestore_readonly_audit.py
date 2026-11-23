"""Source-contract guards for the no-mutation F139 owner log audit."""
from pathlib import Path
import unittest

WORKFLOW = (Path(__file__).resolve().parents[1] /
    ".github" / "workflows" / "f139-fresh-original-owner-rebind.yml")


class F139PostrestoreReadOnlyAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.audit = cls.workflow.split("  fresh-release-readonly-audit:", 1)[1]

    def test_existing_owner_only_issue_admission_unchanged(self):
        self.assertIn("github.event.issue.number == 1830", self.workflow)
        self.assertIn("github.event.comment.author_association == 'OWNER'", self.workflow)
        self.assertIn("startsWith(github.event.comment.body, 'F139-FRESH-DEV-RELEASE-CUSTODY-READONLY ')", self.audit)
        self.assertNotIn("workflow_dispatch:", self.workflow)
        self.assertEqual(self.workflow.count("  issue_comment:"), 1)

    def test_snapshot_preserves_cold_source_and_sqlite_checks(self):
        for field in ("source_forward_task_binding", "source_forward_stage_class",
                      "source_forward_certificate_class", "historical", "fresh",
                      "task_mutations=0", "sqlite_mutations=0",
                      "worker_dispatches=0", "scientific_first_use=$false"):
            self.assertIn(field, self.audit)
        self.assertIn("release-candidates\\f24251e0d95938e593a54c1577a34efadc8080d8", self.audit)

    def test_bounded_redacted_log_metrics(self):
        for token in ("Get-ScheduledTaskInfo", "Get-Content -LiteralPath $logPath -Tail 160",
                      "$line.Length -gt 4096", "Select-Object -Last 12",
                      "controller_log_event_classes", "controller_poll_records_in_tail",
                      "controller_log_readable", "last_task_run_utc",
                      "next_task_run_utc", "last_task_result",
                      "SOURCE_CERT_MISMATCH", "NO_UNUSED_SOURCE_RECIPE",
                      "ReparsePoint"):
            self.assertIn(token, self.audit)

    def test_no_new_execution_or_raw_log_disclosure(self):
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask",
                          "Enable-ScheduledTask", "Disable-ScheduledTask",
                          "Register-ScheduledTask", "Set-ScheduledTask",
                          "Start-Process", "Invoke-RestMethod", "workflow_dispatch:",
                          "Write-Output $line", "Write-Host $line",
                          "ConvertTo-Json $line", "create_native_feed_issue"):
            self.assertNotIn(forbidden, self.audit)
        self.assertIn("F139_FRESH_CUSTODY_READONLY_MUTATIONS=0", self.audit)


if __name__ == "__main__":
    unittest.main()
