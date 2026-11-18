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
import test_nci04_owner_ledger as fixture_owner_ledger
from test_nci04_owner_ledger import MAIN


class OriginalOwnerModelBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_owner_ledger.LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
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

    def _two_original_quarantined_issues_same_candidate(self):
        """Real isolated append-only admissions, distinct tickets and receipts."""
        from f139.nci04_owner_issue import inspect_owner_issue
        from test_nci04_owner_issue import issue as make_issue, TARGET, TREE
        self.assertTrue(admit_native_issue(
            self.db, self.fixture.native, "2026-10-27T09:00:00Z"))
        first = self.fixture.native.ticket
        self.db.claim(first, "2026-10-27T09:01:00Z")
        self.db.quarantine(first, "EXPERIMENT_FAILED")
        raw = make_issue()
        raw["number"], raw["id"] = 703, 5951234568
        second = inspect_owner_issue(
            raw, protected_main=MAIN,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TREE)
        self.assertNotEqual(first, second.ticket)
        self.assertTrue(admit_native_issue(
            self.db, second, "2026-10-27T09:03:00Z"))
        self.db.claim(second.ticket, "2026-10-27T09:04:00Z")
        self.db.quarantine(second.ticket, "EXPERIMENT_FAILED")
        self.db.verify()
        return first, second.ticket

    def test_repeated_authentic_candidate_history_retains_both_negative_tickets(self):
        from f139.nci04_owner_ledger import native_events
        from f139.nci04_native_contract import canonical, digest
        first, second = self._two_original_quarantined_issues_same_candidate()
        events = native_events(self.db)
        self.assertEqual(len(events), 2)
        self.assertEqual({x["ticket"] for x in events}, {first, second})
        original = self.db.meta()
        h = owner_history(self.db)
        self.assertEqual(len(h["history"]), 1)
        self.assertEqual(h["history"][0]["outcome"], "QUARANTINED")
        self.assertIn("2 distinct issues", h["history"][0]["summary"])
        self.assertEqual(len(h["consumed_candidates"]), 1)
        self.assertEqual(len(h["consumed_after_hashes"]), 1)
        # Every ticket survives, in original append-only order, in the
        # source-bound history identity. Grouping changes only advisor view.
        full = [
            {"candidate_identity": h["history"][0]["candidate_identity"],
             "after_sha256": x["after_sha256"], "outcome": "QUARANTINED",
             "ticket": x["ticket"]} for x in events
        ]
        self.assertEqual(h["history_sha256"], digest(canonical({
            "schema": "forge.f139.owner-model-retained-history.v1",
            "head_seq": original["head_seq"], "head_hash": original["head_hash"],
            "all_original_native_outcomes": full,
        })))
        self.assertEqual(self.db.meta(), original)
        self.assertEqual(self.begin()["request"]["history"], h["history"])
        with self.assertRaisesRegex(ValueError, "PREVIOUSLY_CONSUMED"):
            self.respond(self.begin()["session"],
                         source=self.fixture.native.candidate.after_bytes.decode("utf-8"))

    def test_duplicate_ticket_and_conflicting_after_hash_still_fail_closed(self):
        from f139.nci04_owner_ledger import native_events
        first, second = self._two_original_quarantined_issues_same_candidate()
        events = native_events(self.db)
        with patch("f139.nci04_model_owner_bridge.native_events",
                   return_value=events + [events[0]]):
            with self.assertRaisesRegex(OwnerModelDenied,
                                        "REPEATED_OR_INVALID_CANDIDATE"):
                owner_history(self.db)
        forged = dict(events[1], after_sha256="0"*64)
        with patch("f139.nci04_model_owner_bridge.native_events",
                   return_value=[events[0], forged]):
            with self.assertRaisesRegex(OwnerModelDenied,
                                        "REPEATED_OR_INVALID_CANDIDATE"):
                owner_history(self.db)
        self.db.verify()

    def test_conflicting_synthetic_outcomes_are_mixed_not_verified(self):
        # The original ledger itself remains immutable in production. This
        # isolated fixture models an authenticated mixed outcome projection;
        # only the synthetic Database.verify call is patched here.
        from f139.nci04_owner_ledger import native_events
        first, second = self._two_original_quarantined_issues_same_candidate()
        self.db.conn.execute(
            "UPDATE tasks SET stage='VERIFIED',run_id=123456,"
            "evidence_sha=? WHERE ticket=?", ("d"*64, second))
        with patch.object(type(self.db), "verify", return_value=None):
            h = owner_history(self.db)
        self.assertEqual(len(h["history"]), 1)
        self.assertEqual(h["history"][0]["outcome"], "MIXED")
        self.assertIn("QUARANTINED", h["history"][0]["summary"])
        self.assertIn("VERIFIED", h["history"][0]["summary"])
        self.assertEqual(len(h["consumed_candidates"]), 1)
        self.assertEqual(len(h["consumed_after_hashes"]), 1)

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
