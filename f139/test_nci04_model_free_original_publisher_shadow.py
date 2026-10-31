"""H74 finite grammar through the *existing* at-most-once original publisher.

Mock Windows SingleOwner database and GitHub writer only. No runner dispatch,
real API mutation, original workstation touch, or scientific first-use.
The Yggdrasil original source comes from frozen genuine-byte fixtures.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from f139 import test_nci04_model_free_owner_session_shadow as _h73
from f139 import test_nci04_candidate_publisher as _publisher_fake
from f139.nci04_model_owner_publication import (
    ATTEMPT, SUCCESS, ModelDraftDenied, publish_model_once,
)


class ModelFreeOriginalPublisherShadowTests(unittest.TestCase):
    def setUp(self):
        fixture = _h73.OriginalOwnerSessionModelFreeShadowTests(
            "test_original_readonly_owner_request_response_compiles_finite_candidate")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.f = fixture
        self.db, self.api = fixture.db, fixture.provider
        self.epoch = dict(self.db.meta())
        # The *existing original* fake writer historically asserts its own
        # synthetic SOURCE blob. Bind that fixture assertion to the immutable
        # authenticated original Yggdrasil bytes for this isolated test.
        p = patch.object(_publisher_fake, "SOURCE", fixture.original)
        p.start()
        self.addCleanup(p.stop)
        self.session = fixture.request()
        response = fixture.response(self.session)
        self.assertEqual(len(response["selected"]), 1)
        self.item = response["selected"][0]
        self.raw_response = self.item["model_response_bytes"]

    def run_publisher(self, *, witness=lambda: True):
        return publish_model_once(
            self.db, self.api.get, self.f.steering.get,
            self.api.write, session=self.session["session"],
            raw_response=self.raw_response, owner_witness=witness)

    def rows(self, kind):
        return [json.loads(x["payload"]) for x in
                self.db.conn.execute("SELECT payload FROM events WHERE kind=? ORDER BY seq", (kind,))]

    def test_exact_genuine_source_publishes_one_mock_owner_draft_without_dispatch(self):
        out = self.run_publisher()
        self.assertEqual(out["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(out["pr_number"], 488)
        self.assertFalse(out["scientific_first_use"])
        self.assertFalse(out["worker_dispatched"])
        self.assertEqual([m for m, _ in self.api.write_calls], ["POST", "PUT", "POST"])
        self.assertEqual(self.db.meta()["head_seq"], self.epoch["head_seq"]+2)
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 1)
        self.assertIs(self.rows(ATTEMPT)[0]["retry_allowed"], False)
        self.assertEqual(hashlib.sha256(self.api.head_data).hexdigest(),
                         self.item["after_sha256"])
        self.assertEqual(self.api.head_data,
                         json.loads(self.raw_response)["candidate_source"].encode())
        self.assertTrue(self.api.pr["draft"])
        self.assertTrue(self.api.pr["title"].startswith("F139 autonomy DEV:"))
        note = json.loads(self.api.pr["body"])
        self.assertFalse(note["dispatch_authorized"])
        self.assertFalse(note["independent_scientific_acceptance"])
        self.assertFalse(note["scientific_first_use"])
        self.db.verify()

    def test_mock_owner_draft_same_candidate_rejected_after_first_success(self):
        self.assertEqual(self.run_publisher()["disposition"],
                         "MODEL_DRAFT_AUTHENTICATED")
        self.session = self.f.request()
        self.raw_response = self.f.response(self.session)["selected"][0]["model_response_bytes"]
        with self.assertRaisesRegex(ModelDraftDenied, "PREVIOUSLY_ATTEMPTED"):
            self.run_publisher()
        self.assertEqual(len(self.api.write_calls), 3)
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 1)

    def test_mock_ambiguous_remote_result_is_retained_and_never_retried(self):
        self.api.fail_after_reference = True
        first = self.run_publisher()
        self.assertEqual(first["disposition"], "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        self.assertFalse(first["worker_dispatched"])
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 0)
        self.assertEqual(len(self.api.write_calls), 2)
        self.api.fail_after_reference = False
        self.session = self.f.request()
        self.raw_response = self.f.response(self.session)["selected"][0]["model_response_bytes"]
        with self.assertRaisesRegex(ModelDraftDenied, "UNRESOLVED_REMOTE"):
            self.run_publisher()
        self.assertEqual(len(self.api.write_calls), 2)
        self.db.verify()

    def test_mock_unauthorized_witness_or_stale_git_never_writes(self):
        with self.assertRaisesRegex(ModelDraftDenied, "ORIGINAL_WINDOWS_OWNER"):
            self.run_publisher(witness=lambda: False)
        self.assertEqual(self.api.write_calls, [])
        self.api.parent_data += b"\n# changed after original request\n"
        with self.assertRaises(ValueError):
            self.run_publisher()
        self.assertEqual(self.api.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])
        self.assertEqual(self.db.meta(), self.epoch)


    def test_h75_unresolved_legacy_g3_attempt_fails_before_any_write(self):
        # Original G3 draft history is *separate* from model-free attempts.
        # An indeterminate earlier G3 remote write must block this new model
        # publication, even when the candidate/source itself is different.
        with self.db.transaction():
            self.db.event("G3_DRAFT_ATTEMPTED",
                          {"synthetic_unresolved_remote": True})
        self.db.verify()
        self.session = self.f.request()
        self.raw_response = self.f.response(self.session)["selected"][0]["model_response_bytes"]
        with self.assertRaisesRegex(ModelDraftDenied,
                                    "UNRESOLVED_G3_REMOTE_WRITE"):
            self.run_publisher()
        self.assertEqual(self.api.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])
        self.assertEqual(self.rows(SUCCESS), [])

    def test_h75_preexisting_owner_branch_ref_fails_before_any_write(self):
        # PR/branch identity cannot be inferred solely from a clear local
        # model history. The existing publisher must independently reject
        # a remote ref collision, even when the response validates.
        name = ("f139/auto-model-y-"
                + self.item["owner_candidate_identity"][:20]
                + "-" + self.api.parent[:12])
        self.api.reference = "refs/heads/" + name
        initial = dict(self.db.meta())
        with self.assertRaisesRegex(ModelDraftDenied,
                                    "REF_ALREADY_EXISTS"):
            self.run_publisher()
        self.assertEqual(self.db.meta(), initial)
        self.assertEqual(self.api.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])
        self.db.verify()


if __name__ == "__main__":
    unittest.main()
