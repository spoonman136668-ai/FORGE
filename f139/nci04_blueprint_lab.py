"""Open-Ended Architecture & Training Blueprint Lab ("Spaghetti Lab") for FORGE F139 (Gate 21).

Gives researchers complete freedom to design, plug in, and batch-test ANY
experimental model structure, plasticity rule, optimizer, or custom training
script — no closed architecture enum blocking novel ideas — while preserving
FORGE's fail-closed isolation, bounded execution, checkpoint vaulting,
hash-chained evidence persistence, and multi-objective Pareto ranking.

Supported execution modes per blueprint:
  1. `composable_builtin`: Runs a parameterized open-ended architecture/training
     sandbox supporting arbitrary combinations of state rules (`linear`,
     `slow_fast_trust`, `hebbian_decay`, `elastic_ewc`), learning rates,
     clipping, decay, regularization, state dimension, and shift regimes.
  2. `custom_script`: Executes ANY user-supplied Python entrypoint inside an
     isolated temporary workspace with the full blueprint JSON passed via
     `FORGE_BLUEPRINT_JSON` (strict timeout, bounded capture, sanitized env).

Hard boundaries:
- Crashing, diverging, or invalid configs fail closed as `NEGATIVE` without
  affecting other trials or the live controller.
- Zero paid API calls (`paid_model_calls: 0`), `auto_promote_checkpoint: False`,
  `scientific_first_use: False`.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

from f139.nci04_adaptive_mutator import blueprint_digest, generate_next_blueprint_wave
from f139.nci04_checkpoint_vault import store_checkpoint
from f139.nci04_evidence_store import append_evidence_record
from f139.nci04_native_contract import canonical, digest
from f139.nci04_pareto_comparator import compute_pareto_frontier, format_pareto_markdown

SWEEP_SCHEMA = "forge.f139.open-blueprint-spaghetti-sweep.v1"
MAX_SWEEP_BLUEPRINTS = 64
MAX_CAPTURE_BYTES = 131_072
FORBIDDEN_ENV_PREFIXES = ("OPENAI_", "ANTHROPIC_", "GEMINI_API_", "GH_TOKEN", "GITHUB_TOKEN")


class BlueprintLabDenied(ValueError):
    """Fail-closed denial for invalid sweep parameters or path traversal."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise BlueprintLabDenied("F139_BLUEPRINT_LAB_" + reason)


