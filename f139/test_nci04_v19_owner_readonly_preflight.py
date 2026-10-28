"""Focused V19 original-owner preflight qualification; no live owner access."""
from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.nci04_v19_owner_readonly_preflight import (
    FIELDS, FROM_V18, SCHEMA, V19PreflightDenied,
    build_v19_readonly_preflight, verify_v19_readonly_preflight,
)


class OriginalOwnerV19ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.db = object.__new__(Database)
        self.state = {
            "meta": {
                "source_sha": FROM_V18, "enabled": 1, "legacy_suspended": 1,
                "head_seq": 290, "head_hash": "a" * 64,
            },
            "v18_terminal_event_sha256": "b" * 64,
            "terminal_tasks_sha256": "c" * 64,
            "model_history_sha256": "d" * 64,
            "verified_tasks": 24, "quarantined_tasks": 15,
            "historical_sources": {FROM_V18, "1" * 40},
        }

    def approved(self):
        with patch("f139.nci04_v19_owner_readonly_preflight._original_state",
                   return_value=self.state):
            return build_v19_readonly_preflight(self.db, "f" * 40, 1014)

    def test_readonly_proof_exact_identity_and_zero_authority(self):
        proof = self.approved()
        self.assertEqual(proof["schema"], SCHEMA)
        self.assertEqual(set(proof), FIELDS)
        self.assertEqual(proof["from_source_sha"], FROM_V18)
        self.assertEqual(proof["event_seq"], 290)
        self.assertEqual(proof["verified_tasks"], 24)
        self.assertEqual(proof["quarantined_tasks"], 15)
        self.assertIs(proof["advisory_only"], True)
        self.assertEqual(proof["paid_api_calls"], 0)
        for key in ("scientific_first_use", "production_dispatch_authorized",
                    "new_controller", "new_scheduler", "new_queue"):
            self.assertIs(proof[key], False)

    def test_replay_unknown_sha_and_wrong_event_id_denied(self):
        with patch("f139.nci04_v19_owner_readonly_preflight._original_state",
                   return_value=self.state):
            for sha in (FROM_V18, "1" * 40, "wrong", "F" * 40):
                with self.subTest(sha=sha):
                    with self.assertRaisesRegex(
                        V19PreflightDenied, "TARGET_INVALID_OR_ALREADY_CONSUMED"
                    ):
                        build_v19_readonly_preflight(self.db, sha, 1014)
            for event_id in (0, -1, True):
                with self.subTest(event_id=event_id):
                    with self.assertRaisesRegex(
                        V19PreflightDenied, "OWNER_EVENT_ID_REQUIRED"
                    ):
                        build_v19_readonly_preflight(self.db, "f"*40, event_id)

    def test_changed_custody_and_owner_head_denied(self):
        proof = self.approved()
        with patch("f139.nci04_v19_owner_readonly_preflight._original_state",
                   return_value=self.state):
            for key, new in (
                ("event_seq", 291),
                ("event_head_sha256", "e" * 64),
                ("v18_terminal_event_sha256", "e" * 64),
                ("terminal_tasks_sha256", "e" * 64),
                ("model_history_sha256", "e" * 64),
                ("verified_tasks", 25),
                ("quarantined_tasks", 16),
            ):
                with self.subTest(field=key):
                    with self.assertRaises(V19PreflightDenied):
                        verify_v19_readonly_preflight(
                            self.db, {**proof, key: new})

    def test_no_first_use_new_controller_or_paid_api_authority(self):
        proof = self.approved()
        with patch("f139.nci04_v19_owner_readonly_preflight._original_state",
                   return_value=self.state):
            for key, new in (
                ("advisory_only", False),
                ("scientific_first_use", True),
                ("production_dispatch_authorized", True),
                ("new_controller", True),
                ("new_scheduler", True),
                ("new_queue", True),
                ("paid_api_calls", 1),
            ):
                with self.subTest(field=key):
                    with self.assertRaisesRegex(
                        V19PreflightDenied, "AUTHORITY_EXPANSION_DENIED"
                    ):
                        verify_v19_readonly_preflight(
                            self.db, {**proof, key: new})
            with self.assertRaisesRegex(
                V19PreflightDenied, "FIELDS_NOT_CANONICAL"
            ):
                verify_v19_readonly_preflight(self.db, {**proof, "secret": "no"})

    def test_noncanonical_owner_database_denied(self):
        proof = self.approved()
        with self.assertRaisesRegex(V19PreflightDenied, "ORIGINAL_DATABASE"):
            verify_v19_readonly_preflight(object(), proof)

    def test_v19_stays_readonly_until_separately_qualified_cutover(self):
        import f139.nci04_v19_owner_readonly_preflight as module
        code = inspect.getsource(module._original_state)
        self.assertIn("db.verify()", code)
        self.assertIn("verify_native_activation(db)", code)
        self.assertIn("verified_g54_ambiguous_start(db)", code)
        self.assertIn("db.ready() is None and not db.actives()", code)
        self.assertIn('"FREE_REASONER_ATTEMPTED"', inspect.getsource(module))
        self.assertIn('v18_original_model_history_valid(counts)', code)
        self.assertIn("SingleOwner.held(", code)
        self.assertNotIn("db.event(", code)
        self.assertNotIn("db.conn.execute(\"UPDATE", code)
        self.assertNotIn("requests.post(", inspect.getsource(module))
        from f139.local_controller import cli
        src=inspect.getsource(cli)
        # The successor may now exist, but the read-only proof itself must
        # never authorize a cutover or a model request.
        self.assertIn("transition-qualified-native-v19",src)
        self.assertIn("verify_v19_readonly_preflight(validator_db,approval)",src)
        self.assertIn("with SingleOwner(args.db.with_suffix(\".lock\")):",src)
        self.assertIn("V19_PROTECTED_MAIN_SHA_DRIFT",src)
        self.assertIn("allow_v19=True",src)


if __name__ == "__main__":
    unittest.main()
