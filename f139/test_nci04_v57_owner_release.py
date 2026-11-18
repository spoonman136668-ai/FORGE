"""Static V57 original-owner release route and inert source-fence tests."""
from __future__ import annotations
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.test_nci04_v57_forward_transition import V57OriginalCarriedTicketFixture
from f139.nci04_v57_original_pending_preflight import SOURCE,TICKET
from f139.nci04_v57_owner_release import original_snapshot,apply_copy_or_original
from f139.nci04_v57_forward_transition import V47TransitionDenied

ROOT=Path(__file__).resolve().parents[1]


class V57OriginalOwnerRouteTests(V57OriginalCarriedTicketFixture):
    def setUp(self):
        super().setUp()
        p=patch("f139.nci04_v57_owner_release.verify_native_activation",
                return_value=True)
        p.start()
        self.addCleanup(p.stop)

    def test_frozen_owner_source_receipt_has_no_writes(self):
        before=self.conn.total_changes
        snapshot=original_snapshot(self.db)
        self.assertEqual(self.conn.total_changes,before)
        self.assertEqual(snapshot["source_sha"],SOURCE)
        self.assertEqual(snapshot["head_seq"],1857)
        self.assertEqual(snapshot["ready_ticket"],TICKET)
        self.assertEqual(snapshot["verified_historical_tasks"],154)
        self.assertEqual(snapshot["custodied_negative_tasks"],56)

    def test_no_original_mutation_without_exclusive_mutex(self):
        proof=self.make_proof()
        with self.assertRaisesRegex(V47TransitionDenied,"EXCLUSIVE"):
            apply_copy_or_original(self.db,proof)
        self.assertEqual(original_snapshot(self.db)["head_seq"],1857)

    def test_sole_original_workflow_preserves_old_owner_routes(self):
        existing=(ROOT/".github/workflows/f139-v54-original-owner-release.yml").read_text()
        bridge=(ROOT/"f139/v54_original_owner_repair.ps1").read_text()
        script=(ROOT/"f139/v57_original_owner_repair.ps1").read_text()
        cli=(ROOT/"f139/nci04_v57_owner_release_cli.py").read_text()
        self.assertIn("github.actor == 'spoonman136668-ai'",existing)
        self.assertIn("self-hosted, Windows, forge-codex-isolated",existing)
        self.assertIn("F139-V54-OWNER-RELEASE ",existing)
        for suffix in ("V55","V56","V57"):
            self.assertIn("'F139-V54-OWNER-RELEASE '+$Main+' "+suffix,bridge)
        self.assertIn("F139_V57_FORWARD_ONLY_HOLD_NO_REPLAY",script)
        self.assertIn("Disable-ScheduledTask -TaskName $name",script)
        self.assertIn("Enable-ScheduledTask -TaskName $name",script)
        self.assertIn("head_seq -eq 1857",script)
        self.assertIn("F139_V57_ORIGINAL_EVENT1859=",script)
        self.assertIn("f139-v57-original-rehearsal-",cli)
        self.assertIn("F139_V57_NATIVE_LIVE_AUTHENTICATED",cli)
        self.assertNotIn("workflow_dispatch:",existing)
        self.assertNotIn("schedule:",existing)


if __name__ == "__main__":
    unittest.main()
