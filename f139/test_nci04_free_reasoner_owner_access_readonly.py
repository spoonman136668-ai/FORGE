"""Assure the original owner reasoner-access check is non-mutating and secret-safe."""
from pathlib import Path
import unittest


class OriginalReasonerAccessReadOnlyTests(unittest.TestCase):
    def test_single_owner_readonly_route_has_no_inference_or_secret_output(self):
        path=Path(__file__).resolve().parent.parent/".github/workflows/f139-g54-v9-owner-cutover.yml"
        script=path.read_text(encoding="utf-8")
        label="  free-reasoner-access-readonly:\n"
        self.assertEqual(script.count(label),1)
        begin=script.index(label)
        end=script.index("  read-only-status:\n",begin)
        block=script[begin:end]
        self.assertIn("F139-FREE-REASONER-STATUS ",block)
        self.assertIn("FORGE-CODEX-REMOTE",block)
        self.assertIn("github.actor == 'spoonman136668-ai'",block)
        self.assertIn("github.event.issue.number == 807",block)
        self.assertIn("F139_FREE_ACCESS_ESCALATED_ORIGINAL_OWNER_REQUIRED",block)
        self.assertIn("F139_FREE_ACCESS_OWNER_SID_DRIFT",block)
        self.assertIn("F139_FREE_ACCESS_ORIGINAL_LEDGER_READ_ONLY=PASS",block)
        self.assertIn("F139_FREE_ACCESS_ORIGINAL_LEDGER_NOT_READY",block)
        self.assertIn("F139_FREE_ACCESS_READ_ONLY=PASS",block)
        self.assertIn("F139_FREE_ACCESS_NO_EXTERNAL_MODEL_CALL=PASS",block)
        self.assertIn("[Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','Process')",block)
        self.assertIn("[Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','User')",block)
        self.assertIn("PRAGMA query_only=ON",block)
        self.assertIn('mode=ro',block)
        self.assertIn("persist-credentials: false",block)
        for forbidden in (
            "transition-qualified-native", "gh api -X PATCH",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "OPENROUTER_API_KEY='", "Authorization: Bearer",
            "https://openrouter.ai", "Invoke-RestMethod",
            "gh secret", "sqlite3.connect(sys.argv[2])",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,block)

    def test_readonly_diagnostic_is_not_default_scheduled_controller(self):
        path=Path(__file__).resolve().parent.parent/".github/workflows/f139-g54-v9-owner-cutover.yml"
        text=path.read_text(encoding="utf-8")
        piece=text[text.index("  free-reasoner-access-readonly:\n"):
                   text.index("  read-only-status:\n")]
        self.assertIn("github.event_name == 'issue_comment'",piece)
        self.assertIn("issues: read",piece)
        self.assertIn("contents: read",piece)
        self.assertNotIn("schedule:",piece)
        self.assertNotIn("workflow_dispatch:",piece)
        self.assertNotIn("secrets.",piece)


if __name__=="__main__":
    unittest.main()
