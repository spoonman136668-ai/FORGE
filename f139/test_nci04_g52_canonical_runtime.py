"""Production -m V2 guard and terminal handlers use canonical strict types.

Focused, disposable original-custody fixture. No network, local owner task,
provider dispatch, actual terminal receipts or source mutations.
"""
from __future__ import annotations

import unittest
from unittest import mock

from f139.local_controller import (
    Database, GitHub, SingleOwner, original_owner_v2_guard_canonical,
    settle_original_v2_canonical,
)
from f139.test_nci04_g32_owner_custody import OriginalOwnerG32Tests
from f139.test_nci04_owner_issue import HMAC


class OriginalModuleEntrypointTypeTests(unittest.TestCase):
    def setUp(self):
        fx=OriginalOwnerG32Tests()
        with mock.patch.object(Database, "dispatch_observed", return_value=None):
            fx.setUp()
        self.addCleanup(fx.doCleanups)
        self.fx=fx
        self.before=fx.db.meta()

    def test_strict_v2_guard_receives_same_canonical_original_db(self):
        with mock.patch("f139.local_controller.v2_owner_terminal_release_guard",
                        return_value=True) as guard:
            self.assertTrue(original_owner_v2_guard_canonical(
                self.fx.db, self.fx.db.filename,
                self.fx.db.meta()["source_sha"]))
            guarded=guard.call_args.args[1]
            self.assertIs(type(guarded), Database)
            self.assertEqual(guarded.filename.resolve(),
                             self.fx.db.filename.resolve())
            self.assertEqual(self.fx.db.meta(), self.before)

    def test_guard_fails_on_wrong_db_path_before_signing(self):
        with mock.patch("f139.local_controller.v2_owner_terminal_release_guard"
                        ) as guard:
            with self.assertRaisesRegex(Exception, "G52_ORIGINAL_V2_GUARD_DB_PATH_DRIFT"):
                original_owner_v2_guard_canonical(
                    self.fx.db, __file__, self.fx.db.meta()["source_sha"])
            guard.assert_not_called()
        self.assertEqual(self.fx.db.meta(), self.before)

    def test_g38_real_settlement_requires_only_existing_original_mutex(self):
        with mock.patch("f139.nci04_g38_owner_terminal.settle_original_v2",
                        return_value={"disposition":"MOCK_ONLY"}) as patched:
            with self.assertRaisesRegex(Exception, "G52_ORIGINAL_TERMINAL_LOCK"):
                settle_original_v2_canonical(
                    self.fx.db, GitHub(runner=lambda *_: None),
                    self.fx.db.filename, ticket=self.fx.issue.ticket,
                    run_id=1, started_at="2026-10-25T00:00:00Z",
                    owner_key=HMAC)
            patched.assert_not_called()
            with SingleOwner(self.fx.db.filename.with_suffix(".lock")):
                result=settle_original_v2_canonical(
                    self.fx.db, GitHub(runner=lambda *_: None),
                    self.fx.db.filename, ticket=self.fx.issue.ticket,
                    run_id=1, started_at="2026-10-25T00:00:00Z",
                    owner_key=HMAC)
                self.assertEqual(result["disposition"],"MOCK_ONLY")
                canonical_db, canonical_api=patched.call_args.args[:2]
                self.assertIs(type(canonical_db), Database)
                self.assertIs(type(canonical_api), GitHub)
                self.assertEqual(canonical_db.filename.resolve(),
                                 self.fx.db.filename.resolve())
        self.assertEqual(self.fx.db.meta(), self.before)

    def test_run_once_uses_canonical_guard_and_terminal_without_bypasses(self):
        import inspect
        from f139.local_controller import run_once
        text=inspect.getsource(run_once)
        self.assertIn("original_owner_v2_guard_canonical(",text)
        self.assertIn("settle_original_v2_canonical(",text)
        self.assertNotIn("and not v2_owner_terminal_release_guard(",text)


if __name__=="__main__":
    unittest.main()
