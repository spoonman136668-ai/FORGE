"""G94 temporal activation-delta projection reuse, frozen CPU falsifier.

The sparse regime is intentionally synthetic/favorable. No GPU or model evidence.
Protocol: docs/research/acc_g91_g106/G94_DELTA_PREREG_20261031.md.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g94.delta_projection_cpu_proxy.v1"
SEEDS = (9401, 9402, 9403)
REGIMES = ("iid", "exact_sparse")
DIM_IN, DIM_OUT, TRANSITIONS = 256, 512, 16
CHANGED_COORDINATES = 8
TRIALS = 9
ERROR_LIMIT, SPEEDUP_FLOOR = 1e-9, 1.15


def generate(seed, regime):
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((DIM_OUT, DIM_IN)) / math.sqrt(DIM_IN)
    if regime == "iid":
        states = rng.standard_normal((TRANSITIONS + 1, DIM_IN))
    elif regime == "exact_sparse":
        states = np.empty((TRANSITIONS + 1, DIM_IN), dtype=np.float64)
        states[0] = rng.standard_normal(DIM_IN)
        for t in range(1, TRANSITIONS + 1):
            states[t] = states[t - 1]
            indices = rng.choice(DIM_IN, size=CHANGED_COORDINATES, replace=False)
            states[t, indices] += rng.standard_normal(CHANGED_COORDINATES)
    else:
        raise ValueError("UNKNOWN_REGIME")
    return w, states


def dense_sequence(w, states):
    return [w @ q for q in states]


def delta_sequence(w, states):
    cache = w @ states[0]
    out = [cache]
    for t in range(1, len(states)):
        delta = states[t] - states[t - 1]
        idx = np.flatnonzero(delta != 0.0)
        if len(idx):
            cache = cache + (w[:, idx] @ delta[idx])
        else:
            cache = cache.copy()
        out.append(cache)
    return out


def pair_timing(baseline, candidate):
    baseline()
    candidate()
    base_time, candidate_time = [], []
    for trial in range(TRIALS):
        first, second = (baseline, candidate) if trial % 2 == 0 else (candidate, baseline)
        a = time.perf_counter_ns()
        first()
        b = time.perf_counter_ns()
        second()
        c = time.perf_counter_ns()
        if trial % 2 == 0:
            base_time.append((b - a) / 1e6)
            candidate_time.append((c - b) / 1e6)
        else:
            candidate_time.append((b - a) / 1e6)
            base_time.append((c - b) / 1e6)
    return statistics.median(base_time), statistics.median(candidate_time)


def screen():
    cases, timings = [], []
    with threadpool_limits(limits=1):
        for regime in REGIMES:
            for seed in SEEDS:
                weights, states = generate(seed, regime)
                baseline = lambda: dense_sequence(weights, states)
                candidate = lambda: delta_sequence(weights, states)
                refs = baseline()
                outs = candidate()
                if len(outs) != TRANSITIONS + 1:
                    raise AssertionError("INCOMPLETE_STATES")
                for t in range(1, TRANSITIONS + 1):
                    error = float(np.linalg.norm(outs[t]-refs[t]) / max(float(np.linalg.norm(refs[t])),1e-12))
                    finite = bool(np.all(np.isfinite(outs[t])) and np.all(np.isfinite(refs[t])))
                    support = int(np.count_nonzero(states[t]-states[t-1]))
                    cases.append(dict(seed=seed,regime=regime,transition=t,
                                      delta_support=support,delta_fraction=support/DIM_IN,
                                      relative_l2=error, finite=finite,
                                      within_error_limit=finite and error <= ERROR_LIMIT))
                tbase, tcand = pair_timing(baseline, candidate)
                timings.append(dict(seed=seed,regime=regime,
                                    dense_sequence_ms=tbase,delta_sequence_ms=tcand,
                                    speedup=tbase/tcand))
    if len(cases) != 96 or len(timings) != 6:
        raise AssertionError("INCOMPLETE_SCREEN")
    summary = {}
    for regime in REGIMES:
        group = [x for x in timings if x["regime"] == regime]
        transitions = [x for x in cases if x["regime"] == regime]
        summary[regime] = dict(
            transitions=len(transitions),
            sequences=len(group),
            median_support=statistics.median(x["delta_support"] for x in transitions),
            worst_relative_l2=max(x["relative_l2"] for x in transitions),
            median_speedup=statistics.median(x["speedup"] for x in group),
            all_exact_within_tolerance=all(x["within_error_limit"] for x in transitions),
        )
    passed = all(summary[r]["all_exact_within_tolerance"] and
                 summary[r]["median_speedup"] >= SPEEDUP_FLOOR for r in REGIMES)
    return dict(schema=SCHEMA,
                source_type="synthetic_cpu_numpy_control",authentic_model="NOT_RUN",
                gpu_performance="NOT_RUN",scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),dim_in=DIM_IN,
                            dim_out=DIM_OUT,transitions=TRANSITIONS,
                            sparse_changed_coordinates=CHANGED_COORDINATES,
                            alternating_pairs=TRIALS,error_limit=ERROR_LIMIT,
                            speedup_floor=SPEEDUP_FLOOR),
                cases=cases,sequence_timings=timings,summary=summary,
                decision="CONDITIONAL_FEASIBILITY_ONLY" if passed else "NO_GO_SYNTHETIC_SCREEN",
                caveat="Full per-transition sparsity detection and indexed gather charged. Exact_sparse regime is synthetic; no real model delta sparsity measured.")


if __name__ == "__main__":
    print("G94_JSON=" + json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
