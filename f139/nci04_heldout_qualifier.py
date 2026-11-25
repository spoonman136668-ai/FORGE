"""Independent held-out / OOD scientific qualification harness for FORGE F139.

Strictly separates DEV hypothesis selection (`FROZEN_SEEDS`) from independent
held-out / out-of-distribution (OOD) qualification (`HELDOUT_SEEDS`).

Design boundaries:
- Fail-closed non-leakage check: denies any overlap with DEV `FROZEN_SEEDS`.
- Deterministic pure-stdlib evaluation across 10 disjoint held-out seeds and
  4 harder OOD stress regimes:
    1. `ood_low_gap_causal`: narrower causal signal gap (0.65 vs 0.35).
    2. `ood_extreme_skew`: 8x sampling skew (2 obs best vs 16 obs worse).
    3. `ood_action_null_high_n`: 50/50 null control with 12 obs/arm.
    4. `ood_cold_restart_retention`: 164-byte snapshot/restore invariance.
- Computes paired per-seed utility deltas vs strongest matched control
  (`choose` and `choose_wilson`) and issues a strict fail-closed
  `independent_qualification_pass` verdict.
- Strictly read-only, zero network calls, zero paid model calls,
  `scientific_first_use: False`, and `auto_promote_checkpoint: False`.
"""
from __future__ import annotations

import base64
import json
import random

from f139.nci04_hypothesis_engine import (
    FROZEN_SEEDS, PREREG_SCHEMA, verify_candidate_ast_safety,
)
from f139.nci04_native_contract import canonical, digest
from f139.nci04_scientific_evaluator import (
    MATCHED_CONTROLS, _compile_cells_class, _record_obs,
)

SCHEMA = "forge.f139.independent-heldout-qualification.v1"
HELDOUT_SEEDS = (101, 131, 163, 197, 229, 263, 293, 331, 367, 401)
MIN_PAIRED_SEED_WINS = 7


class HeldoutQualificationDenied(ValueError):
    """Fail-closed denial for seed leakage, invalid candidate, or policy drift."""


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise HeldoutQualificationDenied("F139_HELDOUT_QUAL_" + reason)


