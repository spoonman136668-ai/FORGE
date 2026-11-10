"""Reference-only original-owner issue: synthetic tests, not live issuance."""
from dataclasses import replace
import hashlib
import json
import unittest

from f139.nci04_native_contract import parse_intent
from f139.nci04_signed_native import admit_native_intent, sign_native_intent
from f139.private_hybrid_owner_binding import verify_credentialed_owner_binding
from f139.private_hybrid_reference import canonical
from f139.private_hybrid_opaque_issue import (
    FIELDS, KIND, LABEL, OWNER, SCHEMA, PrivateOpaqueIssueDenied,
    bind_private_issue_to_credentialed_reference, inspect_private_opaque_issue,
    prepare_private_provider_commitment,
)
from f139 import test_private_hybrid_owner_binding as synthetic

REPOSITORY = "spoonman136668-ai/TTT-Hybrid-Lab"


def fixture():
    # This reconstructs the existing two independent real HMAC algorithms
    # with a SYNTHETIC test key, not the installed owner/credential/run.
    ref, payload, observed, inputs, _ = synthetic.fixture()
    public = {
        "schema": SCHEMA, "kind": KIND, "lane": "TTT-Hybrid",
        "source_sha": synthetic.OWNER, "repository": REPOSITORY,
        "private_target_commit": synthetic.COMMIT,
        "private_target_tree": synthetic.TREE,
        "private_payload_commit": ref["private_payload_commit"],
        "private_payload_tree": ref["private_payload_tree"],
        "private_payload_sha256": ref["private_payload_sha256"],
        "private_payload_blob_sha": ref["private_payload_blob_sha"],
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
    }
    assert set(public) == FIELDS
    body = canonical(public).decode("ascii")
    issue_api = {
        "number": int(synthetic.ISSUE), "id": int(synthetic.ISSUE_ID),
        "state": "open", "user": {"login": OWNER},
        "author_association": "OWNER", "labels": [{"name": LABEL}],
        "body": body,
    }
    verify_kw = {
        "owner_source_sha": synthetic.OWNER,
        "authenticated_repository_metadata": synthetic.MD,
        "authenticated_target_commit": synthetic.COMMIT,
        "authenticated_target_tree": synthetic.TREE,
        "authenticated_storage_file": observed,
    }
    inspected = inspect_private_opaque_issue(issue_api, **verify_kw)
    candidate = parse_intent(
        payload, protected_main=synthetic.OWNER,
        target_commit=synthetic.COMMIT, target_tree_sha=synthetic.TREE)
    signature = sign_native_intent(
        inputs, candidate, issue_number=synthetic.ISSUE,
        issue_id=synthetic.ISSUE_ID,
        issue_body_sha256=inspected.issue_body_sha256)
    admitted = admit_native_intent(
        inputs, payload, native_signature=signature,
        issue_number=synthetic.ISSUE, issue_id=synthetic.ISSUE_ID,
        issue_body_sha256=inspected.issue_body_sha256,
        authenticated_main_sha=synthetic.OWNER,
        authenticated_target_commit=synthetic.COMMIT,
        authenticated_target_tree=synthetic.TREE)
    ref["owner_authorization_sha256"] = admitted.authorization_sha256
    binding = verify_credentialed_owner_binding(
        canonical(ref), payload, original_ticket_inputs=inputs,
        native_signature=signature, issue_number=synthetic.ISSUE,
        issue_id=synthetic.ISSUE_ID,
        issue_body_sha256=inspected.issue_body_sha256,
        owner_source_sha=synthetic.OWNER, private_commit=synthetic.COMMIT,
        private_tree=synthetic.TREE,
        authenticated_repository_metadata=synthetic.MD,
        provider_file=observed)
    return public, issue_api, verify_kw, inspected, ref, binding, payload, inputs



def synthetic_candidate_revision(payload, original):
    """Fixture for a real single-commit one-file GitHub compare *shape* only."""
    import base64
    after = base64.b64decode(json.loads(payload)["after_base64"], validate=True)
    after_git_blob = hashlib.sha1(
        b"blob " + str(len(after)).encode("ascii") +
        b"\0" + after).hexdigest()
    candidate_commit = "7" * 40
    head = {
        "repository": REPOSITORY,
        "commit_sha": candidate_commit,
        "tree_sha": "8" * 40,
        "path": original["path"],
        "git_blob_sha": after_git_blob,
    }
    comparison = {
        "status": "ahead", "ahead_by": 1, "behind_by": 0, "total_commits": 1,
        "base_commit": {"sha": original["commit_sha"]},
        "merge_base_commit": {"sha": original["commit_sha"]},
        "commits": [{"sha": candidate_commit,
                     "parents": [{"sha": original["commit_sha"]}]}],
        "files": [{"filename": original["path"], "status": "modified",
                   "sha": after_git_blob, "changes": 1}],
    }
    return after, head, comparison


