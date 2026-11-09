"""R12-G frozen pre-dispatch chronology and original-owner negatives."""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database, canonical
from f139.rsi_r12b_signed_job import valid_binding
from f139.test_rsi_r12b_signed_job import (
    synthetic_binding, KEY, MAIN, TREE,
)
from f139.rsi_r12g_pre_dispatch import (
    SCHEMA, KIND, PreDispatchDenied, prepare, sign,
    validate_bundle, event_payload, validate_event,
    audit_preissued, original_preissue_once,
    observe_provider_job,
)

SOURCE = "c" * 40


class TwoPhaseOriginalOwnerTests(unittest.TestCase):
    def setUp(self):
        self.binding, self.candidate = synthetic_binding()
        self.assertTrue(valid_binding(self.binding))
        self.envelope = prepare(
            binding=self.binding, source_sha=MAIN,
            source_tree_sha=TREE, runner_os="windows-latest")
        self.signature = sign(KEY, self.envelope)

    def test_preissue_has_no_unassigned_github_ids_and_is_deterministic(self):
        self.assertEqual(self.envelope["lane"], "FORGE-self")
        self.assertTrue(self.envelope["ticket"].startswith("f139-rsi-"))
        for key in ("worker_run_id", "worker_job_id",
                    "worker_run_attempt"):
            self.assertNotIn(key, self.envelope)
        validate_bundle(self.envelope, self.binding)
        self.assertEqual(
            sign(KEY, self.envelope), self.signature)
        self.assertNotEqual(
            sign(KEY, self.envelope),
            hashlib.sha256(canonical(self.envelope)).hexdigest())
        another = prepare(
            binding=self.binding, source_sha=MAIN,
            source_tree_sha=TREE, runner_os="ubuntu-latest")
        self.assertNotEqual(
            self.envelope["ticket"], another["ticket"])
        self.assertNotEqual(sign(KEY, self.envelope), sign(KEY, another))

    def test_event_payload_historical_identity_and_false_authority(self):
        doc = event_payload(
            bundle=self.envelope, signature=self.signature,
            binding=self.binding, prior_head="f" * 64)
        row = {"seq": self.binding["reservation_seq"] + 1,
               "prior_sha": "f" * 64}
        validate_event(
            payload=doc, row=row, binding=self.binding,
            source_at_event=SOURCE)
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["lifetime_issue_limit"], 1)
        self.assertTrue(doc["worker_run_id_unassigned"])
        self.assertTrue(doc["worker_job_id_unassigned"])
        self.assertNotIn("worker_run_id", doc["intent"])
        for key, value in (
            ("signature_sha256", "0" * 64),
            ("intent_sha256", "0" * 64),
            ("reservation_seq", -1),
            ("reservation_event_sha256", "0" * 64),
            ("binding_sha256", "0" * 64),
            ("prior_event_head_sha256", "0" * 64),
            ("worker_run_id_unassigned", False),
            ("worker_job_id_unassigned", False),
            ("lifetime_issue_limit", 2),
            ("retry_allowed", True),
            ("worker_dispatched", True),
            ("scientific_first_use", True),
            ("source_promoted", True),
            ("autonomous_rsi_proven", True),
        ):
            with self.subTest(key=key):
                bad = dict(doc)
                bad[key] = value
                with self.assertRaises(PreDispatchDenied):
                    validate_event(
                        payload=bad, row=row, binding=self.binding,
                        source_at_event=SOURCE)
        with self.assertRaises(PreDispatchDenied):
            validate_event(payload=doc, row=row,
                           binding=self.binding,
                           source_at_event="e" * 40)
        altered = dict(self.envelope)
        altered["worker_run_id"] = 42599999999
        with self.assertRaises(PreDispatchDenied):
            validate_bundle(altered, self.binding)

    def test_fake_original_owner_ledger_and_early_issuance_denied(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db = Database.initialize(Path(temp.name) / "state.sqlite", SOURCE)
        self.addCleanup(db.close)
        self.assertEqual(audit_preissued(db), ())
        start = db.meta()["head_hash"]
        with self.assertRaises(Exception):
            original_preissue_once(
                db=db, provider=object(), candidate=self.candidate,
                signing_key=KEY, protected_main_sha=MAIN,
                protected_tree_sha=TREE, runner_os="windows-latest")
        self.assertEqual(db.meta()["head_hash"], start)
        doc = event_payload(
            bundle=self.envelope, signature=self.signature,
            binding=self.binding, prior_head=start)
        db.event(KIND, doc)
        with self.assertRaises(Exception):
            audit_preissued(db)
        with self.assertRaises(Exception):
            db.verify()

    def test_postdispatch_observation_does_not_qualify_worker(self):
        ticket = self.envelope["ticket"]
        run = {
            "id": 42599999999, "event": "workflow_dispatch",
            "run_attempt": 1, "head_sha": MAIN, "head_branch": "main",
            "name": "F139 " + ticket,
            "path": ".github/workflows/forge-f139-development-worker.yml",
            "status": "in_progress", "conclusion": None,
            "actor": {"login": "spoonman136668-ai"},
            "repository": {"full_name": "spoonman136668-ai/FORGE"},
            "head_repository": {"full_name": "spoonman136668-ai/FORGE"},
        }
        job = {
            "id": 12345678, "run_id": run["id"],
            "head_sha": MAIN,
            "name": "rsi-self-qualification (windows-latest)",
            "labels": ["windows-latest"],
            "status": "queued", "conclusion": None,
        }
        report = observe_provider_job(
            bundle=self.envelope, run=run, job=job)
        self.assertEqual(report["run_id"], run["id"])
        self.assertTrue(report["provider_origin_shape_matched"])
        for key in (
            "original_owner_preissue_verified",
            "credentialed_worker_signature_verified",
            "credential_free_worker_admitted",
            "worker_dispatched_by_this_function",
            "scientific_first_use", "source_promoted",
            "autonomous_rsi_proven",
        ):
            self.assertFalse(report[key])
        for key, value in (
            ("run_attempt", 2), ("head_sha", "f" * 40),
            ("head_branch", "feature"), ("event", "push"),
            ("name", "F139 forged-ticket"),
            ("path", ".github/workflows/other.yml"),
            ("status", "completed"), ("conclusion", "success"),
            ("actor", {"login": "attacker"}),
            ("repository", {"full_name": "other/repo"}),
            ("head_repository", {"full_name": "attacker/FORGE"}),
        ):
            with self.subTest(run=key):
                with self.assertRaises(PreDispatchDenied):
                    observe_provider_job(
                        bundle=self.envelope,
                        run={**run, key: value}, job=job)
        for key, value in (
            ("id", 0), ("run_id", 1),
            ("head_sha", "f" * 40),
            ("name", "execute (windows-latest)"),
            ("labels", ["ubuntu-latest"]),
            ("status", "completed"), ("conclusion", "success"),
        ):
            with self.subTest(job=key):
                with self.assertRaises(PreDispatchDenied):
                    observe_provider_job(
                        bundle=self.envelope, run=run,
                        job={**job, key: value})

    def test_original_worker_not_expanded_and_old_issuer_not_new_ticket(self):
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self", WORKER)
        self.assertNotIn("FORGE-self", OWNER)
        with self.assertRaises(PreDispatchDenied):
            sign("short", self.envelope)
        with self.assertRaises(PreDispatchDenied):
            prepare(binding={}, source_sha=MAIN,
                    source_tree_sha=TREE, runner_os="windows-latest")


if __name__ == "__main__":
    unittest.main()
