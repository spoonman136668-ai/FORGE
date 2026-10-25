"""G31 frozen isolated owner V2 domain-separation and no-replay tests."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import hmac
import json
import unittest

from f139.nci04_native_contract import canonical
from f139.nci04_signed_native import NativeAdmission, sign_native_intent
from f139.nci04_worker_v2 import SOURCE_SHA, SOURCE_TREE, RECEIPT_SCHEMA
from f139.nci04_v2_owner_permit import (
    DOMAIN, SCHEMA, V2OwnerPermitDenied,
    issue_v2_owner_permit, verify_v2_owner_permit,
)
from f139.test_nci04_worker_v2 import V2ContractTests

KEY = "G31-offline-owner-fixture-not-production-0123456789012345"
SOURCE = "e" * 40
HEAD = "c" * 64


class OwnerV2AuthorizationTests(unittest.TestCase):
    def setUp(self):
        f = V2ContractTests()
        f.setUp()
        self.c = f.c
        self.a = NativeAdmission(
            "f139-nci04-i933-" + SOURCE[:12] + "-" + f.c.intent_sha256[:8],
            "Yggdrasil", SOURCE, 40200000001, "ubuntu-latest", 933,
            6010000333, f.c, "f" * 64)
        self.args = dict(owner_key=KEY, epoch=6, admission_event_seq=221,
                         admission_event_sha256=HEAD,
                         authenticated_source_sha=SOURCE)

    def issue(self, **change):
        return issue_v2_owner_permit(self.a, **{**self.args, **change})

    def verify(self, raw, admission=None, **change):
        return verify_v2_owner_permit(
            raw, self.a if admission is None else admission,
            **{**self.args, **change})

    def test_qualified_distinct_hmac_bound_to_exact_original_owner(self):
        raw = self.issue()
        doc = json.loads(raw)
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["binding"]["receipt_protocol"], RECEIPT_SCHEMA)
        self.assertEqual(doc["binding"]["target_commit"], SOURCE_SHA)
        self.assertEqual(doc["binding"]["target_tree_sha"], SOURCE_TREE)
        self.assertEqual(doc["binding"]["original_admission_event_seq"], 221)
        self.assertNotIn(KEY, raw.decode())
        result = self.verify(raw)
        self.assertTrue(result["signed_v2_only"])
        self.assertFalse(result["original_event_custody_independently_verified"])
        self.assertFalse(result["worker_dispatched"])
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertEqual(self.issue(), raw)

    def test_actual_v1_hmac_cannot_authorize_v2(self):
        controller = dict(
            key=KEY, ticket=self.a.ticket, lane=self.a.lane,
            source_sha=SOURCE, epoch=str(self.args["epoch"]),
            signature="9" * 64)
        v1 = sign_native_intent(
            controller, self.c, issue_number=str(self.a.issue_number),
            issue_id=str(self.a.issue_id), issue_body_sha256="a" * 64)
        record = json.loads(self.issue())
        self.assertNotEqual(v1, record["hmac_sha256"])
        record["hmac_sha256"] = v1
        with self.assertRaisesRegex(V2OwnerPermitDenied, "V2_HMAC_MISMATCH"):
            self.verify(canonical(record))
        # A plain V1 signature is not a serialized V2 permit either.
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(v1.encode())

    def test_domain_separation_is_explicit_and_unique(self):
        raw = self.issue()
        doc = json.loads(raw)
        expected = hmac.new(KEY.encode(), DOMAIN + canonical(doc["binding"]),
                            hashlib.sha256).hexdigest()
        self.assertEqual(doc["hmac_sha256"], expected)
        other = hmac.new(KEY.encode(), b"F139-NCI04-V1\n" +
                         canonical(doc["binding"]), hashlib.sha256).hexdigest()
        self.assertNotEqual(other, expected)

    def test_replay_earlier_than_activation_head_refused(self):
        for sequence in (0, 220, True, -1):
            with self.subTest(seq=sequence):
                with self.assertRaisesRegex(
                        V2OwnerPermitDenied, "NEW_ORIGINAL_OWNER_EVENT_REQUIRED"):
                    self.issue(admission_event_seq=sequence)
        raw = self.issue()
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(raw, admission_event_seq=222)
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(raw, admission_event_sha256="0" * 64)

    def test_run_os_epoch_and_source_replay_fail_closed(self):
        raw = self.issue()
        for adm in (
            replace(self.a, run_id=40200000002),
            replace(self.a, runner_os="windows-latest"),
            replace(self.a, source_sha="d" * 40),
            replace(self.a, ticket="reused"),
            replace(self.a, authorization_sha256="0" * 64),
            replace(self.a, issue_number=934),
            replace(self.a, issue_id=6010000334),
        ):
            with self.subTest(admission=adm), self.assertRaises(
                    V2OwnerPermitDenied):
                self.verify(raw, admission=adm)
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(raw, epoch=7)
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(raw, owner_key="a" * 48)

    def test_lane_target_candidate_and_qual_key_drift(self):
        raw = self.issue()
        for change in (
            dict(lane="Wingless"),
            dict(target_commit="0" * 40),
            dict(target_tree_sha="0" * 40),
            dict(after_sha256="0" * 64),
            dict(qualification_key="0" * 64),
            dict(path="scripts/changed.py"),
        ):
            with self.subTest(change=change), self.assertRaises(
                    V2OwnerPermitDenied):
                self.verify(raw, admission=replace(
                    self.a, intent=replace(self.c, **change)))

    def test_payload_tampering_never_claims_science(self):
        raw = self.issue()
        for field, value in (
            ("scientific_first_use_authorized", True),
            ("accepted_ref_mutations", 1),
            ("paid_model_calls", 1),
            ("receipt_protocol", "forge.f139.nci04.native-execution-receipt.v1"),
            ("provider_run_id", 999),
            ("original_admission_event_kind", "NATIVE_DEVELOPMENT_ACTIVATED"),
        ):
            doc = json.loads(raw)
            doc["binding"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    V2OwnerPermitDenied, "ORIGINAL_OWNER_BINDING_CHANGED"):
                self.verify(canonical(doc))

    def test_unknown_duplicate_and_noncanonical_fields_rejected(self):
        raw = self.issue()
        doc = json.loads(raw)
        doc["owner_key"] = KEY
        with self.assertRaisesRegex(V2OwnerPermitDenied, "VERSION_OR_NONCANONICAL"):
            self.verify(canonical(doc))
        raw_dup = raw.replace(b'"schema":', b'"schema":"fake","schema":', 1)
        with self.assertRaisesRegex(V2OwnerPermitDenied, "DUPLICATE_JSON_FIELD"):
            self.verify(raw_dup)
        with self.assertRaisesRegex(V2OwnerPermitDenied, "VERSION_OR_NONCANONICAL"):
            self.verify(json.dumps(json.loads(raw), indent=2).encode())
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(raw + b"\n")

    def test_owner_key_type_and_strength_enforced(self):
        for key in ("short", "", True, 12):
            with self.subTest(key=key), self.assertRaisesRegex(
                    V2OwnerPermitDenied, "OWNER_KEY_INVALID"):
                self.issue(owner_key=key)
        with self.assertRaises(V2OwnerPermitDenied):
            self.verify(self.issue(), owner_key="bad")

    def test_existing_v2_result_receipt_is_not_owner_execution_permission(self):
        from f139.nci04_worker_v2 import receipt_v2
        fixture = V2ContractTests()
        fixture.setUp()
        ordinary_dev_receipt = receipt_v2(self.a, fixture.report())
        self.assertEqual(ordinary_dev_receipt["schema"], RECEIPT_SCHEMA)
        with self.assertRaisesRegex(
                V2OwnerPermitDenied, "VERSION_OR_NONCANONICAL_PERMIT"):
            self.verify(canonical(ordinary_dev_receipt))

    def test_receipt_is_not_an_execution_capability(self):
        result = self.verify(self.issue())
        self.assertNotIn("authorizes_dispatch", result)
        self.assertFalse(result["worker_dispatched"])
        self.assertFalse(result["original_event_custody_independently_verified"])


if __name__ == "__main__":
    unittest.main()
