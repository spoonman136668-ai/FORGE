"""One-Command Multi-Generation Open "Spaghetti Lab" CLI for FORGE F139 (Gate 22).

Lets you drop ANY JSON file of experimental architecture/training blueprints
(or run the built-in starter pack with zero setup), automatically execute
multi-generation evolutionary sweeps (`run_spaghetti_sweep` -> Pareto filter ->
breed next wave -> repeat), vault winning checkpoints, log all wins & crashes
to the hash-chained evidence store, and print a clean Markdown Pareto leaderboard.

Usage:
  python -B -m f139.nci04_lab_cli --state-dir ./lab_state [--blueprints ideas.json] [--generations 3] [--markdown]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from f139.nci04_blueprint_lab import run_spaghetti_sweep
from f139.nci04_native_contract import canonical, digest
from f139.nci04_pareto_comparator import compute_pareto_frontier, format_pareto_markdown

LAB_CLI_SCHEMA = "forge.f139.multi-gen-lab-cli-report.v1"

DEFAULT_STARTER_BLUEPRINTS: list[dict] = [
    {
        "blueprint_id": "starter-linear-base",
        "architecture_type": "linear-dynamics",
        "runner_mode": "composable_builtin",
        "hyperparams": {"state_rule": "linear", "lr": 0.15, "dim": 6},
    },
    {
        "blueprint_id": "starter-slow-fast-trust",
        "architecture_type": "slow-fast-trust",
        "runner_mode": "composable_builtin",
        "hyperparams": {"state_rule": "slow_fast_trust", "lr": 0.25, "clip": 0.8, "decay": 0.92, "dim": 6},
    },
    {
        "blueprint_id": "starter-hebbian-decay",
        "architecture_type": "hebbian-plasticity",
        "runner_mode": "composable_builtin",
        "hyperparams": {"state_rule": "hebbian_decay", "lr": 0.22, "clip": 0.9, "decay": 0.90, "reg": 0.04, "dim": 6},
    },
    {
        "blueprint_id": "starter-elastic-ewc",
        "architecture_type": "elastic-continual",
        "runner_mode": "composable_builtin",
        "hyperparams": {"state_rule": "elastic_ewc", "lr": 0.18, "clip": 1.0, "reg": 0.15, "dim": 6},
    },
]

DEFAULT_SEARCH_SPACE: dict[str, dict] = {
    "state_rule": {"type": "choice", "values": ["slow_fast_trust", "hebbian_decay", "elastic_ewc"]},
    "lr": {"type": "float", "min": 0.05, "max": 0.40},
    "clip": {"type": "float", "min": 0.30, "max": 1.50},
    "decay": {"type": "float", "min": 0.80, "max": 0.98},
    "reg": {"type": "float", "min": 0.01, "max": 0.30},
}

DEFAULT_OBJECTIVES: dict[str, str] = {"total_mse": "min", "state_bytes": "min"}


def run_multi_generation_lab(
    *,
    state_dir: Path,
    blueprints: list[dict] | None = None,
    objectives: dict[str, str] | None = None,
    search_space: dict[str, dict] | None = None,
    generations: int = 2,
    wave_size: int = 4,
    workspace_root: Path | None = None,
    sweep_prefix: str = "lab",
) -> dict:
    """Run `1..generations` evolutionary sweeps and compute the overall Pareto frontier."""
    if not (1 <= generations <= 10):
        raise ValueError("F139_LAB_CLI_GENERATIONS_OUT_OF_RANGE")
    active_blueprints = list(DEFAULT_STARTER_BLUEPRINTS if blueprints is None else blueprints)
    active_objectives = dict(DEFAULT_OBJECTIVES if objectives is None else objectives)
    active_space = dict(DEFAULT_SEARCH_SPACE if search_space is None else search_space)

    gen_summaries: list[dict] = []
    all_verified_candidates: list[dict] = []
    total_verified = 0
    total_negative = 0

    for gen in range(1, generations + 1):
        should_breed = (gen < generations) and bool(active_space)
        rep = run_spaghetti_sweep(
            sweep_id=f"{sweep_prefix}-gen{gen}",
            blueprints=active_blueprints,
            objectives=active_objectives,
            state_dir=state_dir,
            workspace_root=workspace_root,
            breed_search_space=(active_space if should_breed else None),
            breed_wave_size=wave_size,
        )
        total_verified += rep["verified_count"]
        total_negative += rep["negative_count"]
        gen_summaries.append({
            "generation": gen,
            "sweep_id": rep["sweep_id"],
            "verified_count": rep["verified_count"],
            "negative_count": rep["negative_count"],
            "frontier_ids": rep["pareto_frontier_ids"],
            "sweep_sha256": rep["sweep_sha256"],
        })
        for t in rep["trials"]:
            if t["status"] == "VERIFIED":
                all_verified_candidates.append({
                    "id": t["blueprint_id"],
                    "metrics": t["metrics"],
                })
        if should_breed and rep.get("next_bred_wave") and rep["next_bred_wave"]["blueprints"]:
            active_blueprints = rep["next_bred_wave"]["blueprints"]
        else:
            break

    overall_pareto = (
        compute_pareto_frontier(all_verified_candidates, objectives=active_objectives)
        if all_verified_candidates
        else {"frontier_ids": [], "frontier": [], "objectives": active_objectives}
    )
    overall_md = format_pareto_markdown(overall_pareto) if overall_pareto.get("frontier") else ""

    result = {
        "schema": LAB_CLI_SCHEMA,
        "generations_executed": len(gen_summaries),
        "total_verified": total_verified,
        "total_negative": total_negative,
        "overall_pareto_ids": overall_pareto["frontier_ids"],
        "overall_pareto": overall_pareto["frontier"],
        "overall_pareto_markdown": overall_md,
        "generations": gen_summaries,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    result["report_sha256"] = digest(canonical(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FORGE multi-generation open Blueprint Lab CLI")
    parser.add_argument("--state-dir", type=Path, required=True, help="Directory for evidence store & checkpoint vault")
    parser.add_argument("--blueprints", type=Path, default=None, help="Optional JSON file with blueprints/objectives/search_space")
    parser.add_argument("--workspace", type=Path, default=None, help="Optional workspace root for custom_script blueprints")
    parser.add_argument("--generations", type=int, default=2, help="Number of evolutionary generations (1-10)")
    parser.add_argument("--wave-size", type=int, default=4, help="Children bred per generation")
    parser.add_argument("--markdown", action="store_true", help="Print Markdown Pareto leaderboard")
    ns = parser.parse_args(argv)

    bps = objs = space = None
    if ns.blueprints is not None:
        cfg = json.loads(ns.blueprints.read_text(encoding="utf-8"))
        if type(cfg) is list:
            bps = cfg
        elif type(cfg) is dict:
            bps = cfg.get("blueprints")
            objs = cfg.get("objectives")
            space = cfg.get("search_space")

    rep = run_multi_generation_lab(
        state_dir=ns.state_dir,
        blueprints=bps,
        objectives=objs,
        search_space=space,
        generations=ns.generations,
        wave_size=ns.wave_size,
        workspace_root=ns.workspace,
    )
    if ns.markdown:
        print(f"### FORGE Multi-Generation Lab Leaderboard ({rep['generations_executed']} gens, {rep['total_verified']} verified / {rep['total_negative']} negative)\n")
        print(rep["overall_pareto_markdown"])
    else:
        print(json.dumps(rep, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
