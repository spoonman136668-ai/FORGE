"""F139 V19 original one-time send: disposable SQLite, fake provider only."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_one_shot_free_send import (
    KIND, SCHEMA, ShadowDenied, one_original_free_send_source_only,
)
from test_nci04_v19_original_one_post_handoff import (
    V19OnePostHandoffCustodyTests,
)

TOKEN = "offline-fake-sentinel-do-not-send"


class OriginalOneShotSendTests(unittest.TestCase):
    def setUp(self):
        source = V19OnePostHandoffCustodyTests(
            "test_atomic_handoff_is_distinct_cold_verifiable_original_event")
        source.setUp()
        self.addCleanup(source.doCleanups)
        self.source = source
        self.db = source.db
        self.mutex = source.mutex
        self.calls = []

    def prepare(self):
        reserved = self.source.start()
        with SingleOwner(self.mutex):
            handoff = self.source.spend(reserved)
            self.assertEqual(handoff["disposition"],
                             "ORIGINAL_POST_HANDOFF_SPENT_NO_POST")
        return handoff

    def transport(self, body, token):
        self.assertEqual(token, TOKEN)
        doc = json.loads(body)
        self.assertEqual(doc["model"],
                         "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(len(self.calls), 0)
        self.calls.append("fake-only")
        payload = json.loads(doc["messages"][1]["content"].split(
            "\nProduce one bounded", 1)[0])
        self.assertEqual(payload, self.source.packet)
        return self.source.mock_provider(body, "offline-sentinel-never-real")

    def send(self, handoff, *, t=None, packet=None, reader=None, witness=None,
             token=TOKEN, fault=False):
        return one_original_free_send_source_only(
            self.db,
            handoff_seq=handoff["original_post_handoff_event_seq"],
            handoff_sha256=handoff["original_post_handoff_event_sha256"],
            public_packet=self.source.packet if packet is None else packet,
            public_reader=(self.source.reader_fixture.public_reader
                           if reader is None else reader),
            owner_witness=(lambda: True) if witness is None else witness,
            token=token, transport=self.transport if t is None else t,
            fault_after_append=fault)

    def count(self):
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)
        ).fetchone()[0]

    def test_one_response_has_original_pre_send_event_and_zero_authority(self):
        handoff = self.prepare()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_free_reasoner_provider._post_one",
                side_effect=AssertionError("NO REAL PROVIDER")):
            old = self.db.meta().copy()
            result = self.send(handoff)
            self.assertEqual(result["disposition"],
                             "ONE_MODEL_RESPONSE_UNTRUSTED_NO_PUBLICATION")
            self.assertEqual(result["provider_calls_in_this_invocation"], 1)
            self.assertTrue(result["provider_attempt_history_spent"])
            self.assertEqual(result["paid_model_calls"], 0)
            self.assertFalse(result["publication_authorized"])
            self.assertFalse(result["scientific_first_use"])
            self.assertFalse(result["accepted_ref_mutations"])
            self.assertFalse(result["original_controller_activated"])
            self.assertEqual(self.db.meta()["head_seq"], old["head_seq"] + 1)
            self.assertEqual(self.db.meta()["head_hash"],
                             result["send_attempt_event_sha256"])
            self.assertEqual(self.count(), 1)
            cold = Database(self.db.filename)
            try:
                cold.verify()
                self.assertEqual(cold.meta(), self.db.meta())
            finally:
                cold.close()
        self.assertEqual(self.calls, ["fake-only"])
        response = result["untrusted_response"]
        self.assertFalse(response["remote_response_trusted"])
        self.assertFalse(response["publication_authorized"])

    def test_second_send_after_success_is_blocked_before_public_fetch(self):
        handoff = self.prepare()
        with SingleOwner(self.mutex):
            self.send(handoff)
            before = self.db.meta().copy()
            def forbidden(_):
                self.fail("already spent: no anonymous Git network")
            result = self.send(handoff, reader=forbidden)
            self.assertEqual(result["disposition"],
                             "BLOCKED_HANDOFF_ALREADY_SPENT_OR_HEAD_MOVED")
            self.assertEqual(result["provider_calls_in_this_invocation"], 0)
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(self.count(), 1)
        self.assertEqual(self.calls, ["fake-only"])

    def test_timeout_spent_irreversibly_even_after_cold_reopen(self):
        handoff = self.prepare()
        failed = []
        def ambiguous(body, token):
            failed.append(1)
            raise TimeoutError("offline mock ambiguous")
        with SingleOwner(self.mutex):
            result = self.send(handoff, t=ambiguous)
            self.assertEqual(result["disposition"],
                             "MODEL_SEND_FAILED_OR_AMBIGUOUS_NO_RETRY")
            self.assertEqual(result["provider_calls_in_this_invocation"], 1)
            self.assertEqual(len(failed), 1)
            saved = self.db.meta().copy()
            cold = Database(self.db.filename)
            try:
                cold.verify()
                self.assertEqual(cold.meta(), saved)
            finally:
                cold.close()
            again = self.send(handoff, t=ambiguous)
            self.assertEqual(again["provider_calls_in_this_invocation"], 0)
            self.assertEqual(self.db.meta(), saved)
        self.assertEqual(len(failed), 1)

    def test_precommit_fault_rolls_back_original_chain_and_never_sends(self):
        handoff = self.prepare()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied,
                                        "INJECTED_PRECOMMIT_ROLLBACK"):
                self.send(handoff, fault=True)
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.calls, [])
            self.db.verify()
            self.assertEqual(self.send(handoff)["provider_calls_in_this_invocation"], 1)
            self.assertEqual(self.count(), 1)

    def test_mismatched_packet_denied_without_spending_or_sending(self):
        handoff = self.prepare()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            altered = {**self.source.packet, "history_sha256": "a" * 64}
            with self.assertRaisesRegex(ShadowDenied,
                                         "PUBLIC_BYTES_OR_SCOPE_CHANGED"):
                self.send(handoff, packet=altered)
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), old)
        self.assertEqual(self.calls, [])

    def test_original_mutex_and_owner_witness_required(self):
        handoff = self.prepare()
        with self.assertRaisesRegex(ShadowDenied,
                                     "ORIGINAL_OWNER_LOCK_OR_WITNESS_REQUIRED"):
            self.send(handoff)
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(ShadowDenied,
                                         "ORIGINAL_OWNER_LOCK_OR_WITNESS_REQUIRED"):
                self.send(handoff, witness=lambda: False)
            self.assertEqual(self.count(), 0)
        self.assertEqual(self.calls, [])

    def test_no_credential_or_implicit_http_transport(self):
        handoff = self.prepare()
        with SingleOwner(self.mutex):
            for token in ("", "token\nX", "X" * 3000):
                with self.assertRaisesRegex(ShadowDenied,
                                             "PUBLIC_INPUT_OR_EXPLICIT_CREDENTIAL_REQUIRED"):
                    self.send(handoff, token=token)
            with self.assertRaisesRegex(ShadowDenied,
                                         "PUBLIC_INPUT_OR_EXPLICIT_CREDENTIAL_REQUIRED"):
                self.send(handoff, t=object())
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.calls, [])

    def test_owner_revoked_after_append_rolls_back_without_transport(self):
        handoff = self.prepare()
        witnessed = []
        def witness():
            witnessed.append(1)
            return len(witnessed) < 3
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied,
                                         "ORIGINAL_OWNER_REVOKED_PRECOMMIT"):
                self.send(handoff, witness=witness)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)
        self.assertEqual(self.calls, [])

    def test_forged_second_sha_chained_send_event_rejected_cold(self):
        handoff = self.prepare()
        with SingleOwner(self.mutex):
            self.send(handoff)
            old = self.db.meta().copy()
            doc = json.loads(self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)
            ).fetchone()["payload"])
            doc["prior_event_head_sha256"] = old["head_hash"]
            with self.assertRaisesRegex(ShadowDenied,
                                         "ORIGINAL_HANDOFF_MISSING_OR_REPLAY|"
                                         "SEND_ORIGINAL_HANDOFF_MISSING_OR_REPLAY|"
                                         "SEND_HANDOFF_BINDING_OR_NONADJACENT_EVENT"):
                with self.db.transaction():
                    self.db.event(KIND, doc)
                    self.db.verify()
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 1)


if __name__ == "__main__":
    unittest.main()
