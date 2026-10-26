"""G54 V9 one-use owner transition guard tests; no owner-state mutation."""
from __future__ import annotations

import inspect
import unittest

from f139.local_controller import Database, cli
from f139.nci04_v9_owner_release import (
    EXPECTED_HEAD_SEQ, EXPECTED_HEAD_SHA256, FIELDS, SCHEMA, SOURCE_V8,
    V9OwnerDenied, validate_v9_original_owner,
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

    def test_cold_verifier_binds_v8_and_g49_custody(self):
        source = inspect.getsource(Database.verify)
        self.assertIn("if is_v9:", source)
        self.assertIn("SOURCE_TRANSITION_V9_ORIGINAL_CUSTODY_DRIFT", source)
        self.assertIn('"v8_terminal_event_sha256"', source)
        self.assertIn("verify_g49_custody(self)", source)


if __name__ == "__main__":
    unittest.main()
