"""Synthetic, non-authorizing V41 release preflight source/negative controls.

The offline restore is mocked ONLY for the cross-verifier receipt join. Real
SQLite restore and cold negative ZIP tests remain in their existing modules.
No original owner, release branch, comment or live source is created.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v41_guarded_release_preflight as release
from f139 import nci04_v41_offline_cold_bundle as offline
from f139 import nci04_v41_owner_approval as approval
from f139.test_nci04_v41_owner_approval import (
    SourceOnlyApprovalTests, TARGET, COMMENT_ID)


PR_NUMBER = 1744
RUN_ID = 43396349980
CHECKS = (
    ("FORGE public Linux and Windows qualification", 43407362723),
    ("FORGE F73 protected-main cryptographic origin (no science permission)",
     43407362762),
)


class V41ReleaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / ("f139-v41-before-" + str(RUN_ID))
        self.folder.mkdir()
        self.v41 = SourceOnlyApprovalTests(
            "test_canonical_owner_comment_is_read_only_not_authority")
        self.v41.setUp()
        self.cold = copy.deepcopy(self.v41.cold)
        self.pending = copy.deepcopy(self.v41.pending)
        self.doc = copy.deepcopy(self.v41.doc)
        self.fixture_manifest = {
            "schema": offline.SCHEMA,
            "original_source_sha": release.source.FROM_V40,
            "target_source_sha": TARGET,
            "run_id": RUN_ID,
            "original_head_seq": self.cold["original_head_seq"],
            "original_head_sha256": self.cold["original_head_sha256"],
            "files_sha256": {
                "state.sqlite": self.cold["backup_sha256"]},
            "logical_all_tables_sha256":
                self.cold["logical_all_tables_sha256"],
            "provider_archives_manifest_sha256":
                self.cold["provider_archives_manifest_sha256"],
            "generation_binary_manifest_sha256":
                self.cold["generation_binary_manifest_sha256"],
        }
        self.seal_manifest()
        self.offline_receipt = {
            "schema": "forge.f139.v41.independent-offline-restore-readonly.v1",
            "original_source_sha": release.source.FROM_V40,
            "target_source_sha": TARGET,
            "original_head_seq": self.cold["original_head_seq"],
            "original_head_sha256": self.cold["original_head_sha256"],
            "manifest_sha256": self.seal,
            "independent_restore_verified": True,
            "release_qualified": False,
            "source_transition_authorized": False,
            "scientific_first_use": False,
            "hybrid_admission": False,
        }
        self.mutate = lambda k, x: x
        self.calls = []
        self.offline_calls = 0

    def seal_manifest(self):
        raw = canonical(self.fixture_manifest)
        (self.folder / "manifest.sha256.json").write_bytes(raw)
        self.seal = digest(raw)

    def provider(self, route):
        self.calls.append(route)
        prefix = "repos/" + release.REPO + "/"
        if route == prefix + "branches/f139-owner-release-" + TARGET:
            result = {"name": "f139-owner-release-" + TARGET,
                      "protected": True,
                      "commit": {"sha": TARGET}}
        elif route == prefix + "pulls/" + str(PR_NUMBER):
            result = {
                "number": PR_NUMBER, "merged": True, "state": "closed",
                "merge_commit_sha": TARGET, "base": {"ref": "main"},
                "user": {"login": release.OWNER},
                "head": {"sha": "f" * 40},
            }
        elif route == (prefix + "actions/runs?head_sha=" + TARGET
                       + "&event=push&branch=main&per_page=30"):
            result = {"workflow_runs": [
                {"name": name, "id": ident, "head_sha": TARGET,
                 "head_branch": "main", "event": "push",
                 "run_attempt": 1, "status": "completed",
                 "conclusion": "success",
                 "actor": {"login": release.OWNER}}
                for name, ident in CHECKS]}
        else:
            self.v41.doc = self.doc
            result = self.v41.provider(route)
        return self.mutate(route, copy.deepcopy(result))

    def run_gate(self, **overrides):
        values = {
            "get": self.provider, "bundle_root": self.folder,
            "target": TARGET, "release_pr": PR_NUMBER,
            "backup_run_id": RUN_ID,
            "sealed_manifest_sha256": self.seal,
            "original_head_seq": self.cold["original_head_seq"],
            "original_head_sha256": self.cold["original_head_sha256"],
            "cold_receipt": self.cold,
            "pending_receipt": self.pending,
            "owner_comment_id": COMMENT_ID,
        }
        values.update(overrides)
        def verifier(*args, **kwargs):
            self.offline_calls += 1
            self.assertEqual(kwargs["target"], TARGET)
            self.assertEqual(kwargs["expected_manifest_sha256"], self.seal)
            self.assertEqual(kwargs["run_id"], RUN_ID)
            return copy.deepcopy(self.offline_receipt)
        with patch.object(offline, "verify_sealed_bundle_offline",
                          side_effect=verifier):
            return release.qualify_inert_release_preflight(
                values.pop("get"), values.pop("bundle_root"), **values)

    def test_exact_source_and_owner_intent_readonly_preflight(self):
        raw = (self.folder / "manifest.sha256.json").read_bytes()
        result = self.run_gate()
        self.assertEqual(result["source_sha"], TARGET)
        self.assertEqual(result["original_head_seq"], self.cold["original_head_seq"])
        self.assertTrue(result["independent_restore_verified"])
        self.assertTrue(result["pending_1715_escrow_intent_verified"])
        self.assertTrue(result["candidate_inputs_readonly_qualified"])
        for name in (
                "original_owner_installed", "source_transition_authorized",
                "release_qualified", "scientific_first_use",
                "hybrid_admission"):
            self.assertFalse(result[name])
        self.assertEqual(result["remote_writes"], 0)
        self.assertEqual(result["new_dispatches"], 0)
        self.assertEqual(result["owner_mutations"], 0)
        self.assertEqual(result["exact_first_attempt_ci_runs"],
                         dict(CHECKS))
        self.assertEqual(self.offline_calls, 1)
        self.assertEqual(len(self.calls), 20)  # 5+double-read(5)+5
        self.assertTrue(all(x.startswith("repos/" + release.REPO + "/")
                            for x in self.calls))
        self.assertEqual((self.folder / "manifest.sha256.json").read_bytes(), raw)

    def test_missing_or_unprotected_immutable_release_ref_refuses(self):
        ref = "branches/f139-owner-release-" + TARGET
        for variant in ("missing", "unprotected", "wrong_target"):
            with self.subTest(variant=variant):
                def altered(route, value):
                    if route.endswith(ref):
                        if variant == "missing":
                            return {}
                        if variant == "unprotected":
                            value["protected"] = False
                        if variant == "wrong_target":
                            value["commit"]["sha"] = "e"*40
                    return value
                self.mutate = altered
                with self.assertRaisesRegex(
                        release.V41ReleasePreflightDenied,
                        "IMMUTABLE_RELEASE_REF_OR_MAIN_MISSING"):
                    self.run_gate()

    def test_qualifications_are_first_attempt_exact_sha_success(self):
        for variant in ("failed", "attempt2", "wrong_actor",
                        "wrong_sha", "duplicate", "missing"):
            with self.subTest(variant=variant):
                def altered(route, value):
                    if "/actions/runs?" in route:
                        rows = value["workflow_runs"]
                        if variant == "failed":
                            rows[0]["conclusion"] = "failure"
                        if variant == "attempt2":
                            rows[0]["run_attempt"] = 2
                        if variant == "wrong_actor":
                            rows[0]["actor"]["login"] = "random-person"
                        if variant == "wrong_sha":
                            rows[0]["head_sha"] = "e"*40
                        if variant == "duplicate":
                            rows.append(copy.deepcopy(rows[0]))
                        if variant == "missing":
                            rows.pop(0)
                    return value
                self.mutate = altered
                with self.assertRaisesRegex(
                        release.V41ReleasePreflightDenied,
                        "QUALIFIED_EXACT_SOURCE_FIRST_ATTEMPT_REQUIRED"):
                    self.run_gate()

    def test_wrong_merged_pr_and_protected_main_deny(self):
        for variant in ("wrong_pr", "not_merged", "wrong_tree",
                        "wrong_main", "foreign_author"):
            with self.subTest(variant=variant):
                def altered(route, value):
                    if route.endswith("/pulls/" + str(PR_NUMBER)):
                        if variant == "wrong_pr":
                            value["merge_commit_sha"] = "0"*40
                        if variant == "not_merged":
                            value["merged"] = False
                        if variant == "foreign_author":
                            value["user"]["login"] = "other"
                    if route.endswith("/branches/main") and variant == "wrong_main":
                        value["commit"]["sha"] = "e"*40
                    if route.endswith("/git/commits/" + TARGET) and variant == "wrong_tree":
                        value["tree"]["sha"] = "bad"
                    return value
                self.mutate = altered
                with self.assertRaises(release.V41ReleasePreflightDenied):
                    self.run_gate()

    def test_backup_receipt_and_seal_must_match_same_target(self):
        old = copy.deepcopy(self.fixture_manifest)
        for variant in ("wrong_target", "wrong_backup", "wrong_archive",
                        "wrong_head", "tampered_bytes"):
            with self.subTest(variant=variant):
                self.fixture_manifest = copy.deepcopy(old)
                self.seal_manifest()
                self.offline_receipt["manifest_sha256"] = self.seal
                if variant == "wrong_target":
                    self.fixture_manifest["target_source_sha"] = "1" * 40
                if variant == "wrong_backup":
                    self.fixture_manifest["files_sha256"]["state.sqlite"] = "1" * 64
                if variant == "wrong_archive":
                    self.fixture_manifest["provider_archives_manifest_sha256"] = "1"*64
                if variant == "wrong_head":
                    self.fixture_manifest["original_head_seq"] += 1
                if variant == "tampered_bytes":
                    (self.folder / "manifest.sha256.json").write_bytes(b"{}")
                else:
                    self.seal_manifest()
                    self.offline_receipt["manifest_sha256"] = self.seal
                with self.assertRaises(release.V41ReleasePreflightDenied):
                    self.run_gate()
        self.fixture_manifest = old

    def test_missing_owner_comment_or_remote_policy_drifts_denied(self):
        def bad_comment(route, value):
            if "/issues/comments/" in route:
                value["id"] = COMMENT_ID + 1
            return value
        self.mutate = bad_comment
        with self.assertRaises(approval.V41ApprovalDenied):
            self.run_gate()
        def bad_policy(route, value):
            if route.endswith("/issues/807"):
                body = json.loads(value["body"])
                body["source_sha"] = "e" * 40
                value["body"] = json.dumps(body)
            return value
        self.mutate = bad_policy
        with self.assertRaises(approval.V41ApprovalDenied):
            self.run_gate()

    def test_changed_remote_second_read_denied(self):
        hits = 0
        def mutate(route, value):
            nonlocal hits
            if route.endswith("/branches/f139-owner-release-" + TARGET):
                hits += 1
                if hits == 3:
                    value["protected"] = False
            return value
        self.mutate = mutate
        # Remote source is read once before, once after owner intent; a
        # changing immutable release ref must never be treated as accepted.
        with self.assertRaises(release.V41ReleasePreflightDenied):
            self.run_gate()
        self.assertGreaterEqual(hits, 2)

    def test_invalid_inputs_fail_before_any_remote_or_backup_read(self):
        with self.assertRaisesRegex(
                release.V41ReleasePreflightDenied,
                "EXACT_IDENTITY_INPUTS_REQUIRED"):
            self.run_gate(owner_comment_id=0)
        self.assertEqual(self.offline_calls, 0)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
