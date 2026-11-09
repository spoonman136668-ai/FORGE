"""R12 source-only identity binding: positive data check, negative authority."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from f139.local_controller import Database
from f139.nci04_owner_ledger import SEALED_OWNER_PREFIX_HEAD
from f139.rsi_r11_owner_once import KIND, SCHEMA as R11_SCHEMA, SCOPE
from f139.rsi_r10_self_scope import AFTER_RUN
from f139.rsi_r6_known_repair_cycle import (
    Proposal, SCHEMA as R6_SCHEMA, FAILURE, digest,
)
from f139.rsi_r6_provider_readback import Readback, READBACK_SCHEMA
from f139.rsi_r12_candidate_binding import (
    SCHEMA, CandidateBindingDenied, matches_reserved_candidate,
    bind_original_candidate,
)

SOURCE = "c" * 40
CANDIDATE_SOURCE = b"import sqlite3\n# corrected candidate\n"
BEFORE = b"import sqlite3\n# original candidate\n"


def fixture():
    p = Proposal(
        R6_SCHEMA, "1" * 64, "2" * 40, "f139/diagnostic.py",
        digest(BEFORE), digest(CANDIDATE_SOURCE), CANDIDATE_SOURCE,
        "r16-direct", FAILURE,
    )
    rb = Readback(
        READBACK_SCHEMA, AFTER_RUN + 1, 128880000001,
        p.parent_sha, p.path, "4" * 40, "5" * 64, p,
    )
    reservation = {
        "schema": R11_SCHEMA,
        "owner_source_sha": SOURCE,
        "original_owner_prefix_sha256": SEALED_OWNER_PREFIX_HEAD,
        "failed_head_sha": rb.original_head_sha,
        "failed_run_id": rb.run_id,
        "failed_job_id": rb.job_id,
        "failed_log_sha256": rb.log_sha256,
        "source_git_blob_sha": rb.source_git_blob_sha,
        "target_path": rb.path,
        "before_sha256": p.original_sha256,
        "candidate_sha256": p.candidate_sha256,
        "task_scope_sha256": p.task_scope_sha256,
        "failure_class": FAILURE,
        "mechanism": p.mechanism,
        "prior_event_head_sha256": "0" * 64,
        "operator_scope": SCOPE,
        "development_only": True,
        "new_worker_created": False,
        "owner_self_worker_admitted": False,
        "worker_dispatched": False,
        "source_promoted": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "autonomous_rsi_proven": False,
    }
    return reservation, rb


class SourceBindingTests(unittest.TestCase):
    def test_all_authentic_source_fields_match_without_authority(self):
        doc, rb = fixture()
        self.assertTrue(matches_reserved_candidate(doc, rb))
        self.assertFalse(rb.original_owner_admitted)
        self.assertFalse(rb.proposal.qualified)

    def test_negative_source_and_readback_drifts(self):
        doc, rb = fixture()
        for key, value in (
            ("failed_run_id", rb.run_id + 1),
            ("failed_job_id", rb.job_id + 1),
            ("failed_head_sha", "e" * 40),
            ("failed_log_sha256", "e" * 64),
            ("source_git_blob_sha", "e" * 40),
            ("target_path", "f139/another.py"),
            ("candidate_sha256", "e" * 64),
            ("before_sha256", "e" * 64),
            ("task_scope_sha256", "e" * 64),
            ("mechanism", "different"),
            ("failure_class", "OTHER"),
            ("schema", "other"),
        ):
            with self.subTest(field=key):
                altered = dict(doc)
                altered[key] = value
                self.assertFalse(matches_reserved_candidate(altered, rb))
        self.assertFalse(matches_reserved_candidate(doc, replace(
            rb, original_owner_admitted=True)))
        self.assertFalse(matches_reserved_candidate(doc, replace(
            rb, source_regression_pass=True)))
        self.assertFalse(matches_reserved_candidate(doc, replace(
            rb, scientific_first_use=True)))
        self.assertFalse(matches_reserved_candidate(doc, replace(
            rb, production_release=True)))
        self.assertFalse(matches_reserved_candidate(doc, replace(
            rb, proposal=replace(rb.proposal, qualified=True))))
        self.assertFalse(matches_reserved_candidate(doc, replace(
            rb, proposal=replace(rb.proposal, source=b"altered"))))
        self.assertFalse(matches_reserved_candidate(doc, object()))

    def test_synthetic_original_ledgers_fail_cold_audit(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database.initialize(Path(tmp.name) / "state.sqlite", SOURCE)
        self.addCleanup(db.close)
        doc, rb = fixture()
        before = db.meta()["head_hash"]
        with self.assertRaisesRegex(CandidateBindingDenied,
                                    "ONE_AUTHENTIC_RESERVATION_REQUIRED"):
            bind_original_candidate(
                db=db, candidate=rb, expected_owner_source_sha=SOURCE)
        self.assertEqual(before, db.meta()["head_hash"])
        db.event(KIND, doc)
        with self.assertRaises(Exception):
            bind_original_candidate(
                db=db, candidate=rb, expected_owner_source_sha=SOURCE)
        self.assertEqual(
            db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)

    def test_no_unsigned_forge_self_worker_admission(self):
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self", OWNER)
        self.assertNotIn("FORGE-self", WORKER)


if __name__ == "__main__":
    unittest.main()
