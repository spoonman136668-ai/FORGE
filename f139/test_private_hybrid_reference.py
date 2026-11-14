"""Synthetic negative controls only; no private bytes, Git access or worker."""
import json
import unittest

from f139.private_hybrid_reference import (
    FIELDS, LANE, REPOSITORY, SCHEMA, PrivateReferenceDenied,
    canonical, parse_reference, public_identity,
)

OWNER = "a" * 40
COMMIT = "b" * 40
TREE = "c" * 40
STORAGE_COMMIT = "e" * 40
STORAGE_TREE = "f" * 40
MD = {"full_name": REPOSITORY, "private": True}


def sample(**changes):
    doc = {
        "schema": SCHEMA,
        "lane": LANE,
        "repository": REPOSITORY,
        "controller_source_sha": OWNER,
        "private_target_commit": COMMIT,
        "private_target_tree": TREE,
        "private_payload_commit": STORAGE_COMMIT,
        "private_payload_tree": STORAGE_TREE,
        "source_path": "scripts/native_example.py",
        "before_sha256": "1" * 64,
        "after_sha256": "2" * 64,
        "private_payload_sha256": "3" * 64,
        "private_payload_blob_sha": "d" * 40,
        "private_payload_path": "f139/private-native/" + "3" * 64 + ".json",
        "owner_signed_intent_sha256": "4" * 64,
        "owner_authorization_sha256": "5" * 64,
        "scientific_first_use": False,
        "paid_api_calls": 0,
        "accepted_ref_mutations": 0,
    }
    doc.update(changes)
    return doc


def parse(doc=None, *, raw=None, owner=OWNER, commit=COMMIT, tree=TREE, md=MD):
    if raw is None:
        raw = canonical(sample() if doc is None else doc)
    return parse_reference(raw, owner_source_sha=owner,
                           private_commit=commit, private_tree=tree,
                           authenticated_repository_metadata=md)


class PrivateHybridReferenceTests(unittest.TestCase):
    def test_exact_reference_and_public_projection_contain_no_private_code(self):
        ref = parse()
        self.assertEqual(set(ref), FIELDS)
        projected = public_identity(canonical(ref), owner_source_sha=OWNER,
                                    private_commit=COMMIT, private_tree=TREE,
                                    authenticated_repository_metadata=MD)
        self.assertFalse(projected["worker_authorized"])
        self.assertFalse(projected["signed_worker_qualified"])
        for forbidden in ("private_payload_path", "private_payload_blob_sha",
                          "source_path", "after_sha256", "after_base64",
                          "intent_base64", "owner_authorization_sha256"):
            self.assertNotIn(forbidden, projected)
        self.assertEqual(len(projected["reference_sha256"]), 64)

    def test_private_or_unknown_visibility_always_fails(self):
        for md in ({"full_name": REPOSITORY, "private": False},
                   {"full_name": REPOSITORY, "private": None},
                   {"full_name": REPOSITORY},
                   {"full_name": REPOSITORY + "-lookalike", "private": True},
                   {}, None):
            with self.subTest(md=md), self.assertRaises(PrivateReferenceDenied):
                parse(md=md)

    def test_identity_drift_fails(self):
        for params in ({"owner": "e" * 40}, {"commit": "e" * 40},
                       {"tree": "e" * 40}, {"owner": "unqualified"}):
            with self.subTest(params=params), self.assertRaises(PrivateReferenceDenied):
                parse(**params)

    def test_inline_private_bytes_or_unrecognized_fields_always_fail(self):
        for name in ("after_base64", "intent_base64", "code", "source_bytes",
                     "worker_authorized", "signed_worker_qualified"):
            with self.subTest(name=name), self.assertRaises(PrivateReferenceDenied):
                parse(sample(**{name: "cHJpdmF0ZQ=="}))

    def test_artifact_path_is_content_addressed_and_bounded(self):
        for value in ("../private.json", "/tmp/private", "f139/private-native/mutable.json",
                      "f139/private-native/" + "f" * 64 + ".json"):
            with self.subTest(path=value), self.assertRaises(PrivateReferenceDenied):
                parse(sample(private_payload_path=value))

    def test_reject_invalid_paths_and_repositories(self):
        for path in ("model.py", "scripts/native_../private.py",
                     "tests/test_model.py", "scripts/native_x/../../key.py",
                     "scripts/native_x.py;echo"):
            with self.subTest(path=path), self.assertRaises(PrivateReferenceDenied):
                parse(sample(source_path=path))
        for repo in ("spoonman136668-ai/FORGE", "spoonman136668-ai/TTT-Hybrid-Lab/other"):
            with self.assertRaises(PrivateReferenceDenied):
                parse(sample(repository=repo))

    def test_fail_closed_on_no_change_unsigned_shape_and_authority(self):
        for edits in ({"after_sha256": "1" * 64},
                      {"private_payload_blob_sha": "short"},
                      {"owner_authorization_sha256": "unsigned"},
                      {"scientific_first_use": True},
                      {"paid_api_calls": True},
                      {"accepted_ref_mutations": 1}):
            with self.subTest(edits=edits), self.assertRaises(PrivateReferenceDenied):
                parse(sample(**edits))

    def test_reject_noncanonical_nonunique_and_oversize_json(self):
        doc = sample()
        for raw in (json.dumps(doc).encode(),
                    b" " + canonical(doc),
                    b'{"schema":"x","schema":"y"}',
                    canonical(doc) + b" "*2049,
                    b'[]', b'null', b''):
            with self.subTest(raw=raw[:20]), self.assertRaises(PrivateReferenceDenied):
                parse(raw=raw)

    def test_public_projection_is_not_an_authenticator(self):
        with self.assertRaises(PrivateReferenceDenied):
            public_identity(canonical({"schema": SCHEMA}), owner_source_sha=OWNER,
                            private_commit=COMMIT, private_tree=TREE,
                            authenticated_repository_metadata=MD)
        with self.assertRaises(PrivateReferenceDenied):
            parse(sample(owner_signed_intent_sha256="bad"))