def _score_method_one_ood_seed(cls, method_name: str, seed: int) -> dict:
    """Evaluate one PublicCausalCells method on a single held-out OOD seed."""
    rng = random.Random(seed)
    low_gap_correct = low_gap_wrong = low_gap_abstain = 0
    skew_correct = skew_wrong = skew_abstain = 0
    null_false = null_total = 0
    restart_correct = restart_wrong = restart_abstain = 0
    checkpoint_invariant = True

    # OOD Regime 1: harder low-gap causal transfer (p_best=0.65, p_worse=0.35)
    cells = cls()
    truths = []
    for addr in range(7):
        best = rng.randint(0, 1)
        truths.append(best)
        for arm in (0, 1):
            n = rng.randint(5, 9)
            p = 0.65 if arm == best else 0.35
            for _ in range(n):
                _record_obs(cells, addr, arm, 1 if rng.random() < p else 0)
    for addr, best in enumerate(truths):
        c = getattr(cells, method_name)(addr)
        if c is None:
            low_gap_abstain += 1
        elif c == best:
            low_gap_correct += 1
        else:
            low_gap_wrong += 1

    # OOD Regime 2: 8x extreme sampling skew (2 obs best vs 16 obs worse)
    cells_skew = cls()
    truths_skew = []
    for addr in range(7):
        best = rng.randint(0, 1)
        truths_skew.append(best)
        for arm in (0, 1):
            n = 2 if arm == best else 16
            p = 0.78 if arm == best else 0.28
            for _ in range(n):
                _record_obs(cells_skew, addr, arm, 1 if rng.random() < p else 0)
    for addr, best in enumerate(truths_skew):
        c = getattr(cells_skew, method_name)(addr)
        if c is None:
            skew_abstain += 1
        elif c == best:
            skew_correct += 1
        else:
            skew_wrong += 1

    # OOD Regime 3: high-n null negative control (both arms p=0.5, 12 obs/arm)
    cells_null = cls()
    for addr in range(7):
        for arm in (0, 1):
            for _ in range(12):
                _record_obs(cells_null, addr, arm, 1 if rng.random() < 0.5 else 0)
        c = getattr(cells_null, method_name)(addr)
        null_total += 1
        if c is not None:
            null_false += 1

    # OOD Regime 4: 164-byte cold-restart retention invariance
    if hasattr(cells, "snapshot") and hasattr(cls, "restore"):
        snap = cells.snapshot()
        if len(snap) != 164:
            checkpoint_invariant = False
        restored = cls.restore(snap)
        for addr, best in enumerate(truths):
            c1 = getattr(cells, method_name)(addr)
            c2 = getattr(restored, method_name)(addr)
            if c1 != c2:
                checkpoint_invariant = False
            if c2 is None:
                restart_abstain += 1
            elif c2 == best:
                restart_correct += 1
            else:
                restart_wrong += 1
        if cells.snapshot() != snap or restored.snapshot() != snap:
            checkpoint_invariant = False

    utility = (
        (low_gap_correct - 2 * low_gap_wrong)
        + (skew_correct - 2 * skew_wrong)
        - null_false
    )
    return {
        "seed": seed,
        "low_gap_correct": low_gap_correct,
        "low_gap_wrong": low_gap_wrong,
        "low_gap_abstain": low_gap_abstain,
        "skew_correct": skew_correct,
        "skew_wrong": skew_wrong,
        "skew_abstain": skew_abstain,
        "null_false_choices": null_false,
        "null_total": null_total,
        "cold_restart_correct": restart_correct,
        "cold_restart_wrong": restart_wrong,
        "cold_restart_abstain": restart_abstain,
        "checkpoint_164_byte_invariance": checkpoint_invariant,
        "composite_utility": utility,
    }


def _aggregate_seed_scores(method_name: str, per_seed: list[dict]) -> dict:
    return {
        "method": method_name,
        "low_gap_correct": sum(s["low_gap_correct"] for s in per_seed),
        "low_gap_wrong": sum(s["low_gap_wrong"] for s in per_seed),
        "low_gap_abstain": sum(s["low_gap_abstain"] for s in per_seed),
        "skew_correct": sum(s["skew_correct"] for s in per_seed),
        "skew_wrong": sum(s["skew_wrong"] for s in per_seed),
        "skew_abstain": sum(s["skew_abstain"] for s in per_seed),
        "null_false_choices": sum(s["null_false_choices"] for s in per_seed),
        "null_total": sum(s["null_total"] for s in per_seed),
        "cold_restart_correct": sum(s["cold_restart_correct"] for s in per_seed),
        "cold_restart_wrong": sum(s["cold_restart_wrong"] for s in per_seed),
        "cold_restart_abstain": sum(s["cold_restart_abstain"] for s in per_seed),
        "checkpoint_164_byte_invariance": all(
            s["checkpoint_164_byte_invariance"] for s in per_seed
        ),
        "composite_utility": sum(s["composite_utility"] for s in per_seed),
    }


