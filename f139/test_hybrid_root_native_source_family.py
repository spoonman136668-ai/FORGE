"""Synthetic negative controls for genuine private Hybrid P-number native source paths.

No private project source, ticket, HMAC key, native training or workers here.
Root source family is narrow and identical across the native candidate and
private artifact reference validators. Actual private Git provider custody must
still be checked independently of any local or test-supplied mapping.
"""
import hashlib
import json
import unittest

from f139.nci04_native_contract import (
    NativeContractError, REPOS, canonical as native_canonical,
    model_source_path_allowed, parse_intent,
)
from f139.private_hybrid_reference import (
    PATH, PrivateReferenceDenied, canonical as reference_canonical,
    parse_reference,
)
from f139.private_hybrid_opaque_issue import (
    PrivateOpaqueIssueDenied, prepare_private_provider_commitment,
)
from f139 import test_private_hybrid_reference as fixtures
from f139.test_private_hybrid_opaque_issue import synthetic_candidate_revision
from f139.nci04_native_worker import COMMANDS, commands_for


def blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def example(path="native_p00_synthetic.py"):
    ref, original_payload, observed = (
        fixtures.PrivatePayloadCustodyTests.fixture())
    private_intent = json.loads(original_payload)
    private_intent["path"] = path
    payload = native_canonical(private_intent)
    payload_sha = hashlib.sha256(payload).hexdigest()
    observed = {
        **observed,
        "path": "f139/private-native/" + payload_sha + ".json",
        "git_blob_sha": blob(payload),
    }
    before = b"def synthetic():\\n    return 0\\n"
    original_file = {
        "repository": fixtures.REPOSITORY,
        "commit_sha": fixtures.COMMIT,
        "tree_sha": fixtures.TREE,
        "path": path,
        "git_blob_sha": blob(before),
    }
    return ref, payload, before, original_file, observed


