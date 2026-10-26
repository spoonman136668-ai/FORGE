"""G37 local original-owner compact native V2 dispatch proof."""
from __future__ import annotations

import base64
import json
import unittest
from unittest import mock

from f139.local_controller import Database, GitHub
from f139.nci04_g36_v2_dispatch import original_owner_v2_fields
from f139.nci04_owner_issue import make_signed_dispatch_inputs
from f139.test_nci04_g32_owner_custody import OriginalOwnerG32Tests
from f139.test_nci04_owner_issue import HMAC


class OriginalG37PayloadTests(unittest.TestCase):
    def setUp(self):
        fx = OriginalOwnerG32Tests()
        with mock.patch.object(Database, "dispatch_observed", return_value=None):
            fx.setUp()
        self.addCleanup(fx.doCleanups)
        self.fx = fx
        self.sent = []
        self.api = GitHub(runner=lambda argv: self.sent.append(tuple(argv)))
        # The original authenticated source ref is a read-only GitHub GET;
        # no extra workflow POST and no ref move is permitted.
        source=self.fx.issue.source_sha
        branch="f139-owner-release-"+source
        def pinned(route):
            self.assertEqual(route,
                "repos/spoonman136668-ai/FORGE/branches/"+branch)
            return {"name":branch,"commit":{"sha":source}}
        self.api.native_repo_get=pinned

    def decode(self):
        self.assertEqual(len(self.sent), 1)
        self.assertIn("ref=f139-owner-release-"+self.fx.issue.source_sha,
                      self.sent[0])
        parts = [x for x in self.sent[0] if x.startswith("inputs[")]
        data = {key[7:]: val for key, val in
                (part.split("]=", 1) for part in parts)}
        self.assertEqual(len(data), len(parts))
        return data, json.loads(base64.b64decode(
            data["native_bundle"], validate=True))

    def test_existing_v1_payload_retained(self):
        original = make_signed_dispatch_inputs(
            self.fx.issue, owner_hmac_key=HMAC, epoch=self.fx.db.meta()["epoch"])
        self.api.dispatch_native(original, self.fx.issue)
        fields, data = self.decode()
        self.assertEqual(len(fields), 6)
        self.assertNotIn("target_package", fields)
        self.assertEqual(len(data), 8)
        self.assertNotIn("v2_owner_signature", data)
        self.assertNotIn(HMAC, repr(self.sent))

    def test_fresh_original_claim_uses_seven_of_ten_inputs(self):
        original = original_owner_v2_fields(
            self.fx.db, self.fx.issue.ticket, owner_hmac_key=HMAC)
        self.api.dispatch_native(original, self.fx.issue)
        fields, data = self.decode()
        self.assertEqual(len(fields), 7)
        self.assertEqual(fields["target_package"], "f139-nci04-v2")
        self.assertEqual(len(data), 13)
        self.assertEqual(data["v2_owner_signature"],
                         original["v2_owner_signature"])
        self.assertGreater(int(data["v2_claim_event_seq"]),
                           int(data["v2_original_event_seq"]))
        self.assertNotIn(HMAC, repr(self.sent))

    def test_incomplete_v2_claim_denied_without_post(self):
        fields = original_owner_v2_fields(
            self.fx.db, self.fx.issue.ticket, owner_hmac_key=HMAC)
        fields.pop("v2_owner_signature")
        with self.assertRaises(Exception):
            self.api.dispatch_native(fields, self.fx.issue)
        self.assertEqual(self.sent, [])

    def test_old_v1_signature_never_authorizes_v2(self):
        fields = make_signed_dispatch_inputs(
            self.fx.issue, owner_hmac_key=HMAC, epoch=self.fx.db.meta()["epoch"])
        fields["native_protocol"] = "v2"
        with self.assertRaises(Exception):
            self.api.dispatch_native(fields, self.fx.issue)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
