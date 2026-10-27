"""V12 source-only release guards; strict preservation of original V11 custody."""
from __future__ import annotations
import inspect
import unittest
from unittest.mock import patch

from f139.local_controller import Database, cli, v2_owner_terminal_release_guard
from f139.nci04_g54_ambiguous_start_custody import EVENT_SHA256 as G54_SEAL
from f139.nci04_v12_owner_release import (
    SCHEMA, FIELDS, SOURCE_V11, V12OwnerDenied,
    build_v12_owner_approval, validate_v12_original_owner,
)


class V12OriginalOwnerTests(unittest.TestCase):
    def setUp(self):
        self.db = object.__new__(Database)
        self.state = {
            "meta": {"head_seq": 251, "head_hash": "a" * 64,
                     "source_sha": SOURCE_V11},
            "v11_terminal_event_sha256": "b" * 64,
            "g54_ambiguous_start_event_sha256": G54_SEAL,
            "quarantined_tickets_sha256": "c" * 64,
            "verified_tickets_sha256": "d" * 64,
            "g3_draft_history_sha256": "e" * 64,
            "historical_sources": {SOURCE_V11, "1" * 40},
            "quarantined": 15, "verified": 21,
        }

    def approval(self):
        with patch("f139.nci04_v12_owner_release._original_state",
                   return_value=self.state):
            return build_v12_owner_approval(self.db, "f" * 40, 1012)

    def test_complete_owner_v12_approval_has_no_new_authority(self):
        approval=self.approval()
        self.assertEqual(SCHEMA, "forge.f139.nci04.original-owner-source-v12-approval.v1")
        self.assertEqual(set(approval), FIELDS)
        self.assertEqual(approval["from_source_sha"], SOURCE_V11)
        self.assertEqual(approval["g54_ambiguous_start_event_sha256"], G54_SEAL)
        self.assertEqual(approval["g3_draft_history_sha256"], "e"*64)
        self.assertEqual(approval["owner_event_seq"], 251)
        for field in ("scientific_first_use",
                      "v2_production_dispatch_authorized", "new_controller",
                      "new_scheduler", "new_queue"):
            self.assertIs(approval[field], False)
        self.assertEqual(approval["paid_api_calls"], 0)

    def test_reject_owner_source_replay_and_bad_event_identity(self):
        with patch("f139.nci04_v12_owner_release._original_state",
                   return_value=self.state):
            for old in (SOURCE_V11, "1"*40):
                with self.assertRaisesRegex(V12OwnerDenied, "SOURCE_REPLAY"):
                    build_v12_owner_approval(self.db, old, 1012)
            with self.assertRaisesRegex(V12OwnerDenied, "OWNER_EVENT_ID_REQUIRED"):
                build_v12_owner_approval(self.db, "f"*40, 0)

    def test_reject_changed_event_head_negatives_g3_and_first_use(self):
        approved=self.approval()
        with patch("f139.nci04_v12_owner_release._original_state",
                   return_value=self.state):
            for field,changed in (
                ("owner_event_seq",252),
                ("owner_event_sha256","f"*64),
                ("v11_terminal_event_sha256","f"*64),
                ("g54_ambiguous_start_event_sha256","f"*64),
                ("g3_draft_history_sha256","f"*64),
                ("verified_tickets_sha256","f"*64),
                ("quarantined_tickets_sha256","f"*64),
            ):
                with self.subTest(field=field):
                    with self.assertRaisesRegex(
                        V12OwnerDenied, "OWNER_EVENT_HEAD_CHANGED|FROZEN_HISTORY_CHANGED"
                    ):
                        validate_v12_original_owner(
                            self.db, {**approved, field:changed})
            for field,changed in (
                ("scientific_first_use",True),
                ("new_controller",True),("new_scheduler",True),
                ("new_queue",True),
                ("v2_production_dispatch_authorized",True),
                ("paid_api_calls",1)
            ):
                with self.subTest(field=field):
                    with self.assertRaisesRegex(V12OwnerDenied, "NEW_AUTHORITY_FORBIDDEN"):
                        validate_v12_original_owner(
                            self.db, {**approved, field:changed})

    def test_stale_fields_and_noncanonical_owner_denied(self):
        approved=self.approval()
        with self.assertRaisesRegex(V12OwnerDenied,"CANONICAL_ORIGINAL"):
            validate_v12_original_owner(object(),approved)
        with patch("f139.nci04_v12_owner_release._original_state",
                   return_value=self.state):
            with self.assertRaisesRegex(V12OwnerDenied,"EXACT_APPROVAL_FIELDS_REQUIRED"):
                validate_v12_original_owner(self.db,{**approved,"additional":True})

    def test_v12_remains_single_original_source_successor_not_model_authority(self):
        cli_code=inspect.getsource(cli)
        self.assertIn("transition-qualified-native-v12",cli_code)
        self.assertIn("validate_v12_original_owner(validator_db,approval)",cli_code)
        self.assertIn("allow_v12=True",cli_code)
        self.assertIn("native_original_owner_profile(args.db)",cli_code)
        self.assertIn("with SingleOwner(args.db.with_suffix(\".lock\")):",cli_code)
        transition=inspect.getsource(Database.transition_source)
        self.assertIn("SOURCE_TRANSITION_V12_ORIGINAL_CUSTODY_REQUIRED",transition)
        self.assertIn("SOURCE_TRANSITION_V12_V11_SEAL_MISSING",transition)
        self.assertIn("SOURCE_TRANSITION_V12_G3_HISTORY_DRIFT",transition)
        self.assertIn("g54_original_canonical(self)",transition)
        cold=inspect.getsource(Database.verify)
        self.assertIn("if is_v12:",cold)
        self.assertIn("SOURCE_TRANSITION_V12_ORIGINAL_CUSTODY_DRIFT",cold)
        self.assertIn("v11_terminal_event_sha256",cold)
        self.assertIn("g3_draft_history_sha256",cold)
        self.assertIn("prior_g54_ambiguous",cold)
        signer=inspect.getsource(v2_owner_terminal_release_guard)
        self.assertIn("v12 = False",signer)
        self.assertIn("v11_terminal_event_sha256",signer)
        self.assertIn("g54_original_canonical(db)",signer)
        self.assertIn("verify_native_activation(db)",signer)


if __name__ == "__main__":
    unittest.main()
