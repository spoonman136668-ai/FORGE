"""Mock original-owner model publication: no real GitHub, runner or local owner."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import GitHub
from f139.nci04_model_owner_publication import (
    ATTEMPT, SUCCESS, ModelDraftDenied, publish_model_once)
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_model_proposal import SCHEMA as MODEL_SCHEMA
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139 import nci04_research_steering as steering
from f139.test_nci04_candidate_producer import SOURCE
from f139.test_nci04_candidate_publisher import FakeOriginalOwner
from f139.test_nci04_research_steering import SteeringProvider
from test_nci04_owner_ledger import LedgerTests, MAIN


class OwnerModelPublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.assertTrue(activate_native(self.db, fixture.approval()))
        self.provider = FakeOriginalOwner()
        self.provider.source = MAIN
        self.steering = SteeringProvider()
        steering_patch = patch.object(steering, "DOCUMENTS", self.steering.documents)
        steering_patch.start()
        self.addCleanup(steering_patch.stop)

    def snapshot(self, witness=lambda: True):
        return owner_request(
            self.db, self.provider.get, self.steering.get, source_sha=MAIN,
            lane="Yggdrasil", target_commit=self.provider.parent,
            path=self.provider.path, owner_witness=witness)

    def response(self, snapshot, *, source=None, lane="Yggdrasil"):
        changed = source if source is not None else (
            SOURCE.decode("utf-8") +
            "\n# prospective bounded retained-state comparison\n")
        return json.dumps({
            "schema": MODEL_SCHEMA, "lane": lane,
            "target_commit": self.provider.parent, "path": self.provider.path,
            "history_sha256": snapshot["session"]["history_sha256"],
            "question": "Can local memories reduce exploration errors?",
            "hypothesis": "Local count-memory improves decisions.",
            "control": "Matched conventional local-count policy.",
            "candidate_source": changed,
        }).encode("utf-8")

    def publish(self, snapshot=None, *, witness=lambda: True,
                source=None, writer=None):
        session = snapshot or self.snapshot()
        return publish_model_once(
            self.db, self.provider.get, self.steering.get,
            writer if writer is not None else self.provider.write,
            session=session["session"],
            raw_response=self.response(session, source=source),
            owner_witness=witness)

    def rows(self, kind):
        return [json.loads(r["payload"]) for r in self.db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq", (kind,))]

    def test_original_owner_single_model_draft_publication_and_no_dispatch(self):
        prepared = self.snapshot()
        old = self.db.meta()["head_seq"]
        result = self.publish(prepared)
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(result["pr_number"], 488)
        self.assertFalse(result["scientific_first_use"])
        self.assertFalse(result["worker_dispatched"])
        self.assertEqual(self.db.meta()["head_seq"], old + 2)
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 1)
        self.assertFalse(self.rows(ATTEMPT)[0]["retry_allowed"])
        self.assertEqual([m for m, _ in self.provider.write_calls],
                         ["POST", "PUT", "POST"])
        self.assertEqual(self.provider.head_data, (
            SOURCE.decode("utf-8") +
            "\n# prospective bounded retained-state comparison\n").encode())
        self.assertTrue(self.provider.pr["draft"])
        self.assertEqual(json.loads(self.provider.pr["body"])["schema"],
                         "forge.f139.owner-model-draft-note.v1")
        self.db.verify()

    def test_missing_original_owner_witness_forbids_any_write(self):
        with self.assertRaisesRegex(ModelDraftDenied, "ORIGINAL_WINDOWS_OWNER"):
            self.publish(witness=lambda: False)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])

    def test_moved_source_and_historical_head_forbid_any_write(self):
        snapshot = self.snapshot()
        self.provider.parent_data += b"\n# tampered upstream\n"
        with self.assertRaises(ValueError):
            self.publish(snapshot)
        self.assertFalse(self.provider.write_calls)
        self.assertFalse(self.rows(ATTEMPT))
        self.provider.parent_data = SOURCE
        snapshot = self.snapshot()
        with self.db.transaction():
            self.db.event("FIXTURE_UNTRUSTED", {"sequence": 234})
        with self.assertRaises(ValueError):
            self.publish(snapshot)
        self.assertFalse(self.provider.write_calls)

    def test_failed_git_write_is_at_most_once_and_suppresses_replays(self):
        original = self.snapshot()
        self.provider.fail_after_reference = True
        first = self.publish(original)
        self.assertEqual(first["disposition"],
                         "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 0)
        self.db.verify()
        self.provider.fail_after_reference = False
        with self.assertRaises(ValueError):
            self.publish(original)
        self.assertEqual(len(self.provider.write_calls), 2)
        with self.assertRaisesRegex(ModelDraftDenied, "UNRESOLVED_REMOTE"):
            self.publish(self.snapshot(), source=SOURCE.decode()+"\n# new one\n")
        self.assertEqual(len(self.provider.write_calls), 2)

    def test_repeated_published_source_is_never_republished(self):
        first = self.snapshot()
        self.assertEqual(self.publish(first)["disposition"],
                         "MODEL_DRAFT_AUTHENTICATED")
        self.provider.pr = None
        self.provider.reference = None
        self.provider.head_sha = None
        with self.assertRaisesRegex(ModelDraftDenied, "PREVIOUSLY_ATTEMPTED"):
            self.publish(self.snapshot())
        self.assertEqual(len(self.provider.write_calls), 3)

    def test_wrong_model_lane_rejected_without_remote_write(self):
        prepared = self.snapshot()
        with self.assertRaises(ValueError):
            publish_model_once(
                self.db, self.provider.get, self.steering.get,
                self.provider.write, session=prepared["session"],
                raw_response=self.response(prepared, lane="Wingless"),
                owner_witness=lambda: True)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])

    def test_negative_original_custody_is_not_erased(self):
        self.assertTrue(admit_native_issue(
            self.db, self.fixture.native, "2026-10-27T09:00:00Z"))
        t = self.fixture.native.ticket
        self.db.claim(t, "2026-10-27T09:01:00Z")
        self.db.quarantine(t, "PROSPECTIVE_NEGATIVE")
        snap = self.snapshot()
        self.assertEqual(snap["request"]["history"][0]["outcome"],
                         "QUARANTINED")
        result = self.publish(snap)
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(snap["request"]["history"][0]["outcome"],
                         "QUARANTINED")
        self.db.verify()

    def test_unauthorized_write_endpoints_rejected_before_network(self):
        api = GitHub(runner=lambda args: (_ for _ in ()).throw(
            AssertionError("network forbidden")))
        with self.assertRaisesRegex(Exception, "MODEL_WRITE_TARGET"):
            api.owner_model_write("POST", "repos/spoonman136668-ai/FORGE/issues",
                                  {"title": "bypass"})
        with self.assertRaisesRegex(Exception, "MODEL_SOURCE_WRITE"):
            api.owner_model_write(
                "PUT", "repos/spoonman136668-ai/Yggdrasil/contents/scripts/../secrets.py",
                {"message": "F139 MODEL DEV: owner-validated isolated source candidate",
                 "content": "YQ==", "sha": "a"*40,
                 "branch": "f139/auto-model-y-" + "a"*20 + "-" + "b"*12})


if __name__ == "__main__":
    unittest.main()
