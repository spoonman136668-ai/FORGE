"""Tests for Gate 21: Dataset leakage guard, open Blueprint Lab, Pareto comparator, and adaptive mutator."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from f139.nci04_adaptive_mutator import generate_next_blueprint_wave
from f139.nci04_blueprint_lab import SWEEP_SCHEMA, run_spaghetti_sweep
from f139.nci04_dataset_registry import (
    DATASET_SCHEMA, DatasetRegistryDenied, register_pinned_dataset,
)
from f139.nci04_evidence_store import summarize_evidence_store
from f139.nci04_pareto_comparator import compute_pareto_frontier, format_pareto_markdown


class Gate21OpenLabAndParetoTests(unittest.TestCase):
    def test_dataset_registry_pins_clean_splits_and_denies_leakage(self):
        with tempfile.TemporaryDirectory(prefix="forge_ds_") as td:
            root = Path(td)
            tr = root / "train.txt"
            dv = root / "dev.txt"
            ho = root / "heldout.txt"
            tr.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            dv.write_text("delta\nepsilon\n", encoding="utf-8")
            ho.write_text("zeta\neta\n", encoding="utf-8")

            man = register_pinned_dataset(
                dataset_id="clean-corpus-v1",
                train_path=tr,
                dev_path=dv,
                heldout_ood_path=ho,
            )
            self.assertEqual(man["schema"], DATASET_SCHEMA)
            self.assertTrue(man["zero_split_leakage_verified"])
            self.assertEqual(man["splits"]["heldout_ood"]["samples"], 2)

            # Leak one sample from train into heldout -> must fail closed
            ho.write_text("zeta\nalpha\n", encoding="utf-8")
            with self.assertRaises(DatasetRegistryDenied) as ctx:
                register_pinned_dataset(
                    dataset_id="leaked-corpus",
                    train_path=tr,
                    dev_path=dv,
                    heldout_ood_path=ho,
                )
            self.assertIn("TRAIN_HELDOUT_LEAKAGE_DETECTED", str(ctx.exception))

    def test_pareto_frontier_identifies_nondominated_tradeoffs(self):
        cands = [
            {"id": "fast-weak", "metrics": {"loss": 0.40, "ms": 5}},
            {"id": "slow-strong", "metrics": {"loss": 0.15, "ms": 50}},
            {"id": "dominated", "metrics": {"loss": 0.45, "ms": 60}},
            {"id": "balanced-winner", "metrics": {"loss": 0.20, "ms": 12}},
        ]
        rep = compute_pareto_frontier(cands, objectives={"loss": "min", "ms": "min"})
        self.assertEqual(set(rep["frontier_ids"]), {"fast-weak", "slow-strong", "balanced-winner"})
        self.assertEqual(rep["dominated_ids"], ["dominated"])
        md = format_pareto_markdown(rep)
        self.assertIn("balanced-winner", md)

    def test_open_spaghetti_sweep_runs_wild_configs_custom_script_and_breeds_next_wave(self):
        with tempfile.TemporaryDirectory(prefix="forge_spaghetti_") as td:
            root = Path(td)
            state_dir = root / "state"
            ws = root / "custom_ws"
            ws.mkdir()
            # Custom user experimental script accepting FORGE_BLUEPRINT_JSON
            (ws / "my_wild_arch.py").write_text(
                "import json, os, pathlib\n"
                "bp = json.loads(os.environ['FORGE_BLUEPRINT_JSON'])\n"
                "scale = float(bp.get('hyperparams', {}).get('scale', 1.0))\n"
                "pathlib.Path(os.environ['FORGE_CHECKPOINT_DIR'], 'custom.bin').write_bytes(b'wild-ckpt')\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text("
                "json.dumps({'total_mse': round(0.18 * scale, 6), 'state_bytes': 64}))\n",
                encoding="utf-8",
            )

            blueprints = [
                {
                    "blueprint_id": "linear-baseline",
                    "architecture_type": "wild-linear",
                    "runner_mode": "composable_builtin",
                    "hyperparams": {"state_rule": "linear", "lr": 0.18, "dim": 6},
                },
                {
                    "blueprint_id": "trust-slow-fast",
                    "architecture_type": "wild-slow-fast-agi",
                    "runner_mode": "composable_builtin",
                    "hyperparams": {"state_rule": "slow_fast_trust", "lr": 0.25, "clip": 0.8, "decay": 0.92, "dim": 6},
                },
                {
                    "blueprint_id": "broken-divergent",
                    "architecture_type": "wild-broken",
                    "runner_mode": "composable_builtin",
                    "hyperparams": {"state_rule": "linear", "lr": 999.0},  # Intentionally crashes
                },
                {
                    "blueprint_id": "my-custom-python-arch",
                    "architecture_type": "custom-script-glm",
                    "runner_mode": "custom_script",
                    "entrypoint": "my_wild_arch.py",
                    "hyperparams": {"scale": 0.9},
                },
            ]
            search_space = {
                "lr": {"type": "float", "min": 0.05, "max": 0.40},
                "clip": {"type": "float", "min": 0.3, "max": 1.5},
                "decay": {"type": "float", "min": 0.80, "max": 0.98},
                "state_rule": {"type": "choice", "values": ["slow_fast_trust", "hebbian_decay", "elastic_ewc"]},
            }

            report = run_spaghetti_sweep(
                sweep_id="spaghetti-test-01",
                blueprints=blueprints,
                objectives={"total_mse": "min", "state_bytes": "min"},
                state_dir=state_dir,
                workspace_root=ws,
                breed_search_space=search_space,
                breed_wave_size=4,
            )
            self.assertEqual(report["schema"], SWEEP_SCHEMA)
            self.assertEqual(report["verified_count"], 3)
            self.assertEqual(report["negative_count"], 1)
            self.assertTrue(report["retained_all_failures"])
            self.assertGreaterEqual(len(report["pareto_frontier_ids"]), 1)
            self.assertIsNotNone(report["next_bred_wave"])
            self.assertEqual(report["next_bred_wave"]["generated_count"], 4)
            self.assertFalse(report["auto_promote_checkpoint"])

            # Verify all 4 trials (3 verified + 1 negative) persisted to evidence store
            ev = summarize_evidence_store(state_dir / "research_evidence.jsonl")
            self.assertEqual(ev["total_records"], 4)

    def test_adaptive_mutator_produces_unique_nonrepeating_wave(self):
        parents = [
            {"blueprint_id": "p1", "hyperparams": {"lr": 0.2, "dim": 8, "opt": "sgd"}},
            {"blueprint_id": "p2", "hyperparams": {"lr": 0.1, "dim": 16, "opt": "adam"}},
        ]
        space = {
            "lr": {"type": "float", "min": 0.01, "max": 0.5},
            "dim": {"type": "int", "min": 4, "max": 32},
            "opt": {"type": "choice", "values": ["sgd", "adam", "trust"]},
        }
        wave = generate_next_blueprint_wave(parents=parents, search_space=space, wave_size=6, seed=42)
        self.assertEqual(wave["generated_count"], 6)
        shas = [b["blueprint_sha256"] for b in wave["blueprints"]]
        self.assertEqual(len(shas), len(set(shas)))


if __name__ == "__main__":
    unittest.main()
