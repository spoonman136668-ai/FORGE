"""V23 live-source branch: real original SQLite, fake provider and Git only."""
from __future__ import annotations

import inspect
from unittest import TestCase
from unittest.mock import Mock, patch

from f139 import nci04_v23_original_renewal_natural_tick as runtime
from f139.local_controller import Database, GitHub, SingleOwner, run_once
from test_nci04_v19_original_attempt_schema import OriginalRequestColdVerifierTests


class OriginalNaturalRenewalTests(TestCase):
    def setUp(self):
        fixture = OriginalRequestColdVerifierTests(
            "test_no_new_events_original_behavior_and_original_head_unchanged")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = fixture.mutex
        self.api = GitHub.__new__(GitHub)
        self.calls = Mock(side_effect=AssertionError("NO_MODEL_POST"))
        self.public = Mock(side_effect=AssertionError("NO_PUBLIC_GIT"))
        profile = patch(
            "f139.local_controller.native_original_running_publisher_profile",
            return_value=True)
        profile.start()
        self.addCleanup(profile.stop)

    def cycle(self, token="fixture-only-not-a-real-key", witness=lambda: True,
              day="2026-10-28"):
        return runtime.run_original_renewal_from_natural_tick(
            self.db, self.api, self.db.filename,
            source_sha=self.db.meta()["source_sha"],
            owner_witness=witness, utc_day=day,
            token=token, public_reader=self.public, transport=self.calls)

    def preserve(self, before):
        self.db.verify()
        self.assertEqual(self.db.meta(), before)
        self.calls.assert_not_called()
        self.public.assert_not_called()
        cold = Database.open_readonly(self.db.filename)
        try:
            cold.verify()
            self.assertEqual(cold.meta(), before)
        finally:
            cold.close()

    def test_no_credential_means_no_original_request(self):
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            result = self.cycle(token="")
            self.assertEqual(
                result["disposition"],
                "NATIVE_RENEWAL_NO_FREE_CREDENTIAL_NO_REQUEST")
            self.preserve(before)

    def test_original_legacy_spend_after_terminal_makes_native_stale(self):
        self.fixture.real_native()
        self.fixture.original_spent_free_request()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            result = self.cycle()
            self.assertEqual(
                result["disposition"],
                "BLOCKED_NO_FRESH_ELIGIBLE_NATIVE_TERMINAL")
            self.preserve(before)

    def test_new_original_terminal_cannot_override_old_same_day_spend(self):
        self.fixture.original_spent_free_request()
        self.fixture.real_native()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            result = self.cycle()
            self.assertEqual(
                result["disposition"],
                "BLOCKED_ORIGINAL_PLUS_RENEWAL_ROLLING_BUDGET")
            self.preserve(before)

    def test_missing_running_owner_witness_and_bad_token_fail_before_io(self):
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(
                runtime.OriginalRenewalRuntimeDenied,
                "RUNNING_OWNER_WITNESS_REQUIRED"):
                self.cycle(witness=lambda: False)
            with self.assertRaisesRegex(
                runtime.OriginalRenewalRuntimeDenied,
                "CREDENTIAL_FORMAT_INVALID"):
                self.cycle(token="bad\nkey")
            self.preserve(before)

    def test_only_after_eight_original_attempts_is_live_tick_route_reachable(self):
        source = inspect.getsource(run_once)
        self.assertIn("if free_spent >= 8:", source)
        self.assertIn("run_original_renewal_from_natural_tick(", source)
        self.assertIn("NATIVE_RENEWAL_GUARD_BLOCKED_FAIL_CLOSED", source)
        self.assertIn("run_original_free_reasoner_once(", source)
        # The original G3/G29 finite route and native dispatch remain present.
        self.assertIn("run_original_g29_once(", source)
        self.assertIn("publish_once(", source)
