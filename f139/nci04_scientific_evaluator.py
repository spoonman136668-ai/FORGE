"""Preregistered, deterministic scientific evaluation harness for F139 hypotheses.

Evaluates AST-verified Yggdrasil local-cell hypotheses head-to-head against the
strongest matched baselines (`choose` and, when present, `choose_wilson`) across
frozen deterministic seeds on four distinct local-learning regimes:
  1. `sparse_causal`: low-sample stochastic binary causal arms.
  2. `imbalanced_sampling`: 5x sampling skew favoring the worse arm.
  3. `action_null` (negative control): identical 50/50 arms (false-choice rate).
  4. `cold_restart_retention`: 164-byte snapshot/restore invariance + accuracy.

Design boundaries:
- Strictly read-only, deterministic (pure stdlib PRNG seeded by `FROZEN_SEEDS`),
  zero network calls, zero paid model calls, zero automatic checkpoint promotion,
  and `scientific_first_use: False`.
- Feeds verified/dominated empirical outcomes back into `select_next_hypothesis`
  so FORGE retains all consumed and failed trials and advances along winning
  mechanism axes and matched ablations.
"""
from __future__ import annotations

import base64
import json
import random

from f139.nci04_hypothesis_engine import (
    FROZEN_SEEDS, PREREG_SCHEMA, HypothesisEngineDenied,
    select_next_hypothesis, verify_candidate_ast_safety,
)
from f139.nci04_native_contract import canonical, digest

EVAL_SCHEMA = "forge.f139.preregistered-scientific-eval.v1"
MATCHED_CONTROLS = ("choose", "choose_wilson")


class ScientificEvalDenied(ValueError):
    """Fail-closed denial for invalid candidate, preregistration, or control drift."""


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ScientificEvalDenied("F139_SCI_EVAL_" + reason)


def _compile_cells_class(source_code: str, method_name: str):
    verify_candidate_ast_safety(source_code, method_name)
    ns: dict = {}
    exec(compile(source_code, "<f139_sci_eval>", "exec"), ns, ns)
    cls = ns.get("PublicCausalCells")
    need(cls is not None and hasattr(cls, method_name) and hasattr(cls, "choose"),
         "TARGET_CLASS_OR_METHOD_MISSING")
    return cls


def _record_obs(cells, addr: int, arm: int, outcome: int) -> None:
    if hasattr(cells, "observe"):
        cells.observe(addr, arm, outcome)
    else:
        cells._counts[addr][arm][outcome] = min(65535, cells._counts[addr][arm][outcome] + 1)


def _score_method_on_suite(cls, method_name: str, seeds=FROZEN_SEEDS) -> dict:
    """Evaluate one PublicCausalCells method deterministically across 4 regimes."""
    sparse_correct = sparse_wrong = sparse_abstain = 0
    imb_correct = imb_wrong = imb_abstain = 0
    null_false_choices = null_total = 0
    restart_correct = restart_wrong = restart_abstain = 0
    checkpoint_invariant = True

    for seed in seeds:
        rng = random.Random(seed)

        # Regime 1: sparse_causal (7 active cells, 6-10 observations total/cell)
        cells = cls()
        truths = []
        for addr in range(7):
            best = rng.randint(0, 1)
            truths.append(best)
            p_best, p_worse = 0.78, 0.25
            for arm in (0, 1):
                n = rng.randint(3, 6)
                p = p_best if arm == best else p_worse
                for _ in range(n):
                    _record_obs(cells, addr, arm, 1 if rng.random() < p else 0)
        for addr, best in enumerate(truths):
            c = getattr(cells, method_name)(addr)
            if c is None:
                sparse_abstain += 1
            elif c == best:
                sparse_correct += 1
            else:
                sparse_wrong += 1

        # Regime 2: imbalanced_sampling (worse arm observed 5x more than best)
        cells_imb = cls()
        truths_imb = []
        for addr in range(7):
            best = rng.randint(0, 1)
            truths_imb.append(best)
            for arm in (0, 1):
                n = 3 if arm == best else 15
                p = 0.75 if arm == best else 0.30
                for _ in range(n):
                    _record_obs(cells_imb, addr, arm, 1 if rng.random() < p else 0)
        for addr, best in enumerate(truths_imb):
            c = getattr(cells_imb, method_name)(addr)
            if c is None:
                imb_abstain += 1
            elif c == best:
                imb_correct += 1
            else:
                imb_wrong += 1

        # Regime 3: action_null (negative control: both arms identical p=0.5)
        cells_null = cls()
        for addr in range(7):
            for arm in (0, 1):
                for _ in range(8):
                    _record_obs(cells_null, addr, arm, 1 if rng.random() < 0.5 else 0)
            c = getattr(cells_null, method_name)(addr)
            null_total += 1
            if c is not None:
                null_false_choices += 1

        # Regime 4: cold_restart_retention (164-byte snapshot -> restore)
        if hasattr(cells, "snapshot") and hasattr(cls, "restore"):
            snap_before = cells.snapshot()
            if len(snap_before) != 164:
                checkpoint_invariant = False
            restored = cls.restore(snap_before)
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
            if cells.snapshot() != snap_before or restored.snapshot() != snap_before:
                checkpoint_invariant = False

    # Asymmetric risk-adjusted composite utility:
    # +1 per correct decision, -2 per wrong decision, -1 per action_null false choice.
    # Abstention scores 0 (safe conservatism beats confident error).
    composite_utility = (
        (sparse_correct - 2 * sparse_wrong)
        + (imb_correct - 2 * imb_wrong)
        - null_false_choices
    )
    return {
        "method": method_name,
        "sparse_correct": sparse_correct,
        "sparse_wrong": sparse_wrong,
        "sparse_abstain": sparse_abstain,
        "imbalanced_correct": imb_correct,
        "imbalanced_wrong": imb_wrong,
        "imbalanced_abstain": imb_abstain,
        "action_null_false_choices": null_false_choices,
        "action_null_total": null_total,
        "cold_restart_correct": restart_correct,
        "cold_restart_wrong": restart_wrong,
        "cold_restart_abstain": restart_abstain,
        "checkpoint_164_byte_invariance": checkpoint_invariant,
        "composite_utility": composite_utility,
    }


