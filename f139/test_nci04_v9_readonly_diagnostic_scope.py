"""Source-only regression: V9 read-only owner diagnostic must not treat a
qualified V41 successor as legacy source drift, or leak failure strings.

Does not trigger issue comments, owner runner, task or SQLite activity.
"""
from __future__ import annotations

from pathlib import Path
import unittest

from f139.nci04_model_free_failure import SAFE_CODES

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_SOURCE = "2c7caad5a4502d4b874a11d57207a35cf033eb08"


class V9OwnerReadOnlyDiagnosticScopeTests(unittest.TestCase):
    def segment(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        return content.split("  read-only-status:\n", 1)[1].split(
            "\n  v40-invocation-qualification:", 1)[0]

    def test_current_source_does_not_run_obsolete_v41_guard(self):
        scope = self.segment()
        self.assertIn(
            "github.sha == '" + V41_SOURCE + "'", scope)
        self.assertIn(
            "github.sha != '" + V41_SOURCE + "'", scope)
        self.assertIn("F139_V41_LEGACY_CHECK=NOT_APPLICABLE_NEWER_SOURCE",
                      scope)
        # Keep the historic assertion for its ONLY legitimate source.
        self.assertIn("$old='" + V41_SOURCE + "'", scope)
        self.assertIn("F139_V41_ORIGINAL_INSTALL_OR_SOURCE_DRIFT", scope)

    def test_model_free_failure_code_is_read_only_and_allowlisted(self):
        scope = self.segment()
        self.assertIn("from f139.nci04_model_free_failure import SAFE_CODES",
                      scope)
        self.assertIn("failure_code=$safeCode", scope)
        self.assertIn("[string]$rawCode -cin $failureCodeAllowlist",
                      scope)
        self.assertIn("'UNCLASSIFIED_REDACTED'", scope)
        self.assertIn("F139_G54_FAILURE_CODE_ALLOWLIST_UNVERIFIED", scope)
        self.assertIn("F139_G54_STATUS_READ_ONLY=PASS", scope)
        self.assertIn("F139_GENENV_EXECUTABLE_DRIFT", SAFE_CODES)
        self.assertIn("F139_OWNER_MODEL_ORIGINAL_OWNER_NOT_IDLE_OR_ACTIVATED",
                      SAFE_CODES)

    def test_owner_only_request_and_original_nonmutation_retained(self):
        scope = self.segment()
        self.assertIn("github.actor == 'spoonman136668-ai'", scope)
        self.assertIn("github.event.issue.number == 807", scope)
        self.assertIn("startsWith(github.event.comment.body, 'F139-V9-STATUS ')",
                      scope)
        self.assertIn("[self-hosted, Windows, forge-codex-isolated]", scope)
        self.assertIn("query_only=ON", scope)
        self.assertIn("PRAGMA quick_check", scope)
        self.assertIn("github.sha == '" + V41_SOURCE + "'", scope)
        for unsafe in ("Start-ScheduledTask", "Set-ScheduledTask",
                       "Register-ScheduledTask", "gh api --method POST",
                       "gh api --method PATCH", "sqlite3.connect(path)"):
            with self.subTest(unsafe=unsafe):
                self.assertNotIn(unsafe, scope)


if __name__ == "__main__":
    unittest.main()
