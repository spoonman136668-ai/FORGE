"""Synthetic one-shot F139 fresh-activation transaction and fail-closed tests.

The original Windows task, runner, GitHub owner comment, provider and cold
archive verifier are MOCKED. This is engineering qualification only, never
proof of real owner release, deployment or scientific first-use.
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_dev_epoch import hash_file
from f139.nci04_fresh_native_activation import (
    audit_fresh_native_activation,
)
from f139.nci04_fresh_remote_floor import SCHEMA as FLOOR_SCHEMA
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.test_nci04_fresh_dev_epoch import (
    SyntheticFreshDevelopmentTests, TARGET,
)
from f139.nci04_fresh_activation_writer import (
    FreshActivationWriteDenied, _owner_windows_quiesced,
    write_fresh_native_activation_once, _WINDOWS_READONLY_PROBE,
)


class OneShotActivationWriterTests(unittest.TestCase):
    def setUp(self):
        # Reuse the already-qualified synthetic cold-staging setup instead
        # of creating another incompatible historical 1864-event fixture.
        self.fixture = SyntheticFreshDevelopmentTests(
            "test_creates_only_separate_disabled_empty_sqlite")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.prepare()
        self.fresh_path = self.fixture.fresh() / "state.sqlite"
        self.fresh = Database(self.fresh_path)
        self.addCleanup(self.fresh.close)
        self.original = self.fixture.orig
        self.before_original = hash_file(self.fixture.old)
        self.floor = {
            "schema": FLOOR_SCHEMA,
            "original_source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "target_forge_source_sha": TARGET,
            "consumed_exclusions_sha256":
                digest(canonical(self.fixture.exclusions)),
            "remote_cutover_issue_number_floor": 4000,
            "remote_cutover_issue_provider_verified": True,
            "fresh_activation_authorized": False,
            "owner_task_rebind_authorized": False,
            "release_qualified": False,
            "scientific_first_use": False,
        }
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        name = "f139.nci04_fresh_activation_writer."
        self.host = self.stack.enter_context(
            patch(name + "_owner_windows_quiesced", return_value=True))
        self.stack.enter_context(patch(
            name + "audit_frozen_original_readonly",
            return_value=self.fixture.frozen))
        self.stack.enter_context(patch(
            name + "verify_original_cold_backup",
            return_value=self.fixture.verified))
        self.stack.enter_context(patch(
            name + "read_yggdrasil_research_boundary",
            return_value=self.fixture.lineage))
        self.provider = self.stack.enter_context(patch(
            name + "prove_fresh_native_issue_cutover_floor",
            return_value=self.floor))

    def commit(self):
        def forbidden_get(route):
            raise AssertionError("TEST_STUB_MUST_NOT_CALL_NETWORK")
        return write_fresh_native_activation_once(
            self.original, self.fresh, get=forbidden_get)

    def assert_original_unchanged(self):
        self.assertEqual(hash_file(self.fixture.old), self.before_original)
        self.assertEqual(self.original.conn.total_changes, 0)

    def assert_still_inert(self):
        self.assertEqual(self.fresh.meta()["head_seq"], 0)
        self.assertEqual(self.fresh.meta()["enabled"], 0)
        self.assertEqual(self.fresh.meta()["legacy_suspended"], 0)
        self.assertEqual(self.fresh.conn.execute(
            "SELECT count(*) FROM tasks").fetchone()[0], 0)
        self.assert_original_unchanged()

    def test_actual_two_event_transaction_and_cold_restart_remain_inert(self):
        receipt = self.commit()
        self.assertEqual(receipt["schema"],
                         "forge.f139.fresh-native-activation-write-receipt.v1")
        self.assertEqual(receipt["head_seq"], 2)
        self.assertEqual(receipt["source_sha"], TARGET)
        for field in ("task_rebound", "worker_dispatched",
                      "native_issue_admitted", "scientific_first_use"):
            self.assertIs(receipt[field], False)
        self.assertEqual(receipt["paid_model_calls"], 0)
        self.assertTrue(self.host.called)
        self.assertEqual(self.provider.call_count, 1)
        activation = audit_fresh_native_activation(self.fresh)
        self.assertEqual(activation["remote_issue_number_floor"], 4000)
        self.assertEqual(activation["owner_run_id"], self.fixture.RUN
                         if hasattr(self.fixture, "RUN") else 44584522737)
        self.assert_original_unchanged()
        self.fresh.close()
        frozen = Database.open_readonly(self.fresh_path)
        try:
            frozen.verify()
            self.assertEqual(audit_fresh_native_activation(frozen), activation)
            self.assertEqual(frozen.conn.execute(
                "SELECT count(*) FROM tasks").fetchone()[0], 0)
        finally:
            frozen.close()

    def test_second_activation_cannot_replay_or_add_events(self):
        self.commit()
        head = dict(self.fresh.meta())
        with self.assertRaisesRegex(
                FreshActivationWriteDenied, "FRESH_STAGE_ALREADY_CONSUMED"):
            self.commit()
        self.assertEqual(dict(self.fresh.meta()), head)
        self.assert_original_unchanged()

    def test_missing_host_release_denies_before_any_receipt_write(self):
        self.host.return_value = False
        with self.assertRaisesRegex(
                FreshActivationWriteDenied, "ORIGINAL_HOST_NOT_QUIESCED"):
            self.commit()
        self.assert_still_inert()
        self.assertFalse((self.fresh_path.parent /
                          "original-task-release.json").exists())

    def test_host_lost_during_sql_transaction_rolls_back_both_events(self):
        # Initial, before external create-only receipts, then inside SQL.
        self.host.side_effect = [True, True, False]
        with self.assertRaisesRegex(
                FreshActivationWriteDenied, "ORIGINAL_RELEASE_OR_FRESH_HEAD"):
            self.commit()
        self.assert_still_inert()
        # A partial create-only attempt is burned: no cleanup/retry of
        # uncertain-effect receipt identities.
        self.assertTrue((self.fresh_path.parent /
                         "remote-issue-cutover-floor.json").exists())
        self.host.side_effect = None
        self.host.return_value = True
        with self.assertRaisesRegex(
                FreshActivationWriteDenied, "ONE_SHOT_RECEIPT_PATH_ALREADY_SPENT"):
            self.commit()
        self.assert_still_inert()

    def test_provider_floor_regression_denied_without_writes(self):
        self.floor["remote_cutover_issue_number_floor"] = 1
        with self.assertRaisesRegex(ValueError, "ORIGINAL_PROVIDER_FLOOR"):
            self.commit()
        self.assert_still_inert()
        self.assertFalse((self.fresh_path.parent /
                          "remote-issue-cutover-floor.json").exists())

    def test_original_head_drift_denied_before_external_receipts(self):
        self.fixture.frozen = {
            **self.fixture.frozen, "head_sha256": "0" * 64}
        with patch("f139.nci04_fresh_activation_writer."
                   "audit_frozen_original_readonly",
                   return_value=self.fixture.frozen):
            with self.assertRaisesRegex(
                    FreshActivationWriteDenied, "ORIGINAL_LEDGER_HEAD_DRIFT"):
                self.commit()
        self.assert_still_inert()

    def test_windows_probe_explicitly_has_no_task_mutation(self):
        for forbidden in (
            "Stop-ScheduledTask", "Start-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Register-ScheduledTask", "Set-ScheduledTask",
            "Stop-Process"):
            self.assertNotIn(forbidden, _WINDOWS_READONLY_PROBE)
        self.assertIn("Get-ScheduledTask", _WINDOWS_READONLY_PROBE)
        self.assertIn("Get-CimInstance", _WINDOWS_READONLY_PROBE)

    def test_real_windows_host_guard_fails_closed_off_owner(self):
        with patch("f139.nci04_fresh_activation_writer.sys.platform",
                   "linux"), self.assertRaisesRegex(
                       FreshActivationWriteDenied,
                       "ORIGINAL_WINDOWS_AUTHENTICATED_WORKFLOW_REQUIRED"):
            _owner_windows_quiesced(Path("/tmp/does-not-exist"), TARGET,
                                    44584522737)


if __name__ == "__main__":
    unittest.main()
