"""R12-I: original one-use terminal custody with real negative controls."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from f139.local_controller import Database
from f139.rsi_r12g_pre_dispatch import (
    prepare as preprepare, event_payload as prepayload, sign as presign,
)
from f139.rsi_r12i_terminal import (
    KIND, SCHEMA, TerminalDenied, snapshot, payload, validate_event,
    audit_terminal, record_original_terminal_once,
)
from f139.test_rsi_r12b_signed_job import (
    synthetic_binding, KEY, MAIN, TREE,
)

SOURCE = "c" * 40


def fixture():
    binding, candidate = synthetic_binding()
    intent = preprepare(binding=binding, source_sha=MAIN,
                        source_tree_sha=TREE, runner_os="windows-latest")
    pre = prepayload(bundle=intent, signature=presign(KEY, intent),
                     binding=binding, prior_head="d" * 64)
    pre_row = {"seq": binding["reservation_seq"] + 1,
               "sha": "a" * 64}
    run_id = max(42599999999, intent["failed_run_id"] + 1)
    run = {
        "id": run_id, "run_attempt": 1, "status": "completed",
        "conclusion": "failure", "event": "workflow_dispatch",
        "head_sha": MAIN, "head_branch": "main",
        "name": "F139 " + intent["ticket"],
        "path": ".github/workflows/forge-f139-development-worker.yml",
        "actor": {"login": "spoonman136668-ai"},
        "repository": {"full_name": "spoonman136668-ai/FORGE"},
        "head_repository": {"full_name": "spoonman136668-ai/FORGE"},
    }
    job = {
        "id": 129999999999, "run_id": run_id, "head_sha": MAIN,
        "name": "rsi-self-qualification (windows-latest)",
        "labels": ["windows-latest"], "status": "completed",
        "conclusion": "failure",
    }
    row = {"seq": pre_row["seq"] + 1, "prior_sha": "e" * 64}
    doc = payload(preissue=pre, preissue_row=pre_row, binding=binding,
                  run=run, job=job, prior_head=row["prior_sha"])
    return binding, intent, pre, pre_row, run, job, row, doc


class OriginalTerminalTests(unittest.TestCase):
    def setUp(self):
        (self.binding, self.intent, self.pre, self.pre_row,
         self.run, self.job, self.row, self.doc) = fixture()

    def test_frozen_terminal_event_is_log_only_not_worker_admission(self):
        validate_event(document=self.doc, event_row=self.row,
                       preissue=self.pre, preissue_row=self.pre_row,
                       binding=self.binding, source_at_event=SOURCE)
        self.assertEqual(self.doc["schema"], SCHEMA)
        self.assertEqual(self.doc["worker_run_conclusion"], "failure")
        self.assertEqual(self.doc["worker_job_conclusion"], "failure")
        self.assertEqual(self.doc["one_terminal_maximum"], 1)
        for name in (
            "original_only_public_signature_verified",
            "credentialed_worker_signature_verified",
            "credential_free_worker_admitted", "scientific_first_use",
            "source_promoted", "autonomous_rsi_proven"):
            self.assertIs(self.doc[name], False)
        self.assertEqual(self.doc["retry_allowed"], False)

    def test_strict_provider_terminal_identity_and_negative_outcomes(self):
        a, b = snapshot(intent=self.intent, run=self.run, job=self.job)
        self.assertEqual(a["id"], b["run_id"])
        for field, bad in (
            ("run_attempt", 2), ("status", "in_progress"),
            ("head_sha", "f" * 40), ("head_branch", "dev"),
            ("name", "F139 forged"), ("event", "push"),
            ("actor", {"login": "attacker"}),
            ("repository", {"full_name": "unrelated/FORGE"}),
            ("head_repository", {"full_name": "wrong/FORGE"}),
            ("path", ".github/workflows/other.yml"),
            ("id", self.intent["failed_run_id"]),
            ("conclusion", None),
        ):
            with self.subTest(run_field=field):
                with self.assertRaises(TerminalDenied):
                    snapshot(intent=self.intent,
                             run={**self.run, field: bad},
                             job=self.job)
        for field, bad in (
            ("run_id", 1), ("id", 0), ("status", "queued"),
            ("conclusion", None), ("head_sha", "f" * 40),
            ("labels", ["ubuntu-latest"]),
            ("name", "forge-f139-generic"),
        ):
            with self.subTest(job_field=field):
                with self.assertRaises(TerminalDenied):
                    snapshot(intent=self.intent, run=self.run,
                             job={**self.job, field: bad})

    def test_historic_terminal_tamper_and_replay_controls(self):
        for key, value in (
            ("owner_source_sha", "f" * 40),
            ("preissue_event_sha256", "f" * 64),
            ("preissue_seq", -1),
            ("reservation_seq", -1),
            ("reservation_event_sha256", "f" * 64),
            ("protected_main_tree_sha", "f" * 40),
            ("preissue_intent_sha256", "f" * 64),
            ("candidate_sha256", "f" * 64),
            ("worker_run_id", 1),
            ("worker_job_id", 0),
            ("worker_run_attempt", 2),
            ("worker_run_conclusion", "queued"),
            ("provider_run_snapshot_sha256", "invalid"),
            ("prior_event_head_sha256", "a" * 64),
            ("one_terminal_maximum", 2),
            ("retry_allowed", True),
            ("original_only_public_signature_verified", True),
            ("credential_free_worker_admitted", True),
            ("source_promoted", True), ("scientific_first_use", True),
            ("autonomous_rsi_proven", True),
        ):
            with self.subTest(field=key):
                bad = {**self.doc, key: value}
                with self.assertRaises(TerminalDenied):
                    validate_event(document=bad, event_row=self.row,
                                   preissue=self.pre, preissue_row=self.pre_row,
                                   binding=self.binding, source_at_event=SOURCE)
        with self.assertRaises(TerminalDenied):
            validate_event(document=self.doc,
                           event_row={**self.row, "seq": self.pre_row["seq"]},
                           preissue=self.pre, preissue_row=self.pre_row,
                           binding=self.binding, source_at_event=SOURCE)

    def test_disposable_sqlite_cannot_forge_original_terminal(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database.initialize(Path(tmp.name) / "state.sqlite", SOURCE)
        self.addCleanup(db.close)
        before = db.meta()["head_hash"]
        self.assertEqual(audit_terminal(db), ())
        with self.assertRaises(Exception):
            record_original_terminal_once(
                db=db, provider=object(), run_id=self.run["id"],
                job_id=self.job["id"])
        self.assertEqual(db.meta()["head_hash"], before)
        db.event(KIND, self.doc)
        with self.assertRaises(Exception):
            db.verify()
        with self.assertRaises(Exception):
            audit_terminal(db)
        self.assertEqual(db.meta()["head_seq"], 1)

    def test_synthetic_terminal_is_never_public_key_owner_proof(self):
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self", WORKER)
        self.assertNotIn("FORGE-self", OWNER)
        self.assertIs(self.doc["original_only_public_signature_verified"],
                      False)
        self.assertIs(self.doc["credential_free_worker_admitted"], False)


if __name__ == "__main__":
    unittest.main()
