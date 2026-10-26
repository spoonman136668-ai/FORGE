"""G54 V9 one-use owner transition guard tests; no owner-state mutation."""
from __future__ import annotations

import inspect
import unittest

from f139.local_controller import (
    Database, cli, v2_owner_terminal_release_guard,
)
from f139.nci04_owner_ledger import activate_native
from f139.nci04_v9_owner_release import (
    EXPECTED_HEAD_SEQ, EXPECTED_HEAD_SHA256, FIELDS, SCHEMA, SOURCE_V8,
    SHA40, SHA64, V9OwnerDenied, validate_v9_original_owner,
)


class G54V9OwnerReleaseTests(unittest.TestCase):
    def test_exact_frozen_predecessor_identity(self):
        self.assertEqual(SOURCE_V8, "157d3b545ceda507f4f8fabdf5c7b654a0b2fc84")
        self.assertEqual(EXPECTED_HEAD_SEQ, 229)
        self.assertEqual(
            EXPECTED_HEAD_SHA256,
            "26c8a6a0543c75392df845c9716382979df029e5674297cb662469fb71677248",
        )
        self.assertIn("v8_terminal_event_sha256", FIELDS)
        self.assertIn("owner_event_id", FIELDS)
        self.assertEqual(
            SCHEMA, "forge.f139.nci04.original-owner-source-v9-approval.v1"
        )

    def test_sha_fields_are_anchored_and_exact(self):
        self.assertIsNotNone(SHA40.fullmatch("a" * 40))
        self.assertIsNone(SHA40.fullmatch("a" * 40 + "x"))
        self.assertIsNotNone(SHA64.fullmatch("b" * 64))
        self.assertIsNone(SHA64.fullmatch("b" * 64 + "x"))

    def test_invalid_class_rejected_before_owner_mutation(self):
        with self.assertRaisesRegex(V9OwnerDenied, "CANONICAL_OWNER_DATABASE"):
            validate_v9_original_owner(None, {})
        with self.assertRaisesRegex(V9OwnerDenied, "CANONICAL_OWNER_DATABASE"):
            validate_v9_original_owner(object(), dict.fromkeys(FIELDS))

    def test_v9_is_distinct_original_owner_cli(self):
        source = inspect.getsource(cli)
        self.assertIn('transition-qualified-native-v9', source)
        self.assertIn('validate_v9_original_owner(validator_db,approval)', source)
        self.assertIn('from f139.local_controller import Database as CanonicalOwnerDB', source)
        self.assertIn('allow_v9=True)', source)
        self.assertIn('native_original_owner_profile(args.db)', source)

    def test_v9_transition_is_one_shot_and_frozen_to_v8(self):
        source = inspect.getsource(Database.transition_source)
        self.assertIn("SOURCE_TRANSITION_V9_ONE_SHOT_CUSTODY_REQUIRED", source)
        self.assertIn('events[-1]["schema"] ==', source)
        self.assertIn('"forge.f139.source-transition.v8"', source)
        self.assertIn("allow_v9 is True", source)

    def test_native_activation_accepts_sealed_v9_negative_successor(self):
        source = inspect.getsource(activate_native)
        self.assertIn('"forge.f139.source-transition.v9"', source)
        self.assertIn('negative_successors[-1]["to_source_sha"]==meta["source_sha"]', source)
        self.assertIn('negative_successors[-1]["custodied_negative_tickets"]==sorted(all_certified)', source)

    def test_v2_guard_validates_v9_v8_seal_and_g49_before_activation(self):
        source = inspect.getsource(v2_owner_terminal_release_guard)
        self.assertIn('event.get("schema")=="forge.f139.source-transition.v9"', source)
        self.assertIn('event.get("v8_terminal_event_sha256")==v8_rows[0]["sha"]', source)
        self.assertIn("verify_g49_custody(db)", source)
        self.assertIn("verify_native_activation(db)", source)

    def test_cold_verifier_binds_v8_and_g49_custody(self):
        source = inspect.getsource(Database.verify)
        self.assertIn("if is_v9:", source)
        self.assertIn("SOURCE_TRANSITION_V9_ORIGINAL_CUSTODY_DRIFT", source)
        self.assertIn('"v8_terminal_event_sha256"', source)
        self.assertIn("verify_g49_custody(self)", source)


if __name__ == "__main__":
    unittest.main()
