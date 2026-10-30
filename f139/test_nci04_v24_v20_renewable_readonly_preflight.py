"""V24 exact V20-to-renewable release preflight; never modifies original."""
from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v24_v20_renewable_readonly_preflight as gate
from test_nci04_v19_original_attempt_schema import OriginalRequestColdVerifierTests


class V24V20ReleaseReadOnlyTests(unittest.TestCase):
    def setUp(self):
        # Positive schema contract uses typed canonical Database + frozen
        # summary, not an invented original-owner SQLite history.
        self.db = object.__new__(Database)
        self.state = {
            "meta": {
                "source_sha": gate.FROM_V20, "enabled": 1,
                "legacy_suspended": 1, "head_seq": 332,
                "head_hash": "a" * 64,
            },
            "v20_terminal_event_sha256": "b" * 64,
            "terminal_tasks_sha256": "c" * 64,
            "model_history_sha256": "d" * 64,
            "last_original_free_event_seq": 332,
            "last_original_free_event_sha256": "e" * 64,
            "verified_tasks": 27, "quarantined_tasks": 17,
            "legacy_free_attempts_spent": 8,
            "historical_sources": {gate.FROM_V20, "1" * 40},
        }

    def approved(self):
        with patch.object(gate, "original_v20_state", return_value=self.state):
            return gate.build_v24_readonly_preflight(self.db, "f" * 40, 6513130744)

    def test_exact_original_frozen_ledger_proof_has_zero_authority(self):
        proof = self.approved()
        self.assertEqual(set(proof), gate.FIELDS)
        self.assertEqual(proof["schema"], gate.SCHEMA)
        self.assertEqual(proof["from_source_sha"], gate.FROM_V20)
        self.assertEqual(proof["last_original_free_event_seq"], 332)
        self.assertEqual(proof["legacy_free_attempts_spent"], 8)
        self.assertEqual(proof["v20_terminal_event_sha256"], "b" * 64)
        for key in ("scientific_first_use", "production_dispatch_authorized",
                    "new_controller", "new_scheduler", "new_queue"):
            self.assertFalse(proof[key])
        self.assertTrue(proof["advisory_only"])
        with patch.object(gate, "original_v20_state", return_value=self.state):
            output = gate.verify_v24_readonly_preflight(self.db, proof)
        self.assertFalse(output["release_authorized"])
        self.assertFalse(output["model_request_authorized"])

    def test_no_replay_source_or_owner_event_forgery(self):
        with patch.object(gate, "original_v20_state", return_value=self.state):
            for sha in (gate.FROM_V20, "1" * 40, "bad", "F" * 40):
                with self.subTest(sha=sha), self.assertRaises(
                        gate.V24ReadOnlyDenied):
                    gate.build_v24_readonly_preflight(self.db, sha, 1)
            for ev in (0, -1, True):
                with self.subTest(event_id=ev), self.assertRaises(
                        gate.V24ReadOnlyDenied):
                    gate.build_v24_readonly_preflight(self.db, "f" * 40, ev)

    def test_head_custody_and_spent_original_counts_are_immutable(self):
        p = self.approved()
        with patch.object(gate, "original_v20_state", return_value=self.state):
            for field, changed in (
                ("event_seq", 333),
                ("event_head_sha256", "9" * 64),
                ("v20_terminal_event_sha256", "9" * 64),
                ("terminal_tasks_sha256", "9" * 64),
                ("model_history_sha256", "9" * 64),
                ("last_original_free_event_seq", 331),
                ("last_original_free_event_sha256", "9" * 64),
                ("verified_tasks", 28),
                ("quarantined_tasks", 16),
                ("legacy_free_attempts_spent", 7),
                ("advisory_only", False),
                ("scientific_first_use", True),
                ("production_dispatch_authorized", True),
                ("new_controller", True),
                ("new_scheduler", True),
                ("new_queue", True),
                ("paid_api_calls", 1),
            ):
                with self.subTest(field=field):
                    with self.assertRaises(gate.V24ReadOnlyDenied):
                        gate.verify_v24_readonly_preflight(self.db, {**p, field: changed})
            with self.assertRaises(gate.V24ReadOnlyDenied):
                gate.verify_v24_readonly_preflight(self.db, {**p, "secret": "x"})

    def test_original_v19_fixture_cannot_pose_as_v20_release(self):
        source = OriginalRequestColdVerifierTests(
            "test_no_new_events_original_behavior_and_original_head_unchanged")
        source.setUp()
        self.addCleanup(source.doCleanups)
        with SingleOwner(source.mutex):
            before = source.db.meta().copy()
            with self.assertRaisesRegex(gate.V24ReadOnlyDenied,
                                        "V20_ORIGINAL_NOT_IDLE_OR_AUTHENTICATED"):
                gate.build_v24_readonly_preflight(source.db, "f" * 40, 1)
            source.db.verify()
            self.assertEqual(source.db.meta(), before)
            cold = Database.open_readonly(source.db.filename)
            try:
                cold.verify()
                self.assertEqual(cold.meta(), before)
            finally:
                cold.close()

    def test_readonly_source_cannot_activate_existing_task(self):
        code = inspect.getsource(gate)
        self.assertIn("db.verify()", code)
        self.assertIn("verify_native_activation(db)", code)
        self.assertIn("verified_g54_ambiguous_start(db)", code)
        self.assertIn("FREE_REASONER_ATTEMPTED", code)
        self.assertIn("legacy_free_attempts_spent", code)
        self.assertNotIn("db.event(", code)
        self.assertNotIn("db.transition_source(", code)
        self.assertNotIn("Start-ScheduledTask", code)
        self.assertNotIn("_post_one(", code)


if __name__ == "__main__":
    unittest.main()
