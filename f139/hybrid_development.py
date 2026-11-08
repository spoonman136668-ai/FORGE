"""F139 third-lane TTT-Hybrid *development-only* factual-memory learning.

Shares the existing F139 development engine and its exact-source receipt.
No model import from the independent Hybrid repository, no runner allocation,
scheduler, protected experiment, GPU, controller or research acceptance.

The trained example is deliberately small, deterministic and inspectable:
a causal action/outcome memory gate versus a conventional clipped recurrent
effect estimator, fit on identical factual histories with identical 64-way
parameter search. It is NOT an implementation of the actual Hybrid P7 model.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re

SCHEMA = "forge.f139.hybrid-third-lane-development.v1"
PROJECT = "TTT-Hybrid"
REPO = "spoonman136668-ai/TTT-Hybrid-Lab"
# Verified prior negative, not a positive training signal or owner grant.
NEGATIVE_C10_PR = 82
NEGATIVE_C10_SHA = "5cb633d129c0500dbb857ecafa02cacc122abb09"
BASELINE_MAIN_SHA = "6df5aa3f0dd5a99867098166aeed5b0fc70b4ec2"
GRID = (0.0, 0.05, 0.15, 0.3, 0.5, 0.7, 0.9, 1.0)
BATCH = 96
BIAS = 0.04
EFFECT = 0.45
NOISE = (-0.025, 0.025)
MAX_GENERATION = 100000


class HybridDevDenied(ValueError):
    pass


def need(value, why):
    if not value:
        raise HybridDevDenied("F139_HYBRID_DEV_" + why)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def cohort(generation: int, phase: int):
    """96 source-internal episodes. Hidden regimes are evaluator-only labels."""
    need(type(generation) is int and 1 <= generation <= MAX_GENERATION,
         "GENERATION")
    need(phase in (1, 2) and type(phase) is int, "PHASE")
    rng = random.Random(30011 + 811 * generation + 16001 * phase)
    episodes = []
    for _ in range(BATCH):
        regime = rng.choice((-1, 1))
        length = rng.randint(8, 12) if phase == 1 else rng.randint(16, 22)
        flip = rng.randint(3, length - 4)
        history = []
        for t in range(length):
            if t == flip:
                regime *= -1
            executed_action = rng.choice((-1, 1))
            factual_outcome = BIAS + EFFECT * regime * executed_action + rng.choice(NOISE)
            history.append([executed_action, factual_outcome])
        # Label is held by evaluator and never passed to the predictor.
        episodes.append({"completed_factual_history": history,
                         "target_context_evaluator_only": regime})
    return episodes


def infer(completed_facts, parameters, candidate, trace=False):
    """Per-action causal evidence; no latent context/future outcome access."""
    need(isinstance(completed_facts, (list, tuple))
         and 0 < len(completed_facts) <= 64, "FACTS_LENGTH")
    need(type(candidate) is bool
         and isinstance(parameters, (list, tuple))
         and len(parameters) == 2, "MODEL_PARAMETERS")
    decay, threshold = parameters
    need(decay in GRID and threshold in GRID, "FROZEN_GRID")
    state = 0.0
    debug = []
    for pair in completed_facts:
        need(isinstance(pair, (list, tuple)) and len(pair) == 2,
             "FACTUAL_PAIR_SHAPE")
        action, consequence = pair
        need(type(action) is int and action in (-1, 1)
             and type(consequence) in (float, int)
             and math.isfinite(consequence), "FACTUAL_EVENT_INVALID")
        effect = action * (consequence - BIAS)
        prior = state
        contradiction = candidate and state * effect < -threshold and abs(effect) >= 0.2
        if contradiction:
            state = effect
        elif candidate:
            state = decay * state + (1.0 - decay) * effect
        else:
            # Conventional adaptive recurrent control uses identical factual
            # pairs and same two fitted parameters, clipping outlying effects.
            cap = 0.1 + threshold
            limited = max(-cap, min(cap, effect))
            state = decay * state + (1.0 - decay) * limited
        if trace:
            debug.append({"executed_action": action,
                          "actual_consequence": consequence,
                          "inferred_effect": effect,
                          "state_before": prior, "state_after": state,
                          "contradiction_reset": bool(contradiction)})
    return (1 if state >= 0 else -1), debug


def evaluate(rows, params, candidate, full_trace=False):
    need(len(rows) == BATCH, "COHORT_SIZE")
    correct = 0
    trace_hash = hashlib.sha256()
    examples = []
    for i, row in enumerate(rows):
        need(isinstance(row, dict)
             and set(row) == {"completed_factual_history",
                              "target_context_evaluator_only"},
             "COHORT_FIELDS")
        choice, trace = infer(row["completed_factual_history"],
                              params, candidate, trace=True)
        correct += (choice == row["target_context_evaluator_only"])
        event = {"index": i, "prediction_before_evaluator_label": choice,
                 "steps": trace}
        trace_hash.update(canonical(event) + b"\n")
        if full_trace and i < 2:
            examples.append(event)
    return {"correct": correct, "total": BATCH,
            "decision_trace_sha256": trace_hash.hexdigest(),
            "debug_examples": examples}


def train(rows, candidate):
    need(len(rows) == BATCH, "TRAIN_ROWS")
    ranked = []
    for decay in GRID:
        for threshold in GRID:
            p = [decay, threshold]
            score = evaluate(rows, p, candidate)["correct"]
            ranked.append((score, p))
    max_score = max(x[0] for x in ranked)
    selected = next(params for score, params in ranked if score == max_score)
    return {"parameters": selected, "training_correct": max_score,
            "training_total": BATCH, "search_evaluations": len(ranked)}


def run(generation: int, forge_sha: str):
    need(type(forge_sha) is str
         and re.fullmatch(r"[a-f0-9]{40}", forge_sha) is not None,
         "EXACT_FORGE_SHA")
    train_rows = cohort(generation, 1)
    transfer_rows = cohort(generation, 2)
    trained = train(train_rows, True)
    control = train(train_rows, False)
    train_hash = digest(train_rows)
    transfer_hash = digest(transfer_rows)
    for item, is_candidate in ((trained, True), (control, False)):
        score = evaluate(transfer_rows, item["parameters"],
                         is_candidate, full_trace=True)
        again = evaluate(transfer_rows, item["parameters"],
                         is_candidate, full_trace=True)
        need(score == again, "NONDETERMINISTIC_COLD_REPLAY")
        item.update({
            "transfer_correct": score["correct"],
            "transfer_total": score["total"],
            "transfer_debug_trace_sha256": score["decision_trace_sha256"],
            "debug_examples": score["debug_examples"],
            "training_cohort_sha256": train_hash,
            "transfer_cohort_sha256": transfer_hash,
            "model_class": ("causal_contradiction_gated_memory_dev"
                            if is_candidate else
                            "conventional_clipped_recurrent_effect_dev"),
            "model_parameter_sha256": digest(item["parameters"]),
            "cold_replay_bit_exact": True,
        })
    need(trained["search_evaluations"] == control["search_evaluations"] == 64
         and trained["training_cohort_sha256"] == control["training_cohort_sha256"]
         and trained["transfer_cohort_sha256"] == control["transfer_cohort_sha256"],
         "MATCHED_OBSERVATIONS_AND_PARAMETER_SEARCH")
    delta = trained["transfer_correct"] - control["transfer_correct"]
    return {
        "schema": SCHEMA, "lane": PROJECT,
        "repository": REPO, "forge_source_sha": forge_sha,
        "synthetic_development_only": True,
        "actual_hybrid_research_training_executed": False,
        "original_hybrid_main_sha_reference": BASELINE_MAIN_SHA,
        "prior_negative_pr": NEGATIVE_C10_PR,
        "prior_negative_candidate_sha": NEGATIVE_C10_SHA,
        "prior_specialized_superiority": "FAILED_NOT_RELABELED",
        "training_data_origin": "FORGE_GENERATED_PUBLIC_DEV_NOT_ORIGINAL_HYBRID",
        "training_seed_rule": "30011+811*generation+16001*phase",
        "matched_factual_inputs": True, "matched_search_evaluations": True,
        "matched_total_flops_verified": False,
        "trained_candidate": trained, "trained_control": control,
        "transfer_correct_delta": delta,
        "classification": ("POSITIVE_DEVELOPMENT" if delta > 0
                           else "NEGATIVE_OR_TIE_DEVELOPMENT"),
        "new_architecture_proven": False,
        "independent_scientific_validation": False,
        "native_hybrid_model_promoted": False,
        "scientific_first_use": False,
        "protected_holdouts_accessed": 0,
        "external_calls": 0, "paid_api_calls": 0,
        "owner_tickets_dispatched": 0,
        "accepted_ref_mutations": 0,
        "non_token_cognitive_interface": True,
        "debuggable_per_action_state_and_causal_effect": True,
        "deterministic_cold_replay_verified": True,
    }
