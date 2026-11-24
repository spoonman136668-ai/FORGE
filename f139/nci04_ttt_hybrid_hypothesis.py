"""Preregistered TTT-Hybrid bounded-assimilation evaluator for FORGE F139.

Maintains strict architectural separation for the `TTT-Hybrid` lane
(weight and structure assimilation, bounded test-time adaptation, persistent
memory integration without homogenization).

Evaluates three distinct non-transformer adaptation policies on 3 regimes:
  1. `regime_shift_adaptation`: non-stationary target shift requiring fast
     bounded test-time adaptation.
  2. `forgetting_resistance`: retention of prior consolidated structure after
     adapting to a shifted burst (catastrophic-forgetting resistance).
  3. `adversarial_outlier_burst`: resilience against corrupted/outlier steps
     without weight blow-up or drift collapse.

Design boundaries:
- Zero transformer/attention layers, zero paid model calls, zero KTRADE
  contamination, `scientific_first_use: False`, `auto_promote_checkpoint: False`.
- Deterministic stdlib math across frozen seeds with SHA-256 report digest.
"""
from __future__ import annotations

import math
import random

from f139.nci04_multi_lane_targets import get_lane_contract
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.ttt-hybrid-bounded-assimilation-eval.v1"
FROZEN_SEEDS = (13, 29, 53, 71, 97)
TTT_HYBRID_POLICIES = (
    "static_memory_control",
    "bounded_adaptation_control",
    "trust_region_slow_fast_assimilation",
)


class TTTHybridEvalDenied(ValueError):
    """Fail-closed denial for invalid TTT-Hybrid evaluation inputs."""


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise TTTHybridEvalDenied("F139_TTT_HYBRID_" + reason)


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _l2_norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _clip_norm(v: list[float], max_norm: float) -> list[float]:
    n = _l2_norm(v)
    if n <= max_norm or n == 0.0:
        return list(v)
    scale = max_norm / n
    return [x * scale for x in v]


def _run_policy_on_seed(policy: str, seed: int) -> dict:
    """Deterministic simulation of slow structural + fast plastic assimilation."""
    rng = random.Random(seed)
    dim = 4
    w_prior = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
    w_shift = [w_prior[i] + rng.uniform(-0.9, 0.9) for i in range(dim)]

    # Start consolidated on prior task
    w_slow = list(w_prior)
    w_fast = [0.0] * dim

    def predict(x: list[float]) -> float:
        w_eff = [w_slow[i] + w_fast[i] for i in range(dim)]
        return _dot(w_eff, x)

    def update(x: list[float], y: float) -> None:
        nonlocal w_slow, w_fast
        err = y - predict(x)
        if policy == "static_memory_control":
            return
        if policy == "bounded_adaptation_control":
            # Single-timescale clipped SGD on w_slow (forgets prior + outlier sensitive)
            lr = 0.22
            step = _clip_norm([lr * err * xi for xi in x], 0.45)
            w_slow = _clip_norm([w_slow[i] + step[i] for i in range(dim)], 3.0)
            return
        if policy == "trust_region_slow_fast_assimilation":
            # Huber-damped fast plastic residual + slow structural assimilation with
            # strict trust-region radius around persistent memory `w_slow`.
            delta = 0.8
            clipped_err = max(-delta, min(delta, err))
            fast_lr = 0.28
            fast_step = _clip_norm([fast_lr * clipped_err * xi for xi in x], 0.35)
            w_fast = _clip_norm(
                [0.92 * w_fast[i] + fast_step[i] for i in range(dim)], 1.25
            )
            # Slow assimilation only integrates consistent low-residual drift
            if abs(err) <= 1.2:
                slow_lr = 0.03
                w_slow = _clip_norm(
                    [w_slow[i] + slow_lr * w_fast[i] for i in range(dim)], 3.0
                )
            return
        need(False, "UNKNOWN_POLICY")

    # Phase 1: Regime shift adaptation (24 steps on w_shift)
    shift_sq_errors: list[float] = []
    for step_idx in range(24):
        x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
        y = _dot(w_shift, x) + rng.gauss(0.0, 0.05)
        pred = predict(x)
        if step_idx >= 12:
            shift_sq_errors.append((y - pred) ** 2)
        update(x, y)

    # Phase 2: Adversarial outlier burst (6 steps with massive label corruption)
    for _ in range(6):
        x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
        y = _dot(w_shift, x) + rng.choice([-12.0, 12.0])
        update(x, y)

    # Post-outlier stability test on w_shift (12 clean steps, read-only)
    outlier_recovery_sq_errors: list[float] = []
    for _ in range(12):
        x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
        y = _dot(w_shift, x)
        outlier_recovery_sq_errors.append((y - predict(x)) ** 2)

    # Phase 3: Forgetting resistance on w_prior after resetting ephemeral fast state
    # (simulating cold-restart retention of consolidated `w_slow` structure)
    w_fast_saved = list(w_fast)
    w_fast = [0.0] * dim
    forgetting_sq_errors: list[float] = []
    for _ in range(12):
        x = [rng.gauss(0.0, 0.7) for _ in range(dim)]
        y = _dot(w_prior, x)
        forgetting_sq_errors.append((y - predict(x)) ** 2)
    w_fast = w_fast_saved

    # Verify bounded weight norm invariant
    bounded_norm_ok = (_l2_norm(w_slow) <= 3.0001) and (_l2_norm(w_fast) <= 1.2501)

    shift_mse = sum(shift_sq_errors) / len(shift_sq_errors)
    outlier_mse = sum(outlier_recovery_sq_errors) / len(outlier_recovery_sq_errors)
    forgetting_mse = sum(forgetting_sq_errors) / len(forgetting_sq_errors)
    # Composite score: negative sum of MSEs (higher is better; 0 is perfect)
    composite_score = -(shift_mse + outlier_mse + forgetting_mse)
    return {
        "shift_mse": shift_mse,
        "outlier_recovery_mse": outlier_mse,
        "forgetting_mse": forgetting_mse,
        "bounded_norm_ok": bounded_norm_ok,
        "composite_score": composite_score,
    }


