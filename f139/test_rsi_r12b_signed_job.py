"""R12-B signed job contract: exact-source negatives, no live admission."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, canonical
from f139.rsi_r12b_signed_job import (
    SCHEMA, AUTH_SCHEMA, SignedDevelopmentDenied,
    valid_binding, prepare, validate_intent, _development_signature,
    validate_credentialed,
)
from f139.test_rsi_r12_candidate_binding import fixture
from f139.rsi_r12_candidate_binding import SCHEMA as BIND_SCHEMA

MAIN = "a" * 40
TREE = "b" * 40
KEY = "test-only-f139-cryptographic-development-key-v1"


def synthetic_binding():
    row, candidate = fixture()
    b = {
        "schema": BIND_SCHEMA,
        "owner_source_sha": row["owner_source_sha"],
        "reservation_seq": 1472,
        "reservation_event_sha256": "d" * 64,
        "original_owner_ledger_head_sha256": "e" * 64,
        "failed_head_sha": row["failed_head_sha"],
        "failed_run_id": row["failed_run_id"],
        "failed_job_id": row["failed_job_id"],
        "failed_log_sha256": row["failed_log_sha256"],
        "source_git_blob_sha": row["source_git_blob_sha"],
        "target_path": row["target_path"],
        "before_sha256": row["before_sha256"],
        "candidate_sha256": row["candidate_sha256"],
        "task_scope_sha256": row["task_scope_sha256"],
        "mechanism": row["mechanism"],
        "development_only": True,
        "original_owner_signed": False,
        "worker_admitted": False,
        "worker_dispatched": False,
        "original_regression_qualified": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }
    b["candidate_binding_sha256"] = hashlib.sha256(canonical(b)).hexdigest()
    return b, candidate


class SignedDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.binding, self.candidate = synthetic_binding()
        self.intent = prepare(
            binding=self.binding, source_sha=MAIN, source_tree_sha=TREE,
            worker_run_id=42570000000, worker_job_id=128999999999,
            runner_os="windows-latest")

    def test_exact_contract_and_domain_separated_signature(self):
        self.assertTrue(valid_binding(self.binding))
        validate_intent(self.intent, self.binding)
        sig = _development_signature(KEY, self.intent)
        self.assertEqual(len(sig), 64)
        self.assertEqual(sig, _development_signature(KEY, self.intent))
        self.assertNotEqual(sig, hashlib.sha256(canonical(self.intent)).hexdigest())
        self.assertEqual(self.intent["schema"], SCHEMA)
        self.assertEqual(self.intent["lane"], "FORGE-self")
        for field in ("worker_admitted", "worker_dispatched",
                      "scientific_first_use", "source_promoted",
                      "autonomous_rsi_proven"):
            self.assertIs(self.intent[field], False)

    def test_binding_tamper_and_immutable_source_bytes(self):
        for field, value in (
            ("candidate_binding_sha256", "0" * 64),
            ("original_owner_ledger_head_sha256", "0" * 64),
            ("reservation_event_sha256", "0" * 64),
            ("reservation_seq", 0),
            ("candidate_sha256", "0" * 64),
            ("target_path", "../escape.py"),
            ("worker_admitted", True),
            ("original_owner_signed", True),
            ("scientific_first_use", True),
        ):
            with self.subTest(field=field):
                b = dict(self.binding)
                b[field] = value
                self.assertFalse(valid_binding(b))
                with self.assertRaises(SignedDevelopmentDenied):
                    prepare(
                        binding=b, source_sha=MAIN, source_tree_sha=TREE,
                        worker_run_id=42570000000,
                        worker_job_id=128999999999,
                        runner_os="windows-latest")

    def test_ticket_tamper_and_wrong_attempt(self):
        # Structural changes cannot be encoded as a valid R12-B intent.
        for field, value in (
            ("worker_run_attempt", 2),
            ("lane", "Yggdrasil"),
            ("workflow", "new-scheduler.yml"),
            ("event", "push"),
            ("candidate_sha256", "0" * 64),
            ("reservation_event_sha256", "0" * 64),
            ("development_only", False),
            ("worker_admitted", True),
            ("worker_dispatched", True),
            ("source_promoted", True),
            ("scientific_first_use", True),
            ("autonomous_rsi_proven", True),
        ):
            with self.subTest(field=field):
                bad = dict(self.intent)
                bad[field] = value
                with self.assertRaises(SignedDevelopmentDenied):
                    validate_intent(bad, self.binding)

        # These fields can be structurally valid for a DIFFERENT job.
        # They are covered by the HMAC and must then match independently
        # authenticated GitHub origin in validate_credentialed(), not be
        # compared with a fabricated expected source in a local fixture.
        for field, value in (
            ("source_sha", "0" * 40),
            ("source_tree_sha", "0" * 40),
            ("worker_run_id", 42570000001),
            ("worker_job_id", 128999999998),
            ("runner_os", "ubuntu-latest"),
        ):
            with self.subTest(field=field):
                other = dict(self.intent)
                other[field] = value
                validate_intent(other, self.binding)
                self.assertNotEqual(
                    _development_signature(KEY, other),
                    _development_signature(KEY, self.intent))

        for run in (0, 1, self.binding["failed_run_id"], True, None):
            with self.subTest(run=run):
                with self.assertRaises(SignedDevelopmentDenied):
                    prepare(
                        binding=self.binding, source_sha=MAIN,
                        source_tree_sha=TREE, worker_run_id=run,
                        worker_job_id=128999999999,
                        runner_os="windows-latest")
        with self.assertRaises(SignedDevelopmentDenied):
            prepare(
                binding=self.binding, source_sha=MAIN, source_tree_sha=TREE,
                worker_run_id=42570000000, worker_job_id=128999999999,
                runner_os=[])

    def test_key_length_and_signature_domain(self):
        with self.assertRaisesRegex(
                SignedDevelopmentDenied, "SIGNING_KEY_NOT_BOUNDED"):
            _development_signature("short", self.intent)
        other_domain = hashlib.sha256(
            b"LEGACY-F139-" + canonical(self.intent)).hexdigest()
        self.assertNotEqual(other_domain,
                            _development_signature(KEY, self.intent))

    def test_no_original_owner_proof_means_no_credentialed_admission(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database.initialize(Path(tmp.name) / "state.sqlite", "c" * 40)
        self.addCleanup(db.close)
        original_head = db.meta()["head_hash"]
        with self.assertRaises(Exception):
            validate_credentialed(
                db=db, candidate=self.candidate,
                owner_source_sha="c" * 40, intent=self.intent,
                signature=_development_signature(KEY, self.intent),
                signing_key=KEY,
                authenticated_main_sha=MAIN,
                authenticated_main_tree_sha=TREE,
                authenticated_run_id=self.intent["worker_run_id"],
                authenticated_job_id=self.intent["worker_job_id"],
                authenticated_attempt=1,
                authenticated_event="workflow_dispatch",
                authenticated_repository="spoonman136668-ai/FORGE",
                authenticated_workflow="forge-f139-development-worker.yml",
                authenticated_runner_os="windows-latest")
        self.assertEqual(db.meta()["head_hash"], original_head)
        self.assertEqual(
            db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)

    def test_credentialed_original_requires_historical_spend(self):
        # Verify the HMAC structure alone cannot forge an owner issuance.
        # The source-verified original SQLite ledger is required separately.
        from f139.rsi_r12e_issued_authorization import (
            AuthorizationDenied, attest_original_issuance,
        )
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database.initialize(Path(tmp.name) / "state.sqlite", "c" * 40)
        self.addCleanup(db.close)
        before = db.meta()["head_hash"]
        sig = _development_signature(KEY, self.intent)
        with self.assertRaises(AuthorizationDenied):
            attest_original_issuance(
                db=db, candidate=self.candidate,
                owner_source_sha="c" * 40, intent=self.intent,
                signature=sig, signing_key=KEY,
                authenticated_main_sha=MAIN,
                authenticated_main_tree_sha=TREE,
                authenticated_run_id=self.intent["worker_run_id"],
                authenticated_job_id=self.intent["worker_job_id"],
                authenticated_attempt=1,
                authenticated_event="workflow_dispatch",
                authenticated_repository="spoonman136668-ai/FORGE",
                authenticated_workflow="forge-f139-development-worker.yml",
                authenticated_runner_os="windows-latest")
        self.assertEqual(db.meta()["head_hash"], before)

    def test_existing_signed_worker_lanes_remain_closed(self):
        from f139.local_controller import LANES as OWNER_LANES
        from f139.verify_ticket import LANES as WORKER_LANES
        self.assertNotIn("FORGE-self", OWNER_LANES)
        self.assertNotIn("FORGE-self", WORKER_LANES)
        self.assertFalse(self.intent["worker_admitted"])


if __name__ == "__main__":
    unittest.main()
