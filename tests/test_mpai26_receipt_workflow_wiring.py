"""Static acceptance for candidate workflow wiring; does not run the model."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/mpai26-new-family-token-matched-development.yml"
EXPORTER = ROOT / "tools/mpai26_development_trial_receipts.py"


class ArtifactWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.exporter = EXPORTER.read_text(encoding="utf-8")

    def test_original_owner_only_push_boundary_preserved(self):
        self.assertIn(
            "branches: [oneoff/mpai21-owner-approved-two-record-admission-20261029]",
            self.source)
        self.assertIn(
            "paths: ['.github/workflows/mpai26-new-family-token-matched-development.yml']",
            self.source)
        # No PR/dispatch trigger on this original-owner inference workflow.
        trigger = self.source.split("permissions:", 1)[0]
        self.assertNotIn("workflow_dispatch:", trigger)
        self.assertNotIn("pull_request:", trigger)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", self.source)
        self.assertIn("needs: preregistration", self.source)

    def test_source_blobs_and_existing_execution_qualification(self):
        self.assertIn("1d919799482731caf77bc25ee404407dbd0a4f5d", self.source)
        self.assertIn("fae7191202e5547b36e762991c3d6d42ea9c14fe", self.source)
        self.assertIn("MPAI26_ORIGINAL_WINDOWS_AUTHORITY", self.source)
        self.assertIn("MPAI26_PAID_API_DENIED", self.source)
        self.assertIn("MPAI26_SOURCE_COMMIT_DRIFT", self.source)
        self.assertIn("MPAI26_ORIGINAL_WINDOWS_QUALIFICATION=PASS", self.source)

    def test_receipt_generated_after_original_execution_before_scratch_cleanup(self):
        run = self.source.index("& python.exe -B tools/mpai26_new_family_transfer_development.py")
        validate = self.source.index("Assert ($seen.Count -eq 3) 'ARM_COUNT'")
        export = self.source.index("& python.exe -B tools/mpai26_development_trial_receipts.py")
        clean = self.source.index("Remove-Item -LiteralPath $scratch -Recurse")
        upload = self.source.index("uses: actions/upload-artifact@v4")
        remove = self.source.index("MPAI26_RECEIPT_TRANSIENT_CLEANUP=PASS")
        self.assertTrue(run < validate < export < clean < upload < remove)
        self.assertIn("private_trial.json", self.source)
        self.assertIn("--forge-sha $env:GITHUB_SHA", self.source)
        self.assertIn("if-no-files-found: error", self.source)
        self.assertIn("retention-days: 7", self.source)
        self.assertIn("if: success()", self.source)
        self.assertIn("if: always()", self.source)
        self.assertIn("TASK_RECEIPT_EXPORT_FAILED", self.source)

    def test_never_promote_or_self_attest(self):
        self.assertIn('"recursive_improvement_proven": False', self.exporter)
        self.assertIn('"actual_execution_authenticated_by_this_receipt": False', self.exporter)
        self.assertIn('"independent_holdout_custody": False', self.exporter)
        self.assertIn('"production_memory_writes": 0', self.exporter)
        self.assertNotIn("workflow_run:", self.source)


if __name__ == "__main__":
    unittest.main()
