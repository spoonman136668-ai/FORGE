"""Unified Autonomous Research Driver for FORGE F139 (Gate 20).

Connects Gate 14–20's core platform stack into a single bounded, fail-closed
execution tick (`run_research_tick` / `python -B -m f139.nci04_research_driver`):
  1. Consults `select_next_lane()` over the persistent hash-chained evidence store.
  2. Builds a bounded `HardwareBudget` via `detect_hardware_profile()`.
  3. Runs a real isolated training experiment for the selected lane, stores any
     verified checkpoint into the content-addressed Checkpoint Vault, and
     appends the sealed `ExperimentReceipt` into the persistent evidence store.
  4. Optionally runs a bounded FORGE-on-FORGE self-improvement cycle and builds
     a strictly `draft: true` PR payload when a verified OOD gain is found.
  5. Emits a sealed `ResearchTickReport` + updated `collect_readonly_status()`.

Hard boundaries:
- Never mutates controller `state.sqlite` or protected kernel files.
- Never auto-promotes checkpoints (`auto_promote_checkpoint: False`).
- Never auto-merges self-improvement PRs (`requires_human_or_ci_merge: True`).
- Zero paid model calls (`paid_model_calls: 0`), `scientific_first_use: False`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from f139.nci04_checkpoint_vault import store_checkpoint
from f139.nci04_evidence_store import append_evidence_record
from f139.nci04_hardware_trainer import (
    build_hardware_budget, run_hardware_bounded_training,
)
from f139.nci04_multi_lane_scheduler import select_next_lane
from f139.nci04_native_contract import canonical, digest
from f139.nci04_self_improvement_cli import run_default_wingless_calibration_proposal
from f139.nci04_self_pr_proposer import build_draft_pr_payload
from f139.nci04_status_cli import collect_readonly_status

TICK_SCHEMA = "forge.f139.autonomous-research-tick.v1"

# Default real local benchmark mappings per lane for unified driver execution
LANE_BENCHMARKS: dict[str, tuple[str, str, str, bool]] = {
    "LLM-Experimental": ("LLM-Experimental", "l2_cosine_sgd", "val_loss", False),
    "GLM-WorldModel": ("GLM-WorldModel", "slow_fast_world_model", "ood_mse", False),
    "AGI-Kernel": ("AGI-Kernel", "elastic_consolidated_kernel", "continual_mse", False),
}


def run_research_tick(
    *,
    forge_root: Path,
    state_dir: Path,
    lane_budgets: dict[str, int] | None = None,
    run_self_improve: bool = False,
) -> dict:
    """Execute one bounded, end-to-end FORGE research & learning tick."""
    forge_root = Path(forge_root).resolve(strict=True)
    state_dir = Path(state_dir).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    store_path = state_dir / "research_evidence.jsonl"
    vault_root = state_dir / "checkpoint_vault"

    budgets = (
        {"LLM-Experimental": 10, "GLM-WorldModel": 10, "AGI-Kernel": 10}
        if lane_budgets is None
        else dict(lane_budgets)
    )
    sched = select_next_lane(lane_budgets=budgets, evidence_store_path=store_path)
    lane = sched["selected_lane"]

    experiment_receipt = None
    vault_entry = None
    if lane in LANE_BENCHMARKS:
        fam, variant, metric, higher = LANE_BENCHMARKS[lane]
        hw_budget = build_hardware_budget(max_wall_seconds=60, max_threads=2)
        with tempfile.TemporaryDirectory(prefix="forge_driver_ws_") as td:
            ws = Path(td)
            shutil.copy2(forge_root / "f139" / "nci04_method_benchmarks.py", ws / "bench_core.py")
            (ws / "run_job.py").write_text(
                f"import os, subprocess, sys\n"
                f"env = dict(os.environ, FORGE_METHOD_TASK={fam + ':' + variant!r})\n"
                f"raise SystemExit(subprocess.call([sys.executable, '-B', 'bench_core.py'], env=env))\n",
                encoding="utf-8",
            )
            experiment_receipt = run_hardware_bounded_training(
                experiment_id=f"driver-{lane.lower()}-{variant}",
                method_family=fam,
                entrypoint="run_job.py",
                source_root=ws,
                budget=hw_budget,
                primary_metric=metric,
                higher_is_better=higher,
                evidence_store_path=store_path,
            )
            if experiment_receipt["status"] == "VERIFIED":
                ckpt_payload = canonical({
                    "experiment_id": experiment_receipt["experiment_id"],
                    "metrics": experiment_receipt["metrics"],
                    "checkpoint_digests": experiment_receipt["checkpoint_digests"],
                })
                vault_entry = store_checkpoint(
                    vault_root,
                    checkpoint_bytes=ckpt_payload,
                    experiment_id=experiment_receipt["experiment_id"],
                    method_family=fam,
                    metric_summary=experiment_receipt["metrics"],
                )

    self_improve_summary = None
    draft_pr_payload = None
    if run_self_improve:
        bundle = run_default_wingless_calibration_proposal(forge_root)
        append_evidence_record(
            store_path,
            kind="self_improvement_bundle",
            method_family="Wingless",
            status="QUALIFIED" if bundle["qualified_count"] >= 1 else "REJECTED",
            payload={
                "cycle_id": bundle["cycle_id"],
                "bundle_sha256": bundle["bundle_sha256"],
                "qualified_count": bundle["qualified_count"],
                "selected_meta_delta": bundle["selected_meta_delta"],
                "paid_model_calls": 0,
                "auto_promote_checkpoint": False,
                "scientific_first_use": False,
            },
            primary_metric="ood_meta_delta",
            primary_value=bundle["selected_meta_delta"],
            higher_is_better=True,
        )
        self_improve_summary = {
            "cycle_id": bundle["cycle_id"],
            "qualified_count": bundle["qualified_count"],
            "selected_candidate_id": bundle["selected_candidate_id"],
            "selected_meta_delta": bundle["selected_meta_delta"],
            "bundle_sha256": bundle["bundle_sha256"],
        }
        if bundle["qualified_count"] >= 1 and (bundle["selected_meta_delta"] or 0) > 0:
            draft_pr_payload = build_draft_pr_payload(bundle)

    status = collect_readonly_status(evidence_store_path=store_path)

    tick_report = {
        "schema": TICK_SCHEMA,
        "selected_lane": lane,
        "experiment_status": experiment_receipt["status"] if experiment_receipt else None,
        "experiment_metrics": experiment_receipt["metrics"] if experiment_receipt else None,
        "vault_checkpoint_sha256": vault_entry["checkpoint_sha256"] if vault_entry else None,
        "self_improvement": self_improve_summary,
        "draft_pr_proposed": draft_pr_payload is not None,
        "draft_pr_title": draft_pr_payload["title"] if draft_pr_payload else None,
        "status_sha256": status["status_sha256"],
        "evidence_records_total": status["evidence_store"]["total_records"],
        "next_recommended_lane": status["next_recommended_lane"],
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    tick_report["tick_sha256"] = digest(canonical(tick_report))
    return tick_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FORGE unified bounded research driver")
    parser.add_argument("--state-dir", type=Path, required=True, help="Directory for evidence store & checkpoint vault")
    parser.add_argument("--run-self-improve", action="store_true", help="Also run bounded self-improvement sweep")
    ns = parser.parse_args(argv)
    forge_root = Path(__file__).resolve().parent.parent
    rep = run_research_tick(
        forge_root=forge_root,
        state_dir=ns.state_dir,
        run_self_improve=ns.run_self_improve,
    )
    print(json.dumps(rep, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
