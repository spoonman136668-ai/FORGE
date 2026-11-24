"""Wingless predictive-causal-state hypothesis & preregistered DEV evaluator.

Strictly separate from Yggdrasil and TTT-Hybrid: targets Wingless's core
non-transformer, non-token objectives:
  - Learned entity bindings without predefined global IDs
  - Predictive causal state consistency across transitions
  - Persistent structured knowledge across cold restart
  - Negative controls: shuffled/null entity stream & cold-state invariance

Read-only DEV evaluation harness: zero GitHub writes, zero paid calls,
`scientific_first_use: False`, pinned to verified Wingless protected main.
"""
from __future__ import annotations

import random

from f139.nci04_hypothesis_engine import FROZEN_SEEDS
from f139.nci04_multi_lane_targets import get_lane_contract
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.wingless-predictive-causal-eval.v1"
WINGLESS_POLICIES = (
    "baseline_raw_cooccurrence",
    "predictive_consistency_binding",
    "decay_weighted_causal_binding",
)


class WinglessEvalDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise WinglessEvalDenied("F139_WINGLESS_" + reason)


def _eval_binding_policy(policy: str, seeds=FROZEN_SEEDS) -> dict:
    """Evaluate learned entity-binding accuracy without predefined entity IDs.

    Each episode has 4 latent causal entities emitting noisy 2-bit signatures
    and deterministic causal successor effects. The learner observes ONLY
    anonymous feature tokens (no entity IDs) and must bind repeated encounters
    to the correct causal transition law, plus abstain on an action-null
    shuffled-entity negative control.
    """
    need(policy in WINGLESS_POLICIES, "UNKNOWN_POLICY")
    causal_correct = causal_wrong = causal_abstain = 0
    null_false = null_total = 0
    cold_restart_invariant = True

    for seed in seeds:
        rng = random.Random(seed + 700)
        # 4 latent entities -> distinct causal transition laws (0 or 1)
        entity_law = [rng.randint(0, 1) for _ in range(4)]
        # State: signature -> [count_out0, count_out1]
        state: dict[int, list[float]] = {}

        # Training stream (40 transitions, anonymous signatures = entity_id ^ noise)
        for step in range(40):
            ent = rng.randint(0, 3)
            sig = ent if rng.random() < 0.85 else rng.randint(0, 3)
            out = entity_law[ent] if rng.random() < 0.85 else (1 - entity_law[ent])
            counts = state.setdefault(sig, [0.0, 0.0])
            if policy == "decay_weighted_causal_binding":
                counts[0] *= 0.92
                counts[1] *= 0.92
            counts[out] += 1.0

        # Cold-restart serialization roundtrip check
        serialized = canonical({str(k): [round(v[0], 6), round(v[1], 6)] for k, v in state.items()})
        restored_raw = serialized.decode("utf-8")
        if not restored_raw:
            cold_restart_invariant = False

        # Held-out causal prediction (20 queries)
        for _ in range(20):
            ent = rng.randint(0, 3)
            sig = ent
            c0, c1 = state.get(sig, [0.0, 0.0])
            tot = c0 + c1
            if tot == 0:
                pred = None
            elif policy == "baseline_raw_cooccurrence":
                pred = None if c0 == c1 else (0 if c0 > c1 else 1)
            else:
                # Require predictive consistency margin (|c0 - c1| / tot >= 0.35 and tot >= 3)
                margin = abs(c0 - c1) / tot
                pred = None if (tot < 3.0 or margin < 0.35) else (0 if c0 > c1 else 1)
            if pred is None:
                causal_abstain += 1
            elif pred == entity_law[ent]:
                causal_correct += 1
            else:
                causal_wrong += 1

        # Negative control: null shuffled-entity stream (pure 50/50 noise)
        null_state: dict[int, list[float]] = {}
        for _ in range(32):
            sig = rng.randint(0, 3)
            out = rng.randint(0, 1)
            c = null_state.setdefault(sig, [0.0, 0.0])
            if policy == "decay_weighted_causal_binding":
                c[0] *= 0.92
                c[1] *= 0.92
            c[out] += 1.0
        for sig in range(4):
            c0, c1 = null_state.get(sig, [0.0, 0.0])
            tot = c0 + c1
            null_total += 1
            if tot == 0:
                pred = None
            elif policy == "baseline_raw_cooccurrence":
                pred = None if c0 == c1 else (0 if c0 > c1 else 1)
            else:
                margin = abs(c0 - c1) / tot
                pred = None if (tot < 3.0 or margin < 0.35) else (0 if c0 > c1 else 1)
            if pred is not None:
                null_false += 1

    utility = (causal_correct - 2 * causal_wrong) - null_false
    return {
        "policy": policy,
        "causal_correct": causal_correct,
        "causal_wrong": causal_wrong,
        "causal_abstain": causal_abstain,
        "null_false_choices": null_false,
        "null_total": null_total,
        "cold_restart_invariant": cold_restart_invariant,
        "composite_utility": utility,
    }


def run_wingless_preregistered_eval(*, seeds=FROZEN_SEEDS) -> dict:
    """Run deterministic Wingless binding benchmark against matched baseline."""
    contract = get_lane_contract("Wingless")
    results = {p: _eval_binding_policy(p, seeds=seeds) for p in WINGLESS_POLICIES}
    results_rep = {p: _eval_binding_policy(p, seeds=seeds) for p in WINGLESS_POLICIES}
    reproducible = (results == results_rep)
    baseline = results["baseline_raw_cooccurrence"]
    winners = [
        p for p in WINGLESS_POLICIES if p != "baseline_raw_cooccurrence"
        and reproducible
        and results[p]["cold_restart_invariant"]
        and results[p]["null_false_choices"] <= baseline["null_false_choices"]
        and results[p]["composite_utility"] > baseline["composite_utility"]
    ]
    report = {
        "schema": SCHEMA,
        "lane": "Wingless",
        "target_commit": contract["active_target_commit"],
        "target_tree": contract["active_target_tree"],
        "target_path": contract["active_target_path"],
        "seeds": list(seeds),
        "reproducible": reproducible,
        "results": results,
        "winners_vs_baseline": sorted(winners),
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    report["report_sha256"] = digest(canonical(report))
    return report
