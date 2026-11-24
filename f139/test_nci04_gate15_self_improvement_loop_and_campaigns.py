"""Tests for Gate 15: Multi-trial training campaigns & end-to-end FORGE self-improvement loop."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from f139.nci04_experiment_runner import build_experiment_spec
from f139.nci04_self_improvement_loop import (
    BUNDLE_SCHEMA, run_self_improvement_cycle,
)
from f139.nci04_training_campaign import (
    CAMPAIGN_SCHEMA, run_training_campaign,
)

FORGE_ROOT = Path(__file__).resolve().parent.parent


class Gate15SelfImprovementLoopAndCampaignTests(unittest.TestCase):
    def test_multi_trial_training_campaign_retains_failures_and_ranks_winners(self):
        with tempfile.TemporaryDirectory(prefix="forge_campaign_") as td:
            root = Path(td)
            # Baseline: simple online SGD on a deterministic causal regression task
            (root / "train_base.py").write_text(
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['FORGE_CHECKPOINT_DIR'], 'w.bin').write_bytes(b'base')\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text(json.dumps({'val_loss': 0.50}))\n",
                encoding="utf-8",
            )
            # Candidate 1: worse loss
            (root / "train_worse.py").write_text(
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text(json.dumps({'val_loss': 0.62}))\n",
                encoding="utf-8",
            )
            # Candidate 2: crashing trial (must be retained as NEGATIVE)
            (root / "train_crash.py").write_text("raise RuntimeError('diverged')\n", encoding="utf-8")
            # Candidate 3: better loss (lower_is_better=True)
            (root / "train_best.py").write_text(
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['FORGE_CHECKPOINT_DIR'], 'w.bin').write_bytes(b'best')\n"
                "pathlib.Path(os.environ['FORGE_METRICS_OUT']).write_text(json.dumps({'val_loss': 0.28}))\n",
                encoding="utf-8",
            )
            base_spec = build_experiment_spec(
                experiment_id="llm-exp-sgd-base",
                method_family="LLM-Experimental",
                profile="python_script",
                entrypoint="train_base.py",
                primary_metric="val_loss",
                higher_is_better=False,
            )
            cand_specs = [
                build_experiment_spec(
                    experiment_id="llm-exp-worse",
                    method_family="LLM-Experimental",
                    profile="python_script",
                    entrypoint="train_worse.py",
                    primary_metric="val_loss",
                    higher_is_better=False,
                ),
                build_experiment_spec(
                    experiment_id="llm-exp-crash",
                    method_family="LLM-Experimental",
                    profile="python_script",
                    entrypoint="train_crash.py",
                    primary_metric="val_loss",
                    higher_is_better=False,
                ),
                build_experiment_spec(
                    experiment_id="llm-exp-trust-region",
                    method_family="LLM-Experimental",
                    profile="python_script",
                    entrypoint="train_best.py",
                    primary_metric="val_loss",
                    higher_is_better=False,
                ),
            ]
            ledger = run_training_campaign(
                campaign_id="llm-exp-campaign-01",
                baseline_spec=base_spec,
                candidate_specs=cand_specs,
                source_root=root,
            )
            self.assertEqual(ledger["schema"], CAMPAIGN_SCHEMA)
            self.assertEqual(ledger["total_trials_executed"], 3)
            self.assertEqual(ledger["verified_count"], 2)
            self.assertEqual(ledger["negative_count"], 1)
            self.assertTrue(ledger["retained_all_failures"])
            self.assertEqual(ledger["best_experiment_id"], "llm-exp-trust-region")
            self.assertAlmostEqual(ledger["best_delta_vs_baseline"], -0.22, places=6)
            self.assertFalse(ledger["auto_promote_checkpoint"])
            self.assertFalse(ledger["scientific_first_use"])
            self.assertEqual(ledger["paid_model_calls"], 0)

    def test_self_improvement_loop_filters_denied_rejected_and_qualifies_real_gain(self):
        target = "f139/nci04_wingless_gen2.py"
        orig_src = (FORGE_ROOT / target).read_text(encoding="utf-8")

        # Candidate A: Denied (forbidden network import)
        cand_denied = "import urllib.request\n" + orig_src

        # Candidate B: Rejected (breaks regression tests)
        cand_broken = orig_src.replace("return None", "raise RuntimeError('broken')", 1)

        # Candidate C: Real algorithmic self-improvement on Wingless Gen-2!
        # Replace eb_shrunk_zscore_100's pseudocount (tot + 1.0) with (tot + 0.5)
        # or add a tighter calibrated threshold and test against real 10-seed held-out OOD.
        cand_improved = orig_src.replace(
            "diff < 1.00 * math.sqrt(tot)",
            "diff < 0.90 * math.sqrt(tot)",
            1,
        )

        meta_script = (
            "from f139.nci04_wingless_gen2 import qualify_wingless_gen2_heldout\n"
            "res = qualify_wingless_gen2_heldout()\n"
            "print(res['evaluations'][0]['total_delta_vs_baseline'])\n"
        )
        bundle = run_self_improvement_cycle(
            cycle_id="forge-self-wingless-cal-01",
            forge_root=FORGE_ROOT,
            target_rel_path=target,
            candidates=[
                {"candidate_id": "unsafe-net", "source": cand_denied},
                {"candidate_id": "broken-reg", "source": cand_broken},
                {"candidate_id": "zscore-090-cal", "source": cand_improved},
            ],
            regression_test_modules=("f139/test_nci04_gate13_multi_lane_qualification.py",),
            meta_benchmark_script=meta_script,
        )
        self.assertEqual(bundle["schema"], BUNDLE_SCHEMA)
        self.assertEqual(bundle["total_candidates"], 3)
        self.assertEqual(bundle["denied_count"], 1)
        self.assertGreaterEqual(bundle["rejected_count"], 1)
        self.assertTrue(bundle["retained_all_attempts"])
        self.assertFalse(bundle["live_controller_mutated"])
        self.assertTrue(bundle["requires_human_or_ci_merge"])
        self.assertEqual((FORGE_ROOT / target).read_text(encoding="utf-8"), orig_src)


if __name__ == "__main__":
    unittest.main()
