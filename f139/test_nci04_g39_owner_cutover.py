"""G39 release entrypoint one-shot original-owner source safety checks."""
import pathlib
import unittest
from f139.nci04_v7_owner_release import OLD, FIELDS, V7OwnerDenied, validate_v7_original_owner


class G39OwnerCutoverTests(unittest.TestCase):
    def test_only_original_owner_issue_comment_can_dispatch_release(self):
        path=pathlib.Path(__file__).resolve().parent.parent / (
          ".github/workflows/f139-g39-original-owner-v7-cutover.yml")
        raw=path.read_text()
        self.assertIn("issue_comment:",raw)
        self.assertNotIn("\n  schedule:",raw)
        self.assertNotIn("\n  workflow_dispatch:",raw)
        self.assertIn("github.actor == 'spoonman136668-ai'",raw)
        self.assertIn("github.event.issue.number == 807",raw)
        self.assertIn("F139-V7-OWNER-CUTOVER ",raw)
        self.assertIn("FORGE-CODEX-REMOTE",raw)
        self.assertIn("forge-codex-isolated",raw)

    def test_source_transition_requires_exact_old_one_shot_v6(self):
        from f139.local_controller import Database
        import inspect
        transition=inspect.getsource(Database.transition_source)
        self.assertIn("allow_v7 is True",transition)
        self.assertIn(OLD,transition)
        self.assertIn("SOURCE_TRANSITION_V7_ONE_SHOT",transition)
        self.assertIn('schema="forge.f139.source-transition.v7"',transition)

    def test_original_history_must_not_replay_or_elevate_science(self):
        from f139.local_controller import Database
        import inspect
        verify=inspect.getsource(Database.verify)
        self.assertIn("SOURCE_TRANSITION_V7_ORIGINAL_SEAL_DRIFT",verify)
        self.assertIn("v6_terminal_event_sha256",verify)
        self.assertIn('"v2_receipt_authorized" is False',verify)

    def test_owner_signer_cannot_accept_ambient_env_only(self):
        from f139.local_controller import v2_owner_terminal_release_guard
        self.assertFalse(v2_owner_terminal_release_guard(OLD))
        self.assertFalse(v2_owner_terminal_release_guard("notasha"))
        self.assertFalse(v2_owner_terminal_release_guard("f"*40))

    def test_quiescence_evidence_and_backup_required_before_source_checkout(self):
        raw=(pathlib.Path(__file__).resolve().parent.parent /
              ".github/workflows/f139-g39-original-owner-v7-cutover.yml").read_text()
        for evidence in (
            "Disable-ScheduledTask","Stop-ScheduledTask",
            "Get-FileHash","src.backup(dest)",
            "checkout --detach $target",
            "transition-qualified-native-v7",
            "activate-native --approval",
            "Enable-ScheduledTask",
        ):
            self.assertIn(evidence,raw)
        self.assertLess(raw.index("src.backup(dest)"),
                        raw.index("checkout --detach $target"))

if __name__=="__main__":
    unittest.main()