class PrivatePayloadCustodyTests(unittest.TestCase):
    """All examples are local synthetic bytes: never real private project code."""

    @staticmethod
    def fixture():
        import base64
        import hashlib
        from f139.nci04_native_contract import (
            SCHEMA as INTENT_SCHEMA, canonical as intent_canonical,
        )
        before = b"def synthetic():\\n    return 0\\n"
        after = b"def synthetic():\\n    return 1\\n"
        intent = {
            "schema": INTENT_SCHEMA,
            "controller_source_sha": OWNER,
            "lane": LANE,
            "target_repository": REPOSITORY,
            "target_commit": COMMIT,
            "target_tree_sha": TREE,
            "dependency_sha256": "6" * 64,
            "qualification_harness_sha256": "7" * 64,
            "training_config_sha256": "8" * 64,
            "suite_identity_sha256": "9" * 64,
            "toolchain_identity": "python3.11.11",
            "path": "scripts/native_example.py",
            "before_sha256": hashlib.sha256(before).hexdigest(),
            "after_sha256": hashlib.sha256(after).hexdigest(),
            "after_base64": base64.b64encode(after).decode("ascii"),
            "worker_mode": "isolated-candidate-only",
            "scientific_first_use": False,
            "paid_api_calls": 0,
            "accepted_ref_mutations": 0,
            "optimizer_policy_mutations": 0,
            "protected_holdouts_accessed": 0,
        }
        payload = intent_canonical(intent)
        payload_digest = hashlib.sha256(payload).hexdigest()
        blob = hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload,
        ).hexdigest()
        ref = sample(before_sha256=intent["before_sha256"],
                     after_sha256=intent["after_sha256"],
                     private_payload_sha256=payload_digest,
                     owner_signed_intent_sha256=payload_digest,
                     private_payload_path="f139/private-native/" + payload_digest + ".json",
                     private_payload_blob_sha=blob)
        observed = {"repository": REPOSITORY, "commit_sha": STORAGE_COMMIT,
                    "tree_sha": STORAGE_TREE, "path": ref["private_payload_path"],
                    "git_blob_sha": blob}
        return ref, payload, observed

    @staticmethod
    def check(ref, payload, observed, **kw):
        from f139.private_hybrid_reference import verify_private_payload
        return verify_private_payload(canonical(ref), payload,
                                      owner_source_sha=kw.get("owner", OWNER),
                                      private_commit=kw.get("commit", COMMIT),
                                      private_tree=kw.get("tree", TREE),
                                      authenticated_repository_metadata=kw.get("md", MD),
                                      provider_file=observed)

    def test_synthetic_exact_private_blob_integrity_pass_without_authority(self):
        ref, payload, observed = self.fixture()
        receipt = self.check(ref, payload, observed)
        self.assertTrue(receipt["private_blob_integrity_verified"])
        for key in ("owner_signature_verified", "signed_worker_qualified",
                    "candidate_code_executed", "private_code_emitted",
                    "scientific_first_use"):
            self.assertFalse(receipt[key])
        for forbidden in ("after_base64", "source_path", "private_payload_path",
                          "owner_authorization_sha256", "synthetic", "def "):
            self.assertNotIn(forbidden, json.dumps(receipt, sort_keys=True))

    def test_tampered_private_payload_never_passes(self):
        ref, payload, observed = self.fixture()
        for value in (payload+b" ", payload.replace(b"scripts/native_example.py", b"scripts/native_other.py"),
                      b"{}", b"", payload[:1]):
            with self.subTest(value=value[:30]):
                self.assertNotEqual(value, payload, "tamper fixture must change bytes")
                with self.assertRaises(PrivateReferenceDenied):
                    self.check(ref, value, observed)

    def test_private_provider_blob_identity_and_commit_tree_are_mandatory(self):
        ref, payload, observed = self.fixture()
        for edit in ({"repository": "spoonman136668-ai/FORGE"},
                     {"commit_sha": COMMIT}, {"tree_sha": TREE},
                     {"commit_sha": "0"*40}, {"tree_sha": "0"*40},
                     {"path": "f139/private-native/foreign.json"},
                     {"git_blob_sha": "f"*40}, {"extra": "anything"}):
            with self.subTest(edit=edit), self.assertRaises(PrivateReferenceDenied):
                self.check(ref, payload, {**observed, **edit})

    def test_storage_commit_is_independent_of_unchanged_research_source(self):
        ref, payload, observed = self.fixture()
        self.assertNotEqual(ref["private_target_commit"], ref["private_payload_commit"])
        self.assertNotEqual(ref["private_target_tree"], ref["private_payload_tree"])
        self.assertTrue(self.check(ref, payload, observed)["private_blob_integrity_verified"])
        for changes in ({"private_payload_commit": COMMIT},
                        {"private_payload_tree": TREE},
                        {"private_payload_commit": "not-a-sha"},
                        {"private_payload_tree": "not-a-tree"}):
            with self.subTest(changes=changes), self.assertRaises(PrivateReferenceDenied):
                self.check({**ref, **changes}, payload, observed)

    def test_private_ref_and_native_intent_cannot_disagree(self):
        ref, payload, observed = self.fixture()
        for edit in ({"source_path": "scripts/native_other.py"},
                     {"before_sha256": "f"*64}, {"after_sha256": "f"*64},
                     {"owner_signed_intent_sha256": "f"*64}):
            with self.subTest(edit=edit), self.assertRaises(PrivateReferenceDenied):
                self.check({**ref, **edit}, payload, observed)

    def test_preexisting_signature_digest_is_never_treated_as_verified(self):
        ref, payload, observed = self.fixture()
        for claimed in ("4"*64, "f"*64):
            receipt = self.check({**ref, "owner_authorization_sha256": claimed},
                                 payload, observed)
            self.assertFalse(receipt["owner_signature_verified"])

    def test_authenticated_private_visibility_and_owner_source_required(self):
        ref, payload, observed = self.fixture()
        with self.assertRaises(PrivateReferenceDenied):
            self.check(ref, payload, observed, md={"full_name":REPOSITORY,"private":False})
        with self.assertRaises(PrivateReferenceDenied):
            self.check(ref, payload, observed, owner="f"*40)

    def test_private_payload_contract_rejects_bad_native_authority_fields(self):
        ref, payload, observed = self.fixture()
        changed = json.loads(payload)
        for field, value in (("paid_api_calls", 1), ("scientific_first_use", True),
                             ("accepted_ref_mutations", 1), ("target_repository", "foreign")):
            modified = dict(changed, **{field:value})
            raw = canonical(modified)
            import hashlib
            sha = hashlib.sha256(raw).hexdigest()
            blob = hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
            new_ref = dict(ref, private_payload_sha256=sha,
                           private_payload_blob_sha=blob,
                           private_payload_path="f139/private-native/"+sha+".json",
                           owner_signed_intent_sha256=sha)
            new_provider = dict(observed, path=new_ref["private_payload_path"],
                                git_blob_sha=blob)
            with self.subTest(field=field), self.assertRaises(PrivateReferenceDenied):
                self.check(new_ref, raw, new_provider)

    def test_reject_duplicate_json_even_with_matching_hashes(self):
        import hashlib
        ref, _, observed = self.fixture()
        raw = b'{"schema":"x","schema":"x"}'
        sha = hashlib.sha256(raw).hexdigest()
        blob = hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
        new_ref = dict(ref, private_payload_sha256=sha,
                       private_payload_blob_sha=blob,
                       private_payload_path="f139/private-native/"+sha+".json",
                       owner_signed_intent_sha256=sha)
        new_provider = dict(observed, path=new_ref["private_payload_path"],
                            git_blob_sha=blob)
        with self.assertRaises(PrivateReferenceDenied):
            self.check(new_ref, raw, new_provider)

    def test_reject_reference_only_if_provider_metadata_missing(self):
        ref, payload, observed = self.fixture()
        with self.assertRaises(PrivateReferenceDenied):
            self.check(ref, payload, {})
        with self.assertRaises(PrivateReferenceDenied):
            self.check(ref, payload, None)



if __name__ == "__main__":
    unittest.main()
