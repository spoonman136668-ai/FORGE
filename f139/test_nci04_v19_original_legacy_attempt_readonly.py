"""V19 read-only ledger history; real SQLite fixture, mocked free provider."""
from __future__ import annotations

import tempfile
import unittest

from f139.local_controller import SingleOwner
from f139.nci04_v19_original_legacy_attempt_readonly import (
    original_legacy_attempt_snapshot, ShadowDenied, FREE,
)
from f139.nci04_free_reasoner_provider import FreeReasonerUnavailable
from test_nci04_owner_free_reasoner_proposal import (
    NativeFreeReasonerCustodyTests,
)


class V19OriginalLegacyHistoryTests(unittest.TestCase):
    def setUp(self):
        # Reuse the prior native-owner original SQLite fixture; all provider
        # responses are local test doubles, never live model/network calls.
        fixture = NativeFreeReasonerCustodyTests(
            "test_one_external_free_model_proposal_with_authenticated_draft")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = self.db.filename.with_suffix(".lock")

    def read(self):
        return original_legacy_attempt_snapshot(self.db)

    def test_must_hold_actual_original_single_owner_lock(self):
        with self.assertRaisesRegex(ShadowDenied, "MUTEX_REQUIRED"):
            self.read()
        self.assertFalse(SingleOwner.held(self.mutex))

    def test_zero_legacy_history_does_not_invent_v19_authority(self):
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            r = self.read()
            self.assertEqual(r["free_attempt_total"], 0)
            self.assertEqual(r["original_unresolved_draft_attempts"], 0)
            self.assertEqual(r["original_event_head_sha256"], old["head_hash"])
            self.assertFalse(r["v19_attempt_history_authenticated"])
            self.assertFalse(r["v19_provider_request_authorized"])
            self.assertFalse(r["scientific_first_use"])
            self.assertEqual(r["provider_requests"], 0)
            self.assertEqual(r["original_ledger_mutations"], 0)
            self.assertEqual(self.db.meta()["head_hash"], old["head_hash"])

    def test_existing_free_provider_and_draft_publication_are_spent(self):
        published = self.fixture.attempt()
        self.assertEqual(published["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            r = self.read()
            self.assertEqual(r["free_attempt_total"], 1)
            self.assertEqual(r["free_attempt_counts"]["Yggdrasil"], 1)
            self.assertEqual(r["free_attempt_counts"]["Wingless"], 0)
            self.assertEqual(r["original_draft_attempts"], 1)
            self.assertEqual(r["original_draft_authenticated"], 1)
            self.assertEqual(r["original_unresolved_draft_attempts"], 0)
            self.assertEqual(len(r["spent_free_scope_sha256"]), 1)
            self.assertEqual(len(r["history_sha256"]), 64)
            self.assertEqual(r["disposition"],
                             "VERIFIED_SPENT_ORIGINAL_HISTORY_NOT_RENEWAL_AUTHORITY")
            self.assertFalse(r["v19_provider_request_authorized"])
            self.assertEqual(r["provider_requests"], 0)
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"])
            self.assertEqual(self.db.meta()["head_hash"], before["head_hash"])
            self.assertEqual(r["history_sha256"], self.read()["history_sha256"])

    def test_ambiguous_free_provider_request_is_still_spent(self):
        def unavailable(_body, _token):
            raise ConnectionError("fixture timeout; no remote request")
        with self.assertRaises(FreeReasonerUnavailable):
            self.fixture.attempt(transport=unavailable)
        with SingleOwner(self.mutex):
            prior = self.db.meta()["head_hash"]
            r = self.read()
            self.assertEqual(r["free_attempt_total"], 1)
            self.assertEqual(r["original_draft_attempts"], 0)
            self.assertEqual(r["original_draft_authenticated"], 0)
            self.assertEqual(len(r["spent_free_scope_sha256"]), 1)
            self.assertEqual(self.db.meta()["head_hash"], prior)
            self.assertEqual(r["provider_requests"], 0)
            self.assertFalse(r["v19_provider_request_authorized"])

    def test_forged_extra_scope_rejected_after_immutable_append(self):
        self.assertEqual(self.fixture.attempt()["disposition"],
                         "MODEL_DRAFT_AUTHENTICATED")
        old = self.fixture.rows(FREE)[0]
        with self.db.transaction():
            self.db.event(FREE, {
                **old, "scope_sha256": "a" * 64,
                "prior_event_head_sha256": self.db.meta()["head_hash"],
            })
        with SingleOwner(self.mutex):
            with self.assertRaises(Exception):
                self.read()

    def test_original_event_head_tamper_fails_closed(self):
        self.db.conn.execute(
            "UPDATE meta SET head_hash=? WHERE id=1", ("f"*64,))
        with SingleOwner(self.mutex):
            with self.assertRaises(Exception):
                self.read()

    def test_wrong_db_object_cannot_supply_arbitrary_attempts(self):
        class FakeLedger:
            def verify(self):
                return True
        with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_DB_REQUIRED"):
            original_legacy_attempt_snapshot(FakeLedger())

    def test_disabled_owner_prohibits_shadow_projection(self):
        self.db.conn.execute("UPDATE meta SET enabled=0 WHERE id=1")
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_NOT_RUNNING"):
                self.read()

    def test_original_no_replay_semantics_survive_projection(self):
        self.assertEqual(self.fixture.attempt()["disposition"],
                         "MODEL_DRAFT_AUTHENTICATED")
        with SingleOwner(self.mutex):
            before = self.db.meta()["head_hash"]
            r = self.read()
            self.assertFalse(r["v19_attempt_history_authenticated"])
            self.assertFalse(r["v19_provider_request_authorized"])
            self.assertEqual(r["paid_model_calls"], 0)
            self.assertEqual(r["accepted_ref_mutations"], 0)
            self.assertEqual(r["worker_dispatched"], False)
            self.assertEqual(self.db.meta()["head_hash"], before)
        result = self.fixture.attempt(utc_day="2026-10-28")
        self.assertEqual(result["disposition"],
                         "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY")


if __name__ == "__main__":
    unittest.main()
