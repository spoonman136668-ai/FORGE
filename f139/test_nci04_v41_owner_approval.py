"""Pure, synthetic adversarial V41 owner intent tests, no actual owner access."""
import copy
import json
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v41_owner_approval as v41

ORIGINAL = v41.source.OWNER_SOURCE
TARGET = "51389291ac77e5caaa0e3a20eacaef80261d49f8"
TREE = "7b52324e0d841c4c04c825ab262479fab9f409e1"
HEAD = v41.source.OBSERVED_HEAD
COMMENT_ID = 6822229999


def owner_issue_body():
    return {
        "schema": "forge.f139.nci04.owner-native-development.v1",
        "source_sha": ORIGINAL, "lane": "Yggdrasil",
        "kind": "native-cognitive-candidate",
        "intent_base64": "YQ==",
        "scientific_first_use": False, "paid_model_calls": 0,
    }


def cold_receipt():
    return {
        "schema": "forge.f139.v41.original-owner-cold-copy-readonly.v1",
        "source_sha": ORIGINAL, "candidate_sha": TARGET,
        "original_head_seq": 1826, "original_head_sha256": HEAD,
        "backup_sha256": "a"*64,
        "verified_isolated_snapshot_sha256": "a"*64,
        "logical_all_tables_sha256": "b"*64,
        "provider_archives_manifest_sha256": "c"*64,
        "generation_binary_manifest_sha256": "d"*64,
        "preserved_verified_tasks": 153, "preserved_quarantined_tasks": 56,
        "original_owner_mutations": 0, "source_transition_authorized": False,
        "new_dispatches": 0, "scientific_first_use": False,
        "hybrid_admission": False,
    }


def pending_receipt():
    return {
        "schema": v41.pending.SCHEMA, "source_sha": ORIGINAL,
        "original_head_seq": 1826, "original_head_sha256": HEAD,
        "issue_number": 1715, "issue_id": 6333201763,
        "ticket": "f139-nci04-i1715-" + ORIGINAL[:12] + "-ffffffff",
        "issue_body_sha256": digest(canonical(owner_issue_body())), "native_intent_sha256": "f"*64,
        "target_commit": "1"*40, "target_tree_sha": "2"*40,
        "semantic_identity_sha256": "3"*64,
        "disposition": "UNADMITTED_RETAINED_NO_DISPATCH",
        "source_transition_authorized": False, "reissue_authorized": False,
        "new_dispatches": 0, "owner_mutations": 0,
        "scientific_first_use": False,
    }


def approved_doc(cold, pending):
    return {
        "schema": v41.SCHEMA, "owner_comment_id": COMMENT_ID,
        "from_source_sha": ORIGINAL, "to_source_sha": TARGET,
        "to_source_tree_sha": TREE,
        "original_head_seq": cold["original_head_seq"],
        "original_head_sha256": cold["original_head_sha256"],
        "cold_backup_sha256": cold["backup_sha256"],
        "logical_all_tables_sha256": cold["logical_all_tables_sha256"],
        "provider_archives_manifest_sha256":
            cold["provider_archives_manifest_sha256"],
        "generation_binary_manifest_sha256":
            cold["generation_binary_manifest_sha256"],
        "pending_issue_number": pending["issue_number"],
        "pending_issue_id": pending["issue_id"],
        "pending_ticket": pending["ticket"],
        "pending_semantic_identity_sha256":
            pending["semantic_identity_sha256"],
        "pending_disposition": "EXPLICIT_ESCROW_ONCE",
        "pending_disposition_receipt_sha256":
            v41.pending_disposition_intent_sha256(
                pending, TARGET, "EXPLICIT_ESCROW_ONCE"),
        "qualification_run_id": 43197218249,
        "qualification_artifact_id": 4567,
        "qualification_artifact_sha256": "5"*64,
        "original_task_definition_sha256": "6"*64,
        "original_owner_sid_sha256": "7"*64,
        "owner_source_transition": True,
        "owner_policy_source_update": True,
        "pause_resume_existing_task": True,
        "create_immutable_release_ref": True,
        "scientific_first_use": False, "hybrid_admission": False,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_model_calls": 0,
    }


