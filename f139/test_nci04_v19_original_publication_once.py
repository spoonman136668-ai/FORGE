"""V19 original-owner draft publication: fake writes and disposable SQLite only."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_publication_once import (
    ShadowDenied, publish_original_v19_candidate_once,
)
from test_nci04_v19_original_publication_preflight_no_write import (
    OriginalDraftPreflightTests,
)


class OriginalV19OnceWriterTests(unittest.TestCase):
    def setUp(self):
        base = OriginalDraftPreflightTests(
            "test_exact_original_candidate_compiles_native_draft_no_write")
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.base = base
        self.db = base.db
        self.mutex = base.mutex
        self.remote_calls = []

    def candidate(self):
        return self.base.stage_candidate()

    def writer(self, saved, *, source=None, witness=None, getter=None):
        return publish_original_v19_candidate_once(
            self.db,
            validation_seq=saved["validation_event_seq"],
            validation_sha256=saved["validation_event_sha256"],
            candidate_source=(saved["candidate"]["candidate_source"]
                              if source is None else source),
            public_packet=self.base.stage.fixture.source.packet,
            original_get=(self.base.original_get if getter is None else getter),
            public_reader=self.base.public_reader,
            original_write=lambda method, route, payload: self.remote_calls.append(
                (method, route, payload)),
            owner_witness=(lambda: True) if witness is None else witness,
        )

    def fake_authenticated_write(self, get, write, plan):
        # Confirm a cold-reopenable original attempt is durable before any
        # simulated outbound Git mutation. Never contact GitHub.
        self.remote_calls.append(("FAKE_ONLY", plan["repository"], plan["branch"]))
        latest = self.db.conn.execute(
            "SELECT kind,payload,prior_sha,sha FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(latest["kind"], "MODEL_DRAFT_ATTEMPTED")
        self.assertFalse(json.loads(latest["payload"])["retry_allowed"])
        self.assertEqual(latest["prior_sha"],
                         self.db.conn.execute(
                             "SELECT sha FROM events WHERE seq=?",
                             (latest["seq"] - 1,)).fetchone()["sha"])
        cold = Database(self.db.filename)
        try:
            cold.verify()
            self.assertEqual(cold.meta(), self.db.meta())
        finally:
            cold.close()
        self.assertTrue(plan["branch"].startswith("f139/auto-model-w-"))
        self.assertFalse(json.loads(plan["body"])["scientific_first_use"])
        return {"pr_number": 1234, "head_commit": "a" * 40}

    def count(self, kind):
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (kind,)
        ).fetchone()[0]

    def test_fake_only_success_attempt_precedes_remote_and_cold_verifies(self):
        saved = self.candidate()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=self.fake_authenticated_write):
            result = self.writer(saved)
            self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
            self.assertFalse(result["retry_allowed"])
            self.assertEqual(self.count("MODEL_DRAFT_ATTEMPTED"), 1)
            self.assertEqual(self.count("MODEL_DRAFT_AUTHENTICATED"), 1)
            self.assertEqual(len(self.remote_calls), 1)
            self.db.verify()
        cold = Database(self.db.filename)
        try:
            cold.verify()
        finally:
            cold.close()

    def test_fake_remote_timeout_spends_attempt_no_replay(self):
        saved = self.candidate()
        def unknown(*args):
            self.remote_calls.append(("FAKE_TIMEOUT",))
            raise TimeoutError("simulated lost response after unknown write")
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=unknown):
            result = self.writer(saved)
            self.assertEqual(result["disposition"],
                             "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
            self.assertEqual(self.count("MODEL_DRAFT_ATTEMPTED"), 1)
            self.assertEqual(self.count("MODEL_DRAFT_AUTHENTICATED"), 0)
            with self.assertRaisesRegex(
                    ShadowDenied, "VALIDATION_ALREADY_CONSUMED_OR_HEAD_MOVED"):
                self.writer(saved)
            self.assertEqual(len(self.remote_calls), 1)
        cold = Database(self.db.filename)
        try:
            cold.verify()
        finally:
            cold.close()

    def test_owner_revocation_after_freeze_spends_without_post(self):
        saved = self.candidate()
        calls = []
        def witness():
            calls.append(1)
            return len(calls) < 7
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=AssertionError("NO REMOTE CALL")):
            result = self.writer(saved, witness=witness)
            self.assertEqual(result["disposition"],
                             "OWNER_REVOKED_ATTEMPT_SPENT_NO_POST")
            self.assertEqual(self.count("MODEL_DRAFT_ATTEMPTED"), 1)
            self.assertEqual(self.remote_calls, [])
            self.db.verify()

    def test_source_tamper_fails_before_attempt_and_remote(self):
        saved = self.candidate()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=AssertionError("NO REMOTE CALL")):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(
                    ShadowDenied, "MODEL_CANDIDATE_BYTES_OR_SOURCE_DRIFT"):
                self.writer(saved, source=b"untrusted alteration")
            self.assertEqual(before, self.db.meta())
            self.assertEqual(self.count("MODEL_DRAFT_ATTEMPTED"), 0)

    def test_successful_attempt_cannot_replay(self):
        saved = self.candidate()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=self.fake_authenticated_write):
            self.writer(saved)
            with self.assertRaisesRegex(
                    ShadowDenied, "VALIDATION_ALREADY_CONSUMED_OR_HEAD_MOVED"):
                self.writer(saved)
            self.assertEqual(len(self.remote_calls), 1)

    def test_disabled_original_policy_fails_before_any_write(self):
        saved = self.candidate()
        self.base.policy_enabled = False
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=AssertionError("NO REMOTE CALL")):
            before = self.db.meta().copy()
            with self.assertRaises(Exception):
                self.writer(saved)
            self.assertEqual(self.db.meta(), before)
            self.assertEqual(self.count("MODEL_DRAFT_ATTEMPTED"), 0)

    def test_spoofed_remote_result_spent_not_authenticated(self):
        saved = self.candidate()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                return_value={"pr_number": "spoof", "head_commit": "z" * 40}):
            result = self.writer(saved)
            self.assertEqual(result["disposition"],
                             "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
            self.assertEqual(self.count("MODEL_DRAFT_ATTEMPTED"), 1)
            self.assertEqual(self.count("MODEL_DRAFT_AUTHENTICATED"), 0)


if __name__ == "__main__":
    unittest.main()
