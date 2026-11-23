"""Synthetic credentialed owner HMAC + private blob joins; never a live owner."""
import unittest

from f139.nci04_native_contract import parse_intent
from f139.nci04_signed_native import admit_native_intent, sign_native_intent
from f139.private_hybrid_owner_binding import (
    PrivateOwnerBindingDenied, verify_credentialed_owner_binding,
)
from f139 import test_private_hybrid_reference as reference_fixtures
from f139.private_hybrid_reference import canonical

OWNER = reference_fixtures.OWNER
COMMIT = reference_fixtures.COMMIT
TREE = reference_fixtures.TREE
MD = reference_fixtures.MD
from f139.verify_ticket import signature as sign_controller, Untrusted

KEY = "f139-original-owner-synthetic-test-key-0123456789"
ISSUE = "702"
ISSUE_ID = "5951234567"
BODY = "7" * 64
RUN = "39513290000"


def fixture():
    ref, payload, provider = reference_fixtures.PrivatePayloadCustodyTests.fixture()
    candidate = parse_intent(
        payload, protected_main=OWNER, target_commit=COMMIT, target_tree_sha=TREE)
    ticket = "f139-nci04-i" + ISSUE + "-" + OWNER[:12] + "-" + candidate.intent_sha256[:8]
    inp = {
        "key": KEY, "ticket": ticket, "lane": "TTT-Hybrid",
        "source_sha": OWNER, "epoch": "1",
        "repository": "spoonman136668-ai/FORGE",
        "ref": "refs/heads/main", "event": "workflow_dispatch",
        "head_sha": OWNER, "run_attempt": "1", "run_id": RUN,
        "os": "ubuntu-latest",
    }
    inp["signature"] = sign_controller(KEY, ticket, "TTT-Hybrid", OWNER, "1")
    native_sig = sign_native_intent(
        inp, candidate, issue_number=ISSUE, issue_id=ISSUE_ID,
        issue_body_sha256=BODY,
    )
    admitted = admit_native_intent(
        inp, payload, native_signature=native_sig,
        issue_number=ISSUE, issue_id=ISSUE_ID, issue_body_sha256=BODY,
        authenticated_main_sha=OWNER, authenticated_target_commit=COMMIT,
        authenticated_target_tree=TREE,
    )
    ref["owner_authorization_sha256"] = admitted.authorization_sha256
    return ref, payload, provider, inp, native_sig


def verify(ref, payload, provider, inp, sig, **kw):
    return verify_credentialed_owner_binding(
        canonical(ref), payload, original_ticket_inputs=inp,
        native_signature=sig,
        issue_number=kw.get("issue_number", ISSUE),
        issue_id=kw.get("issue_id", ISSUE_ID),
        issue_body_sha256=kw.get("body_sha256", BODY),
        owner_source_sha=kw.get("owner", OWNER),
        private_commit=kw.get("commit", COMMIT),
        private_tree=kw.get("tree", TREE),
        authenticated_repository_metadata=kw.get("metadata", MD),
        provider_file=provider,
    )


class CredentialedOwnerPrivatePayloadBindingTests(unittest.TestCase):
    def test_two_real_hmac_algorithms_match_private_blob_only_in_synthetic_fixture(self):
        ref, payload, provider, inp, sig = fixture()
        result = verify(ref, payload, provider, inp, sig)
        self.assertEqual(result["ticket"], inp["ticket"])
        self.assertEqual(result["authorization_binding_sha256"],
                         ref["owner_authorization_sha256"])
        self.assertTrue(result["provided_owner_hmac_pair_matched"])
        self.assertTrue(result["private_blob_bytes_matched"])
        for key in ("original_owner_live_issue_verified", "private_worker_executed",
                    "signed_worker_qualified", "owner_schema_migrated",
                    "scientific_first_use", "gpu_used"):
            self.assertFalse(result[key])
        serialized = str(result)
        self.assertNotIn(KEY, serialized)
        for forbidden in ("after_base64", "def synthetic", "source_path",
                          "private_payload_path", "native_signature"):
            self.assertNotIn(forbidden, serialized)

    def test_owner_key_and_both_signatures_must_match(self):
        ref, payload, provider, inp, sig = fixture()
        for changed, native in (
            ({**inp, "key": "wrong"*12}, sig),
            ({**inp, "signature": "0"*64}, sig),
            (inp, "0"*64),
            (inp, ""),
        ):
            with self.subTest(kind=changed["signature"][:7], native=native[:7]):
                with self.assertRaises(Untrusted):
                    verify(ref, payload, provider, changed, native)

    def test_wrong_owner_ticket_issue_or_provenance_rejected(self):
        ref, payload, provider, inp, sig = fixture()
        for keys in ({"issue_number":"703"}, {"issue_id":"4"},
                     {"body_sha256":"8"*64}, {"owner":"f"*40},
                     {"commit":"f"*40}, {"tree":"f"*40}):
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                verify(ref, payload, provider, inp, sig, **keys)
        for fields in ({"run_attempt":"2"}, {"event":"push"},
                       {"ref":"refs/heads/other"}, {"head_sha":"f"*40},
                       {"repository":"foreign/FORGE"}, {"os":"unknown"}):
            with self.subTest(fields=fields), self.assertRaises(Untrusted):
                verify(ref, payload, provider, {**inp, **fields}, sig)

    def test_reference_cannot_claim_another_authorization(self):
        ref, payload, provider, inp, sig = fixture()
        for change in ({"owner_authorization_sha256":"f"*64},
                       {"owner_signed_intent_sha256":"f"*64},
                       {"source_path":"scripts/native_other.py"},
                       {"before_sha256":"f"*64}):
            with self.subTest(change=change), self.assertRaises(PrivateOwnerBindingDenied):
                verify({**ref, **change}, payload, provider, inp, sig)

    def test_private_blob_or_provider_mapping_cannot_drift(self):
        ref, payload, provider, inp, sig = fixture()
        for raw, doc in (
            (payload+b" ", provider),
            (payload.replace(b"scripts/native_example.py",b"scripts/native_other.py"),provider),
            (payload,{**provider,"git_blob_sha":"e"*40}),
            # The valid storage commit now uses e*40; mutate to a genuinely
            # distinct SHA so this negative cannot silently become a no-op.
            (payload,{**provider,"commit_sha":"0"*40}),
            (payload,{**provider,"tree_sha":"0"*40}),
            (payload,{**provider,"path":"f139/private-native/other.json"}),
        ):
            self.assertTrue(raw != payload or doc != provider,
                            "negative fixture must actually change bytes or provider")
            with self.subTest(bytes=len(raw),provider=doc), self.assertRaises(ValueError):
                verify(ref, raw, doc, inp, sig)

    def test_private_project_metadata_cannot_be_omitted_or_public(self):
        ref, payload, provider, inp, sig = fixture()
        for md in ({}, {"full_name":MD["full_name"],"private":False},
                   {"full_name":MD["full_name"],"private":None}):
            with self.subTest(md=md), self.assertRaises(ValueError):
                verify(ref, payload, provider, inp, sig, metadata=md)

    def test_legacy_ticket_cannot_be_promoted_to_private_native(self):
        ref, payload, provider, inp, sig = fixture()
        with self.assertRaises(Untrusted):
            verify(ref, payload, provider,
                   {**inp, "ticket":"f139-d2k-i702-"+OWNER[:12]+"-"+"7"*8},
                   sig)


if __name__ == "__main__":
    unittest.main()
