"""V56 source-only release fencing (no real original-owner writes)."""
from __future__ import annotations

import unittest
from pathlib import Path

from f139.test_nci04_v56_forward_transition import V46SyntheticReadyCarry
from f139.nci04_v56_original_pending_preflight import SOURCE, TICKET
from f139.nci04_v56_owner_release import original_snapshot, apply_copy_or_original
from f139.nci04_v56_forward_transition import V46TransitionDenied


ROOT = Path(__file__).resolve().parents[1]


class V56OriginalReleaseSource(V46SyntheticReadyCarry):
    def setUp(self):
        super().setUp()
        from unittest.mock import patch
        native = patch(
            "f139.nci04_v56_owner_release.verify_native_activation",
            return_value=True,
        )
        native.start()
        self.addCleanup(native.stop)

    def test_readonly_original_snapshot_retains_one_ready_identity(self):
        before = self.conn.total_changes
        frozen = original_snapshot(self.db)
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(frozen["source_sha"], SOURCE)
        self.assertEqual(frozen["head_seq"], 1855)
        self.assertEqual(frozen["ready_ticket"], TICKET)
        self.assertEqual(frozen["verified_historical_tasks"], 154)
        self.assertEqual(frozen["custodied_negative_tasks"], 56)

    def test_live_api_cannot_write_without_exclusive_owner(self):
        doc = self.proof()
        with self.assertRaisesRegex(V46TransitionDenied, "EXCLUSIVE"):
            apply_copy_or_original(self.db, doc)
        self.assertEqual(original_snapshot(self.db)["head_seq"], 1855)

    def test_original_owner_workflow_is_unique_and_operator_authenticated(self):
        workflow = (ROOT / ".github/workflows/f139-v54-original-owner-release.yml").read_text()
        bridge = (ROOT / "f139/v54_original_owner_repair.ps1").read_text()
        script = (ROOT / "f139/v56_original_owner_repair.ps1").read_text()
        cli = (ROOT / "f139/nci04_v56_owner_release_cli.py").read_text()
        self.assertIn("issue_comment:", workflow)
        self.assertIn("github.actor == 'spoonman136668-ai'", workflow)
        self.assertIn("github.event.issue.number == 807", workflow)
        self.assertIn("self-hosted, Windows, forge-codex-isolated", workflow)
        self.assertIn("F139-V54-OWNER-RELEASE ", workflow)
        self.assertIn("F139-V54-OWNER-RELEASE ", bridge)
        self.assertIn(" V56", bridge)
        self.assertIn("v56_original_owner_repair.ps1", bridge)
        self.assertNotIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("V56_FORWARD_ONLY_HOLD_NO_REPLAY", script)
        self.assertIn("Disable-ScheduledTask -TaskName $name", script)
        self.assertIn("Enable-ScheduledTask -TaskName $name", script)
        self.assertIn("f139-v56-original-rehearsal-", cli)
        self.assertIn("F139_V56_NATIVE_LIVE_AUTHENTICATED", cli)
        self.assertNotIn("OPENAI_API_KEY", workflow)

if __name__ == "__main__":
    unittest.main()