def parse_issue(raw, kw):
    return inspect_private_opaque_issue(raw, **kw)


def join(issue, binding, ref):
    return bind_private_issue_to_credentialed_reference(
        issue, binding, canonical(ref),
        authenticated_repository_metadata=synthetic.MD)


class PrivateHybridOpaqueIssueTests(unittest.TestCase):
    def test_opaque_public_issue_then_signed_private_reference(self):
        public, api, kw, issue, ref, binding, payload, inputs = fixture()
        out = join(issue, binding, ref)
        self.assertTrue(out["opaque_issue_reference_binding_verified"])
        self.assertTrue(out["owner_hmac_algorithm_pair_matched"])
        self.assertEqual(out["issue_body_sha256"],
                         hashlib.sha256(api["body"].encode()).hexdigest())
        self.assertEqual(out["private_payload_sha256"],
                         hashlib.sha256(payload).hexdigest())
        self.assertEqual(out["reference_sha256"], binding["reference_sha256"])
        self.assertEqual(issue.ticket, inputs["ticket"])
        self.assertFalse(out["live_owner_ledger_verified"])
        self.assertFalse(out["private_worker_execution_verified"])
        self.assertFalse(out["hybrid_lane_admitted"])
        self.assertFalse(out["scientific_first_use"])
        for sensitive in ("intent_base64", "after_base64", "owner_signature",
                          "owner_authorization_sha256", "reference_sha256",
                          "owner_signed_intent_sha256", "source_path"):
            self.assertNotIn(sensitive, public)
            self.assertNotIn(sensitive, api["body"])
        self.assertNotIn(synthetic.KEY, json.dumps(out))
        for sensitive in ("private_payload_path", "after_base64", "native_signature",
                          "source_path", synthetic.KEY):
            self.assertNotIn(sensitive, json.dumps(out))

    def test_real_private_source_first_prepares_only_opaque_public_body(self):
        public, issue_api, kw, issue, ref, bound, payload, _ = fixture()
        before = b"def synthetic():\\n    return 0\\n"
        def blob(raw):
            return hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") +
                b"\0" + raw).hexdigest()
        original = {
            "repository": REPOSITORY,
            "commit_sha": synthetic.COMMIT,
            "tree_sha": synthetic.TREE,
            "path": ref["source_path"],
            "git_blob_sha": blob(before),
        }
        args = {
            "owner_source_sha": synthetic.OWNER,
            "authenticated_repository_metadata": synthetic.MD,
            "authenticated_target_commit": synthetic.COMMIT,
            "authenticated_target_tree": synthetic.TREE,
            "authenticated_target_file": original,
            "authenticated_storage_file": kw["authenticated_storage_file"],
        }
        after, head, comparison = synthetic_candidate_revision(payload, original)
        args["authenticated_candidate_file"] = head
        args["authenticated_candidate_comparison"] = comparison
        outcome = prepare_private_provider_commitment(payload, before, after, **args)
        self.assertEqual(outcome["issue_body"], issue_api["body"])
        self.assertEqual(outcome["issue_body_sha256"], issue.issue_body_sha256)
        self.assertEqual(outcome["private_payload_sha256"],
                         hashlib.sha256(payload).hexdigest())
        self.assertTrue(outcome["real_baseline_blob_bytes_matched"])
        self.assertTrue(outcome["real_after_blob_bytes_matched"])
        self.assertTrue(outcome["single_commit_single_source_delta_verified"])
        self.assertTrue(outcome["real_storage_blob_bytes_matched"])
        self.assertFalse(outcome["public_private_code_emitted"])
        self.assertFalse(outcome["original_owner_live_issue_verified"])
        self.assertFalse(outcome["private_worker_executed"])
        self.assertFalse(outcome["scientific_first_use"])
        self.assertEqual(parse_issue(
            {**issue_api, "body": outcome["issue_body"]}, kw), issue)
        self.assertEqual(join(issue, bound, ref)["issue_body_sha256"],
                         outcome["issue_body_sha256"])
        for forbidden in ("after_base64", "intent_base64",
                          "source_path", "private_payload_path",
                          "def synthetic", synthetic.KEY,
                          "owner_authorization_sha256", "native_signature"):
            self.assertNotIn(forbidden, outcome["issue_body"])
            self.assertNotIn(forbidden, json.dumps(outcome))
        return outcome

    def test_preissue_real_original_and_storage_blob_drifts_fail_closed(self):
        _, _, kw, _, ref, _, payload, _ = fixture()
        before = b"def synthetic():\\n    return 0\\n"
        original_sha = hashlib.sha1(
            b"blob " + str(len(before)).encode("ascii") +
            b"\0" + before).hexdigest()
        original = {
            "repository": REPOSITORY,
            "commit_sha": synthetic.COMMIT,
            "tree_sha": synthetic.TREE,
            "path": ref["source_path"],
            "git_blob_sha": original_sha,
        }
        after, head, comparison = synthetic_candidate_revision(payload, original)
        arguments = {
            "authenticated_candidate_file": head,
            "authenticated_candidate_comparison": comparison,
            "owner_source_sha": synthetic.OWNER,
            "authenticated_repository_metadata": synthetic.MD,
            "authenticated_target_commit": synthetic.COMMIT,
            "authenticated_target_tree": synthetic.TREE,
            "authenticated_target_file": original,
            "authenticated_storage_file": kw["authenticated_storage_file"],
        }
        bad_inputs = (
            (payload, b"", arguments),
            (payload, before + b"edited", arguments),
            (payload + b" ", before, arguments),
            (b"{}", before, arguments),
            (payload, before, {**arguments,
                "owner_source_sha": "0"*40}),
            (payload, before, {**arguments,
                "authenticated_repository_metadata": {
                    "full_name": REPOSITORY, "private": False}}),
            (payload, before, {**arguments,
                "authenticated_target_commit": "0"*40}),
            (payload, before, {**arguments,
                "authenticated_target_tree": "0"*40}),
            (payload, before, {**arguments,
                "authenticated_target_file": {**original,
                    "path": "tests/test_other_native.py"}}),
            (payload, before, {**arguments,
                "authenticated_target_file": {**original,
                    "git_blob_sha": "0"*40}}),
            (payload, before, {**arguments,
                "authenticated_storage_file": {
                    **kw["authenticated_storage_file"],
                    "git_blob_sha": "0"*40}}),
            (payload, before, {**arguments,
                "authenticated_storage_file": {
                    **kw["authenticated_storage_file"],
                    "commit_sha": synthetic.COMMIT}}),
            (payload, before, {**arguments,
                "authenticated_storage_file": {
                    **kw["authenticated_storage_file"],
                    "path": "f139/private-native/other.json"}}),
        )
        for i, (p, source, opts) in enumerate(bad_inputs):
            self.assertTrue(p != payload or source != before or opts != arguments)
            with self.subTest(case=i), self.assertRaises(PrivateOpaqueIssueDenied):
                prepare_private_provider_commitment(p, source, after, **opts)


    def test_candidate_revision_must_be_verified_one_file_modified(self):
        _, _, kw, _, ref, _, payload, _ = fixture()
        before = b"def synthetic():\\n    return 0\\n"
        original = {
            "repository": REPOSITORY, "commit_sha": synthetic.COMMIT,
            "tree_sha": synthetic.TREE, "path": ref["source_path"],
            "git_blob_sha": hashlib.sha1(
                b"blob " + str(len(before)).encode() +
                b"\0" + before).hexdigest(),
        }
        after, head, comparison = synthetic_candidate_revision(payload, original)
        args = {
            "owner_source_sha": synthetic.OWNER,
            "authenticated_repository_metadata": synthetic.MD,
            "authenticated_target_commit": synthetic.COMMIT,
            "authenticated_target_tree": synthetic.TREE,
            "authenticated_target_file": original,
            "authenticated_storage_file": kw["authenticated_storage_file"],
            "authenticated_candidate_file": head,
            "authenticated_candidate_comparison": comparison,
        }
        for change in (
            {"after": after + b"modified"},
            {"head": {**head, "git_blob_sha": "0"*40}},
            {"head": {**head, "commit_sha": synthetic.COMMIT}},
            {"head": {**head, "tree_sha": "bad"}},
            {"head": {**head, "path": "tests/test_model.py"}},
            {"compare": {**comparison, "total_commits": 2}},
            {"compare": {**comparison, "ahead_by": True}},
            {"compare": {**comparison, "behind_by": 1}},
            {"compare": {**comparison, "merge_base_commit": {"sha": "0"*40}}},
            {"compare": {**comparison, "commits": []}},
            {"compare": {**comparison, "commits": [
                {"sha": head["commit_sha"], "parents": [
                    {"sha": synthetic.COMMIT}, {"sha": "0"*40}]}]}},
            {"compare": {**comparison, "files": [
                *comparison["files"], {"filename": "tests/test_unrelated.py",
                                       "status": "added", "sha": "a"*40,
                                       "changes": 1}]}},
            {"compare": {**comparison, "files": [
                {**comparison["files"][0], "status": "added"}]}},
            {"compare": {**comparison, "files": [
                {**comparison["files"][0], "sha": "0"*40}]}},
            {"compare": {**comparison, "files": [
                {**comparison["files"][0], "changes": False}]}},
            {"storage": {**kw["authenticated_storage_file"],
                         "commit_sha": head["commit_sha"]}},
        ):
            with self.subTest(change=tuple(change)):
                observed = {**args}
                new_after = change.get("after", after)
                observed["authenticated_candidate_file"] = change.get("head", head)
                observed["authenticated_candidate_comparison"] = change.get("compare", comparison)
                observed["authenticated_storage_file"] = change.get(
                    "storage", kw["authenticated_storage_file"])
                with self.assertRaises(PrivateOpaqueIssueDenied):
                    prepare_private_provider_commitment(
                        payload, before, new_after, **observed)

    def test_public_issue_is_frozen_before_final_private_ref_exists(self):
        public, api, kw, issue, ref, binding, payload, inputs = fixture()
        # The original issue's hash is independent of the subsequently
        # created signature-bound reference and its content-addressed hash.
        before = issue.issue_body_sha256
        modified = {**ref, "owner_authorization_sha256": "0"*64}
        self.assertNotEqual(canonical(ref), canonical(modified))
        self.assertEqual(before, parse_issue(api, kw).issue_body_sha256)
        self.assertNotIn(hashlib.sha256(canonical(ref)).hexdigest(), api["body"])

    def test_owner_identity_and_label_fail_closed(self):
        public, api, kw, *_ = fixture()
        mutations = (
            {"state": "closed"},
            {"user": {"login": "forged-owner"}},
            {"author_association": "CONTRIBUTOR"},
            {"number": 0}, {"number": "702"}, {"number": True},
            {"id": 0}, {"id": "5951234567"},
            {"pull_request": {"url": "untrusted"}},
            {"labels": []}, {"labels": [{"name": "f139-native-development-eligible"}]},
            {"labels": [{"name": LABEL}, {"name": "f139-native-development-eligible"}]},
            {"labels": [{"name": LABEL}, {"name": LABEL}]},
        )
        for change in mutations:
            self.assertNotEqual({**api, **change}, api)
            with self.subTest(change=change), self.assertRaises(PrivateOpaqueIssueDenied):
                parse_issue({**api, **change}, kw)

    def test_public_payload_refused_code_and_authority_field_smuggling(self):
        public, api, kw, *_ = fixture()
        for key, val in (
            ("after_base64", "ZGVmIGNvZGUoKTogcGFzcw=="),
            ("intent_base64", "ZXZpbA=="),
            ("source_path", "scripts/native_private.py"),
            ("owner_authorization_sha256", "a"*64),
            ("reference_sha256", "b"*64),
            ("worker_authorized", True),
            ("scientific_first_use", True),
            ("accepted_ref_mutations", 1),
            ("paid_model_calls", 1),
            ("kind", "native-cognitive-candidate"),
            ("lane", "Wingless"),
            ("repository", "spoonman136668-ai/FORGE"),
            ("source_sha", "0"*40),
        ):
            body = canonical({**public, key: val}).decode()
            self.assertNotEqual(body, api["body"])
            with self.subTest(key=key), self.assertRaises(PrivateOpaqueIssueDenied):
                parse_issue({**api, "body": body}, kw)

    def test_provider_identity_source_and_storage_are_independent(self):
        public, api, kw, *_ = fixture()
        changed = (
            {"owner_source_sha": "0"*40},
            {"authenticated_target_commit": "0"*40},
            {"authenticated_target_tree": "0"*40},
            {"authenticated_repository_metadata": {"full_name": REPOSITORY, "private": False}},
            {"authenticated_repository_metadata": {"full_name": REPOSITORY, "private": None}},
            {"authenticated_repository_metadata": {"full_name": REPOSITORY+"-lookalike", "private": True}},
            {"authenticated_storage_file": {**kw["authenticated_storage_file"], "commit_sha": "0"*40}},
            {"authenticated_storage_file": {**kw["authenticated_storage_file"], "tree_sha": "0"*40}},
            {"authenticated_storage_file": {**kw["authenticated_storage_file"], "git_blob_sha": "0"*40}},
            {"authenticated_storage_file": {**kw["authenticated_storage_file"], "path": "f139/private-native/mutable.json"}},
        )
        for change in changed:
            self.assertNotEqual({**kw, **change}, kw)
            with self.subTest(change=change), self.assertRaises(PrivateOpaqueIssueDenied):
                parse_issue(api, {**kw, **change})

    def test_public_body_must_be_unique_canonical_and_bounded(self):
        public, api, kw, *_ = fixture()
        raw_candidates = (
            " " + api["body"], api["body"] + "\n",
            json.dumps(public),
            '{"schema":"a","schema":"b"}',
            "{}", "[]", "",
            canonical(public).decode() + " "*2400,
        )
        for body in raw_candidates:
            with self.subTest(body=body[:30]), self.assertRaises(PrivateOpaqueIssueDenied):
                parse_issue({**api, "body": body}, kw)

    def test_public_private_source_commit_and_hash_tamper_fails(self):
        public, api, kw, *_ = fixture()
        for change in (
            {"private_target_commit": "0"*40},
            {"private_target_tree": "0"*40},
            {"private_payload_commit": "0"*40},
            {"private_payload_tree": "0"*40},
            {"private_payload_sha256": "0"*64},
            {"private_payload_blob_sha": "0"*40},
            {"private_payload_sha256": "not-a-hash"},
            {"private_payload_blob_sha": "short"},
        ):
            self.assertNotEqual({**public, **change}, public)
            with self.subTest(change=change), self.assertRaises(PrivateOpaqueIssueDenied):
                parse_issue({**api, "body": canonical({**public, **change}).decode()}, kw)

    def test_original_hmac_bound_result_must_match_exact_issue_body(self):
        _, api, kw, issue, ref, binding, _, _ = fixture()
        mutations = (
            {"ticket": "forged"},
            {"issue_number": issue.number+1},
            {"issue_id": issue.issue_id+1},
            {"issue_body_sha256": "0"*64},
            {"owner_source_sha": "0"*40},
            {"private_payload_sha256": "0"*64},
            {"authorization_binding_sha256": "0"*64},
            {"reference_sha256": "0"*64},
            {"provided_owner_hmac_pair_matched": False},
            {"private_blob_bytes_matched": False},
            {"original_owner_live_issue_verified": True},
            {"private_worker_executed": True},
        )
        for change in mutations:
            self.assertNotEqual({**binding, **change}, binding)
            with self.subTest(change=change), self.assertRaises(PrivateOpaqueIssueDenied):
                join(issue, {**binding, **change}, ref)

    def test_final_private_reference_cannot_be_substituted(self):
        _, _, _, issue, ref, binding, _, _ = fixture()
        for change in (
            {"owner_authorization_sha256": "0"*64},
            {"private_payload_sha256": "0"*64},
            {"private_payload_blob_sha": "0"*40},
            {"private_payload_commit": "0"*40},
            {"private_payload_tree": "0"*40},
            {"private_target_commit": "0"*40},
        ):
            with self.subTest(change=change), self.assertRaises((PrivateOpaqueIssueDenied, ValueError)):
                join(issue, binding, {**ref, **change})
        # Even a forged dataclass copied from a real issue isn't admission.
        with self.assertRaises(PrivateOpaqueIssueDenied):
            join(replace(issue, issue_body_sha256="0"*64), binding, ref)

    def test_invalid_binding_type_never_accepted(self):
        _, _, _, issue, ref, binding, _, _ = fixture()
        with self.assertRaises(PrivateOpaqueIssueDenied):
            join(issue, {"provided_owner_hmac_pair_matched": True}, ref)
        with self.assertRaises(PrivateOpaqueIssueDenied):
            join(issue, "untrusted", ref)


if __name__ == "__main__":
    unittest.main()
