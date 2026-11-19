"""V58 protected original-owner V9 status-only failure-code projection."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_rar_g145_pr_scope import FROZEN_SCOPES

WORKFLOW = ROOT / ".github/workflows/f139-g54-v9-owner-cutover.yml"
BRANCH = "engineering/f139-v58-model-free-status-readonly-20261119"
BASE = "c06403c8b6035c6c7013866a7ea08cef1244b507"
EXPECTED = {
    ".github/workflows/f139-g54-v9-owner-cutover.yml",
    "f139/test_nci04_v58_model_free_status_projection.py",
    "f139/test_v40_readonly_workflow_scope.py",
    "docs/F139-V58-MODEL-FREE-STATUS-READONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
}

class V58ReadOnlyStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.status = cls.workflow.split("  read-only-status:\n", 1)[1].split(
            "      - name: V41 original-owner locked issue/ledger read-only preflight", 1)[0]

    def test_exact_frozen_scope(self):
        self.assertEqual(FROZEN_SCOPES[BRANCH][0], BASE)
        self.assertEqual(set(FROZEN_SCOPES[BRANCH][1]), EXPECTED)

    def test_only_existing_owner_status_job_projects_code(self):
        self.assertEqual(self.workflow.count("  read-only-status:\n"), 1)
        self.assertEqual(self.status.count(
            "failure_code=(SafeModelFreeFailureCode $e)"), 1)
        self.assertIn("F139_G54_CONTROLLER_LOG_TAIL=", self.status)
        self.assertIn("F139_G54_STATUS_READ_ONLY=PASS", self.status)
        self.assertIn("F139-V9-STATUS ", self.status)
        self.assertIn("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'", self.status)

    def test_codes_are_exact_allowlist_not_raw_log_values(self):
        self.assertIn("from f139.nci04_model_free_failure import SAFE_CODES", self.status)
        self.assertIn("$allowlistScript | & $python -B -", self.status)
        self.assertNotIn(" & $python -B -c ", self.status)
        self.assertIn("$allowedModelFreeCodes -ccontains $code", self.status)
        self.assertIn("$fallbackModelFreeCodes -ccontains $code", self.status)
        self.assertIn("return 'REDACTED_OR_MISSING'", self.status)
        self.assertIn("-cne 'MODEL_FREE_SEARCH_BLOCKED_FAIL_CLOSED'", self.status)
        self.assertNotIn("failure_code=(OptionalField $e 'failure_code')", self.status)
        self.assertNotIn("Write-Host ('F139_MODEL_FREE_RAW_CODE=", self.status)

    def test_no_new_trigger_or_database_write_in_status_job(self):
        self.assertNotIn("Register-ScheduledTask", self.status)
        self.assertNotIn("Start-ScheduledTask", self.status)
        self.assertNotIn("Stop-ScheduledTask", self.status)
        self.assertIn("PRAGMA query_only=ON", self.status)
        self.assertIn("mode=ro", self.status)
        self.assertNotIn("scientific_first_use=True", self.status)
        self.assertIn("Get-Content -LiteralPath $log | Select-Object -Last 2000", self.status)

if __name__ == "__main__":
    unittest.main()