def _run_composable_builtin(bp: dict, seeds: list[int]) -> tuple[dict, bytes]:
    """Execute an open-ended parameterized structure/training blueprint."""
    hp = dict(bp.get("hyperparams", {}))
    rule = str(hp.get("state_rule", "linear"))
    dim = max(2, min(64, int(hp.get("dim", 6))))
    lr = float(hp.get("lr", 0.15))
    clip = float(hp.get("clip", 1.0))
    decay = float(hp.get("decay", 0.92))
    reg = float(hp.get("reg", 0.05))
    slow_lr = float(hp.get("slow_lr", 0.03))
    steps = max(10, min(200, int(hp.get("steps", 30))))

    if lr <= 0.0 or lr > 10.0 or clip <= 0.0 or not (0.0 <= decay <= 1.0):
        raise ValueError("Divergent or out-of-range hyperparameters")

    t0 = time.monotonic()
    shift_mses: list[float] = []
    forget_mses: list[float] = []
    last_state: dict = {}

    for seed in seeds:
        rng = random.Random(seed + 500)
        w_prior = [rng.uniform(-0.9, 0.9) for _ in range(dim)]
        w_shift = [w_prior[i] + rng.uniform(-0.8, 0.8) for i in range(dim)]
        w_slow = list(w_prior)
        w_fast = [0.0] * dim
        anchor = list(w_prior)

        # Regime shift + outlier burst
        s_errs = []
        for step in range(steps):
            x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
            y_clean = sum(w_shift[i] * x[i] for i in range(dim))
            outlier = rng.choice([-12.0, 12.0]) if (step in (steps // 3, (2 * steps) // 3)) else 0.0
            y = y_clean + outlier
            pred = sum((w_slow[i] + w_fast[i]) * x[i] for i in range(dim))
            if not math.isfinite(pred) or abs(pred) > 1e6:
                raise RuntimeError("Numeric divergence detected")
            if step >= steps // 2 and outlier == 0.0:
                s_errs.append((y_clean - pred) ** 2)
            err = y - pred
            c_err = max(-clip, min(clip, err))
            if rule == "linear":
                for i in range(dim):
                    w_slow[i] += lr * err * x[i]
            elif rule == "slow_fast_trust":
                for i in range(dim):
                    w_fast[i] = max(-2.0, min(2.0, decay * w_fast[i] + lr * c_err * x[i]))
                    if abs(err) <= clip * 1.5:
                        w_slow[i] = max(-4.0, min(4.0, w_slow[i] + slow_lr * w_fast[i]))
            elif rule == "hebbian_decay":
                for i in range(dim):
                    w_fast[i] = max(-2.0, min(2.0, decay * w_fast[i] + lr * c_err * x[i] - reg * w_fast[i]))
            elif rule == "elastic_ewc":
                for i in range(dim):
                    w_slow[i] += lr * (c_err * x[i] - reg * (w_slow[i] - anchor[i]))
            else:
                raise ValueError(f"Unsupported builtin state_rule: {rule}")

        shift_mses.append(sum(s_errs) / max(1, len(s_errs)))

        # Forgetting test on prior task after ephemeral fast reset
        f_errs = []
        for _ in range(12):
            x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
            y = sum(w_prior[i] * x[i] for i in range(dim))
            pred = sum(w_slow[i] * x[i] for i in range(dim))
            f_errs.append((y - pred) ** 2)
        forget_mses.append(sum(f_errs) / len(f_errs))
        last_state = {"rule": rule, "dim": dim, "w_slow": [round(v, 5) for v in w_slow]}

    elapsed_ms = max(1, int((time.monotonic() - t0) * 1000))
    shift_mse = round(sum(shift_mses) / len(shift_mses), 6)
    forget_mse = round(sum(forget_mses) / len(forget_mses), 6)
    total_mse = round(shift_mse + forget_mse, 6)
    ckpt_bytes = canonical(last_state)
    metrics = {
        "total_mse": total_mse,
        "shift_mse": shift_mse,
        "forgetting_mse": forget_mse,
        "state_bytes": len(ckpt_bytes),
        "elapsed_ms": elapsed_ms,
    }
    return metrics, ckpt_bytes


def _run_custom_script_blueprint(
    bp: dict, *, workspace_root: Path, seeds: list[int], timeout_seconds: int
) -> tuple[dict, bytes]:
    """Execute ANY user-supplied Python script in an isolated temporary copy."""
    entry = str(bp.get("entrypoint", ""))
    rel = Path(entry)
    need(len(entry) > 0 and not rel.is_absolute() and ".." not in rel.parts, "CUSTOM_ENTRYPOINT_INVALID")
    workspace_root = Path(workspace_root).resolve(strict=True)
    need((workspace_root / rel).is_file(), "CUSTOM_ENTRYPOINT_MISSING")

    with tempfile.TemporaryDirectory(prefix="forge_custom_bp_") as td:
        td_path = Path(td)
        work = td_path / "work"
        shutil.copytree(
            workspace_root, work,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        metrics_out = td_path / "metrics.json"
        ckpt_dir = td_path / "checkpoints"
        ckpt_dir.mkdir()
        env = {
            k: v for k, v in os.environ.items()
            if not any(k.upper().startswith(p) for p in FORBIDDEN_ENV_PREFIXES)
        }
        env["FORGE_BLUEPRINT_JSON"] = json.dumps(bp, sort_keys=True)
        env["FORGE_EXPERIMENT_SEEDS"] = ",".join(str(s) for s in seeds)
        env["FORGE_METRICS_OUT"] = str(metrics_out)
        env["FORGE_CHECKPOINT_DIR"] = str(ckpt_dir)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        t0 = time.monotonic()
        proc = subprocess.run(
            [sys.executable, "-B", str(rel)],
            cwd=str(work),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed_ms = max(1, int((time.monotonic() - t0) * 1000))
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout)[:1024].decode("utf-8", errors="replace")
            raise RuntimeError(f"Custom script failed (rc={proc.returncode}): {err}")
        if not metrics_out.is_file():
            raise RuntimeError("Custom script did not write FORGE_METRICS_OUT")
        metrics = json.loads(metrics_out.read_text(encoding="utf-8"))
        metrics.setdefault("elapsed_ms", elapsed_ms)

        ckpts = sorted(f for f in ckpt_dir.rglob("*") if f.is_file())
        ckpt_bytes = ckpts[0].read_bytes() if ckpts else canonical(metrics)
        metrics.setdefault("state_bytes", len(ckpt_bytes))
        return metrics, ckpt_bytes


def run_spaghetti_sweep(
    *,
    sweep_id: str,
    blueprints: list[dict],
    objectives: dict[str, str],
    state_dir: Path,
    workspace_root: Path | None = None,
    seeds: tuple[int, ...] = (13, 29, 53),
    timeout_seconds: int = 30,
    breed_search_space: dict[str, dict] | None = None,
    breed_wave_size: int = 4,
) -> dict:
    """Batch-test ANY set of custom architecture/training blueprints and surface what sticks."""
    need(type(sweep_id) is str and 2 <= len(sweep_id) <= 128, "SWEEP_ID_INVALID")
    need(type(blueprints) is list and 1 <= len(blueprints) <= MAX_SWEEP_BLUEPRINTS,
         "BLUEPRINTS_INVALID")
    state_dir = Path(state_dir).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    store_path = state_dir / "research_evidence.jsonl"
    vault_root = state_dir / "checkpoint_vault"

    trial_results: list[dict] = []
    pareto_inputs: list[dict] = []
    bp_by_id: dict[str, dict] = {}
    seen_digests: set[str] = set()

    for idx, bp in enumerate(blueprints):
        need(type(bp) is dict, "BLUEPRINT_NOT_DICT")
        bid = str(bp.get("blueprint_id") or f"bp-{idx + 1:02d}")
        arch_type = str(bp.get("architecture_type") or "custom-experimental")
        mode = str(bp.get("runner_mode") or "composable_builtin")
        b_sha = blueprint_digest(bp)
        seen_digests.add(b_sha)
        bp_copy = dict(bp, blueprint_id=bid, blueprint_sha256=b_sha)
        bp_by_id[bid] = bp_copy

        try:
            if mode == "composable_builtin":
                metrics, ckpt_bytes = _run_composable_builtin(bp_copy, list(seeds))
            elif mode == "custom_script":
                need(workspace_root is not None, "WORKSPACE_ROOT_REQUIRED_FOR_CUSTOM_SCRIPT")
                metrics, ckpt_bytes = _run_custom_script_blueprint(
                    bp_copy, workspace_root=workspace_root,
                    seeds=list(seeds), timeout_seconds=timeout_seconds,
                )
            else:
                raise ValueError(f"Unknown runner_mode: {mode}")

            vault_entry = store_checkpoint(
                vault_root,
                checkpoint_bytes=ckpt_bytes,
                experiment_id=bid,
                method_family=arch_type[:64],
                metric_summary=metrics,
            )
            first_obj = next(iter(objectives))
            append_evidence_record(
                store_path,
                kind="experiment_receipt",
                method_family=arch_type[:64],
                status="VERIFIED",
                payload={
                    "sweep_id": sweep_id,
                    "blueprint_id": bid,
                    "blueprint_sha256": b_sha,
                    "metrics": metrics,
                    "checkpoint_sha256": vault_entry["checkpoint_sha256"],
                    "paid_model_calls": 0,
                    "auto_promote_checkpoint": False,
                    "scientific_first_use": False,
                },
                primary_metric=first_obj,
                primary_value=float(metrics[first_obj]) if first_obj in metrics else None,
                higher_is_better=(objectives[first_obj] == "max"),
            )
            trial_results.append({
                "blueprint_id": bid,
                "architecture_type": arch_type,
                "status": "VERIFIED",
                "metrics": metrics,
                "checkpoint_sha256": vault_entry["checkpoint_sha256"],
                "error": None,
            })
            pareto_inputs.append({"id": bid, "metrics": metrics})
        except Exception as exc:
            err_msg = str(exc)[:256]
            append_evidence_record(
                store_path,
                kind="experiment_receipt",
                method_family=arch_type[:64],
                status="NEGATIVE",
                payload={
                    "sweep_id": sweep_id,
                    "blueprint_id": bid,
                    "blueprint_sha256": b_sha,
                    "error": err_msg,
                    "paid_model_calls": 0,
                    "auto_promote_checkpoint": False,
                    "scientific_first_use": False,
                },
            )
            trial_results.append({
                "blueprint_id": bid,
                "architecture_type": arch_type,
                "status": "NEGATIVE",
                "metrics": {},
                "checkpoint_sha256": None,
                "error": err_msg,
            })

    pareto = (
        compute_pareto_frontier(pareto_inputs, objectives=objectives)
        if pareto_inputs
        else {"frontier_ids": [], "frontier": [], "frontier_count": 0, "objectives": dict(objectives)}
    )
    pareto_md = format_pareto_markdown(pareto) if pareto.get("frontier") else ""

    next_wave = None
    if breed_search_space and pareto.get("frontier_ids"):
        parents = [bp_by_id[fid] for fid in pareto["frontier_ids"]]
        next_wave = generate_next_blueprint_wave(
            parents=parents,
            search_space=breed_search_space,
            wave_size=breed_wave_size,
            seen_digests=seen_digests,
            wave_prefix=f"{sweep_id}-gen2",
        )

    report = {
        "schema": SWEEP_SCHEMA,
        "sweep_id": sweep_id,
        "total_blueprints": len(trial_results),
        "verified_count": sum(1 for r in trial_results if r["status"] == "VERIFIED"),
        "negative_count": sum(1 for r in trial_results if r["status"] == "NEGATIVE"),
        "retained_all_failures": True,
        "pareto_frontier_ids": pareto["frontier_ids"],
        "pareto_frontier": pareto["frontier"],
        "pareto_markdown": pareto_md,
        "next_bred_wave": next_wave,
        "trials": trial_results,
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    report["sweep_sha256"] = digest(canonical(report))
    return report