def run_ttt_hybrid_preregistered_eval(
    *, seeds: tuple[int, ...] = FROZEN_SEEDS
) -> dict:
    """Run deterministic preregistered TTT-Hybrid bounded-assimilation DEV eval."""
    need(type(seeds) is tuple and len(seeds) >= 3
         and all(type(s) is int and s > 0 for s in seeds),
         "SEEDS_INVALID")
    contract = get_lane_contract("TTT-Hybrid")
    need(contract["lane"] == "TTT-Hybrid"
         and contract["architecture_class"] == "hybrid_weight_structure_assimilation",
         "LANE_CONTRACT_DRIFT")

    def eval_all():
        out = {}
        for policy in TTT_HYBRID_POLICIES:
            per_seed = [_run_policy_on_seed(policy, s) for s in seeds]
            out[policy] = {
                "policy": policy,
                "mean_shift_mse": round(sum(r["shift_mse"] for r in per_seed) / len(per_seed), 6),
                "mean_outlier_recovery_mse": round(
                    sum(r["outlier_recovery_mse"] for r in per_seed) / len(per_seed), 6
                ),
                "mean_forgetting_mse": round(
                    sum(r["forgetting_mse"] for r in per_seed) / len(per_seed), 6
                ),
                "bounded_norm_ok": all(r["bounded_norm_ok"] for r in per_seed),
                "composite_score": round(
                    sum(r["composite_score"] for r in per_seed) / len(per_seed), 6
                ),
            }
        return out

    run1 = eval_all()
    run2 = eval_all()
    reproducible = (run1 == run2)

    controls = ("static_memory_control", "bounded_adaptation_control")
    strongest_ctrl = max(controls, key=lambda k: run1[k]["composite_score"])
    strongest_score = run1[strongest_ctrl]["composite_score"]
    winners = [
        p for p in TTT_HYBRID_POLICIES
        if p not in controls
        and run1[p]["bounded_norm_ok"]
        and run1[p]["composite_score"] > strongest_score
    ]

    report = {
        "schema": SCHEMA,
        "lane": "TTT-Hybrid",
        "architecture_class": contract["architecture_class"],
        "seeds": list(seeds),
        "reproducible": reproducible,
        "strongest_control": strongest_ctrl,
        "results": run1,
        "winners_vs_controls": winners,
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    report["report_sha256"] = digest(canonical(report))
    return report