class HybridRootNativeEligibilityTests(unittest.TestCase):
    def test_root_project_p_number_family_only_for_private_hybrid(self):
        positives = (
            "native_p00_synthetic.py",
            "native_p64k_synthetic.py",
            "native_p64s_synthetic.py",
            "native_p99_state_v2.py",
        )
        for p in positives:
            with self.subTest(path=p):
                self.assertTrue(model_source_path_allowed("TTT-Hybrid", p))
                self.assertIsNotNone(PATH.fullmatch(p))
                self.assertFalse(model_source_path_allowed("Yggdrasil", p))
                self.assertFalse(model_source_path_allowed("Wingless", p))

    def test_no_generic_root_extension_imports_or_neighboring_repos(self):
        negatives = (
            "native_random.py", "native_p.py", "native_p1_fake.py",
            "native_p999_fake.py", "native_p64K_fake.py", "native_p64k.py",
            "native_p64k_synthetic.py.bak", "native_p64k_example.PY",
            "native_p64k__\\evil.py", "native_p64k_../key.py",
            "native_p64k_X.py", "native_p64k_.py",
            "native_p64k_example.go", "native_p64k_example.py/evil",
            "../native_p64k_test.py", "/native_p64k_test.py",
            "native_p64k_test.py/..", "other/native_p64k_test.py",
            ".github/workflows/native_p64k_test.py",
            "scripts/private_models.py", "model.py", "authentic_hybrid.py",
            "native_p64k_test.py;touch-key",
        )
        for p in negatives:
            with self.subTest(path=p):
                self.assertFalse(model_source_path_allowed("TTT-Hybrid", p))
                self.assertIsNone(PATH.fullmatch(p))

    def test_parser_and_reference_agree_on_native_synthetic_original(self):
        for path in ("native_p00_synthetic.py", "native_p64k_synthetic.py"):
            with self.subTest(path=path):
                ref, payload, before, target, stored = example(path)
                source = parse_intent(
                    payload, protected_main=fixtures.OWNER,
                    target_commit=fixtures.COMMIT, target_tree_sha=fixtures.TREE)
                self.assertEqual(source.path, path)
                self.assertEqual(source.materialize_bytes(before),
                                 b"def synthetic():\\n    return 1\\n")
                ref.update({
                    "source_path": path,
                    "private_payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "owner_signed_intent_sha256": hashlib.sha256(payload).hexdigest(),
                    "private_payload_path": stored["path"],
                    "private_payload_blob_sha": stored["git_blob_sha"],
                })
                checked = parse_reference(
                    reference_canonical(ref), owner_source_sha=fixtures.OWNER,
                    private_commit=fixtures.COMMIT, private_tree=fixtures.TREE,
                    authenticated_repository_metadata=fixtures.MD)
                self.assertEqual(checked["source_path"], path)
                after, head, comparison = synthetic_candidate_revision(payload, target)
                output = prepare_private_provider_commitment(
                    payload, before, after, owner_source_sha=fixtures.OWNER,
                    authenticated_repository_metadata=fixtures.MD,
                    authenticated_target_commit=fixtures.COMMIT,
                    authenticated_target_tree=fixtures.TREE,
                    authenticated_target_file=target,
                    authenticated_storage_file=stored,
                    authenticated_candidate_file=head,
                    authenticated_candidate_comparison=comparison)
                public = json.loads(output["issue_body"])
                self.assertEqual(public["private_payload_sha256"],
                                 hashlib.sha256(payload).hexdigest())
                self.assertTrue(output["real_baseline_blob_bytes_matched"])
                self.assertFalse(output["original_owner_live_issue_verified"])
                for private_only in ("source_path", "intent_base64",
                                     "after_base64", "owner_authorization_sha256",
                                     "private_payload_path", path):
                    self.assertNotIn(private_only, output["issue_body"])

    def test_hybrid_fixed_worker_compiles_root_native_and_preserves_full_suite(self):
        # Source path is synthetic: never embed or emit an actual private module.
        _, payload, _, _, _ = example("native_p64k_synthetic.py")
        candidate = parse_intent(
            payload, protected_main=fixtures.OWNER,
            target_commit=fixtures.COMMIT, target_tree_sha=fixtures.TREE)
        fixed = commands_for(candidate)
        self.assertEqual(fixed, COMMANDS["TTT-Hybrid"])
        self.assertEqual(fixed[0], (
            "python", "-B", "-m", "pytest", "-q", "tests/test_model.py"))
        self.assertEqual(fixed[1], (
            "python", "-B", "-m", "pytest", "-q"))
        self.assertEqual(fixed[-1], (
            "python", "-B", "-m", "compileall", "-q", "."))
        self.assertFalse(any(candidate.path in argv for argv in fixed))
        self.assertFalse(any("after_base64" in argv for argv in fixed))
        self.assertEqual(len(fixed), 3)
        # Existing native tests are not bypassed by compiling root files.
        self.assertEqual(fixed[1][-2:], ("pytest", "-q"))

    def test_wrong_private_path_cannot_be_laundered_through_reference(self):
        for path in ("native_random.py", "model.py",
                     "native_p64k_synthetic.py/../secret"):
            with self.subTest(path=path):
                ref, payload, before, target, stored = example(path)
                with self.assertRaises(NativeContractError):
                    parse_intent(
                        payload, protected_main=fixtures.OWNER,
                        target_commit=fixtures.COMMIT,
                        target_tree_sha=fixtures.TREE)
                ref.update({"source_path": path})
                with self.assertRaises(PrivateReferenceDenied):
                    parse_reference(
                        reference_canonical(ref),
                        owner_source_sha=fixtures.OWNER,
                        private_commit=fixtures.COMMIT,
                        private_tree=fixtures.TREE,
                        authenticated_repository_metadata=fixtures.MD)
                after, head, comparison = synthetic_candidate_revision(payload, target)
                with self.assertRaises(PrivateOpaqueIssueDenied):
                    prepare_private_provider_commitment(
                        payload, before, after, owner_source_sha=fixtures.OWNER,
                        authenticated_repository_metadata=fixtures.MD,
                        authenticated_target_commit=fixtures.COMMIT,
                        authenticated_target_tree=fixtures.TREE,
                        authenticated_target_file=target,
                        authenticated_storage_file=stored,
                        authenticated_candidate_file=head,
                        authenticated_candidate_comparison=comparison)


if __name__ == "__main__":
    unittest.main()
