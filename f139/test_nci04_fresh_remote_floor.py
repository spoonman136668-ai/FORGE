"""Synthetic original-owner, provider metadata and replay-floor negatives.

No Windows task or GitHub request is executed by these tests. The original
V59 audit is substituted with exact synthetic pinned head fields, while the
real standard F139 empty-database integrity checker still runs.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSION_SCHEMA
from f139.nci04_fresh_remote_floor import (
    API, ISSUE_PAGE, ROOT, SCHEMA,
    FreshRemoteCutoverDenied, prove_fresh_native_issue_cutover_floor,
)

TARGET = "f408e7f6c27acc259279b923b9c9eed138bb2d8c"


class FreshCutoverFloorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="f139-remote-floor-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "FORGE-F139"
        root.mkdir()
        filename = root / "state.sqlite"
        database = Database.initialize(filename, SOURCE)
        database.close()
        self.old = Database.open_readonly(filename)
        self.addCleanup(self.old.close)
        self.original = {
            "source_sha": SOURCE, "head_seq": HEAD_SEQ,
            "head_sha256": HEAD_SHA256,
        }
        self.exclusions = {
            "schema": EXCLUSION_SCHEMA,
            "source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "old_issue_numbers": [687, 1715],
            "release_qualified": False,
            "fresh_activation_authorized": False,
            "previous_work_replay_authorized": False,
            "scientific_first_use": False,
            "owner_task_mutations": 0,
        }
        self.policy = {
            "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
            "enabled": True,
            "source_sha": SOURCE,
            "title_prefix": "F139 autonomy DEV:",
            "lanes": ["Wingless", "Yggdrasil", "TTT-Hybrid"],
            "max_issue_creations_per_cycle": 2,
            "require_owner_authored_pr": True,
            "require_single_head_commit_delta": True,
            "require_single_allowed_source_file": True,
            "scientific_first_use": False,
            "paid_model_calls": 0,
            "accepted_ref_mutations": 0,
            "new_controller": False,
            "new_scheduler": False,
            "new_queue": False,
        }
        self.issue = {
            "number": 1833, "id": 6500191198,
            "created_at": "2026-11-19T22:18:06Z",
            "repository_url": API,
            "url": API + "/issues/1833",
        }
        self.branch = {
            "name": "main", "protected": True,
            "commit": {"sha": TARGET},
        }
        self.read_calls = []
        self.reads = 0
        self.mutator = None
        self.task_quiesced = lambda: True
        self.auditor = patch(
            "f139.nci04_fresh_remote_floor.audit_frozen_original_readonly",
            return_value=self.original)
        self.mutex = patch.object(SingleOwner, "held", return_value=True)
        self.auditor.start()
        self.mutex.start()
        self.addCleanup(self.auditor.stop)
        self.addCleanup(self.mutex.stop)

    def get(self, route):
        self.read_calls.append(route)
        if route == ROOT + "/branches/main":
            return self.branch
        if route == ROOT + "/issues/807":
            return {
                "number": 807, "state": "open",
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER",
                "body": json.dumps(self.policy),
            }
        if route == ISSUE_PAGE:
            self.reads += 1
            if self.mutator is not None and self.reads > 1:
                return [self.mutator]
            return [self.issue]
        if route == ROOT + "/issues/" + str(self.issue["number"]):
            return self.issue
        raise AssertionError("Unexpected provider read: " + route)

    def prove(self, **kwargs):
        inputs = {
            "target_source_sha": TARGET,
            "consumed_exclusions": self.exclusions,
            "get": self.get,
            "original_task_quiesced": self.task_quiesced,
        }
        inputs.update(kwargs)
        return prove_fresh_native_issue_cutover_floor(self.old, **inputs)

    def assert_prewrite_failure(self, reason, **kwargs):
        with self.assertRaisesRegex(FreshRemoteCutoverDenied, reason):
            self.prove(**kwargs)
        self.assertEqual(self.old.conn.total_changes, 0)
        self.assertEqual(self.old.meta()["head_seq"], 0)

    def test_bounded_authenticated_cutoff_is_negative_only(self):
        before = self.old.meta()
        proof = self.prove()
        self.assertEqual(proof["schema"], SCHEMA)
        self.assertEqual(proof["remote_cutover_issue_number_floor"], 1833)
        self.assertEqual(proof["remote_cutover_issue_id"], 6500191198)
        self.assertTrue(proof["remote_cutover_issue_provider_verified"])
        self.assertTrue(proof["original_owner_preimage_verified"])
        self.assertFalse(proof["task_sid_and_process_independently_qualified"])
        for field in (
            "release_qualified", "fresh_activation_authorized",
            "owner_task_rebind_authorized", "issue_admission_authorized",
            "worker_dispatch_authorized", "new_controller",
            "new_scheduler", "new_queue", "scientific_first_use",
        ):
            self.assertIs(proof[field], False, field)
        self.assertEqual(proof["paid_model_calls"], 0)
        self.assertEqual(proof["original_head_seq"], HEAD_SEQ)
        self.assertEqual(self.old.meta(), before)
        self.assertEqual(self.read_calls.count(ISSUE_PAGE), 2)
        self.assertEqual(self.read_calls.count(ROOT + "/branches/main"), 2)
        self.assertIn(ROOT + "/issues/1833", self.read_calls)
        self.assertEqual(proof, json.loads(canonical(proof)))

    def test_original_mutex_and_quiescence_required(self):
        with patch.object(SingleOwner, "held", return_value=False):
            self.assert_prewrite_failure("ORIGINAL_READONLY_MUTEX_REQUIRED")
        self.assert_prewrite_failure(
            "ORIGINAL_OWNER_QUIESCENCE_REQUIRED",
            original_task_quiesced=lambda: False)
        self.assert_prewrite_failure(
            "ORIGINAL_OWNER_QUIESCENCE_REQUIRED",
            original_task_quiesced=None)

    def test_task_resume_during_proof_rejected(self):
        count = [0]
        def witness():
            count[0] += 1
            return count[0] == 1
        self.assert_prewrite_failure(
            "OWNER_TASK_ORIGINAL_PREIMAGE_MOVED",
            original_task_quiesced=witness)

    def test_invalid_exclusions_and_old_history_rejected(self):
        for key, bad in (
            ("original_head_seq", HEAD_SEQ - 1),
            ("source_sha", "a" * 40),
            ("previous_work_replay_authorized", True),
            ("fresh_activation_authorized", True),
            ("owner_task_mutations", 1),
            ("old_issue_numbers", [1715, 1715]),
        ):
            with self.subTest(key=key):
                self.assert_prewrite_failure(
                    "ORIGINAL_EXCLUSION_PREIMAGE_INVALID",
                    consumed_exclusions={**self.exclusions, key: bad})

    def test_original_head_changed_rejected(self):
        with patch(
            "f139.nci04_fresh_remote_floor.audit_frozen_original_readonly",
            return_value={**self.original, "head_seq": HEAD_SEQ - 1}):
            self.assert_prewrite_failure("ORIGINAL_EVENT_HEAD_DRIFT")

    def test_main_and_original_owner_policy_fail_closed(self):
        self.branch["commit"]["sha"] = "a" * 40
        self.assert_prewrite_failure("PROTECTED_MAIN_SOURCE_DRIFT")
        self.branch["commit"]["sha"] = TARGET
        self.policy["source_sha"] = TARGET
        self.assert_prewrite_failure("ORIGINAL_OWNER_POLICY_INVALID")
        self.policy["source_sha"] = SOURCE
        self.policy["new_controller"] = True
        self.assert_prewrite_failure("ORIGINAL_OWNER_POLICY_INVALID")

    def test_latest_issue_repository_identity_and_number(self):
        for key, bad in (
            ("repository_url", "https://example.invalid/unsafe"),
            ("number", True),
            ("created_at", "yesterday"),
            ("id", 0),
        ):
            with self.subTest(key=key):
                original = self.issue
                self.issue = {**original, key: bad}
                try:
                    self.assert_prewrite_failure(
                        "NEWEST_ISSUE_PROVIDER_IDENTITY_INVALID")
                finally:
                    self.issue = original

    def test_issue_floor_must_cover_old_consumed_work(self):
        old = self.issue
        self.issue = {
            **old, "number": 1000,
            "url": API + "/issues/1000",
        }
        self.assert_prewrite_failure("ISSUE_HIGH_WATER_BEHIND_CONSUMED")
        self.issue = old

    def test_issue_index_detail_and_second_read_consistent(self):
        with patch.object(self, "get", wraps=self.get) as read:
            original = self.issue
            # The direct item lookup is a provider identity independent of
            # index values even if the sorted page remains apparently fixed.
            def changed_detail(route):
                item = self.get(route)
                if route == ROOT + "/issues/1833":
                    return {**item, "id": item["id"] + 1}
                return item
            self.assert_prewrite_failure(
                "ISSUE_DETAIL_RACE_OR_IDENTITY_DRIFT",
                get=changed_detail)
            self.issue = original
        self.mutator = {**self.issue, "id": self.issue["id"] + 1}
        self.assert_prewrite_failure(
            "ISSUE_CATALOG_MOVED_DURING_CUTOVER_READ")

    def test_untrusted_target_source_denied_before_provider_reads(self):
        self.assert_prewrite_failure(
            "TARGET_SOURCE_INVALID", target_source_sha=SOURCE)
        self.assert_prewrite_failure(
            "TARGET_SOURCE_INVALID", target_source_sha="not-a-sha")

    def test_no_implicit_authorization_of_new_issue(self):
        proof = self.prove()
        self.assertGreater(proof["remote_cutover_issue_number_floor"], 1715)
        self.assertFalse(proof["issue_admission_authorized"])
        self.assertFalse(proof["fresh_activation_authorized"])
        self.assertFalse(proof["owner_task_rebind_authorized"])


if __name__ == "__main__":
    unittest.main()
