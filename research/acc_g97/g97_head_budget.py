"""G97 certified attention-head contribution budgeting; synthetic CPU only.

Frozen preregistration:
docs/research/acc_g91_g106/G97_HEAD_BOUNDS_PREREG_20261031.md
Neither a pretrained checkpoint nor RTX model throughput is measured here.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g97.certified_head_budget_cpu_proxy.v1"
SEEDS = (9701, 9702, 9703)
REGIMES = ("normal", "three_near_zero_heads")
HEADS, KEY_ROWS, DIMENSION, OUTPUT_DIM, QUERY_COUNT = 8, 128, 16, 64, 8
TRIALS, RELATIVE_TOLERANCE, SPEEDUP_FLOOR = 7, 1e-3, 1.15
ROUNDING_AUDIT, BOUND_INFLATION = 1e-9, 1e-10
SCALE = math.sqrt(DIMENSION)


def make_workload(seed, regime):
    rng = np.random.default_rng(seed)
    keys = rng.standard_normal((HEADS, KEY_ROWS, DIMENSION))
    values = rng.standard_normal((HEADS, KEY_ROWS, DIMENSION))
    queries = rng.standard_normal((QUERY_COUNT, HEADS, DIMENSION))
    weight = rng.standard_normal((HEADS, DIMENSION, OUTPUT_DIM)) / math.sqrt(DIMENSION)
    if regime == "three_near_zero_heads":
        weight[5:8] *= 1e-6
    elif regime != "normal":
        raise ValueError("UNKNOWN_REGIME")
    return keys, values, queries, weight


def head_bounds(values, weight):
    """Upper-bound each head contribution by convexity and spectral norm."""
    value_max = np.linalg.norm(values, axis=-1).max(axis=-1)
    spectral = np.asarray([np.linalg.svd(weight[h], compute_uv=False)[0]
                           for h in range(HEADS)])
    original = value_max * spectral
    return original + BOUND_INFLATION * (1 + np.abs(original))


def single_head(keys, values, query, weight, h):
    logits = (keys[h] @ query[h]) / SCALE
    exp_scores = np.exp(logits - logits.max())
    probability = exp_scores / exp_scores.sum()
    return (probability @ values[h]) @ weight[h]


def full_attention(keys, values, query, weight):
    logits = np.einsum("hnd,hd->hn", keys, query) / SCALE
    probabilities = np.exp(logits - logits.max(axis=1, keepdims=True))
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    outputs = np.einsum("hn,hnd->hd", probabilities, values)
    return np.einsum("hd,hdo->o", outputs, weight)


def budget_attention(keys, values, query, weight, upper):
    if not np.all(np.isfinite(upper)):
        raise ArithmeticError("NONFINITE_BOUND")
    # Sorting is deliberately charged on each query; not precomputed.
    order = np.argsort(-upper, kind="stable")
    acc = np.zeros(OUTPUT_DIM, dtype=np.float64)
    visited = 0
    absolute_certificate = 0.
    early = False
    for head in order:
        acc = acc + single_head(keys, values, query, weight, int(head))
        visited += 1
        if visited == HEADS:
            break
        remaining_bound = float(upper[order[visited:]].sum())
        acc_norm = float(np.linalg.norm(acc))
        if acc_norm > remaining_bound and (
            remaining_bound <= RELATIVE_TOLERANCE * (acc_norm - remaining_bound)
        ):
            absolute_certificate = remaining_bound
            early = True
            break
    if not np.all(np.isfinite(acc)):
        raise ArithmeticError("NONFINITE_CANDIDATE")
    return acc, dict(
        heads_visited=visited, heads_skipped=HEADS-visited,
        rows_scored=visited*KEY_ROWS,
        early_certified=early, certified_absolute_error=absolute_certificate,
    )


def paired_timing(reference, candidate):
    reference()
    candidate()
    td, tc = [], []
    for trial in range(TRIALS):
        first, second = (reference, candidate) if trial % 2 == 0 else (candidate, reference)
        start = time.perf_counter_ns()
        first()
        middle = time.perf_counter_ns()
        second()
        finish = time.perf_counter_ns()
        if trial % 2 == 0:
            td.append((middle-start)/1e6)
            tc.append((finish-middle)/1e6)
        else:
            tc.append((middle-start)/1e6)
            td.append((finish-middle)/1e6)
    return statistics.median(td), statistics.median(tc)


def screen():
    cases, setup = [], []
    with threadpool_limits(limits=1):
        for regime in REGIMES:
            for seed in SEEDS:
                k, v, qs, w = make_workload(seed, regime)
                t0 = time.perf_counter_ns()
                upper = head_bounds(v, w)
                setup.append(dict(seed=seed, regime=regime,
                                  metadata_setup_ms=(time.perf_counter_ns()-t0)/1e6))
                for query_id, query in enumerate(qs):
                    # Independent audit only, never used for pruning.
                    actual = [single_head(k, v, query, w, h) for h in range(HEADS)]
                    all_bounded = bool(all(np.linalg.norm(a) <= upper[h]+ROUNDING_AUDIT
                                           for h,a in enumerate(actual)))
                    base_fn = lambda: full_attention(k, v, query, w)
                    cand_fn = lambda: budget_attention(k, v, query, w, upper)
                    reference = base_fn()
                    estimate, props = cand_fn()
                    absolute = float(np.linalg.norm(estimate-reference))
                    relative = absolute / max(float(np.linalg.norm(reference)),1e-12)
                    cert_valid = bool(absolute <= props["certified_absolute_error"]+ROUNDING_AUDIT)
                    tb, tc = paired_timing(base_fn, cand_fn)
                    finite = bool(np.all(np.isfinite(reference)) and
                                  np.all(np.isfinite(estimate)) and
                                  all(math.isfinite(x) for x in (absolute,relative,tb,tc)))
                    cases.append(dict(
                        seed=seed, regime=regime, query_id=query_id,
                        finite=finite, head_bounds_valid=all_bounded,
                        certificate_valid=cert_valid,
                        within_relative_tolerance=relative <= RELATIVE_TOLERANCE,
                        absolute_error=absolute, relative_l2=relative,
                        baseline_ms=tb, candidate_ms=tc, speedup=tb/tc,
                        **props,
                    ))
    if len(cases)!=48 or len(setup)!=6:
        raise AssertionError("CASE_COUNT_MISMATCH")
    summary={}
    for regime in REGIMES:
        subset=[c for c in cases if c["regime"]==regime]
        summary[regime]=dict(
            count=len(subset),
            median_speedup=statistics.median(c["speedup"] for c in subset),
            median_heads_visited=statistics.median(c["heads_visited"] for c in subset),
            early_cases=sum(c["early_certified"] for c in subset),
            worst_relative_l2=max(c["relative_l2"] for c in subset),
            all_correct=all(c["finite"] and c["head_bounds_valid"] and c["certificate_valid"]
                            and c["within_relative_tolerance"] for c in subset)
        )
    go=all(summary[r]["all_correct"] and summary[r]["median_speedup"]>=SPEEDUP_FLOOR
           for r in REGIMES)
    return dict(
        schema=SCHEMA,source_type="synthetic_cpu_numpy_certified_head_proxy",
        authentic_model="NOT_RUN",gpu_measured="NOT_RUN",scientific_acceptance="NOT_GRANTED",
        environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
        frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),heads=HEADS,key_rows=KEY_ROWS,
                    dimension=DIMENSION,output_dim=OUTPUT_DIM,query_count=QUERY_COUNT,
                    trials=TRIALS,error_tolerance=RELATIVE_TOLERANCE,
                    speedup_floor=SPEEDUP_FLOOR),
        metadata_initialization=setup,cases=cases,summary=summary,
        decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if go else "NO_GO_SYNTHETIC_SCREEN",
        caveat="Spectral-bound setup excluded from timing; favorable near-zero heads are synthetic; no real model/GPU throughput inference is justified."
    )


if __name__=="__main__":
    print("G97_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
