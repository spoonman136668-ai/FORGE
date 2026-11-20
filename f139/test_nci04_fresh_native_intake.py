"""Synthetic exact-source F139 fresh one-ticket intake regression controls.

Never interacts with the genuine original Windows task, remote provider or
real owner SQLite. The original history, worker and checkpoint remain inert.
"""
from __future__ import annotations
import base64
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_fresh_native_owner_route import inspect_staged_fresh_native_mode
from f139.nci04_fresh_native_activation import audit_fresh_native_activation
from f139.nci04_fresh_yggdrasil_boundary import ACCEPTED
from f139.nci04_fresh_native_intake import (
    FreshIntakeDenied, stage_one_fresh_development_issue,
)
from f139.test_nci04_fresh_activation_writer import OneShotActivationWriterTests
from f139.test_nci04_fresh_native_provider_issue import (
    FreshProviderPreflightTests, FORGE, YGG,
)


class FreshOneTicketIntakeTests(unittest.TestCase):
    def setUp(self):
        self.owner = OneShotActivationWriterTests(
            "test_actual_two_event_transaction_and_cold_restart_remain_inert")
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.owner.commit()
        self.db = self.owner.fresh
        self.original = self.owner.original
        self.head = dict(self.db.meta())
        self.original_hash = self.owner.before_original
        self.issue_number = 4001
        self.provider_fixture = FreshProviderPreflightTests(
            "test_provider_candidate_preflight_is_inert_and_rechecks_all")
        self.provider_fixture.setUp()
        self.addCleanup(self.provider_fixture.doCleanups)
        source = self.db.meta()["source_sha"]
        self.intent = deepcopy(self.provider_fixture.intent)
        self.intent["controller_source_sha"] = source
        self.body = deepcopy(self.provider_fixture.issue_body)
        self.body["source_sha"] = source
        self.body["intent_base64"] = base64.b64encode(
            canonical(self.intent)).decode("ascii")
        self.issue = deepcopy(self.provider_fixture.issue)
        self.issue.update({
            "number": self.issue_number, "id": 914001,
            "created_at": "2026-11-19T18:01:00Z",
            "body": json.dumps(self.body, sort_keys=True),
        })
        self.tree = "c" * 40
        self.native = inspect_owner_issue(
            self.issue, protected_main=source,
            authenticated_target_commit=ACCEPTED,
            authenticated_target_tree=self.tree)
        self.proof = {
            "schema": "forge.f139.fresh-provider-issue-preflight-only.v1",
            "source_sha": source, "issue_number": self.issue_number,
            "issue_id": self.native.issue_id,
            "ticket": self.native.ticket,
            "issue_body_sha256": self.native.issue_body_sha256,
            "native_intent_sha256": self.native.native_intent_sha256,
            "accepted_yggdrasil_source_sha": ACCEPTED,
            "issue_admission_authorized": False,
            "worker_dispatch_authorized": False,
        }
        self.routes = {
            FORGE + "/issues/" + str(self.issue_number): self.issue,
            YGG + "/git/commits/" + ACCEPTED: {
                "sha": ACCEPTED, "tree": {"sha": self.tree},
            },
        }
        self.calls = []
        self.host = self.enterContext(
            patch("f139.nci04_fresh_native_intake."
                  "_authenticate_disabled_owner_host"))
        self.preflight = self.enterContext(
            patch("f139.nci04_fresh_native_intake."
                  "inspect_fresh_provider_issue", return_value=self.proof))
        self.audit = self.enterContext(
            patch("f139.nci04_fresh_native_intake."
                  "audit_frozen_original_readonly",
                  return_value=deepcopy(self.owner.fixture.frozen)))

    def provider(self, route: str):
        self.assertIn(route, self.routes)
        self.calls.append(route)
        return deepcopy(self.routes[route])

    def submit(self):
        return stage_one_fresh_development_issue(
            self.db, self.original, issue_number=self.issue_number,
            get=self.provider)

    def assert_no_new_events_or_tasks(self):
        self.assertEqual(dict(self.db.meta()), self.head)
        self.assertEqual(
            self.db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
            0)
        self.owner.assert_original_unchanged()

    def test_one_authenticated_ready_ticket_remains_dispatch_blocked(self):
        report = self.submit()
        self.assertEqual(report["head_seq"], 4)
        self.assertEqual(report["ticket"], self.native.ticket)
        self.assertFalse(report["worker_dispatched"])
        self.assertFalse(report["task_rebound"])
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(report["original_mutations"], 0)
        self.assertEqual(report["paid_model_calls"], 0)
        self.assertGreaterEqual(self.host.call_count, 2)
        self.assertEqual(self.preflight.call_count, 1)
        self.db.verify()
        mode = inspect_staged_fresh_native_mode(
            self.db, self.owner.fresh_path)
        self.assertEqual(
            mode["disposition"],
            "FRESH_DEVELOPMENT_INTAKE_READY_DISPATCH_BLOCKED")
        self.assertTrue(mode["fresh_work_admitted"])
        self.assertFalse(mode["worker_dispatched"])
        audit = audit_fresh_native_activation(self.db)
        self.assertEqual(audit["source_sha"], self.db.meta()["source_sha"])
        self.owner.assert_original_unchanged()
        # A second request can never requeue or replay the same issue.
        with self.assertRaises(FreshIntakeDenied):
            self.submit()
        self.assertEqual(self.db.meta()["head_seq"], 4)
        readonly = Database.open_readonly(self.owner.fresh_path)
        try:
            readonly.verify()
            self.assertEqual(
                audit_fresh_native_activation(readonly), audit)
        finally:
            readonly.close()

    def test_old_issue_floor_fails_before_any_new_host_or_provider_read(self):
        self.issue_number = 3999
        with self.assertRaisesRegex(
                FreshIntakeDenied, "ISSUE_MUST_FOLLOW_CUTOVER_FLOOR"):
            self.submit()
        self.host.assert_not_called()
        self.preflight.assert_not_called()
        self.assert_no_new_events_or_tasks()

    def test_host_quiescence_failure_preserves_original_and_fresh_state(self):
        self.host.side_effect = FreshIntakeDenied(
            "F139_FRESH_INTAKE_ORIGINAL_OWNER_NOT_QUIESCED")
        with self.assertRaisesRegex(
                FreshIntakeDenied, "ORIGINAL_OWNER_NOT_QUIESCED"):
            self.submit()
        self.preflight.assert_not_called()
        self.assert_no_new_events_or_tasks()

    def test_provider_candidate_identity_drift_never_admits(self):
        self.proof["ticket"] = "f139-nci04-another-ticket"
        with self.assertRaisesRegex(
                FreshIntakeDenied, "ISSUE_CHANGED_AFTER_PROVIDER_PREFLIGHT"):
            self.submit()
        self.assert_no_new_events_or_tasks()

    def test_issue_body_changed_after_provider_preflight_denied(self):
        new_intent = deepcopy(self.intent)
        new_intent["suite_identity_sha256"] = "a" * 64
        new_body = deepcopy(self.body)
        new_body["intent_base64"] = base64.b64encode(
            canonical(new_intent)).decode("ascii")
        self.issue["body"] = json.dumps(new_body, sort_keys=True)
        with self.assertRaises(FreshIntakeDenied):
            self.submit()
        self.assert_no_new_events_or_tasks()

    def test_owner_release_lost_inside_transaction_rolls_back(self):
        self.host.side_effect = [
            None, FreshIntakeDenied("F139_FRESH_INTAKE_OWNER_LOST")
        ]
        with self.assertRaisesRegex(FreshIntakeDenied, "OWNER_LOST"):
            self.submit()
        self.assertEqual(self.host.call_count, 2)
        self.assert_no_new_events_or_tasks()

    def test_tampered_or_dispatched_task_invalidates_cold_audit(self):
        self.submit()
        self.db.conn.execute(
            "UPDATE tasks SET stage='START_RISK' WHERE ticket=?",
            (self.native.ticket,))
        with self.assertRaises(FreshIntakeDenied):
            audit_fresh_native_activation(self.db)
        self.owner.assert_original_unchanged()


if __name__ == "__main__":
    unittest.main()
