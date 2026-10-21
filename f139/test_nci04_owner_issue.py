"""F139 NCI04-A5 owner-native typed issue acceptance: no remote writes."""
from __future__ import annotations
import base64
import json
import unittest

from f139.nci04_native_contract import SCHEMA as INTENT_SCHEMA, canonical, digest
from f139.nci04_owner_issue import (
    inspect_owner_issue, make_signed_dispatch_inputs,
    NativeIssueDenied, SCHEMA, LABEL,
)
from f139.nci04_signed_native import admit_native_intent
from f139.verify_ticket import Untrusted

MAIN = "a" * 40
TARGET = "b" * 40
TREE = "c" * 40
SOURCE = b"package cognition\n\n// tested native proposal\n"
HMAC = "f139-nci04-owner-integration-test-only-012345678901234567"


def candidate(lane="Wingless"):
    return {
        "schema": INTENT_SCHEMA, "controller_source_sha": MAIN,
        "lane": lane, "target_repository": ("spoonman136668-ai/Wingless" if lane == "Wingless"
                                          else "spoonman136668-ai/Yggdrasil"),
        "target_commit": TARGET, "target_tree_sha": TREE,
        "dependency_sha256": "d" * 64, "qualification_harness_sha256": "e" * 64,
        "training_config_sha256": "f" * 64, "suite_identity_sha256": "1" * 64,
        "toolchain_identity": "go1.25.0" if lane == "Wingless" else "python3.11",
        "path": "cognition/native_state.go" if lane == "Wingless" else "yggdrasil/native_state.py",
        "before_sha256": digest(b""), "after_sha256": digest(SOURCE),
        "after_base64": base64.b64encode(SOURCE).decode("ascii"),
        "worker_mode": "isolated-candidate-only", "scientific_first_use": False,
        "paid_api_calls": 0, "accepted_ref_mutations": 0,
        "optimizer_policy_mutations": 0, "protected_holdouts_accessed": 0,
    }


def issue(lane="Wingless"):
    body = {
        "schema": SCHEMA, "source_sha": MAIN, "lane": lane,
        "kind": "native-cognitive-candidate",
        "intent_base64": base64.b64encode(canonical(candidate(lane))).decode(),
        "scientific_first_use": False, "paid_model_calls": 0,
    }
    return {
        "number": 702, "id": 5951234567, "state": "open",
        "user": {"login": "spoonman136668-ai"},
        "author_association": "OWNER",
        "labels": [{"name": LABEL}],
        "body": json.dumps(body, sort_keys=True),
    }


def inspect(raw, **kw):
    return inspect_owner_issue(
        raw, protected_main=kw.get("main", MAIN),
        authenticated_target_commit=kw.get("commit", TARGET),
        authenticated_target_tree=kw.get("tree", TREE),
    )


def verifier_inputs(work, signature):
    return {
        "key": HMAC, "ticket": work.ticket, "lane": work.lane,
        "source_sha": work.source_sha, "epoch": "1",
        "signature": signature, "repository": "spoonman136668-ai/FORGE",
        "ref": "refs/heads/main", "event": "workflow_dispatch",
        "head_sha": work.source_sha, "run_attempt": "1",
        "run_id": "39513290000", "os": "ubuntu-latest",
    }


