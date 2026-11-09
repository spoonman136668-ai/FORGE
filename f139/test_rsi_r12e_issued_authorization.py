"""R12-E read-only actual original issuance evidence and no-worker gate."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, canonical
from f139.rsi_r12b_signed_job import (
    _development_signature, SignedDevelopmentDenied,
)
from f139.rsi_r12c_original_spend import KIND
from f139.rsi_r12e_issued_authorization import (
    SCHEMA, AuthorizationDenied, attest_original_issuance,
)
from f139.test_rsi_r12b_signed_job import synthetic_binding, MAIN, TREE, KEY
from f139.rsi_r12b_signed_job import prepare
from f139.test_rsi_r12_candidate_binding import fixture

SOURCE = "c" * 40


class ColdReadOnlyAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database.initialize(
            Path(self.tmp.name) / "state.sqlite", SOURCE)
        self.addCleanup(self.db.close)
        self.binding, self.candidate = synthetic_binding()
        self.intent = prepare(
            binding=self.binding, source_sha=MAIN,
            source_tree_sha=TREE,
            worker_run_id=42570000000, worker_job_id=128999999999,
            runner_os="windows-latest")
        self.signature = _development_signature(KEY, self.intent)
        self.kwargs = dict(
            db=self.db, candidate=self.candidate,
            owner_source_sha=SOURCE, intent=self.intent,
            signature=self.signature, signing_key=KEY,
            authenticated_main_sha=MAIN, authenticated_main_tree_sha=TREE,
            authenticated_run_id=self.intent["worker_run_id"],
            authenticated_job_id=self.intent["worker_job_id"],
            authenticated_attempt=1,
            authenticated_event="workflow_dispatch",
            authenticated_repository="spoonman136668-ai/FORGE",
            authenticated_workflow="forge-f139-development-worker.yml",
            authenticated_runner_os="windows-latest")

    def test_empty_original_cold_ledger_denies_even_valid_hmac(self):
        before = self.db.meta()["head_hash"]
        with self.assertRaisesRegex(
                AuthorizationDenied, "LIFETIME_ISSUANCE_MISSING"):
            attest_original_issuance(**self.kwargs)
        self.assertEqual(self.db.meta()["head_hash"], before)

    def test_synthetic_issuance_cannot_bypass_historical_original_owner(self):
        # A disposable Database event is not the authenticated R11 original
        # owner event chain, irrespective of identical intent and digest.
        from f139.rsi_r12c_original_spend import event_payload
        doc = event_payload(
            binding=self.binding, intent=self.intent,
            signature=self.signature,
            prior_head=self.db.meta()["head_hash"])
        self.db.event(KIND, doc)
        with self.assertRaises(AuthorizationDenied):
            attest_original_issuance(**self.kwargs)

    def test_source_only_success_projection_is_nontransferable(self):
        # Only exercise the source-data projection behind mocked original
        # historic custody; this is NOT a real original issuance PASS.
        from f139.rsi_r12c_original_spend import event_payload
        from f139.rsi_r12e_issued_authorization import KIND as ISSUE_KIND
        doc = event_payload(
            binding=self.binding, intent=self.intent,
            signature=self.signature,
            prior_head=self.db.meta()["head_hash"])
        self.db.event(KIND, doc)
        row = self.db.conn.execute(
            "SELECT seq,sha FROM events WHERE kind=?", (KIND,)
        ).fetchone()
        # Mock ONLY the unavailable original-source ledger custody, while
        # using the REAL R12-B signed provider-context verification.
        # This does not qualify the original Windows owner.
        with (patch("f139.rsi_r12e_issued_authorization.audit_issuance",
                    return_value=(doc,)),
              patch.object(self.db, "verify"),
              patch("f139.rsi_r12b_signed_job.bind_original_candidate",
                    return_value=self.binding)):
            proof = attest_original_issuance(**self.kwargs)
        self.assertEqual(proof["schema"], SCHEMA)
        self.assertEqual(proof["original_issuance_event_sha256"], row["sha"])
        self.assertTrue(proof["original_lifetime_spend_verified"])
        for key in ("credential_free_worker_admitted", "worker_dispatched",
                    "source_regression_qualified", "scientific_first_use",
                    "source_promoted", "autonomous_rsi_proven"):
            self.assertFalse(proof[key])

    def test_tampered_signed_job_and_authority_always_rejected(self):
        from f139.rsi_r12c_original_spend import event_payload
        doc = event_payload(
            binding=self.binding, intent=self.intent,
            signature=self.signature,
            prior_head=self.db.meta()["head_hash"])
        self.db.event(KIND, doc)
        # Full real credentialed HMAC and provider-context validator,
        # substituting ONLY a synthetic original-history binding.
        with (patch("f139.rsi_r12e_issued_authorization.audit_issuance",
                    return_value=(doc,)),
              patch.object(self.db, "verify"),
              patch("f139.rsi_r12b_signed_job.bind_original_candidate",
                    return_value=self.binding)):
            for override in (
                {"authenticated_run_id": self.intent["worker_run_id"] + 1},
                {"authenticated_job_id": self.intent["worker_job_id"] + 1},
                {"authenticated_attempt": 2},
                {"authenticated_main_sha": "f" * 40},
                {"authenticated_main_tree_sha": "f" * 40},
                {"authenticated_repository": "attacker/FORGE"},
                {"authenticated_runner_os": "ubuntu-latest"},
                {"authenticated_event": "push"},
                {"signature": "e" * 64},
                {"signing_key": "wrong-but-long-enough-development-secret-test"},
                {"owner_source_sha": "a" * 40},
                {"intent": {**self.intent, "worker_run_attempt": 2}},
            ):
                with self.subTest(override=override):
                    with self.assertRaises(AuthorizationDenied):
                        attest_original_issuance(
                            **{**self.kwargs, **override})

            # A second issuance makes replay cardinality fail even in the
            # simulated original-history fixture.
            self.db.event(KIND, doc)
            with self.assertRaisesRegex(
                    AuthorizationDenied, "ORIGINAL_ISSUANCE_EVENT_DRIFT"):
                attest_original_issuance(**self.kwargs)

    def test_credentialed_boundary_does_not_enable_worker(self):
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self", WORKER)
        self.assertNotIn("FORGE-self", OWNER)


if __name__ == "__main__":
    unittest.main()
