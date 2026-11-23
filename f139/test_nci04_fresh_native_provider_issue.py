"""Synthetic read-only fresh provider issue preflight negative controls.

No real Windows owner, task, SQLite cutover, GitHub write or model first use.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json
import unittest

from f139.nci04_native_contract import (
    SCHEMA as INTENT_SCHEMA, canonical, digest,
)
from f139.nci04_owner_issue import (
    SCHEMA as ISSUE_SCHEMA, LABEL,
)
from f139.nci04_fresh_native_activation import ACTIVATION_SCHEMA
from f139.nci04_fresh_remote_floor import SCHEMA as FLOOR_SCHEMA
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSION_SCHEMA
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED, ACCEPTED_NATIVE_PATH, ACCEPTED_NATIVE_BLOB, AMALGAM_HEAD,
    AMALGAM_PR, LINEAGE_HEAD, LINEAGE_PR, LINEAGE_RECEIPT_BLOB,
    RECEIPT_SCHEMA as YGG_SCHEMA,
)
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.nci04_fresh_native_provider_issue import (
    FORGE, YGG, API, SCHEMA, FreshProviderIssueDenied,
    inspect_fresh_provider_issue,
)

TARGET = "d" * 40
TREE = "c" * 40
ISSUE = 3001
FLOOR = 3000
CANDIDATE = b"native causal code development only\n"


class FreshProviderPreflightTests(unittest.TestCase):
    def setUp(self):
        self.consumed = {
            "schema": EXCLUSION_SCHEMA,
            "source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "old_issue_numbers": [1715],
            "old_issue_ids": [71815],
            "old_tickets": ["f139-old-ticket"],
            "old_native_candidate_identities": [],
            "old_source_after_sha256": ["9" * 64],
            "previous_work_replay_authorized": False,
            "fresh_activation_authorized": False,
            "release_qualified": False,
        }
        self.boundary = {
            "schema": YGG_SCHEMA,
            "repository": "spoonman136668-ai/Yggdrasil",
            "accepted_main_source_sha": ACCEPTED,
            "accepted_native_path": ACCEPTED_NATIVE_PATH,
            "accepted_native_blob_sha": ACCEPTED_NATIVE_BLOB,
            "amalgam_pr": AMALGAM_PR,
            "amalgam_draft_head_sha": AMALGAM_HEAD,
            "lineage_pr": LINEAGE_PR,
            "lineage_draft_head_sha": LINEAGE_HEAD,
            "lineage_archived_receipt_blob_sha": LINEAGE_RECEIPT_BLOB,
            "lineage_archived_receipt_sha256": "8" * 64,
            "checkpoint_kind": "DRAFT_EXPERIMENTAL_ONLY",
            "official_cumulative_owner_checkpoint": "UNVERIFIED",
            "development_source_only": True,
            "new_canonical_learner": False,
            "checkpoint_imported": False,
            "model_continuation_authorized": False,
            "scientific_first_use": False,
            "new_training_actions": 0,
            "release_qualified": False,
            "owner_task_rebind_authorized": False,
            "worker_dispatched": False,
        }
        self.floor = {
            "schema": FLOOR_SCHEMA,
            "target_forge_source_sha": TARGET,
            "original_source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "remote_cutover_issue_number_floor": FLOOR,
            "remote_cutover_issue_created_at": "2026-11-19T18:00:00Z",
            "remote_cutover_issue_provider_verified": True,
            "fresh_activation_authorized": False,
            "issue_admission_authorized": False,
            "worker_dispatch_authorized": False,
            "consumed_exclusions_sha256": digest(canonical(self.consumed)),
        }
        self.activation = {
            "schema": ACTIVATION_SCHEMA,
            "source_sha": TARGET,
            "original_source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "development_only": True,
            "scientific_first_use": False,
            "paid_model_calls": 0,
            "worker_dispatch_authorized": False,
            "model_continuation_authorized": False,
            "remote_issue_number_floor": FLOOR,
            "remote_cutover_receipt_sha256": digest(canonical(self.floor)),
            "consumed_exclusions_sha256": digest(canonical(self.consumed)),
            "yggdrasil_research_boundary_sha256": digest(canonical(self.boundary)),
        }
        candidate = {
            "schema": INTENT_SCHEMA,
            "controller_source_sha": TARGET,
            "lane": "Yggdrasil",
            "target_repository": "spoonman136668-ai/Yggdrasil",
            "target_commit": ACCEPTED,
            "target_tree_sha": TREE,
            "dependency_sha256": "1" * 64,
            "qualification_harness_sha256": "2" * 64,
            "training_config_sha256": "3" * 64,
            "suite_identity_sha256": "4" * 64,
            "toolchain_identity": "python3.11.11",
            "path": ACCEPTED_NATIVE_PATH,
            "before_sha256": "5" * 64,
            "after_sha256": digest(CANDIDATE),
            "after_base64": base64.b64encode(CANDIDATE).decode("ascii"),
            "worker_mode": "isolated-candidate-only",
            "scientific_first_use": False,
            "paid_api_calls": 0,
            "accepted_ref_mutations": 0,
            "optimizer_policy_mutations": 0,
            "protected_holdouts_accessed": 0,
        }
        self.intent = candidate
        self.issue_body = {
            "schema": ISSUE_SCHEMA,
            "source_sha": TARGET,
            "lane": "Yggdrasil",
            "kind": "native-cognitive-candidate",
            "intent_base64": base64.b64encode(canonical(candidate)).decode("ascii"),
            "scientific_first_use": False,
            "paid_model_calls": 0,
        }
        self.issue = {
            "number": ISSUE,
            "id": 913001,
            "url": API + "/issues/" + str(ISSUE),
            "repository_url": API,
            "created_at": "2026-11-19T18:01:00Z",
            "state": "open",
            "user": {"login": "spoonman136668-ai"},
            "author_association": "OWNER",
            "labels": [{"name": LABEL}],
            "body": json.dumps(self.issue_body, sort_keys=True),
        }
        self.routes = {
            FORGE + "/branches/main": {
                "name": "main", "protected": True, "commit": {"sha": TARGET}},
            YGG + "/branches/main": {
                "name": "main", "protected": True, "commit": {"sha": ACCEPTED}},
            YGG + "/git/commits/" + ACCEPTED: {
                "sha": ACCEPTED, "tree": {"sha": TREE}},
            FORGE + "/issues/" + str(ISSUE): self.issue,
        }
        self.calls = []
        self.second_issue = None

    def get(self, path):
        self.assertIn(path, self.routes)
        self.calls.append(path)
        if (self.second_issue is not None
                and path == FORGE + "/issues/" + str(ISSUE)
                and self.calls.count(path) == 2):
            return deepcopy(self.second_issue)
        return deepcopy(self.routes[path])

    def inspect(self):
        return inspect_fresh_provider_issue(
            activation=self.activation, remote_floor=self.floor,
            consumed=self.consumed, yggdrasil_boundary=self.boundary,
            issue_number=ISSUE, get=self.get)

    def bind(self):
        self.floor["consumed_exclusions_sha256"] = digest(canonical(self.consumed))
        self.activation["consumed_exclusions_sha256"] = digest(canonical(self.consumed))
        self.activation["remote_cutover_receipt_sha256"] = digest(canonical(self.floor))
        self.activation["yggdrasil_research_boundary_sha256"] = (
            digest(canonical(self.boundary)))

    def update_issue_body(self):
        self.issue["body"] = json.dumps(self.issue_body, sort_keys=True)

    def test_provider_candidate_preflight_is_inert_and_rechecks_all(self):
        out = self.inspect()
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["issue_number"], ISSUE)
        self.assertEqual(out["accepted_yggdrasil_source_sha"], ACCEPTED)
        self.assertEqual(out["accepted_yggdrasil_tree_sha"], TREE)
        self.assertTrue(out["issue_provider_readback_twice"])
        self.assertEqual(self.calls.count(FORGE + "/branches/main"), 2)
        self.assertEqual(self.calls.count(YGG + "/branches/main"), 2)
        self.assertEqual(self.calls.count(FORGE + "/issues/" + str(ISSUE)), 2)
        for key in ("issue_admission_authorized", "worker_dispatch_authorized",
                    "owner_task_rebind_authorized", "scientific_first_use",
                    "model_continuation_authorized"):
            self.assertIs(out[key], False, key)

    def test_pre_cutover_issue_rejected_before_remote_read(self):
        with self.assertRaisesRegex(FreshProviderIssueDenied, "OLD_OR_PRE_CUTOVER"):
            inspect_fresh_provider_issue(
                activation=self.activation, remote_floor=self.floor,
                consumed=self.consumed, yggdrasil_boundary=self.boundary,
                issue_number=FLOOR, get=self.get)
        self.assertEqual(self.calls, [])

    def test_missing_or_modified_receipts_fail_closed(self):
        for field, value in (
            ("source_sha", "9" * 40),
            ("worker_dispatch_authorized", True),
            ("scientific_first_use", True),
            ("paid_model_calls", 1),
            ("remote_issue_number_floor", FLOOR - 1),
        ):
            with self.subTest(field=field):
                self.activation[field] = value
                with self.assertRaises(FreshProviderIssueDenied):
                    self.inspect()
                self.activation[field] = {
                    "source_sha": TARGET, "worker_dispatch_authorized": False,
                    "scientific_first_use": False, "paid_model_calls": 0,
                    "remote_issue_number_floor": FLOOR,
                }[field]
        self.consumed["old_issue_ids"].append(913001)
        with self.assertRaises(FreshProviderIssueDenied):
            self.inspect()
        self.bind()
        with self.assertRaisesRegex(ValueError, "OLD_WORK"):
            self.inspect()

    def test_provider_branch_or_target_tree_drift_rejected(self):
        for path, mutate in (
            (FORGE + "/branches/main", lambda r: r["commit"].update(sha="0"*40)),
            (YGG + "/branches/main", lambda r: r["commit"].update(sha="0"*40)),
            (YGG + "/git/commits/" + ACCEPTED,
             lambda r: r["tree"].update(sha="0"*40)),
        ):
            with self.subTest(path=path):
                original = deepcopy(self.routes[path])
                mutate(self.routes[path])
                with self.assertRaises(ValueError):
                    self.inspect()
                self.routes[path] = original

    def test_issue_edit_during_two_reads_rejected(self):
        self.second_issue = deepcopy(self.issue)
        self.second_issue["labels"] = []
        with self.assertRaisesRegex(FreshProviderIssueDenied, "ISSUE_CHANGED"):
            self.inspect()

    def test_issue_wrong_repository_identity_rejected(self):
        self.issue["repository_url"] = "https://api.github.com/repos/foreign/x"
        with self.assertRaisesRegex(FreshProviderIssueDenied, "ISSUE_PROVIDER_IDENTITY"):
            self.inspect()

    def test_issue_wrong_lane_label_or_target_rejected(self):
        self.issue["labels"] = [{"name": "f139-development-eligible"}]
        with self.assertRaises(ValueError):
            self.inspect()
        self.issue["labels"] = [{"name": LABEL}]
        self.intent["target_commit"] = AMALGAM_HEAD
        self.issue_body["intent_base64"] = (
            base64.b64encode(canonical(self.intent)).decode("ascii"))
        self.update_issue_body()
        with self.assertRaises(ValueError):
            self.inspect()

    def test_no_replay_of_original_candidate_after_hash(self):
        self.consumed["old_source_after_sha256"] = [digest(CANDIDATE)]
        self.bind()
        with self.assertRaisesRegex(ValueError, "OLD_WORK"):
            self.inspect()

    def test_new_issue_timestamp_before_cutover_rejected(self):
        self.issue["created_at"] = "2026-11-19T17:59:59Z"
        with self.assertRaisesRegex(FreshProviderIssueDenied, "ISSUE_CREATION"):
            self.inspect()

    def test_absent_provider_read_never_means_no_candidates(self):
        del self.routes[FORGE + "/issues/" + str(ISSUE)]
        with self.assertRaises(AssertionError):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
