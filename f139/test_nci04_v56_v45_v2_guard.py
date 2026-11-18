"""V45 original V2 development guard: detached, synthetic and fail-closed.

No real Windows owner, GitHub dispatch, terminal settlement, or scientific use.
The production V45 ledger must still be verified independently on the owner.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import (
    SingleOwner, v2_owner_terminal_release_guard,
)
from f139.nci04_v55_detached_activation import (
    rehearse_v45_source_and_activation,
)
from f139.test_nci04_v55_detached_activation import V55DetachedActivation


class V45V2DispatchGuardTests(unittest.TestCase):
    def setUp(self):
        fixture = V55DetachedActivation(
            "test_detached_transition_and_activation_are_atomic_and_once_only"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.source = fixture.args()["target"]
        with SingleOwner(fixture.path.with_suffix(".lock")):
            rehearse_v45_source_and_activation(self.db, **fixture.args())
        row = self.db.conn.execute(
            "SELECT payload FROM events WHERE seq=1850"
        ).fetchone()
        self.original = json.loads(row["payload"])
        self.assertEqual(self.original["schema"],
                         "forge.f139.source-transition.v45")
        self.assertNotIn("v2_receipt_authorized", self.original)

    def guard(self, *, g49=True, activation=True):
        with patch("f139.local_controller.g54_original_canonical",
                   return_value={"historical": "synthetic"}), patch(
                   "f139.nci04_g49_prepost_negative.verify_g49_custody",
                   return_value=g49), patch(
                   "f139.nci04_owner_ledger.verify_native_activation",
                   return_value=activation):
            return v2_owner_terminal_release_guard(self.source, self.db)

    def overwrite(self, doc):
        self.db.conn.execute(
            "UPDATE events SET payload=? WHERE seq=1850",
            (json.dumps(doc, sort_keys=True),)
        )

    def test_exact_v45_development_release_is_eligible_without_legacy_field(self):
        before = self.db.conn.total_changes
        self.assertTrue(self.guard())
        self.assertEqual(self.db.conn.total_changes, before)
        self.assertFalse(self.original["scientific_first_use"])
        self.assertEqual(self.original["new_dispatches"], 0)

    def test_v45_malformed_scope_or_field_inventory_denied(self):
        bad = [
            ("scientific_first_use", True),
            ("native_development_approved", False),
            ("new_dispatches", 1),
            ("new_dispatches", True),
            ("new_controller", True),
            ("new_scheduler", True),
            ("new_queue", True),
            ("paid_api_calls", 1),
            ("paid_api_calls", True),
            ("source_transition_purpose", "unqualified"),
            ("from_source_sha", "0" * 40),
            ("to_source_sha", "1" * 40),
            ("schema", "forge.f139.source-transition.v46"),
        ]
        try:
            for name, value in bad:
                with self.subTest(field=name):
                    self.overwrite(dict(self.original, **{name: value}))
                    self.assertFalse(self.guard())
            with self.subTest(field="unreviewed-extra"):
                self.overwrite(dict(self.original, unreviewed=True))
                self.assertFalse(self.guard())
            with self.subTest(field="missing-required"):
                malformed = dict(self.original)
                malformed.pop("new_dispatches")
                self.overwrite(malformed)
                self.assertFalse(self.guard())
            with self.subTest(field="legacy-receipt-forgery"):
                self.overwrite(dict(self.original,
                                    v2_receipt_authorized=True))
                self.assertFalse(self.guard())
        finally:
            self.overwrite(self.original)
        self.assertTrue(self.guard())

    def test_v45_requires_historical_custody_and_native_activation(self):
        self.assertFalse(self.guard(g49=False))
        self.assertFalse(self.guard(activation=False))
        self.assertTrue(self.guard())

    def test_cannot_rebind_to_unrelated_source(self):
        self.assertFalse(v2_owner_terminal_release_guard(
            "f" * 40, self.db))


if __name__ == "__main__":
    unittest.main()
