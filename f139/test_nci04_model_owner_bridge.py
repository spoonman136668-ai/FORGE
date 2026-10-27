"""Isolated original-owner request/response bridge qualification; no live writes."""
import json
import unittest
from unittest.mock import patch

from f139.nci04_model_owner_bridge import (
    OwnerModelDenied, owner_history, owner_request, owner_response)
from f139.nci04_model_proposal import SCHEMA as MODEL_SCHEMA
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139 import nci04_research_steering as steering
from f139.test_nci04_autonomy_feed import FakeProvider
from f139.test_nci04_research_steering import SteeringProvider
from test_nci04_owner_ledger import LedgerTests, MAIN


class OriginalOwnerModelBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = self.fixture.db
        self.assertTrue(activate_native(self.db, self.fixture.approval()))
        self.provider = FakeProvider()
        self.provider.source = MAIN
        self.steering = SteeringProvider()
        patcher = patch.object(steering, "DOCUMENTS", self.steering.documents)
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self, *, owner_witness=lambda: True):
        return dict(source_sha=MAIN, lane="Wingless",
                    target_commit=self.provider.parent,
                    path=self.provider.path, owner_witness=owner_witness)

    def begin(self):
        return owner_request(self.db, self.provider.get, self.steering.get,
                             **self.args())

    def respond(self, snapshot, *, source=None):
        candidate_source = (source if source is not None else
                            "package cognition\nfunc Old(){return}\n")
        response = json.dumps({
            "schema": MODEL_SCHEMA, "lane": "Wingless",
            "target_commit": self.provider.parent, "path": self.provider.path,
            "history_sha256": snapshot["history_sha256"],
            "question": "Does local evidence improve an action?",
            "hypothesis": "Retained state improves local action choice.",
            "control": "Compare to an equal-information fixed-state control.",
            "candidate_source": candidate_source,
        }).encode("utf-8")
        return owner_response(
            self.db, self.provider.get, self.steering.get,
            session=snapshot, raw_response=response, owner_witness=lambda: True)

    def test_original_owner_request_and_response_do_not_write_or_dispatch(self):
        prior = self.db.meta()
        result = self.begin()
        self.assertEqual(result["request"]["controller_source_sha"], MAIN)
        self.assertEqual(result["request"]["target_tree_sha"], self.provider.parent_tree)
        self.assertEqual(result["request"]["history"], [])
        self.assertEqual(self.db.meta(), prior)
        compiled = self.respond(result["session"])
        self.assertEqual(self.db.meta(), prior)
        self.assertEqual(compiled["record"]["lane"], "Wingless")
        self.assertFalse(compiled["proposal"]["dispatch_authorized"])
        self.assertFalse(compiled["proposal"]["eligible"])
        self.assertFalse(compiled["publication_authorized"])
        self.assertFalse(compiled["scientific_first_use"])
        self.assertFalse(compiled["worker_dispatched"])

    def test_original_owner_witness_and_activation_fail_closed(self):
        with self.assertRaisesRegex(OwnerModelDenied, "WITNESS_REQUIRED"):
            owner_request(self.db, self.provider.get, self.steering.get,
                          **self.args(owner_witness=lambda: False))
        # Exact source, not the moving main branch, must match original ledger.
        with self.assertRaisesRegex(OwnerModelDenied, "NOT_IDLE_OR_ACTIVATED"):
            owner_request(self.db, self.provider.get, self.steering.get,
                          **dict(self.args(), source_sha="f" * 40))

    def test_pending_original_work_prevents_advisory_model_intake(self):
        self.assertTrue(admit_native_issue(
            self.db, self.fixture.native, "2026-10-27T09:00:00Z"))
        with self.assertRaisesRegex(OwnerModelDenied, "NOT_IDLE_OR_ACTIVATED"):
            self.begin()

    def test_negative_history_is_kept_and_cross_lane_replay_rejected(self):
        self.assertTrue(admit_native_issue(
            self.db, self.fixture.native, "2026-10-27T09:00:00Z"))
        ticket = self.fixture.native.ticket
        self.db.claim(ticket, "2026-10-27T09:01:00Z")
        self.db.quarantine(ticket, "EXPERIMENT_FAILED")
        history = owner_history(self.db)
        self.assertEqual(len(history["history"]), 1)
        self.assertEqual(history["history"][0]["outcome"], "QUARANTINED")
        self.assertEqual(len(history["consumed_candidates"]), 1)
        self.assertEqual(len(history["consumed_after_hashes"]), 1)
        snapshot = self.begin()
        self.assertEqual(snapshot["request"]["history"][0]["outcome"], "QUARANTINED")
        # Same bytes, different lane/parent: consumed output hash still denied.
        repeated = self.fixture.native.candidate.after_bytes.decode("utf-8")
        with self.assertRaisesRegex(ValueError, "PREVIOUSLY_CONSUMED"):
            self.respond(snapshot["session"], source=repeated)

    def test_new_original_event_invalidates_outstanding_model_response(self):
        prepared = self.begin()
        with self.db.transaction():
            self.db.event("FIXTURE_UNTRUSTED", {"fixture_sequence": 200})
        with self.assertRaisesRegex(OwnerModelDenied, "SESSION_STALE"):
            self.respond(prepared["session"])

    def test_target_source_move_invalidates_outstanding_response(self):
        prepared = self.begin()
        self.provider.before = b"package cognition\nfunc Old(){ /* moved */ }\n"
        with self.assertRaisesRegex(OwnerModelDenied, "SESSION_STALE"):
            self.respond(prepared["session"])

    def test_spoofed_history_binding_and_authority_rejected(self):
        prepared = self.begin()
        session = dict(prepared["session"], history_sha256="f" * 64)
        with self.assertRaisesRegex(OwnerModelDenied, "SESSION_STALE"):
            self.respond(session)
        session = dict(prepared["session"], publication_authorized=True)
        with self.assertRaisesRegex(OwnerModelDenied, "SESSION_INVALID"):
            self.respond(session)

    def test_steering_ambiguity_denies_instead_of_guessing(self):
        prepared = self.begin()
        original_get = self.steering.get
        def poisoned_get(route):
            response = original_get(route)
            if route.endswith("CORE-NATIVE-INTELLIGENCE.md?ref=" +
                              steering.MERGED_STEERING_COMMIT):
                return dict(response, sha="0" * 40)
            return response
        with self.assertRaises(ValueError):
            owner_request(self.db, self.provider.get, poisoned_get,
                          **self.args())
        self.assertEqual(self.db.meta()["head_hash"],
                         prepared["session"]["owner_head_sha256"])


if __name__ == "__main__":
    unittest.main()
