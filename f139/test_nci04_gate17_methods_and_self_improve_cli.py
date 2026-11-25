"""Tests for Gate 17: Multi-method training campaigns, Wingless Go adapter, and Self-Improve CLI."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from f139.nci04_experiment_runner import build_experiment_spec
from f139.nci04_training_campaign import run_training_campaign
from f139.nci04_wingless_go_adapter import (
    SCHEMA as WINGLESS_GO_SCHEMA,
    WinglessGoAdapterDenied,
    build_wingless_go_experiment_spec,
)

FORGE_ROOT = Path(__file__).resolve().parent.parent


def _write_benchmark_workspace(root: Path, family: str, variants: list[str]) -> None:
    shutil.copy2(FORGE_ROOT / "f139" / "nci04_method_benchmarks.py", root / "bench_core.py")
    for var in variants:
        (root / f"run_{var}.py").write_text(
            f"import os, subprocess, sys\n"
            f"env = dict(os.environ, FORGE_METHOD_TASK={family + ':' + var!r})\n"
            f"raise SystemExit(subprocess.call([sys.executable, '-B', 'bench_core.py'], env=env))\n",
            encoding="utf-8",
        )


class Gate17MethodsAndSelfImproveCLITests(unittest.TestCase):
    def test_real_llm_experimental_training_campaign(self):
        with tempfile.TemporaryDirectory(prefix="forge_llm_exp_") as td:
            root = Path(td)
            variants = ["sgd_baseline", "momentum_clipped", "trust_region_adaptive"]
            _write_benchmark_workspace(root, "LLM-Experimental", variants)
            base = build_experiment_spec(
                experiment_id="llm-sgd-base",
                method_family="LLM-Experimental",
                profile="python_script",
                entrypoint="run_sgd_baseline.py",
                primary_metric="val_loss",
                higher_is_better=False,
            )
            cands = [
                build_experiment_spec(
                    experiment_id=f"llm-{v}",
                    method_family="LLM-Experimental",
                    profile="python_script",
                    entrypoint=f"run_{v}.py",
                    primary_metric="val_loss",
                    higher_is_better=False,
                )
                for v in variants[1:]
            ]
            ledger = run_training_campaign(
                campaign_id="llm-exp-next-token-01",
                baseline_spec=base,
                candidate_specs=cands,
                source_root=root,
            )
            self.assertEqual(ledger["verified_count"], 2)
            self.assertEqual(ledger["negative_count"], 0)
            # Honest negative control: neither variant beat SGD on 180-token Markov stream
            self.assertIsNone(ledger["best_experiment_id"])
            self.assertTrue(all(r["metrics"]["val_loss"] > 0 for r in ledger["trial_receipts"]))
            self.assertFalse(ledger["auto_promote_checkpoint"])

    def test_real_glm_world_model_and_agi_kernel_campaigns(self):
        with tempfile.TemporaryDirectory(prefix="forge_glm_agi_") as td:
            root = Path(td)
            _write_benchmark_workspace(
                root, "GLM-WorldModel", ["linear_dynamics_baseline", "slow_fast_world_model"]
            )
            glm_ledger = run_training_campaign(
                campaign_id="glm-world-shift-01",
                baseline_spec=build_experiment_spec(
                    experiment_id="glm-linear-base",
                    method_family="GLM-WorldModel",
                    profile="python_script",
                    entrypoint="run_linear_dynamics_baseline.py",
                    primary_metric="ood_mse",
                    higher_is_better=False,
                ),
                candidate_specs=[
                    build_experiment_spec(
                        experiment_id="glm-slow-fast",
                        method_family="GLM-WorldModel",
                        profile="python_script",
                        entrypoint="run_slow_fast_world_model.py",
                        primary_metric="ood_mse",
                        higher_is_better=False,
                    )
                ],
                source_root=root,
            )
            self.assertEqual(glm_ledger["best_experiment_id"], "glm-slow-fast")
            self.assertLess(glm_ledger["best_delta_vs_baseline"], 0.0)

            _write_benchmark_workspace(
                root, "AGI-Kernel", ["naive_finetune_baseline", "elastic_consolidated_kernel"]
            )
            agi_ledger = run_training_campaign(
                campaign_id="agi-continual-01",
                baseline_spec=build_experiment_spec(
                    experiment_id="agi-naive-base",
                    method_family="AGI-Kernel",
                    profile="python_script",
                    entrypoint="run_naive_finetune_baseline.py",
                    primary_metric="continual_mse",
                    higher_is_better=False,
                ),
                candidate_specs=[
                    build_experiment_spec(
                        experiment_id="agi-elastic-kernel",
                        method_family="AGI-Kernel",
                        profile="python_script",
                        entrypoint="run_elastic_consolidated_kernel.py",
                        primary_metric="continual_mse",
                        higher_is_better=False,
                    )
                ],
                source_root=root,
            )
            self.assertEqual(agi_ledger["best_experiment_id"], "agi-elastic-kernel")
            self.assertLess(agi_ledger["best_delta_vs_baseline"], 0.0)

    def test_wingless_go_adapter_pins_commit_and_rejects_unallowlisted_package(self):
        rec = build_wingless_go_experiment_spec(
            experiment_id="wingless-ice-go-test-01", go_package="./ice"
        )
        self.assertEqual(rec["schema"], WINGLESS_GO_SCHEMA)
        self.assertEqual(rec["target_commit"], "9a92fcae40c811c724b4214da03fff34126f6b4f")
        self.assertEqual(rec["experiment_spec"]["profile"], "go_test")
        self.assertFalse(rec["auto_promote_checkpoint"])
        with self.assertRaises(WinglessGoAdapterDenied):
            build_wingless_go_experiment_spec(
                experiment_id="wingless-bad-pkg", go_package="./evil"
            )

    def test_read_only_self_improvement_cli_runs_cleanly_without_mutating_repo(self):
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "f139.nci04_self_improvement_cli", str(FORGE_ROOT)],
            cwd=str(FORGE_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
        out = json.loads(proc.stdout.decode("utf-8").strip())
        self.assertEqual(out["target_rel_path"], "f139/nci04_wingless_gen2.py")
        self.assertEqual(len(out["bundle_sha256"]), 64)
        self.assertFalse(out["live_controller_mutated"])
        self.assertTrue(out["requires_human_or_ci_merge"])


if __name__ == "__main__":
    unittest.main()
