"""Tests for Gate 14: FORGE core experiment runner & fail-closed self-improvement engine."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from f139.nci04_experiment_runner import (
    ExperimentRunnerDenied, build_experiment_spec, run_bounded_experiment,
)
from f139.nci04_self_improvement import (
    SCHEMA as SELF_IMPROVE_SCHEMA,
    SelfImprovementDenied,
    evaluate_self_improvement_proposal,
    validate_self_patch_target,
)

FORGE_ROOT = Path(__file__).resolve().parent.parent


class Gate14CorePlatformAndSelfImprovementTests(unittest.TestCase):
    def test_experiment_runner_executes_isolated_training_job_and_compares_baseline(self):
        with tempfile.TemporaryDirectory(prefix="forge_exp_test_") as td:
            root = Path(td)
            (root / "train_baseline.py").write_text(
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['FORGE_CHECKPOINT_DIR'], 'model.ckpt').write_bytes(b'v1')\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text("
                "json.dumps({'val_loss': 0.42, 'score': 0.71}))\n",
                encoding="utf-8",
            )
            (root / "train_candidate.py").write_text(
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['FORGE_CHECKPOINT_DIR'], 'model.ckpt').write_bytes(b'v2')\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text("
                "json.dumps({'val_loss': 0.31, 'score': 0.84}))\n",
                encoding="utf-8",
            )
            base_spec = build_experiment_spec(
                experiment_id="glm-world-baseline-v1",
                method_family="GLM-WorldModel",
                profile="python_script",
                entrypoint="train_baseline.py",
                primary_metric="score",
                higher_is_better=True,
            )
            cand_spec = build_experiment_spec(
                experiment_id="glm-world-candidate-v2",
                method_family="GLM-WorldModel",
                profile="python_script",
                entrypoint="train_candidate.py",
                primary_metric="score",
                higher_is_better=True,
            )
            base_rcpt = run_bounded_experiment(base_spec, source_root=root)
            cand_rcpt = run_bounded_experiment(
                cand_spec, source_root=root, baseline_receipt=base_rcpt
            )
            self.assertEqual(base_rcpt["status"], "VERIFIED")
            self.assertEqual(cand_rcpt["status"], "VERIFIED")
            self.assertTrue(cand_rcpt["beats_baseline"])
            self.assertAlmostEqual(cand_rcpt["delta_vs_baseline"], 0.13, places=6)
            self.assertIn("model.ckpt", cand_rcpt["checkpoint_digests"])
            self.assertNotEqual(
                base_rcpt["checkpoint_digests"]["model.ckpt"],
                cand_rcpt["checkpoint_digests"]["model.ckpt"],
            )
            self.assertFalse(cand_rcpt["auto_promote_checkpoint"])
            self.assertFalse(cand_rcpt["scientific_first_use"])
            self.assertEqual(cand_rcpt["paid_model_calls"], 0)

    def test_experiment_runner_denies_path_traversal_and_unsafe_flags(self):
        with self.assertRaises(ExperimentRunnerDenied):
            build_experiment_spec(
                experiment_id="bad-path",
                method_family="LLM-Experimental",
                profile="python_script",
                entrypoint="../escape.py",
            )
        with self.assertRaises(ExperimentRunnerDenied):
            build_experiment_spec(
                experiment_id="bad-promote",
                method_family="AGI-Kernel",
                profile="python_script",
                entrypoint="run.py",
                auto_promote_checkpoint=True,
            )

    def test_self_improvement_denies_protected_kernel_and_safety_overrides(self):
        for forbidden_path in (
            "f139/nci04_fresh_lifecycle.py",
            "f139/local_controller.py",
            "f139/nci04_self_improvement.py",
            ".github/workflows/ci.yml",
        ):
            with self.assertRaises(SelfImprovementDenied):
                validate_self_patch_target(forbidden_path, "x = 1\n")

        with self.assertRaises(SelfImprovementDenied):
            validate_self_patch_target(
                "f139/nci04_wingless_gen2.py",
                "import urllib.request\nx = 1\n",
            )
        with self.assertRaises(SelfImprovementDenied):
            validate_self_patch_target(
                "f139/nci04_wingless_gen2.py",
                "auto_promote_checkpoint = True\n",
            )

    def test_self_improvement_sandbox_qualifies_real_module_improvement_without_mutating_live(self):
        target = "f139/nci04_wingless_gen2.py"
        orig_src = (FORGE_ROOT / target).read_text(encoding="utf-8")
        # Add a bounded metadata constant to simulate a clean allowlisted self-improvement
        cand_src = orig_src + "\nFORGE_SELF_IMPROVE_META_BONUS = 1.0\n"
        meta_script = (
            "import f139.nci04_wingless_gen2 as m\n"
            "res = m.qualify_wingless_gen2_heldout()\n"
            "base_delta = res['evaluations'][0]['total_delta_vs_baseline']\n"
            "bonus = getattr(m, 'FORGE_SELF_IMPROVE_META_BONUS', 0.0)\n"
            "print(base_delta + bonus)\n"
        )
        prop = evaluate_self_improvement_proposal(
            forge_root=FORGE_ROOT,
            target_rel_path=target,
            candidate_source=cand_src,
            regression_test_modules=("f139/test_nci04_gate13_multi_lane_qualification.py",),
            meta_benchmark_script=meta_script,
        )
        self.assertEqual(prop["schema"], SELF_IMPROVE_SCHEMA)
        self.assertTrue(prop["baseline_regression_pass"])
        self.assertTrue(prop["candidate_regression_pass"])
        self.assertTrue(prop["meta_improved"])
        self.assertEqual(prop["meta_delta"], 1.0)
        self.assertTrue(prop["self_improvement_qualified"])
        self.assertFalse(prop["live_controller_mutated"])
        self.assertTrue(prop["requires_human_or_ci_merge"])
        self.assertEqual((FORGE_ROOT / target).read_text(encoding="utf-8"), orig_src)


if __name__ == "__main__":
    unittest.main()
