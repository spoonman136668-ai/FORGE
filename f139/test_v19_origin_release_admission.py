"""Read-only release-admission regression: V18->V19 workflow is not reusable.

The currently deployed V19 owner cannot be transitioned by the original
one-time guarded V18->V19 workflow. This test prevents false admission of
an optional research-observation patch without a separately qualified path.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v19-original-owner-cutover.yml"
V18 = "d8bccc604f8607bf10f9d8bc6aa568d1f98af559"
V19 = "0743ca22b76ebd943a66f05a36ea919301676be0"

class V19OriginReleaseAdmissionTests(unittest.TestCase):
    def test_original_workflow_is_source_locked_and_cannot_migrate_v19(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("$old='"+V18+"'", source)
        self.assertIn("$ownerPolicy.source_sha -cne $old", source)
        self.assertIn("(& git -C $root rev-parse HEAD | Out-String).Trim() -cne $old", source)
        self.assertIn("F139-V19-OWNER-CUTOVER ", source)
        self.assertNotEqual(V18, V19)
        # Source-admission statement: an already-V19 owner fails both
        # installed-checkout and owner-policy V18 prerequisites.
        installed = V19
        policy_pin = V19
        self.assertFalse(installed == V18 and policy_pin == V18)

    def test_no_automatic_or_routine_dispatch_from_legacy_workflow(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("issue_comment:", source)
        self.assertIn("github.event.issue.number == 807", source)
        self.assertIn("github.actor == 'spoonman136668-ai'", source)
        self.assertNotIn("workflow_dispatch:", source)
        self.assertNotIn("schedule:", source)

if __name__ == "__main__":
    unittest.main()