def qualify_hypothesis_heldout(
    item: dict, *, heldout_seeds: tuple[int, ...] = HELDOUT_SEEDS
) -> dict:
    """Run independent held-out / OOD qualification on one preregistered hypothesis."""
    need(type(heldout_seeds) is tuple and len(heldout_seeds) >= 5
         and len(set(heldout_seeds)) == len(heldout_seeds)
         and all(type(s) is int and s > 0 for s in heldout_seeds),
         "HELDOUT_SEEDS_INVALID")
    need(set(heldout_seeds).isdisjoint(set(FROZEN_SEEDS)),
         "DEV_SEED_LEAKAGE_DETECTED")
    need(type(item) is dict and type(item.get("plan")) is dict
         and type(item.get("preregistration")) is dict,
         "HYPOTHESIS_ITEM_INVALID")
    prereg = item["preregistration"]
    need(prereg.get("schema") == PREREG_SCHEMA
         and prereg.get("frozen_protocol", {}).get("scientific_first_use") is False
         and prereg.get("frozen_protocol", {}).get("paid_model_calls") == 0
         and prereg.get("frozen_protocol", {}).get("auto_promote_checkpoint") is False,
         "PREREGISTRATION_CONTRACT_INVALID")

    prereg_no_sig = {k: v for k, v in prereg.items() if k != "preregistration_sha256"}
    need(digest(canonical(prereg_no_sig)) == prereg.get("preregistration_sha256"),
         "PREREGISTRATION_HASH_DRIFT")
    issue = json.loads(item["plan"]["body"])
    raw_intent = base64.b64decode(issue["intent_base64"], validate=True)
    intent = json.loads(raw_intent)
    after_bytes = base64.b64decode(intent["after_base64"], validate=True)
    need(digest(after_bytes) == item["plan"]["after_sha256"], "AFTER_DIGEST_MISMATCH")
    source_code = after_bytes.decode("utf-8")
    axes = prereg["axes"]
    method_name = f"choose_hyp_{axes['estimator']}_{axes['support_gate']}_{axes['tie_policy']}"
    verify_candidate_ast_safety(source_code, method_name)

    cls = _compile_cells_class(source_code, method_name)

    def run_once():
        cand_seeds = [_score_method_one_ood_seed(cls, method_name, s) for s in heldout_seeds]
        ctrl_seeds: dict[str, list[dict]] = {}
        for ctrl in MATCHED_CONTROLS:
            if hasattr(cls, ctrl):
                ctrl_seeds[ctrl] = [_score_method_one_ood_seed(cls, ctrl, s) for s in heldout_seeds]
        return cand_seeds, ctrl_seeds

    cand_s1, ctrl_s1 = run_once()
    cand_s2, ctrl_s2 = run_once()
    reproducible = (cand_s1 == cand_s2) and (ctrl_s1 == ctrl_s2)

    cand_agg = _aggregate_seed_scores(method_name, cand_s1)
    ctrl_agg = {k: _aggregate_seed_scores(k, v) for k, v in ctrl_s1.items()}
    strongest_name = max(ctrl_agg, key=lambda k: ctrl_agg[k]["composite_utility"])
    strongest_seeds = ctrl_s1[strongest_name]
    strongest_agg = ctrl_agg[strongest_name]

    paired_deltas = [
        cand_s1[i]["composite_utility"] - strongest_seeds[i]["composite_utility"]
        for i in range(len(heldout_seeds))
    ]
    seed_wins = sum(1 for d in paired_deltas if d > 0)
    seed_ties = sum(1 for d in paired_deltas if d == 0)
    seed_losses = sum(1 for d in paired_deltas if d < 0)
    total_delta = sum(paired_deltas)
    mean_delta = round(total_delta / len(heldout_seeds), 4)
    worst_seed_delta = min(paired_deltas)
    best_seed_delta = max(paired_deltas)

    null_non_degradation = (
        cand_agg["null_false_choices"] <= strongest_agg["null_false_choices"]
    )
    min_wins_required = min(MIN_PAIRED_SEED_WINS, len(heldout_seeds))
    qualified = bool(
        reproducible
        and cand_agg["checkpoint_164_byte_invariance"]
        and total_delta > 0
        and seed_wins >= min_wins_required
        and null_non_degradation
    )

    report = {
        "schema": SCHEMA,
        "hypothesis_id": prereg["hypothesis_id"],
        "method_name": method_name,
        "after_sha256": item["plan"]["after_sha256"],
        "heldout_seeds": list(heldout_seeds),
        "dev_seeds_disjoint": True,
        "reproducible": reproducible,
        "strongest_control": strongest_name,
        "candidate": cand_agg,
        "controls": ctrl_agg,
        "paired_seed_deltas": paired_deltas,
        "seed_wins": seed_wins,
        "seed_ties": seed_ties,
        "seed_losses": seed_losses,
        "total_delta_vs_strongest": total_delta,
        "mean_delta_vs_strongest": mean_delta,
        "worst_seed_delta": worst_seed_delta,
        "best_seed_delta": best_seed_delta,
        "null_non_degradation": null_non_degradation,
        "independent_qualification_pass": qualified,
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    report["qualification_sha256"] = digest(canonical(report))
    return report


def qualify_pool_heldout(
    pool: list[dict], *, heldout_seeds: tuple[int, ...] = HELDOUT_SEEDS
) -> dict:
    """Qualify a pool of hypotheses on the independent held-out OOD suite."""
    need(type(pool) is list and len(pool) > 0, "EMPTY_POOL")
    reports = [qualify_hypothesis_heldout(item, heldout_seeds=heldout_seeds) for item in pool]
    reports.sort(key=lambda r: (
        not r["independent_qualification_pass"],
        -r["total_delta_vs_strongest"],
        -r["seed_wins"],
        r["hypothesis_id"],
    ))
    qualified_ids = [r["hypothesis_id"] for r in reports if r["independent_qualification_pass"]]
    summary = {
        "schema": SCHEMA,
        "evaluated_count": len(reports),
        "qualified_count": len(qualified_ids),
        "qualified_hypothesis_ids": qualified_ids,
        "top_result": reports[0],
        "reports": reports,
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    summary["summary_sha256"] = digest(canonical(summary))
    return summary


def paired_bootstrap_ci(
    paired_deltas: list[float] | list[int],
    *,
    alpha: float = 0.05,
    n_resamples: int = 1000,
    seed: int = 20261125,
) -> dict:
    """Deterministic paired bootstrap confidence interval over per-seed deltas."""
    need(type(paired_deltas) is list and len(paired_deltas) >= 5, "BOOTSTRAP_DELTAS_INVALID")
    need(0.0001 <= alpha < 0.5, "BOOTSTRAP_ALPHA_INVALID")
    need(100 <= n_resamples <= 10000, "BOOTSTRAP_RESAMPLES_INVALID")
    rng = random.Random(seed)
    n = len(paired_deltas)
    means = []
    for _ in range(n_resamples):
        sample_sum = 0.0
        for _ in range(n):
            sample_sum += float(paired_deltas[rng.randrange(n)])
        means.append(sample_sum / n)
    means.sort()
    lo_idx = max(0, int(round((alpha / 2.0) * (n_resamples - 1))))
    hi_idx = min(n_resamples - 1, int(round((1.0 - alpha / 2.0) * (n_resamples - 1))))
    observed = sum(float(x) for x in paired_deltas) / n
    return {
        "observed_mean": round(observed, 6),
        "alpha": round(alpha, 6),
        "ci_low": round(means[lo_idx], 6),
        "ci_high": round(means[hi_idx], 6),
        "n_resamples": n_resamples,
    }


def multiple_testing_adjusted_pass(
    paired_deltas: list[float] | list[int],
    *,
    cumulative_trials: int = 1,
    base_alpha: float = 0.05,
) -> dict:
    """Bonferroni-adjusted paired bootstrap qualification guard against p-hacking."""
    need(type(cumulative_trials) is int and 1 <= cumulative_trials <= 100000,
         "CUMULATIVE_TRIALS_INVALID")
    effective_alpha = max(0.0005, base_alpha / float(cumulative_trials))
    ci = paired_bootstrap_ci(paired_deltas, alpha=effective_alpha, n_resamples=2000)
    return {
        "cumulative_trials": cumulative_trials,
        "base_alpha": base_alpha,
        "effective_alpha": round(effective_alpha, 6),
        "ci_low": ci["ci_low"],
        "ci_high": ci["ci_high"],
        "observed_mean": ci["observed_mean"],
        "adjusted_pass": bool(ci["observed_mean"] > 0.0 and ci["ci_low"] > 0.0),
    }
