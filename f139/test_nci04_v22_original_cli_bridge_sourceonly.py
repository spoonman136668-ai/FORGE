"""V22 original CLI adapter: disposable real SQLite and no remote traffic."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import f139.local_controller as canonical
from f139.nci04_v22_original_cli_bridge_sourceonly import (
    OriginalCLIBridgeDenied, run_original_cli_v21_source_only,
)
from test_nci04_v19_original_attempt_schema import OriginalRequestColdVerifierTests


class OriginalCLIIdentityBridgeTests(TestCase):
    def setUp(self):
        fixture = OriginalRequestColdVerifierTests(
            "test_no_new_events_original_behavior_and_original_head_unchanged")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = fixture.mutex
        self.packet = Mock(side_effect=AssertionError("NO_PUBLIC_PACKET"))
        self.public = Mock(side_effect=AssertionError("NO_PUBLIC_GIT_FETCH"))
        self.send = Mock(side_effect=AssertionError("NO_MODEL_POST"))
        self.witness = Mock(return_value=True)
        self.original_profile = patch(
            "f139.local_controller.native_original_running_publisher_profile",
            return_value=True)
        self.profile = self.original_profile.start()
        self.addCleanup(self.original_profile.stop)

    def call(self, api, db=None):
        return run_original_cli_v21_source_only(
            self.db if db is None else db, api, self.db.filename,
            utc_day="2026-10-30", packet_for_terminal=self.packet,
            public_reader=self.public, owner_witness=self.witness,
            token="offline-sentinel-never-remote",
            transport=self.send)

    def assert_no_effect(self, before):
        self.db.verify()
        self.assertEqual(self.db.meta(), before)
        self.packet.assert_not_called()
        self.public.assert_not_called()
        self.send.assert_not_called()
        cold = canonical.Database.open_readonly(self.db.filename)
        try:
            self.assertEqual(cold.meta(), before)
        finally:
            cold.close()

    def test_real_canonical_original_no_terminal_never_sends(self):
        api = canonical.GitHub.__new__(canonical.GitHub)
        with canonical.SingleOwner(self.mutex):
            before = self.db.meta().copy()
            response = self.call(api)
            self.assertEqual(response["disposition"],
                             "BLOCKED_NO_FRESH_ELIGIBLE_NATIVE_TERMINAL")
            self.assertFalse(response["runtime_activated"])
            self.assert_no_effect(before)

    def test_actual_cli_module_class_split_reopens_canonical_original(self):
        # Mimic python -m without importing a second controller or owner key.
        cli_db_cls = type("Database", (canonical.Database,),
                          {"__module__": "__main__"})
        cli_api_cls = type("GitHub", (canonical.GitHub,),
                           {"__module__": "__main__"})
        cli_main = SimpleNamespace(
            __file__=canonical.__file__,
            Database=cli_db_cls,
            GitHub=cli_api_cls,
            SingleOwner=canonical.SingleOwner,
        )
        cli_db = cli_db_cls(self.db.filename)
        self.addCleanup(cli_db.close)
        cli_api = cli_api_cls.__new__(cli_api_cls)
        with patch.dict(sys.modules, {"__main__": cli_main}):
            with canonical.SingleOwner(self.mutex):
                before = self.db.meta().copy()
                response = self.call(cli_api, db=cli_db)
                self.assertEqual(response["disposition"],
                                 "BLOCKED_NO_FRESH_ELIGIBLE_NATIVE_TERMINAL")
                self.assert_no_effect(before)
        self.assertTrue(self.profile.called)

    def test_lock_missing_and_owner_profile_rejected_before_reopening(self):
        api = canonical.GitHub.__new__(canonical.GitHub)
        original = self.db.meta().copy()
        with self.assertRaisesRegex(OriginalCLIBridgeDenied,
                                    "NOT_ORIGINAL_RUNNING_MUTEX"):
            self.call(api)
        self.assert_no_effect(original)
        with canonical.SingleOwner(self.mutex):
            self.profile.return_value = False
            with self.assertRaisesRegex(OriginalCLIBridgeDenied,
                                        "ORIGINAL_WINDOWS_OWNER_NOT_ATTESTED"):
                self.call(api)
        self.assert_no_effect(original)

    def test_caller_forgeries_do_not_bypass_owner_identity(self):
        class FakeGitHub:
            native_repo_get = Mock()
            owner_model_write = Mock()
        with canonical.SingleOwner(self.mutex):
            before = self.db.meta().copy()
            with self.assertRaises(OriginalCLIBridgeDenied):
                self.call(FakeGitHub())
            self.assert_no_effect(before)
