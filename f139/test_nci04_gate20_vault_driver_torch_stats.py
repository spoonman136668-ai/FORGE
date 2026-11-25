"""Tests for Gate 20: Checkpoint vault, PyTorch templates, unified driver, and bootstrap/multiple-testing guard."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from f139.nci04_checkpoint_vault import (
    CheckpointVaultDenied, list_vault_checkpoints, load_checkpoint, store_checkpoint,
)
from f139.nci04_heldout_qualifier import (
    multiple_testing_adjusted_pass, paired_bootstrap_ci,
)
from f139.nci04_research_driver import TICK_SCHEMA, run_research_tick
from f139.nci04_torch_templates import run_torch_template, torch_runtime_info

FORGE_ROOT = Path(__file__).resolve().parent.parent


class Gate20VaultDriverTorchStatsTests(unittest.TestCase):
    def test_checkpoint_vault_stores_deduplicates_enforces_quota_and_detects_tamper(self):
        with tempfile.TemporaryDirectory(prefix="forge_vault_") as td:
            vault = Path(td) / "vault"
            payload = b"deterministic-checkpoint-bytes-v1"
            e1 = store_checkpoint(
                vault,
                checkpoint_bytes=payload,
                experiment_id="exp-01",
                method_family="GLM-WorldModel",
                metric_summary={"ood_mse": 0.054},
                max_vault_bytes=4096,
            )
            # Re-storing identical bytes deduplicates cleanly
            e2 = store_checkpoint(
                vault,
                checkpoint_bytes=payload,
                experiment_id="exp-01",
                method_family="GLM-WorldModel",
                max_vault_bytes=4096,
            )
            self.assertEqual(e1["checkpoint_sha256"], e2["checkpoint_sha256"])
            self.assertEqual(len(list_vault_checkpoints(vault)), 1)

            loaded, meta = load_checkpoint(vault, e1["checkpoint_sha256"])
            self.assertEqual(loaded, payload)
            self.assertFalse(meta["auto_promote_checkpoint"])

            # Quota exceeded must fail closed
            with self.assertRaises(CheckpointVaultDenied):
                store_checkpoint(
                    vault,
                    checkpoint_bytes=b"x" * 2048,
                    experiment_id="exp-big",
                    method_family="AGI-Kernel",
                    max_vault_bytes=1024,
                )

            # Tampering with stored blob must fail closed on load
            blob_path = vault / "blobs" / f"{e1['checkpoint_sha256']}.bin"
            blob_path.write_bytes(b"corrupted-bytes")
            with self.assertRaises(CheckpointVaultDenied):
                load_checkpoint(vault, e1["checkpoint_sha256"])

    def test_paired_bootstrap_ci_and_multiple_testing_guard(self):
        strong = [4.0, 5.0, 3.0, 6.0, 4.0, 5.0, 4.0, 3.0, 5.0, 4.0]
        noisy = [2.0, -3.0, 1.0, -1.0, 0.5, -2.0, 2.0, -1.0, 1.0, 0.5]

        ci_strong = paired_bootstrap_ci(strong)
        ci_noisy = paired_bootstrap_ci(noisy)
        self.assertGreater(ci_strong["ci_low"], 0.0)
        self.assertLessEqual(ci_noisy["ci_low"], 0.0)

        adj_strong = multiple_testing_adjusted_pass(strong, cumulative_trials=50)
        adj_noisy = multiple_testing_adjusted_pass(noisy, cumulative_trials=50)
        self.assertTrue(adj_strong["adjusted_pass"])
        self.assertFalse(adj_noisy["adjusted_pass"])
        # Higher cumulative trial count strictly tightens effective alpha
        adj_1 = multiple_testing_adjusted_pass(strong, cumulative_trials=1)
        adj_100 = multiple_testing_adjusted_pass(strong, cumulative_trials=100)
        self.assertLess(adj_100["effective_alpha"], adj_1["effective_alpha"])

    def test_torch_templates_run_or_skip_gracefully(self):
        info = torch_runtime_info()
        rep = run_torch_template(
            template_name="linear_state_deltanet_style", seed=13, steps=5, hidden_dim=8
        )
        self.assertFalse(rep["auto_promote_checkpoint"])
        self.assertFalse(rep["scientific_first_use"])
        self.assertEqual(rep["paid_model_calls"], 0)
        if info["torch_available"]:
            self.assertEqual(rep["status"], "VERIFIED")
            self.assertIsNotNone(rep["checkpoint_sha256"])
        else:
            self.assertEqual(rep["status"], "SKIPPED_NO_TORCH")

    def test_unified_research_driver_rotates_lanes_persists_vault_and_evidence(self):
        with tempfile.TemporaryDirectory(prefix="forge_driver_") as td:
            state_dir = Path(td) / "state"
            t1 = run_research_tick(forge_root=FORGE_ROOT, state_dir=state_dir)
            t2 = run_research_tick(forge_root=FORGE_ROOT, state_dir=state_dir)
            self.assertEqual(t1["schema"], TICK_SCHEMA)
            self.assertEqual(t1["experiment_status"], "VERIFIED")
            self.assertEqual(t2["experiment_status"], "VERIFIED")
            # Scheduler automatically rotates to a different lane on tick 2
            self.assertNotEqual(t1["selected_lane"], t2["selected_lane"])
            self.assertIsNotNone(t1["vault_checkpoint_sha256"])
            self.assertEqual(t2["evidence_records_total"], 2)

            # Verify CLI entrypoint works end-to-end
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "f139.nci04_research_driver",
                 "--state-dir", str(state_dir)],
                cwd=str(FORGE_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
            out = json.loads(proc.stdout.decode("utf-8").strip())
            self.assertEqual(out["evidence_records_total"], 3)
            self.assertFalse(out["auto_promote_checkpoint"])


if __name__ == "__main__":
    unittest.main()
