"""Source-only, negative-only preflight for a future V19-origin release.

No import of the controller, no task/SQLite access, and no live GitHub writes.
The existing V18->V19 workflow must fail closed for an already-V19 owner.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / ".github" / "workflows" / "f139-v19-original-owner-cutover.yml"
V18 = "d8bccc604f8607bf10f9d8bc6aa568d1f98af559"
V19 = "0743ca22b76ebd943a66f05a36ea919301676be0"

def legacy_admissible(*, installed, policy, protected_main, event_target, release_ref):
    return (installed == V18 and policy == V18 and
            protected_main == event_target == release_ref)

class V19OriginNegativeControls(unittest.TestCase):
    def test_actual_v19_owner_must_be_denied(self):
        self.assertFalse(legacy_admissible(installed=V19, policy=V19,
            protected_main=V19, event_target=V19, release_ref=V19))

    def test_protected_main_and_immutable_ref_mismatch_denied(self):
        self.assertFalse(legacy_admissible(installed=V18, policy=V18,
            protected_main=V19, event_target=V19, release_ref=V18))
        self.assertFalse(legacy_admissible(installed=V18, policy=V18,
            protected_main=V19, event_target=V18, release_ref=V19))

    def test_legacy_code_guards_still_explicit(self):
        text = LEGACY.read_text(encoding="utf-8")
        for phrase in ("$old='"+V18+"'", "F139-V19-OWNER-CUTOVER ",
                       "$ownerPolicy.source_sha -cne $old",
                       "F139_V19_IMMUTABLE_RELEASE_REF_NOT_QUALIFIED",
                       "F139_V19_PARTIAL_CUSTODY_EXISTING_TASK_HELD_DISABLED"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("schedule:", text)

if __name__ == "__main__":
    unittest.main()
