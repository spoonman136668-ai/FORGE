"""Original SQLite one-time free-model handoff custody: all traffic mocked."""
from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_free_reasoner_provider import (
    MODEL, FreeReasonerUnavailable, infer_free_once,
    public_packet as publicize,
)
from f139.nci04_model_proposal import validate
from f139.nci04_v19_original_one_post_handoff import (
    KIND, SCHEMA, ShadowDenied, custody_original_post_handoff_without_post,
)
from test_nci04_v19_original_atomic_reserve_no_post import (
    OriginalAtomicNoPostTests,
)
from test_nci04_free_reasoner_provider import FreeReasonerSourceOnlyTests


class V19OnePostHandoffCustodyTests(unittest.TestCase):
    def setUp(self):
        base = OriginalAtomicNoPostTests(
            "test_no_native_terminal_means_no_original_event")
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.base = base
        self.db = base.db
        self.mutex = base.mutex

        source = FreeReasonerSourceOnlyTests(
            "test_exact_free_model_and_bounded_prompt")
        source.setUp()
        self.reader_fixture = source
        # The source blob represents PUBLIC-only native learning source.
        source.source = "package native\n\nfunc LearnLocal() int { return 1 }\n"
        source.request["source"] = source.source
        source.request["before_sha256"] = digest(source.source.encode("utf-8"))
        issue = base.fixture.fixture.fixture.native
        source.request.update({
            "lane": issue.lane,
            "target_commit": issue.candidate.target_commit,
            "path": issue.candidate.path,
        })
        self.packet = publicize(source.request, public_source_verified=True)
        self.calls = []

    def start(self):
        self.base.native()
        with SingleOwner(self.mutex):
            receipt = self.base.reserve()
            self.assertEqual(receipt["disposition"],
                             "ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST")
        return receipt

    def spend(self, reserved, *, p=None, reader=None, witness=None,
              fault=False, day="2026-10-28"):
        return custody_original_post_handoff_without_post(
            self.db,
            reservation_seq=reserved["original_request_attempt_event_seq"],
            reservation_sha256=reserved["original_request_attempt_event_sha256"],
            public_packet=self.packet if p is None else p,
            public_reader=self.reader_fixture.public_reader if reader is None else reader,
            utc_day=day,
            owner_witness=(lambda: True) if witness is None else witness,
            fault_after_append=fault,
        )

    def count(self):
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)
        ).fetchone()[0]

    def mock_provider(self, body, token):
        self.assertEqual(token, "offline-sentinel-never-real")
        p = json.loads(json.loads(body)["messages"][1]["content"].split(
            "\nProduce one bounded", 1)[0])
        self.assertEqual(p, self.packet)
        self.assertEqual(json.loads(body)["model"], MODEL)
        self.assertEqual(len(self.calls), 0)
        self.calls.append("one")
        return canonical({
            "choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": canonical({
                    "schema": "forge.f139.model-proposal.v1",
                    "lane": p["lane"], "target_commit": p["target_commit"],
                    "path": p["path"], "history_sha256": p["history_sha256"],
                    "question": "Can local state retain a causal consequence?",
                    "hypothesis": "A local update improves retained state",
                    "control": "Matched random action and conventional baseline",
                    "candidate_source": self.reader_fixture.source +
                                        "\n// Local update development only\n",
                }).decode("utf-8")}}],
            "usage": {"cost": 0},
        })

    def test_atomic_handoff_is_distinct_cold_verifiable_original_event(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            handoff = self.spend(reserved)
            self.assertEqual(handoff["disposition"],
                             "ORIGINAL_POST_HANDOFF_SPENT_NO_POST")
            self.assertEqual(self.count(), 1)
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"] + 1)
            self.assertEqual(handoff["provider_requests"], 0)
            self.assertFalse(handoff["original_owner_request_authorized"])
            self.assertFalse(handoff["scientific_first_use"])
            self.assertEqual(handoff["original_post_handoff_event_sha256"],
                             self.db.meta()["head_hash"])
            cold = Database(self.db.filename)
            try:
                cold.verify()
                self.assertEqual(cold.meta(), self.db.meta())
            finally:
                cold.close()

    def test_no_second_handoff_after_lost_receipt_or_utc_rollover(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            self.spend(reserved)
            before = self.db.meta().copy()
            for day in ("2026-10-28", "2026-10-29"):
                got = self.spend(reserved, day=day)
                self.assertEqual(got["disposition"],
                                 "BLOCKED_RESERVATION_ALREADY_SPENT_OR_HISTORY_MOVED")
            self.assertEqual(self.count(), 1)
            self.assertEqual(self.db.meta(), before)

    def test_spent_scope_skips_even_anonymous_public_source_network(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            self.spend(reserved)
            frozen = self.db.meta().copy()
            def forbidden_public_fetch(route):
                self.fail("spent handoff must not fetch even public source")
            repeated = self.spend(reserved, reader=forbidden_public_fetch)
            self.assertEqual(repeated["disposition"],
                             "BLOCKED_RESERVATION_ALREADY_SPENT_OR_HISTORY_MOVED")
            self.assertEqual(self.count(), 1)
            self.assertEqual(self.db.meta(), frozen)

    def test_fully_mocked_one_free_model_result_stays_untrusted(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            receipt = self.spend(reserved)
        self.assertEqual(receipt["provider_requests"], 0)
        # Test-only explicit fake transport. No runtime connector or actual
        # model HTTP request is present in any F139 V19 execution path.
        with patch("f139.nci04_free_reasoner_provider._post_one",
                   side_effect=AssertionError("NO_REAL_HTTP_POST")):
            response = infer_free_once(
                self.packet, token="offline-sentinel-never-real",
                transport=self.mock_provider,
                public_reader=self.reader_fixture.public_reader)
        self.assertEqual(self.calls, ["one"])
        self.assertFalse(response["remote_response_trusted"])
        self.assertFalse(response["publication_authorized"])
        self.assertFalse(response["scientific_first_use"])
        candidate = validate(
            response["proposal_bytes"], lane=self.packet["lane"],
            target_commit=self.packet["target_commit"],
            path=self.packet["path"],
            before=self.reader_fixture.source.encode("utf-8"),
            before_sha256=self.packet["before_sha256"],
            history_sha256=self.packet["history_sha256"],
            consumed_candidates=set(), consumed_after_hashes=set())
        self.assertFalse(candidate["record"]["publication_authorized"])
        self.assertEqual(candidate["record"]["lane"], "Wingless")
        with SingleOwner(self.mutex):
            self.assertEqual(self.spend(reserved)["disposition"],
                             "BLOCKED_RESERVATION_ALREADY_SPENT_OR_HISTORY_MOVED")
            self.assertEqual(self.count(), 1)

    def test_ambiguous_mock_transport_failure_never_refunds_spent_handoff(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            self.spend(reserved)
            frozen = self.db.meta().copy()
        def broken(body, token):
            self.calls.append("one")
            raise TimeoutError("fixture only")
        with patch("f139.nci04_free_reasoner_provider._post_one",
                   side_effect=AssertionError("NO_REAL_HTTP_POST")):
            with self.assertRaisesRegex(FreeReasonerUnavailable, "NO_RETRY"):
                infer_free_once(
                    self.packet, token="offline-sentinel-never-real",
                    transport=broken,
                    public_reader=self.reader_fixture.public_reader)
        self.assertEqual(self.calls, ["one"])
        with SingleOwner(self.mutex):
            self.assertEqual(self.spend(reserved)["disposition"],
                             "BLOCKED_RESERVATION_ALREADY_SPENT_OR_HISTORY_MOVED")
            self.assertEqual(self.db.meta(), frozen)
            self.assertEqual(self.count(), 1)

    def test_bad_or_private_public_source_refused_before_post_handoff(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            def private(_):
                raise FileNotFoundError("private-public-source")
            with self.assertRaises(Exception):
                self.spend(reserved, reader=private)
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), before)
            bad = {**self.packet, "public_source": "PRIVATE"}
            with self.assertRaises(Exception):
                self.spend(reserved, p=bad)
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), before)

    def test_wrong_commit_path_or_owner_source_does_not_spend_handoff(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            wrong = {**self.packet, "target_commit": "f" * 40}
            # Use an independently matching Git proof to reach the actual
            # original reservation binding check, not merely publicness.
            self.reader_fixture.request["target_commit"] = "f" * 40
            got = self.spend(reserved, p=wrong)
            self.assertEqual(got["disposition"],
                             "BLOCKED_SOURCE_OR_OWNER_WITNESS_DRIFT")
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), old)

    def test_transaction_fault_after_append_rolls_back_entire_original_head(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied,
                                        "INJECTED_PRECOMMIT_ROLLBACK"):
                self.spend(reserved, fault=True)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)
            self.db.verify()
            self.assertEqual(self.spend(reserved)["disposition"],
                             "ORIGINAL_POST_HANDOFF_SPENT_NO_POST")

    def test_wrong_reservation_hash_never_spends(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            got = custody_original_post_handoff_without_post(
                self.db,
                reservation_seq=reserved["original_request_attempt_event_seq"],
                reservation_sha256="f" * 64,
                public_packet=self.packet,
                public_reader=self.reader_fixture.public_reader,
                utc_day="2026-10-28", owner_witness=lambda: True)
            self.assertEqual(got["disposition"],
                             "BLOCKED_UNKNOWN_OR_FORGED_RESERVATION")
            self.assertEqual(self.count(), 0)

    def test_forged_original_post_event_is_rejected_by_cold_verifier(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            self.spend(reserved)
            original = self.db.meta().copy()
            row = self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)).fetchone()
            tampered = json.loads(row["payload"])
            tampered["retry_allowed"] = True
            with self.assertRaisesRegex(ShadowDenied,
                                        "COLD_FIELDS_OR_AUTHORITY"):
                with self.db.transaction():
                    self.db.event(KIND, tampered)
                    self.db.verify()
            self.assertEqual(self.db.meta(), original)

    def test_no_network_public_readers_in_verify_only_path(self):
        reserved = self.start()
        with SingleOwner(self.mutex):
            self.spend(reserved)
            old = self.db.meta().copy()
            with patch("f139.nci04_free_reasoner_provider._post_one",
                       side_effect=AssertionError("NO POST")), patch(
                       "f139.nci04_free_reasoner_provider._public_get",
                       side_effect=AssertionError("NO PUBLIC HTTP")):
                self.db.verify()
            self.assertEqual(self.db.meta(), old)

    def test_witness_revoke_before_commit_rolls_back_handoff(self):
        reserved = self.start()
        seen = []
        def witness():
            seen.append(1)
            return len(seen) < 3
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied,
                                         "ORIGINAL_OWNER_REVOKED_PRECOMMIT"):
                self.spend(reserved, witness=witness)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)


if __name__ == "__main__":
    unittest.main()
