"""Offline evidence for real free-model request custody; no external model calls."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139 import nci04_research_steering as steering
from f139.local_controller import Database
from f139.nci04_free_reasoner_provider import (
    FreeReasonerUnavailable, MODEL, SCHEMA as PACKET_SCHEMA,
)
from f139.nci04_model_owner_publication import (
    ATTEMPT as DRAFT_ATTEMPT, SUCCESS as DRAFT_SUCCESS,
)
from f139.nci04_native_contract import canonical
from f139.nci04_owner_free_reasoner_proposal import (
    ATTEMPT, MAX_DAILY_REQUESTS, MAX_LIFETIME_REQUESTS, SCHEMA,
    FreeOwnerDenied, original_outcome_fingerprint, reasoner_proposal_once,
    reasoner_scope,
)
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139.test_nci04_candidate_publisher import FakeOriginalOwner, SOURCE
from f139.test_nci04_research_steering import SteeringProvider
from test_nci04_owner_ledger import LedgerTests, MAIN


class NativeFreeReasonerCustodyTests(unittest.TestCase):
    def setUp(self):
        fixture = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.assertTrue(activate_native(self.db, fixture.approval()))
        self.assertTrue(admit_native_issue(
            self.db, fixture.native, "2026-10-27T09:00:00Z"))
        self.db.claim(fixture.native.ticket, "2026-10-27T09:01:00Z")
        self.db.quarantine(fixture.native.ticket, "QUALIFIED_NEGATIVE")
        self.provider = FakeOriginalOwner()
        self.provider.source = MAIN
        self.steering = SteeringProvider()
        p = patch.object(steering, "DOCUMENTS", self.steering.documents)
        p.start()
        self.addCleanup(p.stop)
        self.calls = []
        self.sent = []

    def public_get(self, route):
        self.calls.append(route)
        return self.provider.get(route)

    def model(self, body: bytes, token: str) -> bytes:
        self.assertEqual(token, "fixture-unprinted")
        x = json.loads(body)
        self.assertEqual(x["model"], MODEL)
        contents = x["messages"][1]["content"]
        packet = json.loads(contents.split("\nProduce one bounded", 1)[0])
        self.assertEqual(packet["schema"], PACKET_SCHEMA)
        self.assertEqual(packet["retained_outcome_counts"], {"QUARANTINED": 1})
        self.assertNotIn("QUALIFIED_NEGATIVE", contents)
        self.assertNotIn(self.fixture.native.ticket, contents)
        self.assertNotIn("Mind-Palace", contents)
        self.sent.append(packet)
        return canonical({
            "choices": [{
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": canonical({
                    "schema": "forge.f139.model-proposal.v1",
                    "lane": "Yggdrasil",
                    "target_commit": self.provider.parent,
                    "path": self.provider.path,
                    "history_sha256": packet["history_sha256"],
                    "question": "Does a local learned prediction improve action?",
                    "hypothesis": "Local uncertainty controls safe exploration.",
                    "control": "Matched random and least-observed actions.",
                    "candidate_source": SOURCE.decode("utf-8") +
                                        "\n# source-only free proposal\n",
                }).decode("ascii")},
            }],
            "usage": {"cost": 0},
        })

    def attempt(self, **overrides):
        opts = {
            "source_sha": MAIN, "lane": "Yggdrasil",
            "target_commit": self.provider.parent,
            "path": self.provider.path,
            "owner_witness": lambda: True,
            "token": "fixture-unprinted",
            "transport": self.model,
            "public_reader": self.public_get,
            "utc_day": "2026-10-27",
        }
        opts.update(overrides)
        return reasoner_proposal_once(
            self.db, self.provider.get, self.steering.get,
            self.provider.write, **opts)

    def rows(self, kind):
        return [json.loads(r["payload"]) for r in self.db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq", (kind,))]

    def test_one_external_free_model_proposal_with_authenticated_draft(self):
        old = self.db.meta()["head_seq"]
        feedback = original_outcome_fingerprint(self.db)
        result = self.attempt()
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(result["generator"], "PUBLIC_FREE_NEMOTRON_HISTORY_GROUNDED")
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(result["paid_model_calls"], 0)
        self.assertEqual(self.db.meta()["head_seq"], old + 3)
        self.assertEqual(original_outcome_fingerprint(self.db), feedback)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(DRAFT_ATTEMPT)), 1)
        self.assertEqual(len(self.rows(DRAFT_SUCCESS)), 1)
        self.assertEqual(self.rows(ATTEMPT)[0]["model"], MODEL)
        self.assertFalse(self.rows(ATTEMPT)[0]["remote_request_retry_authorized"])
        self.assertEqual([method for method, _ in self.provider.write_calls],
                         ["POST", "PUT", "POST"])
        self.assertTrue(self.provider.pr["draft"])
        self.assertIn("source-only free proposal", self.provider.head_data.decode())
        self.db.verify()

    def test_once_only_original_request_even_after_authenticated_draft(self):
        result = self.attempt()
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        old = self.db.meta()["head_hash"]
        second = self.attempt()
        self.assertEqual(second["disposition"],
                         "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertEqual(self.db.meta()["head_hash"], old)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(len(self.provider.write_calls), 3)

    def test_provider_timeout_preserves_one_original_no_replay_attempt(self):
        calls = []
        def timeout(body, token):
            calls.append(1)
            raise ConnectionError("PROVIDER_ERROR_PRIVATE")
        with self.assertRaisesRegex(FreeReasonerUnavailable, "NO_RETRY"):
            self.attempt(transport=timeout)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(DRAFT_ATTEMPT)), 0)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.attempt()["disposition"],
                         "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.sent)
        self.db.verify()

    def test_credential_missing_or_original_owner_invalid_denies_network(self):
        start = self.db.meta()["head_hash"]
        absent = self.attempt(token=" ")
        self.assertEqual(absent["disposition"],
                         "FREE_REASONER_NO_CREDENTIAL_NO_REQUEST")
        self.assertEqual(self.db.meta()["head_hash"], start)
        self.assertFalse(self.calls)
        with self.assertRaisesRegex(FreeOwnerDenied, "ORIGINAL_OWNER_NOT_ATTESTED"):
            self.attempt(owner_witness=lambda: False)
        self.assertFalse(self.rows(ATTEMPT))
        self.assertFalse(self.sent)

    def test_private_repo_or_modified_public_git_denied_before_event(self):
        def private(route):
            raise FileNotFoundError("git anonymous 404")
        with self.assertRaisesRegex(FreeReasonerUnavailable, "PUBLIC_GIT_UNAVAILABLE"):
            self.attempt(public_reader=private)
        self.assertFalse(self.rows(ATTEMPT))
        self.assertFalse(self.sent)
        def wrong_tree(route):
            result = self.provider.get(route)
            if "/git/commits/" in route:
                return {**result, "tree": {"sha": "a"*40}}
            return result
        with self.assertRaisesRegex(ValueError,
                                    "ANONYMOUS_SOURCE_GIT_AUTHENTICITY"):
            self.attempt(public_reader=wrong_tree)
        self.assertFalse(self.rows(ATTEMPT))
        self.assertFalse(self.sent)

    def test_owner_history_is_scope_not_a_model_secret(self):
        orig = original_outcome_fingerprint(self.db)
        scope = reasoner_scope(
            source_sha=MAIN, lane="Yggdrasil",
            target_commit=self.provider.parent, path=self.provider.path,
            original_feedback_sha256=orig)
        self.assertEqual(len(scope), 64)
        self.assertNotIn(self.fixture.native.ticket, scope)
        self.assertEqual(MAX_DAILY_REQUESTS, 1)
        self.assertEqual(MAX_LIFETIME_REQUESTS, 8)
        self.assertEqual(SCHEMA, "forge.f139.owner-free-reasoner-attempt.v1")
        self.assertFalse(self.rows(ATTEMPT))

    def test_source_drift_and_unsafe_budget_fail_closed(self):
        with self.assertRaises(ValueError):
            self.attempt(source_sha="f"*40)
        self.assertFalse(self.rows(ATTEMPT))
        self.assertEqual(self.attempt()["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        event = self.rows(ATTEMPT)[0]
        with self.db.transaction():
            self.db.event(ATTEMPT, {**event, "scope_sha256": "1"*64,
                                    "prior_event_head_sha256": self.db.meta()["head_hash"]})
        with self.assertRaisesRegex(Exception, "SCOPE_REPLAY_OR_BUDGET"):
            self.db.verify()


if __name__ == "__main__":
    unittest.main()
