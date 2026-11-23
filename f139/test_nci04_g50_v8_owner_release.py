"""G50 V8 one-time source cutover guard tests. No original owner mutation."""
from __future__ import annotations

import inspect
import unittest

from f139.local_controller import Database, cli, v2_owner_terminal_release_guard
from f139.nci04_g49_prepost_negative import (
    SOURCE_V7, CLAIM_SEQ, verify_g49_custody,
)
from f139.nci04_v8_owner_release import (
    FIELDS, SCHEMA, V8OwnerDenied, validate_v8_original_owner,
)


class G50OneShotV8Tests(unittest.TestCase):
    def test_frozen_prepost_sequence_is_not_reusable(self):
        self.assertEqual(CLAIM_SEQ, 225)
        self.assertIn("prepost_negative_event_sha256", FIELDS)
        self.assertIn("v7_terminal_event_sha256", FIELDS)
        self.assertEqual(SCHEMA,
                         "forge.f139.nci04.original-owner-source-v8-approval.v1")
        self.assertEqual(SOURCE_V7,
                         "72301da157c27fc6fa7d22edce6842c7e4b2a432")

    def test_invalid_class_or_approval_rejected_before_owner_mutations(self):
        with self.assertRaisesRegex(V8OwnerDenied, "CANONICAL_OWNER_DATABASE"):
            validate_v8_original_owner(None, {})
        with self.assertRaisesRegex(V8OwnerDenied, "CANONICAL_OWNER_DATABASE"):
            validate_v8_original_owner(object(), dict.fromkeys(FIELDS))

    def test_v8_is_a_distinct_explicit_exact_owner_cli(self):
        s=inspect.getsource(cli)
        self.assertIn('transition-qualified-native-v8',s)
        self.assertIn('validate_v8_original_owner(validator_db,approval)',s)
        self.assertIn('from f139.local_controller import Database as CanonicalOwnerDB',s)
        self.assertIn('allow_certified_negative=True,',s)
        self.assertIn('allow_v8=True)',s)
        self.assertIn('native_original_owner_profile(args.db)',s)

    def test_v8_requires_frozen_prepost_not_g39_cutover_replay(self):
        s=inspect.getsource(Database.transition_source)
        self.assertIn('SOURCE_TRANSITION_V8_ONE_SHOT_PREPOST_REQUIRED',s)
        self.assertIn('if prepost:',s)
        self.assertIn('recognized[PREPOST] = SOURCE_V7',s)
        self.assertIn('prepost_negative_event_sha256',s)
        self.assertIn('v7_terminal_event_sha256',s)
        self.assertIn('allow_v8 is True',s)

    def test_cold_verifier_binds_source_and_original_negative(self):
        s=inspect.getsource(Database.verify)
        self.assertIn('if is_v8:',s)
        self.assertIn('SOURCE_TRANSITION_V8_ORIGINAL_CUSTODY_DRIFT',s)
        self.assertIn('prior_prepost_negative',s)
        self.assertIn('verify_g49_custody(self)',s)
        signer=inspect.getsource(v2_owner_terminal_release_guard)
        self.assertIn('event.get("schema")=="forge.f139.source-transition.v8"',signer)
        self.assertIn('verify_g49_custody(db)',signer)


if __name__ == "__main__":
    unittest.main()
