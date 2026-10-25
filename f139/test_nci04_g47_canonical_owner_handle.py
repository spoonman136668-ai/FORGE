"""G47 regression: original -m entrypoint class identity must not strand V2."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from f139.local_controller import (
    Database, original_owner_v2_fields_canonical,
)
from f139.nci04_g36_v2_dispatch import (
    G36Denied, original_owner_v2_fields,
)
from f139.test_nci04_g32_owner_custody import OriginalOwnerG32Tests
from f139.test_nci04_owner_issue import HMAC


class MainModuleDatabaseFacade:
    """Represents original -m entrypoint's distinct Database class identity."""
    __module__ = "__main__"

    def __init__(self, actual):
        self.filename = actual.filename
        self._original = actual

    def meta(self):
        return self._original.meta()


class G47ExactOwnerTypeBoundaryTests(unittest.TestCase):
    def setUp(self):
        fixture = OriginalOwnerG32Tests()
        # Retain the disposable fixture's original START_RISK event, not POST.
        with mock.patch.object(Database, "dispatch_observed", return_value=None):
            fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.db = fixture.db
        self.issue = fixture.issue

    def test_original_module_class_mismatch_is_repaired_without_relaxing_g36(self):
        entrypoint = MainModuleDatabaseFacade(self.db)
        before = self.db.meta()
        with self.assertRaisesRegex(G36Denied, "ORIGINAL_DATABASE_REQUIRED"):
            original_owner_v2_fields(
                entrypoint, self.issue.ticket, owner_hmac_key=HMAC)
        fields = original_owner_v2_fields_canonical(
            entrypoint, self.db.filename, self.issue.ticket,
            owner_hmac_key=HMAC)
        self.assertEqual(fields["native_protocol"], "v2")
        self.assertNotIn(HMAC, repr(fields))
        self.assertEqual(self.db.meta(), before)
        self.db.verify()

    def test_different_original_database_path_fails_closed(self):
        entrypoint = MainModuleDatabaseFacade(self.db)
        before = self.db.meta()
        with self.assertRaisesRegex(Exception, "G47_ORIGINAL_DATABASE_PATH_DRIFT"):
            original_owner_v2_fields_canonical(
                entrypoint, Path(__file__).resolve(), self.issue.ticket,
                owner_hmac_key=HMAC)
        self.assertEqual(self.db.meta(), before)

    def test_changed_claim_head_fails_closed_without_second_signature(self):
        entrypoint = MainModuleDatabaseFacade(self.db)
        real_meta = entrypoint.meta
        entrypoint.meta = lambda: {**real_meta(), "head_hash": "f" * 64}
        before = self.db.meta()
        with self.assertRaisesRegex(Exception, "G47_ORIGINAL_LEDGER_HEAD_DRIFT"):
            original_owner_v2_fields_canonical(
                entrypoint, self.db.filename, self.issue.ticket,
                owner_hmac_key=HMAC)
        self.assertEqual(self.db.meta(), before)


if __name__ == "__main__":
    unittest.main()
