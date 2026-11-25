"""Tests for Gate 19: Persistent evidence store, hardware trainer, scheduler, Draft-PR proposer, and status CLI."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from f139.nci04_evidence_store import (
    EvidenceStoreDenied, append_evidence_record, read_evidence_records,
    summarize_evidence_store,
)
from f139.nci04_hardware_trainer import (
    build_hardware_budget, detect_hardware_profile, run_hardware_bounded_training,
)
from f139.nci04_multi_lane_scheduler import select_next_lane
from f139.nci04_native_contract import canonical, digest
from f139.nci04_self_improvement_loop import BUNDLE_SCHEMA
from f139.nci04_self_pr_proposer import (
    SelfPRProposerDenied, build_draft_pr_payload, submit_draft_pr_via_api,
)
from f139.nci04_status_cli import STATUS_SCHEMA, collect_readonly_status

FORGE_ROOT = Path(__file__).resolve().parent.parent


class Gate19PlatformStackTests(unittest.TestCase):
    def test_evidence_store_hash_chains_persists_and_detects_tampering(self):
        with tempfile.TemporaryDirectory(prefix="forge_ev_store_") as td:
            root = Path(td)
            # Refuses controller SQLite path
            with self.assertRaises(EvidenceStoreDenied):
                append_evidence_record(
                    root / "state.sqlite",
                    kind="experiment_receipt",
                    method_family="Yggdrasil",
                    status="VERIFIED",
                    payload={"ok": True},
                )
            store = root / "research_evidence.jsonl"
            r1 = append_evidence_record(
                store,
                kind="experiment_receipt",
                method_family="GLM-WorldModel",
                status="VERIFIED",
                payload={"score": 0.054},
                primary_metric="ood_mse",
                primary_value=0.054,
                higher_is_better=False,
            )
            r2 = append_evidence_record(
                store,
                kind="experiment_receipt",
                method_family="GLM-WorldModel",
                status="NEGATIVE",
                payload={"error": "timeout"},
            )
            self.assertEqual(r2["prev_record_sha256"], r1["record_sha256"])
            recs = read_evidence_records(store)
            self.assertEqual(len(recs), 2)
            summary = summarize_evidence_store(store)
            self.assertTrue(summary["chain_verified"])
            self.assertEqual(summary["by_family"]["GLM-WorldModel"]["verified"], 1)
            self.assertEqual(summary["by_family"]["GLM-WorldModel"]["negative"], 1)

            # Tampering with a single byte must fail closed
            raw = store.read_text(encoding="utf-8").replace("0.054", "0.001")
            store.write_text(raw, encoding="utf-8")
            with self.assertRaises(EvidenceStoreDenied):
                read_evidence_records(store)

    def test_hardware_trainer_runs_bounded_job_and_persists_to_evidence_store(self):
        hw = detect_hardware_profile()
        self.assertGreaterEqual(hw["cpu_count"], 1)
        budget = build_hardware_budget(max_wall_seconds=30, max_threads=2)
        self.assertEqual(budget["device"], "cpu")
        self.assertFalse(budget["auto_promote_checkpoint"])

        with tempfile.TemporaryDirectory(prefix="forge_hw_train_") as td:
            root = Path(td)
            (root / "micro_train.py").write_text(
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['FORGE_CHECKPOINT_DIR'], 'm.pt').write_bytes(b'ckpt')\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text("
                "json.dumps({'val_loss': 0.25, 'device': os.environ.get('FORGE_TRAINING_DEVICE')}))\n",
                encoding="utf-8",
            )
            store = root / "evidence.jsonl"
            rcpt = run_hardware_bounded_training(
                experiment_id="hw-agi-01",
                method_family="AGI-Kernel",
                entrypoint="micro_train.py",
                source_root=root,
                budget=budget,
                primary_metric="val_loss",
                higher_is_better=False,
                evidence_store_path=store,
            )
            self.assertEqual(rcpt["status"], "VERIFIED")
            self.assertEqual(rcpt["metrics"]["device"], "cpu")
            summary = summarize_evidence_store(store)
            self.assertEqual(summary["total_records"], 1)
            self.assertAlmostEqual(summary["by_family"]["AGI-Kernel"]["best_value"], 0.25)

    def test_multi_lane_scheduler_rotates_and_backs_off_failing_lanes(self):
        with tempfile.TemporaryDirectory(prefix="forge_sched_") as td:
            store = Path(td) / "evidence.jsonl"
            # Put 3 consecutive failures on Yggdrasil -> must back off to Wingless
            for _ in range(3):
                append_evidence_record(
                    store,
                    kind="experiment_receipt",
                    method_family="Yggdrasil",
                    status="NEGATIVE",
                    payload={"reason": "fail"},
                )
            dec = select_next_lane(
                lane_budgets={"Yggdrasil": 10, "Wingless": 5, "TTT-Hybrid": 0},
                evidence_store_path=store,
                max_consecutive_failures=3,
            )
            self.assertEqual(dec["selected_lane"], "Wingless")
            self.assertEqual(dec["skipped_lanes"]["Yggdrasil"], "failure_backoff")
            self.assertEqual(dec["skipped_lanes"]["TTT-Hybrid"], "budget_exhausted")

    def test_draft_pr_proposer_enforces_draft_and_rejects_kernel_targets(self):
        unsigned_bundle = {
            "schema": BUNDLE_SCHEMA,
            "cycle_id": "self-cycle-19",
            "target_rel_path": "f139/nci04_wingless_gen2.py",
            "total_candidates": 2,
            "qualified_count": 1,
            "rejected_count": 1,
            "denied_count": 0,
            "retained_all_attempts": True,
            "selected_candidate_id": "wingless-z-0_85",
            "selected_meta_delta": 3.0,
            "selected_after_sha256": "a" * 64,
            "evaluations": [],
            "live_controller_mutated": False,
            "requires_human_or_ci_merge": True,
            "paid_model_calls": 0,
            "auto_promote_checkpoint": False,
            "scientific_first_use": False,
        }
        bundle = dict(unsigned_bundle, bundle_sha256=digest(canonical(unsigned_bundle)))
        pr_payload = build_draft_pr_payload(bundle)
        self.assertTrue(pr_payload["draft"])
        self.assertFalse(pr_payload["auto_merge"])

        # Mock GitHub API submission verifies draft=True enforced
        class _FakeResp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_open(req, timeout=20):
            sent = json.loads(req.data.decode("utf-8"))
            self.assertTrue(sent["draft"])
            return _FakeResp(json.dumps({"number": 2001, "html_url": "https://example/pr/2001", "draft": True}).encode())

        created = submit_draft_pr_via_api(pr_payload, token="t" * 32, opener=fake_open)
        self.assertTrue(created["draft"])
        self.assertFalse(created["auto_merge"])

        # Protected kernel target must be denied
        bad = dict(unsigned_bundle, target_rel_path="f139/nci04_fresh_lifecycle.py")
        bad["bundle_sha256"] = digest(canonical(bad))
        with self.assertRaises(SelfPRProposerDenied):
            build_draft_pr_payload(bad)

    def test_status_cli_reads_sqlite_and_evidence_store_readonly(self):
        with tempfile.TemporaryDirectory(prefix="forge_status_") as td:
            root = Path(td)
            db = root / "state.sqlite"
            conn = sqlite3.connect(str(db))
            conn.execute("CREATE TABLE meta (head_seq INT, head_hash TEXT)")
            conn.execute("INSERT INTO meta VALUES (171, 'abc123')")
            conn.commit()
            conn.close()
            (root / "fresh-original-owner-source-forward-v5.json").write_text("{}", encoding="utf-8")

            store = root / "evidence.jsonl"
            append_evidence_record(
                store,
                kind="experiment_receipt",
                method_family="TTT-Hybrid",
                status="QUALIFIED",
                payload={"score": 1.55},
                primary_metric="ood_delta",
                primary_value=1.55,
                higher_is_better=True,
            )

            rep = collect_readonly_status(db_path=db, evidence_store_path=store)
            self.assertEqual(rep["schema"], STATUS_SCHEMA)
            self.assertTrue(rep["readonly"])
            self.assertEqual(rep["controller"]["head_seq"], 171)
            self.assertEqual(rep["controller"]["highest_cert_version"], 5)
            self.assertEqual(rep["evidence_store"]["total_records"], 1)

            proc = subprocess.run(
                [sys.executable, "-B", "-m", "f139.nci04_status_cli",
                 "--db", str(db), "--store", str(store), "--human"],
                cwd=str(FORGE_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
            self.assertIn("cert=v5", proc.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
