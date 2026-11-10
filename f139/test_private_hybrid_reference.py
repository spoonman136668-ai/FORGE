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
MD = {"full_name": REPOSITORY, "private": True}


def sample(**changes):
    doc = {
        "schema": SCHEMA,
        "lane": LANE,
        "repository": REPOSITORY,
        "controller_source_sha": OWNER,
        "private_target_commit": COMMIT,
        "private_target_tree": TREE,
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


if __name__ == "__main__":
    unittest.main()
