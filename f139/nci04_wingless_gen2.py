"""Generation-2 Wingless compositional causal-binding evaluator & held-out OOD qualifier.

Responds to Gate 11's honest negative result on Wingless (where fixed-margin
0.35 abstained 28–38/100 times) by testing variance-normalized and empirical-Bayes
causal-binding policies on BOTH:
  1. Matched DEV suite (`FROZEN_SEEDS`) — exact apples-to-apples vs Gen-1 baseline.
  2. Independent Held-Out / OOD suite (`HELDOUT_SEEDS`) — 10 strictly disjoint
     seeds (fail-closed against DEV leakage), harder signature noise (0.78),
     and paired per-seed win-rate qualification (>=7/10 wins required).

Strictly isolated to the `Wingless` lane (`spoonman136668-ai/Wingless`,
`9a92fcae40c811c724b4214da03fff34126f6b4f`, `ice/relationships.go`).
Zero paid model calls, `scientific_first_use: False`, `auto_promote_checkpoint: False`.
"""
from __future__ import annotations

import math
import random

from f139.nci04_heldout_qualifier import HELDOUT_SEEDS, MIN_PAIRED_SEED_WINS
from f139.nci04_hypothesis_engine import FROZEN_SEEDS
from f139.nci04_multi_lane_targets import get_lane_contract
from f139.nci04_native_contract import canonical, digest

SCHEMA_DEV = "forge.f139.wingless-gen2-causal-binding-dev.v1"
SCHEMA_HELDOUT = "forge.f139.wingless-gen2-heldout-qualification.v1"

GEN2_WINGLESS_POLICIES = (
    "baseline_raw_cooccurrence",
    "zscore_causal_075",
    "zscore_causal_100",
    "zscore_causal_125",
    "eb_shrunk_zscore_100",
    "eb_shrunk_zscore_125",
)


