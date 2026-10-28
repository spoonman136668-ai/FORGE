"""V19 original Database.verify cold event-schema tests (isolated SQLite only)."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139.nci04_v19_original_attempt_schema import (
    KIND, SCHEMA, legacy_digest,
)
from f139.nci04_v19_original_terminal_witness import (
    project_original_native_terminal,
)
from test_nci04_v19_original_terminal_witness import OriginalWitnessTests


class OriginalRequestColdVerifierTests(unittest.TestCase):
    def setUp(self):
        fixture = OriginalWitnessTests(
            "test_empty_history_is_no_request_and_no_event_changes")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = self.db.filename.with_suffix(".lock")

    def real_native(self):
        issue = self.fixture.fixture.native
        self.assertEqual(issue.lane, "Wingless")
        activate_native(self.db, self.fixture.fixture.approval())
        self.assertTrue(admit_native_issue(
            self.db, issue, "2026-10-28T09:00:00Z"))
        self.db.claim(issue.ticket, "2026-10-28T09:01:00Z")
        self.db.dispatch_observed(issue.ticket)
        self.db.terminal(issue.ticket, 98012345678,
                         "/tmp/fixture-only-source-verifier", "e" * 64)
        return issue

    def payload(self, day="2026-10-28"):
        issue = self.fixture.fixture.native
        proof = project_original_native_terminal(
            self.db, lane=issue.lane, utc_day=day,
            hypothetical_v19_attempts=[])
        self.assertEqual(
            proof["disposition"],
            "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED")
        seq = proof["terminal_event_seq"]
        e = self.db.conn.execute(
            "SELECT sha FROM events WHERE seq=?", (seq,)).fetchone()
        legacy = [dict(r) for r in self.db.conn.execute(
            "SELECT seq,kind,payload,sha FROM events ORDER BY seq")]
        return {
            "schema": SCHEMA, "owner_source_sha": self.db.meta()["source_sha"],
            "lane": issue.lane, "terminal_ticket": issue.ticket,
            "terminal_event_seq": seq, "terminal_event_sha256": e["sha"],
            "terminal_evidence_sha256": "e" * 64,
            "target_commit": issue.candidate.target_commit,
            "native_path": issue.candidate.path,
            "scope_sha256": proof["shadow"]["scope_sha256"],
            "original_legacy_history_sha256": legacy_digest(legacy),
            "utc_day": day,
            "prior_event_head_sha256": self.db.meta()["head_hash"],
            "retry_allowed": False, "request_intent_committed": True,
            "paid_model_calls": 0, "worker_dispatched": False,
            "scientific_first_use": False,
        }

    def append(self, payload):
        with self.db.transaction():
            self.db.event(KIND, payload)
            self.db.verify()

    def assert_rejected(self, mutate):
        with SingleOwner(self.mutex):
            proposal = self.payload()
            mutated = mutate(proposal)
            before = self.db.meta().copy()
            with self.assertRaises(Exception):
                self.append(mutated)
            self.assertEqual(self.db.meta(), before)
            self.db.verify()

    def test_no_new_events_original_behavior_and_original_head_unchanged(self):
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            self.db.verify()
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)).fetchone()[0], 0)

    def test_genuine_signed_chain_and_native_terminal_pass_cold_reopen(self):
        issue = self.real_native()
        with SingleOwner(self.mutex):
            before = self.db.meta()["head_seq"]
            packet = self.payload()
            self.append(packet)
            self.assertEqual(self.db.meta()["head_seq"], before + 1)
            self.assertEqual(self.db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)).fetchone()[0], 1)
            # Cold reopen must run the SAME source verifier, not a test oracle.
            cold = Database(self.db.filename)
            try:
                self.assertEqual(cold.meta()["head_seq"], before + 1)
                cold.verify()
            finally:
                cold.close()
            self.assertEqual(packet["terminal_ticket"], issue.ticket)

    def test_second_use_of_same_original_terminal_is_denied_and_rolled_back(self):
        self.real_native()
        with SingleOwner(self.mutex):
            first = self.payload()
            self.append(first)
            old = self.db.meta().copy()
            second = {**first, "prior_event_head_sha256": old["head_hash"],
                      "utc_day": "2026-10-29"}
            with self.assertRaisesRegex(Exception, "REPLAY|NOT_NEW"):
                self.append(second)
            self.assertEqual(self.db.meta(), old)
            self.db.verify()

    def test_reject_forged_sha256_scope_even_if_owner_event_chain_is_valid(self):
        self.real_native()
        self.assert_rejected(lambda p: {**p, "scope_sha256": "f" * 64})

    def test_reject_future_terminal_or_wrong_legacy_fingerprint(self):
        self.real_native()
        self.assert_rejected(lambda p: {
            **p, "original_legacy_history_sha256": "c" * 64})
        self.assert_rejected(lambda p: {**p, "terminal_event_seq": 99_999_999})

    def test_reject_mismatched_ticket_commit_source_and_lane(self):
        self.real_native()
        self.assert_rejected(lambda p: {**p, "terminal_ticket": "forged-ticket"})
        self.assert_rejected(lambda p: {**p, "target_commit": "a" * 40})
        self.assert_rejected(lambda p: {**p, "owner_source_sha": "b" * 40})
        self.assert_rejected(lambda p: {**p, "lane": "Yggdrasil"})

    def test_reject_unknown_field_and_paid_or_retry_permit(self):
        self.real_native()
        self.assert_rejected(lambda p: {**p, "future_override": True})
        self.assert_rejected(lambda p: {**p, "paid_model_calls": 1})
        self.assert_rejected(lambda p: {**p, "retry_allowed": True})
        self.assert_rejected(lambda p: {**p, "scientific_first_use": True})
        self.assert_rejected(lambda p: {**p, "worker_dispatched": True})

    def test_reject_original_head_mismatch_and_no_write_during_verify(self):
        self.real_native()
        self.assert_rejected(lambda p: {
            **p, "prior_event_head_sha256": "0" * 64})
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with patch.object(self.db, "event", side_effect=AssertionError(
                    "cold verify must not append anything")):
                self.db.verify()
            self.assertEqual(self.db.meta(), old)

    def test_empty_database_has_no_unearned_request(self):
        with SingleOwner(self.mutex):
            with self.assertRaises(Exception):
                self.append({
                    "schema": SCHEMA, "owner_source_sha": self.db.meta()["source_sha"],
                    "lane": "Wingless",
                })
            self.assertEqual(
                self.db.conn.execute(
                    "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)
                ).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
