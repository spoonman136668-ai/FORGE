"""Fresh worker claim/authorization/receipt compatibility; synthetic key only."""
from copy import deepcopy
import unittest

from f139.nci04_fresh_worker_protocol import (
    SOURCE, TARGET, TARGET_TREE, REPO, PREFIX, PROTOCOL, WORKFLOW,
    FreshProtocolDenied, make_claim, sign_claim, verify_signature,
    encode_bundle, decode_bundle, authenticate_provider, worker_context,
    admission_for_run, dispatch_arguments,
)
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import inspect_owner_issue
from f139 import test_nci04_fresh_worker_release_gate as fixture_module


class FreshWorkerProtocolTests(unittest.TestCase):
    def setUp(self):
        fixture = fixture_module.FreshWorkerReleaseGateTests(
            "test_exact_source_issue_and_ref_are_readonly_only")
        fixture.setUp()
        self.fixture = fixture
        self.raw_issue = deepcopy(fixture.routes[fixture.issue_route])
        self.issue = inspect_owner_issue(
            self.raw_issue, protected_main=SOURCE,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TARGET_TREE)
        self.raw = self.issue.intent_raw
        self.release = "a" * 40
        self.tree = "b" * 40
        self.key = "fictional-unit-test-only-key-" * 2
        self.claim = make_claim(
            self.issue, release_sha=self.release, release_tree=self.tree,
            admission_seq=3, admission_sha="c" * 64,
            claim_seq=5, claim_sha="d" * 64)
        self.branch = "repos/" + REPO + "/branches/" + PREFIX + self.release
        self.routes = deepcopy(fixture.routes)
        self.routes[self.branch] = {
            "name": PREFIX + self.release, "protected": True,
            "commit": {"sha": self.release},
        }
        self.routes["repos/" + REPO + "/git/commits/" + self.release] = {
            "sha": self.release, "tree": {"sha": self.tree},
        }

    def get(self, route):
        return deepcopy(self.routes[route])

    def context(self):
        return {
            "GITHUB_REPOSITORY": REPO, "GITHUB_ACTOR": "spoonman136668-ai",
            "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_REF": "refs/heads/" + PREFIX + self.release,
            "GITHUB_SHA": self.release,
            "GITHUB_WORKFLOW_REF": REPO + "/.github/workflows/" + WORKFLOW
                + "@refs/heads/" + PREFIX + self.release,
            "F139_SOURCE_SHA": self.release, "F139_TICKET": self.issue.ticket,
            "F139_LANE": self.issue.lane, "F139_EPOCH": "1",
            "F139_FRESH_PROTOCOL": PROTOCOL, "F139_RUNNER_OS": "ubuntu-latest",
            "GITHUB_RUN_ID": "999",
        }

    def test_distinct_release_genuine_low_sequence_and_signed_receipt_identity(self):
        signed = sign_claim(self.key, self.claim, self.raw)
        commitment = verify_signature(self.key, self.claim, self.raw, signed)
        self.assertEqual(commitment, digest(canonical(self.claim)))
        self.assertEqual(authenticate_provider(self.claim, self.raw, self.get), self.issue)
        bundle = encode_bundle(self.claim, self.raw)
        claim, raw, candidate = decode_bundle(bundle)
        self.assertEqual((claim, raw, candidate), (self.claim, self.raw, self.issue.candidate))
        self.assertEqual(worker_context(self.context(), claim, label="ubuntu-latest"), 999)
        admission = admission_for_run(claim, raw, commitment=commitment,
                                      run_id=999, oslabel="ubuntu-latest")
        self.assertEqual(admission.source_sha, SOURCE)
        self.assertEqual(admission.authorization_sha256, commitment)
        self.assertEqual(admission.ticket, self.issue.ticket)

    def test_release_and_claim_hashes_are_signature_bound(self):
        signed = sign_claim(self.key, self.claim, self.raw)
        for field, value in (("worker_release_sha", "e" * 40),
                             ("worker_release_tree", "f" * 40),
                             ("claim_sha256", "e" * 64),
                             ("admission_sha256", "f" * 64)):
            with self.subTest(field=field):
                claim = dict(self.claim, **{field: value})
                with self.assertRaises(FreshProtocolDenied):
                    verify_signature(self.key, claim, self.raw, signed)

    def test_historical_protocol_and_authority_flags_cannot_be_reinterpreted(self):
        for field, value in (("admission_seq", 323), ("claim_seq", 3), ("claim_seq", 4),
                             ("worker_release_sha", SOURCE),
                             ("scientific_first_use", True),
                             ("model_continuation_authorized", True),
                             ("paid_model_calls", 1), ("epoch", True)):
            with self.subTest(field=field):
                with self.assertRaises(FreshProtocolDenied):
                    sign_claim(self.key, dict(self.claim, **{field: value}), self.raw)

    def test_provider_and_run_drift_rejected(self):
        self.routes[self.branch]["protected"] = False
        with self.assertRaises(FreshProtocolDenied):
            authenticate_provider(self.claim, self.raw, self.get)
        for field, value in (("GITHUB_SHA", SOURCE), ("GITHUB_RUN_ATTEMPT", "2"),
                             ("GITHUB_REF", "refs/heads/main"),
                             ("F139_TICKET", "unrelated")):
            with self.subTest(field=field):
                env = dict(self.context(), **{field: value})
                with self.assertRaises(FreshProtocolDenied):
                    worker_context(env, self.claim, label="ubuntu-latest")

    def test_worker_cannot_change_authenticated_commitment(self):
        with self.assertRaises(FreshProtocolDenied):
            admission_for_run(self.claim, self.raw, commitment="f" * 64,
                              run_id=999, oslabel="ubuntu-latest")


    def test_transport_uses_executable_release_not_immutable_admission_source(self):
        args = dispatch_arguments(self.key, self.claim, self.raw)
        self.assertIn("ref=" + PREFIX + self.release, args)
        self.assertIn("inputs[source_sha]=" + self.release, args)
        self.assertIn("inputs[ticket]=" + self.issue.ticket, args)
        self.assertIn("inputs[target_package]=" + PROTOCOL, args)
        self.assertNotIn(self.key, repr(args))
        encoded = next(x.split("=", 1)[1] for x in args
                       if x.startswith("inputs[native_bundle]="))
        claim, raw, _ = decode_bundle(encoded)
        self.assertEqual(claim["admission_source_sha"], SOURCE)
        self.assertEqual(raw, self.raw)



if __name__ == "__main__":
    unittest.main()