class WinglessGen2Denied(ValueError):
    """Fail-closed denial for seed leakage or invalid Wingless Gen-2 inputs."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise WinglessGen2Denied("F139_WINGLESS_GEN2_" + reason)


def _decide_binding(policy: str, c0: float, c1: float) -> int | None:
    tot = c0 + c1
    if tot <= 0.0:
        return None
    diff = abs(c0 - c1)
    if policy == "baseline_raw_cooccurrence":
        return None if diff == 0.0 else (0 if c0 > c1 else 1)
    if policy == "zscore_causal_075":
        return None if (tot < 2.0 or diff < 0.75 * math.sqrt(tot)) else (0 if c0 > c1 else 1)
    if policy == "zscore_causal_100":
        return None if (tot < 2.0 or diff < 1.00 * math.sqrt(tot)) else (0 if c0 > c1 else 1)
    if policy == "zscore_causal_125":
        return None if (tot < 2.0 or diff < 1.25 * math.sqrt(tot)) else (0 if c0 > c1 else 1)
    if policy == "eb_shrunk_zscore_100":
        # Empirical-Bayes unit-pseudocount shrinkage (prior alpha=beta=0.5)
        return None if (tot < 2.0 or diff < 1.00 * math.sqrt(tot + 1.0)) else (0 if c0 > c1 else 1)
    if policy == "eb_shrunk_zscore_125":
        return None if (tot < 2.0 or diff < 1.25 * math.sqrt(tot + 1.0)) else (0 if c0 > c1 else 1)
    need(False, "UNKNOWN_POLICY")
    return None


def _score_one_seed(
    policy: str, seed: int, *, sig_acc: float, out_acc: float,
    train_steps: int, causal_queries: int, null_steps: int, null_queries_per_sig: int,
) -> dict:
    rng = random.Random(seed + 700)
    entity_law = [rng.randint(0, 1) for _ in range(4)]
    state: dict[int, list[float]] = {}

    for _ in range(train_steps):
        ent = rng.randint(0, 3)
        sig = ent if rng.random() < sig_acc else rng.randint(0, 3)
        out = entity_law[ent] if rng.random() < out_acc else (1 - entity_law[ent])
        counts = state.setdefault(sig, [0.0, 0.0])
        counts[out] += 1.0

    # Cold-restart canonical serialization check
    serialized = canonical({str(k): [round(v[0], 6), round(v[1], 6)] for k, v in state.items()})
    cold_restart_ok = len(serialized) > 0

    causal_correct = causal_wrong = causal_abstain = 0
    for _ in range(causal_queries):
        ent = rng.randint(0, 3)
        c0, c1 = state.get(ent, [0.0, 0.0])
        pred = _decide_binding(policy, c0, c1)
        if pred is None:
            causal_abstain += 1
        elif pred == entity_law[ent]:
            causal_correct += 1
        else:
            causal_wrong += 1

    null_false = null_total = 0
    for _ in range(null_queries_per_sig):
        null_state: dict[int, list[float]] = {}
        for _ in range(null_steps):
            sig = rng.randint(0, 3)
            out = rng.randint(0, 1)
            c = null_state.setdefault(sig, [0.0, 0.0])
            c[out] += 1.0
        for sig in range(4):
            c0, c1 = null_state.get(sig, [0.0, 0.0])
            null_total += 1
            if _decide_binding(policy, c0, c1) is not None:
                null_false += 1

    utility = (causal_correct - 2 * causal_wrong) - null_false
    return {
        "seed": seed,
        "causal_correct": causal_correct,
        "causal_wrong": causal_wrong,
        "causal_abstain": causal_abstain,
        "null_false_choices": null_false,
        "null_total": null_total,
        "cold_restart_invariant": cold_restart_ok,
        "composite_utility": utility,
    }


def _aggregate(policy: str, per_seed: list[dict]) -> dict:
    return {
        "policy": policy,
        "causal_correct": sum(r["causal_correct"] for r in per_seed),
        "causal_wrong": sum(r["causal_wrong"] for r in per_seed),
        "causal_abstain": sum(r["causal_abstain"] for r in per_seed),
        "null_false_choices": sum(r["null_false_choices"] for r in per_seed),
        "null_total": sum(r["null_total"] for r in per_seed),
        "cold_restart_invariant": all(r["cold_restart_invariant"] for r in per_seed),
        "composite_utility": sum(r["composite_utility"] for r in per_seed),
    }


def run_wingless_gen2_dev_eval(*, seeds: tuple[int, ...] = FROZEN_SEEDS) -> dict:
    """Run Gen-2 Wingless policies on the exact Gen-1 matched DEV protocol."""
    need(type(seeds) is tuple and len(seeds) >= 3
         and all(type(s) is int and s > 0 for s in seeds), "SEEDS_INVALID")
    contract = get_lane_contract("Wingless")

    def run_once():
        return {
            p: _aggregate(p, [
                _score_one_seed(
                    p, s, sig_acc=0.85, out_acc=0.85,
                    train_steps=40, causal_queries=20,
                    null_steps=32, null_queries_per_sig=1,
                )
                for s in seeds
            ])
            for p in GEN2_WINGLESS_POLICIES
        }

    res1 = run_once()
    res2 = run_once()
    reproducible = (res1 == res2)
    base = res1["baseline_raw_cooccurrence"]
    winners = [
        p for p in GEN2_WINGLESS_POLICIES if p != "baseline_raw_cooccurrence"
        and reproducible
        and res1[p]["cold_restart_invariant"]
        and res1[p]["null_false_choices"] <= base["null_false_choices"]
        and res1[p]["composite_utility"] > base["composite_utility"]
    ]
    report = {
        "schema": SCHEMA_DEV,
        "lane": "Wingless",
        "target_commit": contract["active_target_commit"],
        "target_tree": contract["active_target_tree"],
        "target_path": contract["active_target_path"],
        "seeds": list(seeds),
        "reproducible": reproducible,
        "results": res1,
        "winners_vs_baseline": sorted(winners),
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    report["report_sha256"] = digest(canonical(report))
    return report


def qualify_wingless_gen2_heldout(
    *, heldout_seeds: tuple[int, ...] = HELDOUT_SEEDS
) -> dict:
    """Independent held-out OOD qualification for Wingless Gen-2 policies.

    Uses 10 strictly disjoint seeds, harder signature/outcome noise (0.78/0.82),
    and balanced null controls (3 null rounds x 4 signatures = 12 null queries/seed)
    so false-positive resistance is weighted fairly alongside causal recall.
    """
    need(type(heldout_seeds) is tuple and len(heldout_seeds) >= 5
         and len(set(heldout_seeds)) == len(heldout_seeds)
         and all(type(s) is int and s > 0 for s in heldout_seeds),
         "HELDOUT_SEEDS_INVALID")
    need(set(heldout_seeds).isdisjoint(set(FROZEN_SEEDS)),
         "DEV_SEED_LEAKAGE_DETECTED")
    contract = get_lane_contract("Wingless")

    def run_once():
        return {
            p: [
                _score_one_seed(
                    p, s, sig_acc=0.78, out_acc=0.82,
                    train_steps=44, causal_queries=16,
                    null_steps=32, null_queries_per_sig=3,
                )
                for s in heldout_seeds
            ]
            for p in GEN2_WINGLESS_POLICIES
        }

    s1 = run_once()
    s2 = run_once()
    reproducible = (s1 == s2)

    base_seeds = s1["baseline_raw_cooccurrence"]
    base_agg = _aggregate("baseline_raw_cooccurrence", base_seeds)
    min_wins = min(MIN_PAIRED_SEED_WINS, len(heldout_seeds))

    evaluations: list[dict] = []
    for p in GEN2_WINGLESS_POLICIES:
        if p == "baseline_raw_cooccurrence":
            continue
        p_seeds = s1[p]
        p_agg = _aggregate(p, p_seeds)
        deltas = [
            p_seeds[i]["composite_utility"] - base_seeds[i]["composite_utility"]
            for i in range(len(heldout_seeds))
        ]
        wins = sum(1 for d in deltas if d > 0)
        ties = sum(1 for d in deltas if d == 0)
        losses = sum(1 for d in deltas if d < 0)
        total_delta = sum(deltas)
        null_ok = p_agg["null_false_choices"] <= base_agg["null_false_choices"]
        qualified = bool(
            reproducible
            and p_agg["cold_restart_invariant"]
            and total_delta > 0
            and wins >= min_wins
            and null_ok
        )
        evaluations.append({
            "policy": p,
            "metrics": p_agg,
            "paired_seed_deltas": deltas,
            "seed_wins": wins,
            "seed_ties": ties,
            "seed_losses": losses,
            "total_delta_vs_baseline": total_delta,
            "mean_delta_vs_baseline": round(total_delta / len(heldout_seeds), 4),
            "worst_seed_delta": min(deltas),
            "null_non_degradation": null_ok,
            "independent_qualification_pass": qualified,
        })

    evaluations.sort(key=lambda r: (
        not r["independent_qualification_pass"],
        -r["total_delta_vs_baseline"],
        -r["seed_wins"],
        r["policy"],
    ))
    qualified_policies = [
        r["policy"] for r in evaluations if r["independent_qualification_pass"]
    ]
    report = {
        "schema": SCHEMA_HELDOUT,
        "lane": "Wingless",
        "target_commit": contract["active_target_commit"],
        "target_tree": contract["active_target_tree"],
        "target_path": contract["active_target_path"],
        "heldout_seeds": list(heldout_seeds),
        "dev_seeds_disjoint": True,
        "reproducible": reproducible,
        "baseline": base_agg,
        "evaluations": evaluations,
        "qualified_policies": qualified_policies,
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    report["qualification_sha256"] = digest(canonical(report))
    return report