class SourceOnlyApprovalTests(unittest.TestCase):
    def setUp(self):
        self.cold = cold_receipt()
        self.pending = pending_receipt()
        self.doc = approved_doc(self.cold, self.pending)
        self.counter = 0

    def provider(self, route):
        prefix = "repos/" + v41.REPO + "/"
        self.assertTrue(route.startswith(prefix))
        self.counter += 1
        if route == prefix + "branches/main":
            return {"protected": True, "commit": {"sha": TARGET}}
        if route == prefix + "git/commits/" + TARGET:
            return {"sha": TARGET, "tree": {"sha": TREE}}
        if route == prefix + "issues/807":
            return {
                "state": "open", "number": 807,
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER",
                "body": json.dumps({
                    "enabled": True, "source_sha": ORIGINAL,
                    "lanes": ["Wingless", "Yggdrasil"],
                    "scientific_first_use": False, "paid_model_calls": 0,
                }),
            }
        if route == prefix + "issues/1715":
            return {
                "id": 6333201763, "number": 1715, "state": "open",
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER",
                "labels": [{"name": "f139-native-development-eligible"}],
                "updated_at": "2026-11-12T10:11:00Z",
                "body": json.dumps(owner_issue_body()),
            }
        if route == prefix + "issues/comments/" + str(COMMENT_ID):
            return {
                "id": COMMENT_ID,
                "issue_url": "https://api.github.com/" + prefix + "issues/807",
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER",
                "updated_at": "2026-11-12T10:30:00Z",
                "body": v41.PREFIX + canonical(self.doc).decode("ascii"),
            }
        raise KeyError(route)

    def verify(self, provider=None):
        return v41.verify_owner_comment(
            self.provider if provider is None else provider,
            target=TARGET, cold=self.cold, pending_receipt=self.pending,
            comment_id=COMMENT_ID)

    def test_canonical_owner_comment_is_read_only_not_authority(self):
        result = self.verify()
        self.assertEqual(self.counter, 10)
        self.assertTrue(result["owner_comment_identity_verified"])
        self.assertFalse(result["source_transition_authorized"])
        self.assertFalse(result["reissue_authorized"])
        self.assertFalse(result["pending_disposition_implemented"])
        self.assertEqual(result["owner_mutations"], 0)
        self.assertEqual(result["new_dispatches"], 0)

    def test_original_head_and_pending_issue_must_agree(self):
        self.pending["original_head_sha256"] = "8"*64
        with self.assertRaisesRegex(v41.V41ApprovalDenied, "PENDING_1715_CUSTODY_DRIFT"):
            self.verify()
        self.pending = pending_receipt()
        self.pending["issue_number"] = 1714
        with self.assertRaisesRegex(v41.V41ApprovalDenied, "PENDING_1715_CUSTODY_DRIFT"):
            self.verify()
        self.pending = pending_receipt()
        self.pending["disposition"] = "ADMITTED"
        with self.assertRaises(v41.V41ApprovalDenied):
            self.verify()

    def test_cold_hash_and_custody_changes_are_rejected(self):
        self.cold["verified_isolated_snapshot_sha256"] = "9"*64
        with self.assertRaisesRegex(v41.V41ApprovalDenied, "COLD_CUSTODY_DRIFT"):
            self.verify()
        self.cold = cold_receipt()
        self.cold["original_owner_mutations"] = 1
        with self.assertRaises(v41.V41ApprovalDenied):
            self.verify()
        self.cold = cold_receipt()
        self.cold["extra_authority"] = True
        with self.assertRaises(v41.V41ApprovalDenied):
            self.verify()

    def test_uncanonical_or_wrong_scope_owner_comment_denied(self):
        self.doc["hybrid_admission"] = True
        with self.assertRaisesRegex(v41.V41ApprovalDenied, "SCOPE_SOURCE_OR_CUSTODY_DRIFT"):
            self.verify()
        self.doc = approved_doc(self.cold, self.pending)
        self.doc["pending_disposition"] = "REPLAY_1715"
        with self.assertRaises(v41.V41ApprovalDenied):
            self.verify()
        self.doc = approved_doc(self.cold, self.pending)
        self.doc["qualification_artifact_sha256"] = "0"*64
        with self.assertRaises(v41.V41ApprovalDenied):
            self.verify()

    def test_disposition_hash_binds_frozen_pending_intent_and_target(self):
        expected = v41.pending_disposition_intent_sha256(
            self.pending, TARGET, "EXPLICIT_ESCROW_ONCE")
        self.assertEqual(self.doc["pending_disposition_receipt_sha256"],
                         expected)
        self.doc["pending_disposition_receipt_sha256"] = "4" * 64
        with self.assertRaisesRegex(
                v41.V41ApprovalDenied, "DISPOSITION_INTENT_HASH_DRIFT"):
            self.verify()

    def test_new_disposition_requires_new_bound_intent_fingerprint(self):
        self.doc["pending_disposition"] = "EXPLICIT_QUARANTINE_ONCE"
        with self.assertRaisesRegex(
                v41.V41ApprovalDenied, "DISPOSITION_INTENT_HASH_DRIFT"):
            self.verify()
        self.doc["pending_disposition_receipt_sha256"] = (
            v41.pending_disposition_intent_sha256(
                self.pending, TARGET, "EXPLICIT_QUARANTINE_ONCE"))
        # The read-only owner intent verifier supports both decisions;
        # the separate V41 source transition permits escrow only.
        self.assertTrue(self.verify()["owner_comment_identity_verified"])

    def test_disposition_hash_rejects_unqualified_inputs(self):
        with self.assertRaisesRegex(
                v41.V41ApprovalDenied, "DISPOSITION_INTENT_INPUT_INVALID"):
            v41.pending_disposition_intent_sha256(
                dict(self.pending, issue_number=1714, extra="injected"),
                TARGET, "EXPLICIT_ESCROW_ONCE")
        with self.assertRaisesRegex(
                v41.V41ApprovalDenied, "DISPOSITION_INTENT_INPUT_INVALID"):
            v41.pending_disposition_intent_sha256(
                self.pending, TARGET, "REPLAY_1715")
        self.assertNotEqual(
            v41.pending_disposition_intent_sha256(
                self.pending, TARGET, "EXPLICIT_ESCROW_ONCE"),
            v41.pending_disposition_intent_sha256(
                self.pending, "f" * 40, "EXPLICIT_ESCROW_ONCE"))

    def test_comment_exact_canonical_encoding_required(self):
        original = self.provider
        def pretty(route):
            doc = original(route)
            if route.endswith("/" + str(COMMENT_ID)):
                doc["body"] = v41.PREFIX + json.dumps(self.doc, indent=2)
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "EXACT_FIELDS_OR_CANONICAL_BYTES"):
            self.verify(pretty)
        self.doc["unknown"] = True
        with self.assertRaises(v41.V41ApprovalDenied):
            self.verify()

    def test_forged_approval_author_and_policy_denied(self):
        original = self.provider
        def wrong_user(route):
            doc = original(route)
            if route.endswith("/" + str(COMMENT_ID)):
                doc["user"] = {"login": "other"}
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "OWNER_COMMENT_IDENTITY_DRIFT"):
            self.verify(wrong_user)
        def wrong_policy(route):
            doc = original(route)
            if route.endswith("/issues/807"):
                body = json.loads(doc["body"])
                body["source_sha"] = TARGET
                doc["body"] = json.dumps(body)
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "ORIGINAL_V40_POLICY_DRIFT"):
            self.verify(wrong_policy)

    def test_wrong_tree_or_main_not_protected_denied(self):
        original = self.provider
        def wrong_tree(route):
            doc = original(route)
            if "/git/commits/" in route:
                doc["tree"]["sha"] = "f"*40
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "SCOPE_SOURCE_OR_CUSTODY_DRIFT"):
            self.verify(wrong_tree)
        def unprotected(route):
            doc = original(route)
            if route.endswith("/branches/main"):
                doc["protected"] = False
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "PROTECTED_MAIN_DRIFT"):
            self.verify(unprotected)

    def test_pending_issue_mutation_or_relabel_denied(self):
        original = self.provider
        def mutated(route):
            doc = original(route)
            if route.endswith("/issues/1715"):
                value = json.loads(doc["body"])
                value["source_sha"] = TARGET
                doc["body"] = json.dumps(value)
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "PENDING_1715_BODY_CHANGED"):
            self.verify(mutated)
        def relabeled(route):
            doc = original(route)
            if route.endswith("/issues/1715"):
                doc["labels"] = []
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "PENDING_1715_REMOTE_IDENTITY_DRIFT"):
            self.verify(relabeled)

    def test_get_only_double_read_detects_pending_edit(self):
        original = self.provider
        state = {"n": 0}
        def changed(route):
            doc = original(route)
            if route.endswith("/issues/1715"):
                state["n"] += 1
                if state["n"] == 2:
                    doc["updated_at"] = "2026-11-12T10:12:00Z"
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "CHANGED_DURING_DOUBLE_READ"):
            self.verify(changed)

    def test_get_only_double_read_detects_comment_edit(self):
        original = self.provider
        state = {"n": 0}
        def edited(route):
            doc = original(route)
            if route.endswith("/" + str(COMMENT_ID)):
                state["n"] += 1
                if state["n"] == 2:
                    doc["updated_at"] = "2026-11-12T10:32:00Z"
            return doc
        with self.assertRaisesRegex(v41.V41ApprovalDenied,
                                    "CHANGED_DURING_DOUBLE_READ"):
            self.verify(edited)

    def test_no_owner_or_dispatch_control_surface(self):
        import inspect
        code = inspect.getsource(v41)
        for forbidden in ("workflow_dispatch(", "create_ref(", "db.event(",
                          "db.transition_source(", "Start-ScheduledTask",
                          "Disable-ScheduledTask", ".post(", "git push"):
            self.assertNotIn(forbidden, code)
        self.assertNotIn("owner_source_transition\": True,", code)


if __name__ == "__main__":
    unittest.main()