def evaluate_hypothesis_item(item: dict, *, seeds=FROZEN_SEEDS) -> dict:
    """Evaluate one preregistered hypothesis item against strongest matched controls."""
    need(type(item) is dict and type(item.get("plan")) is dict
         and type(item.get("preregistration")) is dict,
         "HYPOTHESIS_ITEM_INVALID")
    prereg = item["preregistration"]
    need(prereg.get("schema") == PREREG_SCHEMA
         and prereg.get("frozen_protocol", {}).get("scientific_first_use") is False
         and prereg.get("frozen_protocol", {}).get("paid_model_calls") == 0
         and prereg.get("frozen_protocol", {}).get("auto_promote_checkpoint") is False,
         "PREREGISTRATION_CONTRACT_INVALID")
    # Re-verify sealed preregistration digest before observing results.
    prereg_no_sig = {k: v for k, v in prereg.items() if k != "preregistration_sha256"}
    need(digest(canonical(prereg_no_sig)) == prereg.get("preregistration_sha256"),
         "PREREGISTRATION_HASH_DRIFT")

    issue = json.loads(item["plan"]["body"])
    raw_intent = base64.b64decode(issue["intent_base64"], validate=True)
    intent = json.loads(raw_intent)
    source_code = base64.b64decode(intent["after_base64"], validate=True).decode("utf-8")

    axes = prereg["axes"]
    method_name = f"choose_hyp_{axes['estimator']}_{axes['support_gate']}_{axes['tie_policy']}"
    cls = _compile_cells_class(source_code, method_name)

    cand_run1 = _score_method_on_suite(cls, method_name, seeds=seeds)
    cand_run2 = _score_method_on_suite(cls, method_name, seeds=seeds)
    reproducible = (cand_run1 == cand_run2)

    controls = {}
    for ctrl in MATCHED_CONTROLS:
        if hasattr(cls, ctrl):
            controls[ctrl] = _score_method_on_suite(cls, ctrl, seeds=seeds)
    need(bool(controls), "NO_MATCHED_CONTROLS_AVAILABLE")

    strongest_ctrl_name = max(controls, key=lambda k: controls[k]["composite_utility"])
    strongest_ctrl = controls[strongest_ctrl_name]

    negative_control_pass = (
        cand_run1["checkpoint_164_byte_invariance"] is True
        and cand_run1["action_null_false_choices"] <= strongest_ctrl["action_null_false_choices"]
    )
    beats_strongest = (
        reproducible
        and negative_control_pass
        and cand_run1["composite_utility"] > strongest_ctrl["composite_utility"]
    )
    result = {
        "schema": EVAL_SCHEMA,
        "hypothesis_id": prereg["hypothesis_id"],
        "preregistration_sha256": prereg["preregistration_sha256"],
        "after_sha256": item["plan"]["after_sha256"],
        "axes": dict(axes),
        "seeds": list(seeds),
        "candidate": cand_run1,
        "controls": controls,
        "strongest_control": strongest_ctrl_name,
        "delta_vs_strongest": (
            cand_run1["composite_utility"] - strongest_ctrl["composite_utility"]
        ),
        "reproducible": reproducible,
        "negative_control_pass": negative_control_pass,
        "beats_strongest_control": beats_strongest,
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
    result["evaluation_sha256"] = digest(canonical(result))
    return result


def evaluate_and_rank_pool(pool: list[dict], *, seeds=FROZEN_SEEDS) -> dict:
    """Evaluate all candidates in a pool, retain winners and failures, and select next."""
    need(type(pool) is list and len(pool) > 0, "EMPTY_EVALUATION_POOL")
    evaluations = [evaluate_hypothesis_item(item, seeds=seeds) for item in pool]
    evaluations.sort(
        key=lambda e: (
            not e["beats_strongest_control"],
            -e["delta_vs_strongest"],
            e["candidate"]["action_null_false_choices"],
            e["after_sha256"],
        )
    )
    verified_axes = [e["axes"] for e in evaluations if e["beats_strongest_control"]]
    failed_axes = [e["axes"] for e in evaluations if not e["negative_control_pass"]]
    untested_next = select_next_hypothesis(
        pool, verified_axes=verified_axes, failed_axes=failed_axes,
    )
    return {
        "schema": EVAL_SCHEMA,
        "evaluated_count": len(evaluations),
        "winners_count": len(verified_axes),
        "negative_control_failures": len(failed_axes),
        "top_result": evaluations[0],
        "evaluations": evaluations,
        "recommended_next_hypothesis_id": (
            untested_next["preregistration"]["hypothesis_id"]
            if untested_next is not None else None
        ),
        "scientific_first_use": False,
        "auto_promote_checkpoint": False,
    }