class OwnerNativeIssueTests(unittest.TestCase):
    def test_both_lanes_issue_to_original_ticket_and_native_hmac(self):
        for lane in ("Wingless", "Yggdrasil"):
            with self.subTest(lane=lane):
                record = inspect(issue(lane))
                self.assertEqual(record.lane, lane)
                self.assertEqual(record.native_intent_sha256,
                                 record.candidate.intent_sha256)
                payload = make_signed_dispatch_inputs(record, owner_hmac_key=HMAC,
                                                      epoch=1)
                self.assertEqual(payload["ticket"], record.ticket)
                self.assertNotIn("key", payload)
                self.assertNotIn(HMAC, repr(payload))
                inp = verifier_inputs(record, payload["signature"])
                accepted = admit_native_intent(
                    inp, record.intent_raw,
                    native_signature=payload["native_signature"],
                    issue_number=payload["issue_number"],
                    issue_id=payload["issue_id"],
                    issue_body_sha256=payload["body_sha256"],
                    authenticated_main_sha=MAIN,
                    authenticated_target_commit=TARGET,
                    authenticated_target_tree=TREE)
                self.assertEqual(accepted.issue_number, 702)
                self.assertEqual(accepted.intent.qualification_key,
                                 payload["qualification_key"])

    def test_reject_nonowner_and_nonowner_affiliation(self):
        for field, value in (("state", "closed"), ("author_association", "CONTRIBUTOR"),
                             ("pull_request", {"url":"https://invalid"})):
            raw = issue()
            raw[field] = value
            with self.subTest(field=field), self.assertRaises(NativeIssueDenied):
                inspect(raw)
        raw = issue()
        raw["user"]["login"] = "untrusted"
        with self.assertRaises(NativeIssueDenied):
            inspect(raw)

    def test_separate_labels_legacy_d2k_not_upcast(self):
        raw = issue()
        raw["labels"] = [{"name": "f139-development-eligible"}]
        with self.assertRaisesRegex(NativeIssueDenied, "NATIVE_LABEL_MISSING"):
            inspect(raw)
        raw["labels"].append({"name": LABEL})
        with self.assertRaisesRegex(NativeIssueDenied, "LEGACY_MIXED"):
            inspect(raw)

    def test_source_and_native_tree_drift(self):
        with self.assertRaisesRegex(NativeIssueDenied, "ISSUE_NATIVE_SCHEMA_OR_AUTHORITY"):
            inspect(issue(), main="9" * 40)
        with self.assertRaisesRegex(ValueError, "TARGET_COMMIT_DRIFT"):
            inspect(issue(), commit="9" * 40)
        with self.assertRaisesRegex(ValueError, "TARGET_TREE_DRIFT"):
            inspect(issue(), tree="9" * 40)

    def test_fails_closed_on_native_issue_schema_and_science(self):
        for field, value in (
            ("kind", "go-package-test-diagnostic"), ("scientific_first_use", True),
            ("paid_model_calls", 1), ("paid_model_calls", False),
            ("lane", "Qualification"), ("source_sha", "9" * 40)):
            with self.subTest(field=field):
                raw = issue()
                body = json.loads(raw["body"])
                body[field] = value
                raw["body"] = json.dumps(body)
                with self.assertRaises(NativeIssueDenied):
                    inspect(raw)

    def test_cross_lane_and_native_byte_identity(self):
        raw = issue()
        body = json.loads(raw["body"])
        body["lane"] = "Yggdrasil"
        raw["body"] = json.dumps(body)
        with self.assertRaisesRegex(NativeIssueDenied, "INTENT_ISSUE_LANE_DRIFT"):
            inspect(raw)
        raw = issue()
        body = json.loads(raw["body"])
        forged = candidate()
        forged["after_sha256"] = "0" * 64
        body["intent_base64"] = base64.b64encode(canonical(forged)).decode()
        raw["body"] = json.dumps(body)
        with self.assertRaises(ValueError):
            inspect(raw)

    def test_no_freeform_fields_and_duplicate_keys(self):
        raw = issue()
        b = json.loads(raw["body"])
        b["shell"] = "bash anything"
        raw["body"] = json.dumps(b)
        with self.assertRaisesRegex(NativeIssueDenied, "SCHEMA_OR_AUTHORITY"):
            inspect(raw)
        raw = issue()
        raw["body"] = raw["body"].replace('"schema":', '"schema":"evil","schema":', 1)
        with self.assertRaises(NativeIssueDenied):
            inspect(raw)

    def test_reject_noncanonical_base64_and_oversized_issue(self):
        raw = issue()
        b = json.loads(raw["body"])
        for bad in ("!", "", "AAAA"):
            b["intent_base64"] = bad
            raw["body"] = json.dumps(b)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                inspect(raw)
        raw = issue()
        raw["body"] = " " * 60001
        with self.assertRaisesRegex(NativeIssueDenied, "BODY_SIZE_INVALID"):
            inspect(raw)

    def test_duplicate_issue_identity_or_unsafe_epoch_does_not_sign(self):
        record = inspect(issue())
        for n in (0, -1, 2**31, True):
            with self.subTest(epoch=n), self.assertRaisesRegex(NativeIssueDenied, "OWNER_EPOCH_INVALID"):
                make_signed_dispatch_inputs(record, owner_hmac_key=HMAC, epoch=n)
        with self.assertRaisesRegex(NativeIssueDenied, "OWNER_SECRET_MISSING"):
            make_signed_dispatch_inputs(record, owner_hmac_key="weak", epoch=1)

    def test_tamper_signed_issue_number_body_sha_or_signature(self):
        record = inspect(issue())
        fields = make_signed_dispatch_inputs(record, owner_hmac_key=HMAC, epoch=1)
        inp = verifier_inputs(record, fields["signature"])
        for k, altered in (("issue_number", "703"), ("issue_id", "5951234568"),
                           ("issue_body_sha256", "9" * 64)):
            params = dict(
                native_signature=fields["native_signature"],
                issue_number=fields["issue_number"],
                issue_id=fields["issue_id"],
                issue_body_sha256=fields["body_sha256"],
                authenticated_main_sha=MAIN,
                authenticated_target_commit=TARGET,
                authenticated_target_tree=TREE)
            params[k] = altered
            with self.subTest(k=k), self.assertRaises(Untrusted):
                admit_native_intent(inp, record.intent_raw, **params)


if __name__ == "__main__":
    unittest.main()
