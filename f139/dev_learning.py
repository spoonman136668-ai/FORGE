"""Bounded real CPU-only *development* training, not scientific first-use.

Both lanes optimize trainable parameters against equally searched recurrent
ablations, then score distinct, generated development cohorts. This is not
autonomous code authoring or independent evidence of novel cognition.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import time
import tracemalloc

SCHEMA = "forge.f139.private-cognition-development.v1"
GRID = (0.0, 0.05, 0.15, 0.3, 0.5, 0.7, 0.9, 1.0)
LANES = ("Wingless", "Yggdrasil")

def require(ok, code):
    if not ok:
        raise ValueError("F139_PRIVATE_DEV_" + code)

def fingerprint(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()

def cohort(lane, generation, phase):
    seed = {"Wingless": 10001, "Yggdrasil": 20003}[lane] + 811 * generation + 16001 * phase
    rng = random.Random(seed)
    rows = []
    for _ in range(96):
        if lane == "Wingless":
            n = rng.randint(7, 10) if phase == 1 else rng.randint(11, 16)
            marker = rng.randrange(0, n // 3)
            label = rng.choice((-1, 1))
            history = [(int(i == marker), label if i == marker else rng.choice((-1, 1)))
                       for i in range(n)]
            rows.append((history, label))
        else:
            a, b, c, d, e = rng.sample(range(5), 5)
            ab, bc = rng.choice((-1, 1)), rng.choice((-1, 1))
            history = [(a, b, ab), (b, c, bc), (d, e, rng.choice((-1, 1)))]
            rng.shuffle(history)
            rows.append((history, (a, c), ab * bc))
    return rows

def score_wingless(history, p, q, candidate):
    state = 0.0
    for marker, value in history:
        input_weight = (1.0 if marker else q) if candidate else q
        state = p * state + input_weight * value
    return 1 if state > 0 else -1

def score_yggdrasil(history, query, p, q, candidate):
    matrix = [[0] * 5 for _ in range(5)]
    for a, b, sign in history:
        matrix[a][b] = sign
    a, c = query
    composed = sum(matrix[a][b] * matrix[b][c] for b in range(5))
    noncomposed = sum(matrix[a])
    value = p * matrix[a][c] + q * (composed if candidate else noncomposed)
    return 1 if value > 0 else -1

def accuracy(lane, data, params, candidate):
    hits = 0
    for row in data:
        if lane == "Wingless":
            history, target = row
            predicted = score_wingless(history, *params, candidate)
        else:
            history, query, target = row
            predicted = score_yggdrasil(history, query, *params, candidate)
        hits += predicted == target
    return hits

def fit(lane, generation, candidate):
    training = cohort(lane, generation, 1)
    transfer = cohort(lane, generation, 2)
    ranked = [(accuracy(lane, training, (p, q), candidate), (p, q))
              for p in GRID for q in GRID]
    best = max(x[0] for x in ranked)
    fitted = next(params for hits, params in ranked if hits == best)
    return {"parameters": list(fitted), "training_correct": best,
            "training_total": len(training),
            "transfer_correct": accuracy(lane, transfer, fitted, candidate),
            "transfer_total": len(transfer),
            "search_evaluations": len(ranked),
            "training_cohort_sha256": fingerprint(training),
            "transfer_cohort_sha256": fingerprint(transfer),
            "model_class": ("gated_retention" if lane == "Wingless" else "compositional_edge_readout")
                           if candidate else
                           ("ungated_recurrent_control" if lane == "Wingless"
                            else "noncompositional_recurrent_control")}

def run(lane, generation, source_sha):
    require(lane in LANES + ("Qualification",), "LANE_FORBIDDEN")
    require(type(generation) is int and 1 <= generation <= 100000, "GENERATION_INVALID")
    require(isinstance(source_sha, str) and re.fullmatch("[a-f0-9]{40}", source_sha),
            "SOURCE_INVALID")
    actual = os.environ.get("GITHUB_SHA")
    require(not actual or actual == source_sha, "EXACT_SOURCE_DRIFT")
    began = time.perf_counter()
    tracemalloc.start()
    try:
        choices = LANES if lane == "Qualification" else (lane,)
        results = []
        for name in choices:
            candidate = fit(name, generation, True)
            control = fit(name, generation, False)
            require(candidate["training_cohort_sha256"] == control["training_cohort_sha256"]
                    and candidate["transfer_cohort_sha256"] == control["transfer_cohort_sha256"]
                    and candidate["search_evaluations"] == control["search_evaluations"],
                    "TRAINED_MATCHED_CONTROL_REQUIRED")
            delta = candidate["transfer_correct"] - control["transfer_correct"]
            results.append({"lane": name, "trained_candidate": candidate,
                            "trained_control": control, "transfer_correct_delta": delta,
                            "classification": "POSITIVE_DEVELOPMENT" if delta > 0
                            else "NEGATIVE_OR_TIE_DEVELOPMENT",
                            "new_architecture_proven": False,
                            "independent_scientific_validation": False})
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return {"schema": SCHEMA, "source_sha": source_sha, "generation": generation,
            "lanes": results, "study_type": "generated_development_only_not_scientific",
            "real_cpu_training_executed": True, "persistent_accepted_model_updated": False,
            "autonomous_code_generation": False, "protected_first_use": False,
            "sealed_holdouts_accessed": 0, "scientific_originals_dispatched": 0,
            "accepted_ref_mutations": 0, "optimizer_policy_mutations": 0,
            "cloudflare_writes": 0, "paid_api_calls": 0,
            "peak_python_bytes": peak,
            "elapsed_ms": max(0, math.ceil((time.perf_counter() - began) * 1000))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True, choices=LANES + ("Qualification",))
    parser.add_argument("--generation", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(args.output.parent.is_dir() and not args.output.exists(), "EXCLUSIVE_OUTPUT_REQUIRED")
    report = run(args.lane, args.generation, args.source_sha)
    with args.output.open("xb") as fp:
        fp.write((json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode())
    print("F139_CPU_DEV_LEARNING=EXECUTED_NOT_NOVEL_SCIENCE")
    print("F139_PROTECTED_FIRST_USE=FALSE")

if __name__ == "__main__":
    main()
