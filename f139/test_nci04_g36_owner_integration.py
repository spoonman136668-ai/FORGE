"""G36 original owner's disposable SQLite claim -> domain-signed V2 handoff.

This never reads the installed original F139 DB or executes a GitHub dispatch.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from f139.local_controller import Database
from f139.nci04_g36_v2_dispatch import (
    G36Denied, original_owner_v2_fields, verify_claim, authorize_v2,
)
from f139.test_nci04_g32_owner_custody import OriginalOwnerG32Tests
from f139.test_nci04_owner_issue import HMAC


class G36OriginalOwnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Authentic disposable SQLite admission after synthetic event 220.
        # Suppress only its final fake dispatch acknowledgment so the sample
        # remains in a real START_RISK pre-POST state.
        fixture = OriginalOwnerG32Tests()
        with mock.patch.object(Database, "dispatch_observed",
                               return_value=None):
            fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fx = fixture
        self.db = fixture.db
        self.issue = fixture.issue

    def test_one_original_owner_claim_can_sign_only_v2(self):
        before = self.db.meta()
        fields = original_owner_v2_fields(
            self.db, self.issue.ticket, owner_hmac_key=HMAC)
        self.assertEqual(fields["native_protocol"], "v2")
        self.assertGreater(int(fields["v2_original_event_seq"]), 220)
        self.assertGreater(int(fields["v2_claim_event_seq"]),
                           int(fields["v2_original_event_seq"]))
        proof = verify_claim(
            HMAC, self.issue, self.db.meta()["epoch"],
            int(fields["v2_original_event_seq"]),
            fields["v2_original_event_sha256"],
            int(fields["v2_claim_event_seq"]),
            fields["v2_claim_event_sha256"],
            fields["v2_owner_signature"])
        self.assertEqual(len(proof), 64)
        self.assertNotEqual(fields["signature"], fields["v2_owner_signature"])
        self.assertNotEqual(fields["native_signature"],
                            fields["v2_owner_signature"])
        self.assertNotIn(HMAC, repr(fields))
        self.assertEqual(self.db.meta(), before)
        self.db.verify()

    def test_after_post_original_custody_cannot_issue_second_v2_claim(self):
        self.db.dispatch_observed(self.issue.ticket)
        with self.assertRaisesRegex(G36Denied,
                                    "PRE_DISPATCH_START_RISK_REQUIRED"):
            original_owner_v2_fields(
                self.db, self.issue.ticket, owner_hmac_key=HMAC)

    def test_credentialled_job_rechecks_distinct_v2_owner_claim(self):
        fields = original_owner_v2_fields(
            self.db, self.issue.ticket, owner_hmac_key=HMAC)
        admission = self.fx.admissions["ubuntu-latest"]
        env = {
            "F139_NATIVE_PROTOCOL": "v2",
            "F139_RUNNER_OS": "ubuntu-latest",
            "F139_WORKER_HMAC_KEY": HMAC,
            "F139_ISSUE_NUMBER": str(self.issue.number),
            "F139_ISSUE_ID": str(self.issue.issue_id),
            "F139_BODY_SHA256": self.issue.issue_body_sha256,
            "F139_TICKET": self.issue.ticket,
            "F139_EPOCH": str(self.db.meta()["epoch"]),
            "F139_V2_ORIGINAL_EVENT_SEQ": fields["v2_original_event_seq"],
            "F139_V2_ORIGINAL_EVENT_SHA256":
                fields["v2_original_event_sha256"],
            "F139_V2_CLAIM_EVENT_SEQ": fields["v2_claim_event_seq"],
            "F139_V2_CLAIM_EVENT_SHA256": fields["v2_claim_event_sha256"],
            "F139_V2_OWNER_SIGNATURE": fields["v2_owner_signature"],
        }
        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
            "f139.nci04_g36_v2_dispatch.authorize",
            return_value={
                "native_intent_sha256": self.issue.candidate.intent_sha256,
                "native_target_tree": self.issue.candidate.target_tree_sha,
                "source_sha": self.issue.source_sha,
                "authorization_sha256": admission.authorization_sha256,
            }), mock.patch(
            "f139.nci04_g36_v2_dispatch.common_source",
            return_value=self.issue.source_sha), mock.patch(
            "f139.nci04_g36_v2_dispatch.native_provider_pin",
            return_value=(self.issue.candidate.target_commit,
                          self.issue.candidate.target_tree_sha)), mock.patch(
            "f139.nci04_g36_v2_dispatch.intent_raw",
            return_value=self.issue.intent_raw):
            result = authorize_v2()
            self.assertEqual(result["schema"],
                "forge.f139.nci04.v2-authorized-job.v1")
            self.assertFalse(result["scientific_first_use"])
            self.assertEqual(len(result["v2_owner_claim_sha256"]), 64)
            os.environ["F139_V2_OWNER_SIGNATURE"] = fields["native_signature"]
            with self.assertRaisesRegex(
                    G36Denied, "PRE_DISPATCH_SIGNATURE_REJECTED"):
                authorize_v2()

    def test_claim_is_read_only_and_does_not_start_another_controller(self):
        before = self.db.meta()
        task = self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",
            (self.issue.ticket,)).fetchone()
        original_owner_v2_fields(
            self.db, self.issue.ticket, owner_hmac_key=HMAC)
        after = self.db.conn.execute(
            "SELECT * FROM tasks WHERE ticket=?",
            (self.issue.ticket,)).fetchone()
        self.assertEqual(tuple(task), tuple(after))
        self.assertEqual(self.db.meta(), before)


if __name__ == "__main__":
    unittest.main()
