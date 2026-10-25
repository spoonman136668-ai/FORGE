"""G36 pre-dispatch V2 owner-only signatures, source-only negative contracts."""
from dataclasses import replace
import os
import unittest
from unittest import mock

from f139.nci04_owner_issue import NativeIssue
from f139.nci04_g36_v2_dispatch import (
    G36Denied, signature, verify_claim, original_owner_v2_fields,
    authorize_v2, execute_v2,
)
from f139.nci04_worker_v2 import SOURCE_SHA, SOURCE_TREE
from f139.test_nci04_owner_issue import HMAC
from f139.test_nci04_worker_v2 import V2ContractTests

SOURCE = "e"*40


class G36OwnerV2Tests(unittest.TestCase):
    def setUp(self):
        f = V2ContractTests()
        f.setUp()
        self.c = f.c
        self.issue = NativeIssue(
            number=933, issue_id=6010000333,
            ticket="f139-nci04-i933-" + SOURCE[:12] + "-" +
                   self.c.intent_sha256[:8],
            lane="Yggdrasil", source_sha=SOURCE,
            issue_body_sha256="b"*64,
            native_intent_sha256=self.c.intent_sha256,
            qualification_key=self.c.qualification_key,
            intent_raw=b"", candidate=self.c)
        self.kw = (6, 221, "a"*64, 222, "c"*64)

    def test_v2_only_owner_signature_bound_to_two_new_original_events(self):
        sig = signature(HMAC, self.issue, *self.kw)
        self.assertEqual(len(sig), 64)
        bound = verify_claim(HMAC, self.issue, *self.kw, sig)
        self.assertEqual(len(bound), 64)
        self.assertEqual(bound, verify_claim(HMAC, self.issue, *self.kw, sig))
        self.assertNotEqual(sig, "f"*64)

    def test_old_event_and_same_event_claim_are_denied(self):
        for values in ((6, 220, "a"*64, 221, "b"*64),
                       (6, 221, "a"*64, 221, "b"*64),
                       (6, 221, "a"*64, 220, "b"*64)):
            with self.subTest(values=values), self.assertRaisesRegex(
                    G36Denied, "FRESH_YGG"):
                signature(HMAC, self.issue, *values)

    def test_version_domain_and_changed_owner_binding_fail(self):
        sig = signature(HMAC, self.issue, *self.kw)
        for values in ((7, 221, "a"*64, 222, "c"*64),
                       (6, 222, "a"*64, 223, "c"*64),
                       (6, 221, "0"*64, 222, "c"*64),
                       (6, 221, "a"*64, 223, "c"*64)):
            with self.subTest(values=values), self.assertRaisesRegex(
                    G36Denied, "PRE_DISPATCH_SIGNATURE"):
                verify_claim(HMAC, self.issue, *values, sig)
        with self.assertRaises(G36Denied):
            verify_claim(HMAC, replace(self.issue, number=934), *self.kw, sig)
        with self.assertRaisesRegex(G36Denied, "PRE_DISPATCH_SIGNATURE"):
            verify_claim("z"*64, self.issue, *self.kw, sig)

    def test_v1_native_signed_ticket_does_not_authorize_v2(self):
        from f139.nci04_owner_issue import make_signed_dispatch_inputs
        v1 = make_signed_dispatch_inputs(
            self.issue, owner_hmac_key=HMAC, epoch=6)
        for candidate in (v1["signature"], v1["native_signature"]):
            with self.assertRaisesRegex(G36Denied,
                                        "PRE_DISPATCH_SIGNATURE"):
                verify_claim(HMAC, self.issue, *self.kw, candidate)

    def test_wrong_native_source_path_or_lane_rejected(self):
        for changes in (
            {"lane": "Wingless"},
            {"target_commit": "0"*40},
            {"target_tree_sha": "0"*40},
            {"path": "changed.py"},
        ):
            with self.subTest(changes=changes), self.assertRaises(G36Denied):
                c = replace(self.c, **changes)
                signature(HMAC, replace(self.issue, candidate=c), *self.kw)

    def test_invalid_original_db_cannot_sign(self):
        with self.assertRaisesRegex(G36Denied, "ORIGINAL_DATABASE"):
            original_owner_v2_fields(
                None, self.issue.ticket, owner_hmac_key=HMAC)

    def test_plain_v1_job_does_not_authorize_v2(self):
        with mock.patch.dict(os.environ, {
            "F139_NATIVE_PROTOCOL": "v1",
            "F139_RUNNER_OS": "ubuntu-latest"
        }, clear=True):
            with self.assertRaisesRegex(G36Denied,
                                        "V2_CREDENTIALLED_AUTH_JOB_REQUIRED"):
                authorize_v2()

    def test_v2_worker_requires_separate_auth_job_before_checkout(self):
        with mock.patch.dict(os.environ, {
            "F139_NATIVE_PROTOCOL": "v1"
        }, clear=True), mock.patch(
            "f139.nci04_g36_v2_dispatch.common_source",
            return_value=SOURCE):
            with self.assertRaisesRegex(G36Denied, "V2_AUTH_JOB"):
                execute_v2("no-native", "no-scratch", "no-output")

    def test_real_v1_worker_entrypoint_unchanged(self):
        from f139.nci04_worker_entry import cli
        import inspect
        self.assertIn('commands.add_parser("execute")', inspect.getsource(cli))
        self.assertNotIn("execute-v2", inspect.getsource(cli))


if __name__ == "__main__":
    unittest.main()
