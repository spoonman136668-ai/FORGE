"""Inert V41->Hybrid v37 predecessor and authority negative controls."""
import unittest
from unittest import mock

from f139 import nci04_v41_hybrid_source_transition as successor


class HybridV41SuccessorTests(unittest.TestCase):
    def test_no_live_owner_without_lease_witness(self):
        with self.assertRaisesRegex(
                successor.HybridSourceDenied,
                "SEPARATELY_APPROVED_ORIGINAL_OWNER_REQUIRED"):
            successor.commit_transition(
                None, {},
                disabled_owner_witness=lambda: True,
                verified_release_witness=lambda: True)

    def test_preview_cannot_use_unqualified_database(self):
        with self.assertRaisesRegex(
                successor.HybridSourceDenied, "EXISTING_OWNER_MUTEX_REQUIRED"):
            successor.build_proof(
                None, "a" * 40, 1, 43591751557, "f" * 64)

    def test_cold_event_rejects_foreign_and_missing_fields(self):
        row = {"seq": 1830, "prior_sha": successor.ACTIVATED_HASH}
        for altered in (
            {}, {"schema": successor.SCHEMA},
            {"schema": "forge.f139.source-transition.v36"},
        ):
            with self.subTest(doc=altered):
                with self.assertRaisesRegex(
                        successor.HybridSourceDenied,
                        "EVENT_FIELDS_OR_AUTHORITY_DRIFT"):
                    successor.verify_cold_event(None, row, altered, [])

    def test_forged_predecessor_rejected(self):
        row = {"seq": 1830, "prior_sha": successor.ACTIVATED_HASH}
        with self.assertRaisesRegex(
                successor.HybridSourceDenied,
                "UNIQUE_V41_PREDECESSOR_REQUIRED"):
            successor.snapshot(None, row, [])

    def test_source_has_no_execution_route(self):
        from pathlib import Path
        text = Path(successor.__file__).read_text(encoding="utf-8")
        self.assertNotIn("if __name__ == ", text)
        self.assertNotIn("workflow_dispatch", text)
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask",
                          "Disable-ScheduledTask", "Enable-ScheduledTask",
                          "gh api --method PATCH", "requests.post("):
            self.assertNotIn(forbidden, text)
        self.assertIn("bundle.verify_detached_restore(", text)
        self.assertIn("db.event(\"SOURCE_TRANSITION_ADMITTED\", proof)", text)

    def test_backup_readback_is_proposal_not_dispatch(self):
        self.assertEqual(successor.FROM_V41,
                         "1a40fe4e3ec6e93a1631d59863b95e90981d734e")
        self.assertEqual(successor.ACTIVATED_SEQ, 1829)
        self.assertEqual(successor.ACTIVATED_HASH,
                         "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8")
        self.assertEqual(successor.SCHEMA,
                         "forge.f139.source-transition.v37")


if __name__ == "__main__":
    unittest.main()
