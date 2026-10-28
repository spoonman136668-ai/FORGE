"""V19 untrusted-source validation sealed only in disposable original SQLite."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_model_proposal import ProposalDenied
from f139.nci04_v19_original_proposal_validation_custody import (
    KIND, SCHEMA, ShadowDenied, validate_original_response_without_publication,
)
from test_nci04_v19_original_one_shot_free_send import OriginalOneShotSendTests


class OriginalProposalValidationCustodyTests(unittest.TestCase):
    def setUp(self):
        fixture = OriginalOneShotSendTests(
            "test_one_response_has_original_pre_send_event_and_zero_authority")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = fixture.mutex

    def prepared_response(self):
        handoff = self.fixture.prepare()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_free_reasoner_provider._post_one",
                side_effect=AssertionError("real HTTP NEVER permitted")):
            result = self.fixture.send(handoff)
        self.assertEqual(result["disposition"],
                         "ONE_MODEL_RESPONSE_UNTRUSTED_NO_PUBLICATION")
        self.assertEqual(self.fixture.calls, ["fake-only"])
        return result

    def validate(self, receipt, *, packet=None, witness=None, fault=False):
        return validate_original_response_without_publication(
            self.db, send_receipt=receipt,
            public_packet=(self.fixture.source.packet if packet is None else packet),
            owner_witness=((lambda: True) if witness is None else witness),
            fault_after_append=fault)

    def count(self):
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)
        ).fetchone()[0]

    def test_real_original_send_to_validated_candidate_and_cold_reopen(self):
        send = self.prepared_response()
        with SingleOwner(self.mutex):
            before = self.db.meta().copy()
            result = self.validate(send)
            self.assertEqual(result["disposition"],
                             "ORIGINAL_PROPOSAL_VALIDATED_DATA_ONLY")
            self.assertEqual(self.db.meta()["head_seq"], before["head_seq"] + 1)
            self.assertEqual(result["validation_event_sha256"],
                             self.db.meta()["head_hash"])
            self.assertEqual(result["provider_requests"], 0)
            self.assertEqual(result["paid_model_calls"], 0)
            self.assertFalse(result["publication_authorized"])
            self.assertFalse(result["scientific_first_use"])
            self.assertEqual(self.count(), 1)
            doc = json.loads(self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)
            ).fetchone()["payload"])
            self.assertEqual(doc["schema"], SCHEMA)
            self.assertEqual(doc["proposal_sha256"],
                             send["untrusted_response"]["proposal_sha256"])
            self.assertEqual(doc["candidate_identity"],
                             result["candidate"]["candidate_identity"])
            self.assertEqual(doc["source_after_sha256"],
                             result["candidate"]["source_after_sha256"])
            self.assertNotEqual(doc["source_after_sha256"],
                                doc["source_before_sha256"])
            self.assertIn(b"Local update", result["candidate"]["candidate_source"])
            cold = Database(self.db.filename)
            try:
                cold.verify()
                self.assertEqual(cold.meta(), self.db.meta())
            finally:
                cold.close()

    def test_cannot_validate_same_send_twice_after_cold_reopen(self):
        send = self.prepared_response()
        with SingleOwner(self.mutex):
            self.validate(send)
            old = self.db.meta().copy()
            got = self.validate(send)
            self.assertEqual(got["disposition"],
                             "BLOCKED_SEND_ALREADY_CUSTODIED_OR_HEAD_MOVED")
            self.assertEqual(got["provider_requests"], 0)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 1)

    def test_untrusted_response_sha_and_free_model_identity_required(self):
        send = self.prepared_response()
        reply = send["untrusted_response"]
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            for invalid in (
                {**reply, "proposal_sha256": "a" * 64},
                {**reply, "model_requested": "paid-other-model"},
                {**reply, "remote_response_trusted": True},
                {**reply, "publication_authorized": True},
                {**reply, "paid_model_calls": 1},
            ):
                with self.subTest(invalid=tuple(invalid.items())[:1]):
                    with self.assertRaisesRegex(
                            ShadowDenied, "MODEL_REPLY_AUTHORITY_OR_HASH_INVALID"):
                        self.validate({**send, "untrusted_response": invalid})
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)

    def test_provider_response_cannot_choose_other_target_or_history(self):
        send = self.prepared_response()
        reply = send["untrusted_response"]
        doc = json.loads(reply["proposal_bytes"])
        doc["target_commit"] = "f" * 40
        from f139.nci04_native_contract import canonical, digest
        bad = canonical(doc)
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ProposalDenied, "RESPONSE_BINDING_DRIFT"):
                self.validate({
                    **send, "untrusted_response": {
                        **reply, "proposal_bytes": bad,
                        "proposal_sha256": digest(bad),
                    },
                })
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)

    def test_noop_model_candidate_is_rejected_and_send_remains_spent(self):
        send = self.prepared_response()
        from f139.nci04_native_contract import canonical, digest
        reply = send["untrusted_response"]
        parsed = json.loads(reply["proposal_bytes"])
        parsed["candidate_source"] = self.fixture.source.packet["public_source"]
        raw = canonical(parsed)
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(
                    ProposalDenied, "SOURCE_SIZE_OR_CHANGE_INVALID"):
                self.validate({
                    **send, "untrusted_response": {
                        **reply, "proposal_bytes": raw,
                        "proposal_sha256": digest(raw),
                    },
                })
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)
            no_retry = self.fixture.send({
                "original_post_handoff_event_seq": send["send_attempt_event_seq"] - 1,
                "original_post_handoff_event_sha256": "f" * 64,
            })
            self.assertEqual(no_retry["provider_calls_in_this_invocation"], 0)

    def test_bad_send_receipt_and_wrong_original_head_never_custodied(self):
        send = self.prepared_response()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(
                    ShadowDenied, "UNTRUSTED_OR_MISSING_SEND_RECEIPT"):
                self.validate({**send, "provider_calls_in_this_invocation": 0})
            changed = {**send, "send_attempt_event_sha256": "0" * 64}
            self.assertEqual(
                self.validate(changed)["disposition"],
                "BLOCKED_SEND_ALREADY_CUSTODIED_OR_HEAD_MOVED")
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)

    def test_wrong_public_source_packet_cannot_custody_candidate(self):
        send = self.prepared_response()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            altered = {**self.fixture.source.packet, "history_sha256": "f" * 64}
            with self.assertRaisesRegex(
                    ShadowDenied, "MODEL_PUBLIC_SOURCE_OR_ORIGINAL_SEND_DRIFT"):
                self.validate(send, packet=altered)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)

    def test_original_mutex_mandatory_even_with_valid_response(self):
        send = self.prepared_response()
        with self.assertRaisesRegex(ShadowDenied,
                                     "ORIGINAL_OWNER_MUTEX_AND_WITNESS"):
            self.validate(send)
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(ShadowDenied,
                                         "ORIGINAL_OWNER_MUTEX_AND_WITNESS"):
                self.validate(send, witness=False)
            self.assertEqual(self.count(), 0)

    def test_injected_precommit_power_loss_rolls_back_original_head(self):
        send = self.prepared_response()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied,
                                         "INJECTED_PRECOMMIT_ROLLBACK"):
                self.validate(send, fault=True)
            self.assertEqual(self.count(), 0)
            self.assertEqual(self.db.meta(), old)
            self.db.verify()
            self.assertEqual(self.validate(send)["disposition"],
                             "ORIGINAL_PROPOSAL_VALIDATED_DATA_ONLY")

    def test_owner_revoke_before_commit_rolls_back_data_only_candidate(self):
        send = self.prepared_response()
        calls = []
        def witness():
            calls.append(1)
            return len(calls) < 3
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied,
                                         "ORIGINAL_OWNER_REVOKED_PRECOMMIT"):
                self.validate(send, witness=witness)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 0)

    def test_forged_second_sha_chained_candidate_with_science_flag_denied(self):
        send = self.prepared_response()
        with SingleOwner(self.mutex):
            self.validate(send)
            old = self.db.meta().copy()
            doc = json.loads(self.db.conn.execute(
                "SELECT payload FROM events WHERE kind=?", (KIND,)
            ).fetchone()["payload"])
            doc["prior_event_head_sha256"] = old["head_hash"]
            doc["scientific_first_use"] = True
            with self.assertRaisesRegex(
                    ShadowDenied, "VALIDATED_FIELDS_OR_AUTHORITY"):
                with self.db.transaction():
                    self.db.event(KIND, doc)
                    self.db.verify()
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.count(), 1)


if __name__ == "__main__":
    unittest.main()
