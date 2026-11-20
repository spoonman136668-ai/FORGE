"""Negative controls for the inert fresh worker-release metadata gate.

No Windows owner, live SQLite, GitHub POST, worker or model is used.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json
import unittest

from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_fresh_native_activation import ACTIVATION_SCHEMA
from f139.nci04_fresh_native_intake import SCHEMA as INTAKE_SCHEMA
from f139.nci04_fresh_worker_release_gate import (
    FORGE, YGG, SOURCE, SOURCE_TREE, WORKER_BLOB, WORKER_REF,
    WORKER_PATH, TARGET, TARGET_TREE, TICKET_ISSUE, SCHEMA,
    FreshWorkerReleaseDenied, inspect_fresh_worker_release,
)
from f139.test_nci04_fresh_native_provider_issue import (
    FreshProviderPreflightTests,
)


class FreshWorkerReleaseGateTests(unittest.TestCase):
    def setUp(self):
        fixture = FreshProviderPreflightTests(
            "test_provider_candidate_preflight_is_inert_and_rechecks_all")
        fixture.setUp()
        candidate = deepcopy(fixture.intent)
        candidate["controller_source_sha"] = SOURCE
        candidate["target_commit"] = TARGET
        candidate["target_tree_sha"] = TARGET_TREE
        body = deepcopy(fixture.issue_body)
        body["source_sha"] = SOURCE
        body["intent_base64"] = base64.b64encode(
            canonical(candidate)).decode("ascii")
        issue = deepcopy(fixture.issue)
        issue.update({
            "number": TICKET_ISSUE, "id": 91849,
            "body": json.dumps(body, sort_keys=True),
        })
        native = inspect_owner_issue(
            issue, protected_main=SOURCE,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TARGET_TREE)
        self.activation = {
            "schema": ACTIVATION_SCHEMA, "source_sha": SOURCE,
            "owner_run_id": 44831323193,
            "development_only": True, "scientific_first_use": False,
            "worker_dispatch_authorized": False,
            "model_continuation_authorized": False,
            "paid_model_calls": 0, "remote_issue_number_floor": 1830,
        }
        self.intake = {
            "schema": INTAKE_SCHEMA, "source_sha": SOURCE,
            "owner_run_id": 44831323193,
            "issue_number": TICKET_ISSUE, "issue_id": native.issue_id,
            "lane": "Yggdrasil", "ticket": native.ticket,
            "native_target_commit": TARGET,
            "native_target_tree": TARGET_TREE,
            "native_path": native.candidate.path,
            "issue_body_sha256": native.issue_body_sha256,
            "native_intent_sha256": native.native_intent_sha256,
            "qualification_key": native.qualification_key,
            "before_sha256": native.candidate.before_sha256,
            "after_sha256": native.candidate.after_sha256,
            "scientific_first_use": False,
            "worker_dispatch_authorized": False,
            "model_continuation_authorized": False,
            "paid_model_calls": 0, "remote_issue_number_floor": 1830,
        }
        self.ref_route = FORGE + "/branches/" + WORKER_REF
        self.issue_route = FORGE + "/issues/" + str(TICKET_ISSUE)
        self.routes = {
            self.ref_route: {
                "name": WORKER_REF, "protected": True,
                "commit": {"sha": SOURCE},
            },
            FORGE + "/git/commits/" + SOURCE: {
                "sha": SOURCE, "tree": {"sha": SOURCE_TREE},
            },
            FORGE + "/contents/" + WORKER_PATH + "?ref=" + SOURCE: {
                "path": WORKER_PATH, "type": "file",
                "sha": WORKER_BLOB, "size": 42812,
            },
            YGG + "/branches/main": {
                "name": "main", "protected": True,
                "commit": {"sha": TARGET},
            },
            YGG + "/git/commits/" + TARGET: {
                "sha": TARGET, "tree": {"sha": TARGET_TREE},
            },
            self.issue_route: issue,
        }
        self.calls = []
        self.second_issue = None
        self.second_ref = None

    def get(self, route):
        self.calls.append(route)
        if route == self.issue_route and self.second_issue is not None:
            if self.calls.count(route) == 2:
                return deepcopy(self.second_issue)
        if route == self.ref_route and self.second_ref is not None:
            if self.calls.count(route) == 2:
                return deepcopy(self.second_ref)
        if route not in self.routes:
            raise FileNotFoundError(route)
        return deepcopy(self.routes[route])

    def inspect(self):
        return inspect_fresh_worker_release(
            self.activation, self.intake, get=self.get)

    def test_exact_source_issue_and_ref_are_readonly_only(self):
        result = self.inspect()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["ticket"], self.intake["ticket"])
        self.assertTrue(result["worker_ref_source_verified"])
        self.assertEqual(self.calls.count(self.ref_route), 2)
        self.assertEqual(self.calls.count(self.issue_route), 2)
        for key in ("original_windows_owner_release_verified",
                    "fresh_sqlite_cold_custody_verified",
                    "owner_task_rebind_authorized",
                    "worker_dispatch_authorized", "scientific_first_use"):
            self.assertIs(result[key], False, key)
        self.assertEqual(result["paid_model_calls"], 0)
        self.assertEqual(self.intake["source_sha"], SOURCE)

    def test_missing_branch_fails_closed_before_issue_fetch(self):
        del self.routes[self.ref_route]
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "PROVIDER_UNAVAILABLE"):
            self.inspect()
        self.assertNotIn(self.issue_route, self.calls)

    def test_unprotected_or_moved_ref_rejected(self):
        for change in ({"protected": False},
                       {"commit": {"sha": "a" * 40}},
                       {"name": "wrong-ref"}):
            with self.subTest(change=change):
                self.routes[self.ref_route].update(change)
                with self.assertRaisesRegex(
                        FreshWorkerReleaseDenied, "WORKER_REF"):
                    self.inspect()
                self.routes[self.ref_route] = {
                    "name": WORKER_REF, "protected": True,
                    "commit": {"sha": SOURCE},
                }

    def test_commit_tree_and_workflow_blob_pinned(self):
        commit = self.routes[FORGE + "/git/commits/" + SOURCE]
        commit["tree"]["sha"] = "a" * 40
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "WORKER_COMMIT_TREE_DRIFT"):
            self.inspect()
        commit["tree"]["sha"] = SOURCE_TREE
        self.routes[
            FORGE + "/contents/" + WORKER_PATH + "?ref=" + SOURCE
        ]["sha"] = "b" * 40
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "WORKER_WORKFLOW_BLOB_DRIFT"):
            self.inspect()

    def test_yggdrasil_accepted_main_or_tree_moved(self):
        self.routes[YGG + "/branches/main"]["commit"]["sha"] = "c" * 40
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "YGGDRASIL_ACCEPTED_MAIN_DRIFT"):
            self.inspect()
        self.routes[YGG + "/branches/main"]["commit"]["sha"] = TARGET
        self.routes[YGG + "/git/commits/" + TARGET]["tree"]["sha"] = "d" * 40
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "YGGDRASIL_ACCEPTED_TREE_DRIFT"):
            self.inspect()

    def test_frozen_ticket_identity_drift_rejected(self):
        self.intake["ticket"] = "f139-nci04-i1849-fake"
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "ADMITTED_ISSUE_SOURCE_IDENTITY"):
            self.inspect()

    def test_second_issue_read_changed_rejected(self):
        self.second_issue = deepcopy(self.routes[self.issue_route])
        self.second_issue["id"] += 1
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "ISSUE_CHANGED_DURING_READ"):
            self.inspect()

    def test_second_ref_read_changed_rejected(self):
        self.second_ref = deepcopy(self.routes[self.ref_route])
        self.second_ref["commit"]["sha"] = "a" * 40
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "WORKER_REF"):
            self.inspect()

    def test_synthetic_approval_or_pre_cutover_issue_denied_without_get(self):
        for key, value in (
            ("worker_dispatch_authorized", True),
            ("scientific_first_use", True),
            ("model_continuation_authorized", True),
            ("paid_model_calls", 1),
            ("remote_issue_number_floor", TICKET_ISSUE),
        ):
            with self.subTest(field=key):
                baseline = self.activation[key]
                self.activation[key] = value
                with self.assertRaises(FreshWorkerReleaseDenied):
                    self.inspect()
                self.assertEqual(self.calls, [])
                self.activation[key] = baseline

    def test_intake_claims_dispatch_rejected_without_get(self):
        self.intake["worker_dispatch_authorized"] = True
        with self.assertRaisesRegex(
                FreshWorkerReleaseDenied, "FRESH_READY_TICKET_INVALID"):
            self.inspect()
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
