"""Fail-closed contract checks for the G54 V10 owner approval."""
import unittest

from f139.local_controller import Database
from f139.nci04_v10_owner_release import (
    FIELDS, SCHEMA, V10OwnerDenied, validate_v10_original_owner,
)


class V10OwnerReleaseTests(unittest.TestCase):
    def test_schema_is_exact_and_authority_is_explicitly_limited(self):
        self.assertEqual(SCHEMA, "forge.f139.nci04.original-owner-source-v10-approval.v1")
        self.assertEqual(len(FIELDS), 16)
        self.assertIn("owner_event_sha256", FIELDS)
        self.assertIn("v9_terminal_event_sha256", FIELDS)
        self.assertIn("quarantined_tickets_sha256", FIELDS)

    def test_noncanonical_database_is_rejected(self):
        with self.assertRaisesRegex(V10OwnerDenied, "CANONICAL_OWNER_DATABASE_REQUIRED"):
            validate_v10_original_owner(object(), {})

    def test_missing_or_extra_approval_fields_are_rejected(self):
        db = object.__new__(Database)
        with self.assertRaisesRegex(V10OwnerDenied, "EXACT_APPROVAL_FIELDS_REQUIRED"):
            validate_v10_original_owner(db, {})
        with self.assertRaisesRegex(V10OwnerDenied, "EXACT_APPROVAL_FIELDS_REQUIRED"):
            validate_v10_original_owner(db, {name: None for name in FIELDS} | {"extra": False})

    def test_unapproved_scientific_authority_is_rejected_before_ledger_access(self):
        db = object.__new__(Database)
        approval = {name: None for name in FIELDS}
        approval.update({
            "schema": SCHEMA,
            "from_source_sha": "3f1a3eba68d6b89e24913ca89df5e9bf8062bee0",
            "to_source_sha": "a" * 40,
            "owner_event_id": 1,
            "owner_event_seq": 1,
            "owner_event_sha256": "b" * 64,
            "v9_terminal_event_sha256": "c" * 64,
            "prepost_negative_event_sha256": "d" * 64,
            "quarantined_tickets_sha256": "e" * 64,
            "development_only": True,
            "scientific_first_use": True,
            "v2_production_dispatch_authorized": False,
            "new_controller": False,
            "new_scheduler": False,
            "new_queue": False,
            "paid_api_calls": 0,
        })
        from f139.nci04_native_contract import canonical
        approval = __import__("json").loads(canonical(approval))
        with self.assertRaisesRegex(V10OwnerDenied, "APPROVAL_NO_NEW_AUTHORITY"):
            validate_v10_original_owner(db, approval)


if __name__ == "__main__":
    unittest.main()
