"""V11 development-only owner source successor guards; no live SQLite writes."""
from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

from f139.local_controller import (
    Database, cli, v2_owner_terminal_release_guard,
)
from f139.nci04_g54_ambiguous_start_custody import (
    EVENT_SHA256 as G54_SHA, TICKET as G54_TICKET,
)
from f139.nci04_v11_owner_release import (
    FIELDS, SCHEMA, SOURCE_V10, V11OwnerDenied,
    build_v11_owner_approval, validate_v11_original_owner,
)


class V11SourceOwnerTests(unittest.TestCase):
    def setUp(self):
        self.db = object.__new__(Database)
        self.state = {
            "meta": {
                "head_seq": 249,
                "head_hash": "a" * 64,
                "source_sha": SOURCE_V10,
            },
            "v10_terminal_event_sha256": "b" * 64,
            "g54_ambiguous_start_event_sha256": G54_SHA,
            "quarantined_tickets_sha256": "c" * 64,
            "verified_tickets_sha256": "d" * 64,
            "historical_transition_sources": {SOURCE_V10, "e" * 40},
            "quarantined": 15,
            "verified": 21,
        }

    def build(self):
        with patch("f139.nci04_v11_owner_release._original_state",
                   return_value=self.state):
            return build_v11_owner_approval(self.db, "f" * 40, 1001)

    def test_explicit_owner_proof_is_one_source_and_development_only(self):
        self.assertEqual(
            SCHEMA, "forge.f139.nci04.original-owner-source-v11-approval.v1")
        self.assertIn("g54_ambiguous_start_event_sha256", FIELDS)
        self.assertIn("quarantined_tickets_sha256", FIELDS)
        approval = self.build()
        self.assertEqual(set(approval), FIELDS)
        self.assertEqual(approval["from_source_sha"], SOURCE_V10)
        self.assertEqual(approval["g54_ambiguous_start_event_sha256"], G54_SHA)
        self.assertFalse(approval["scientific_first_use"])
        self.assertFalse(approval["v2_production_dispatch_authorized"])
        self.assertFalse(approval["new_controller"])
        self.assertFalse(approval["new_scheduler"])
        self.assertFalse(approval["new_queue"])
        self.assertEqual(approval["paid_api_calls"], 0)

    def test_spoofed_first_use_model_or_missing_field_denied(self):
        approval = self.build()
        with patch("f139.nci04_v11_owner_release._original_state",
                   return_value=self.state):
            for changes in (
                {"scientific_first_use": True},
                {"paid_api_calls": 1},
                {"v2_production_dispatch_authorized": True},
                {"new_controller": True},
                {"new_scheduler": True},
                {"new_queue": True},
            ):
                with self.subTest(change=changes):
                    with self.assertRaisesRegex(V11OwnerDenied,
                                                "NEW_AUTHORITY_NOT_ALLOWED"):
                        validate_v11_original_owner(
                            self.db, {**approval, **changes})
            with self.assertRaisesRegex(V11OwnerDenied,
                                        "EXACT_APPROVAL_FIELDS_REQUIRED"):
                validate_v11_original_owner(
                    self.db, {**approval, "extra": "bypass"})

    def test_stale_ledger_head_and_g54_identity_denied(self):
        approval = self.build()
        with patch("f139.nci04_v11_owner_release._original_state",
                   return_value=self.state):
            for name in ("owner_event_sha256", "owner_event_seq"):
                with self.subTest(field=name):
                    changed = "f" * 64 if name.endswith("sha256") else 250
                    with self.assertRaisesRegex(V11OwnerDenied,
                                                "OWNER_EVENT_HEAD_CHANGED"):
                        validate_v11_original_owner(
                            self.db, {**approval, name: changed})
            with self.assertRaisesRegex(V11OwnerDenied,
                                        "FROZEN_HISTORY_CHANGED"):
                validate_v11_original_owner(
                    self.db, {**approval,
                              "g54_ambiguous_start_event_sha256": "f" * 64})

    def test_reuse_of_any_old_source_is_denied(self):
        with patch("f139.nci04_v11_owner_release._original_state",
                   return_value=self.state):
            with self.assertRaisesRegex(V11OwnerDenied,
                                        "SOURCE_REPLAY_OR_INVALID_SHA"):
                build_v11_owner_approval(self.db, SOURCE_V10, 1001)
            with self.assertRaisesRegex(V11OwnerDenied,
                                        "SOURCE_REPLAY_OR_INVALID_SHA"):
                build_v11_owner_approval(self.db, "e" * 40, 1001)

    def test_noncanonical_database_and_bad_owner_event_denied(self):
        with self.assertRaisesRegex(V11OwnerDenied,
                                    "CANONICAL_ORIGINAL_DATABASE_REQUIRED"):
            validate_v11_original_owner(object(), {})
        with patch("f139.nci04_v11_owner_release._original_state",
                   return_value=self.state):
            with self.assertRaisesRegex(V11OwnerDenied,
                                        "OWNER_EVENT_ID_REQUIRED"):
                build_v11_owner_approval(self.db, "f" * 40, 0)

    def test_v11_is_distinct_original_owner_command_and_signed_v2_stays_guarded(self):
        source = inspect.getsource(cli)
        self.assertIn('transition-qualified-native-v11', source)
        self.assertIn('validate_v11_original_owner(validator_db,approval)', source)
        self.assertIn('allow_v11=True)', source)
        self.assertIn('native_original_owner_profile(args.db)', source)
        self.assertIn('with SingleOwner(args.db.with_suffix(".lock")):', source)
        transition = inspect.getsource(Database.transition_source)
        self.assertIn("SOURCE_TRANSITION_V11_ORIGINAL_CUSTODY_REQUIRED", transition)
        self.assertIn("g54_original_canonical(self)", transition)
        self.assertIn('event["v10_terminal_event_sha256"]', transition)
        cold = inspect.getsource(Database.verify)
        self.assertIn("if is_v11:", cold)
        self.assertIn("SOURCE_TRANSITION_V11_ORIGINAL_CUSTODY_DRIFT", cold)
        self.assertIn("g54_ambiguous_start_event_sha256", cold)
        signer = inspect.getsource(v2_owner_terminal_release_guard)
        self.assertIn('source-transition.v11', signer)
        self.assertIn("g54_original_canonical(db)", signer)
        self.assertIn("verify_native_activation(db)", signer)


if __name__ == "__main__":
    unittest.main()
