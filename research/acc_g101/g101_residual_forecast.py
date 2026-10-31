"""G101 low-rank cross-layer residual forecast, seeded synthetic CPU only.

Prerecorded protocol:
docs/research/acc_g91_g106/G101_CROSS_LAYER_PREREG_20261031.md
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g101.cross_layer_residual_cpu_proxy.v1"
SEEDS = (10101, 10102, 10103)
REGIMES = ("iid", "paired_correlated")
RANKS = (8, 16)
DIMENSION, LAYERS, QUERIES, TRIALS = 128, 12, 8, 7
ERROR_LIMIT, SPEEDUP_FLOOR = 1e-3, 1.15


def make_workload(seed, regime):
    rng = np.random.default_rng(seed)
    even = rng.standard_normal((LAYERS // 2, DIMENSION, DIMENSION)) * .025
    if regime == "iid":
        odd = rng.standard_normal((LAYERS // 2, DIMENSION, DIMENSION)) * .025
    elif regime == "paired_correlated":
        odd = even + rng.standard_normal((LAYERS // 2, DIMENSION, DIMENSION)) * .00025
    else:
        raise ValueError("UNKNOWN_REGIME")
    weights = np.empty((LAYERS, DIMENSION, DIMENSION), dtype=np.float64)
    weights[0::2], weights[1::2] = even, odd
    queries = rng.standard_normal((QUERIES, DIMENSION))
    return weights, queries


def fit_forecasters(weights, rank):
    if rank not in RANKS:
        raise ValueError("UNREGISTERED_RANK")
    left, right, reconstruction_error = [], [], []
    for l in range(0, LAYERS, 2):
        difference = weights[l+1] - weights[l]
        u, singular, vt = np.linalg.svd(difference, full_matrices=False)
        left.append(np.ascontiguousarray(u[:, :rank] * singular[:rank]))
        right.append(np.ascontiguousarray(vt[:rank, :]))
        error = float(np.linalg.norm(difference - left[-1] @ right[-1]) /
                      max(float(np.linalg.norm(difference)), 1e-12))
        reconstruction_error.append(error)
    return (left, right, reconstruction_error)


def full_forward(weights, initial):
    state = initial.copy()
    for l in range(LAYERS):
        state = state + np.tanh(weights[l] @ state)
    return state


def predicted_forward(weights, forecasters, initial):
    left, right, _ = forecasters
    state = initial.copy()
    for idx in range(LAYERS // 2):
        # The even layer is exact with respect to the candidate's propagated
        # state, which may already contain accumulated past approximation.
        z_even = weights[2 * idx] @ state
        state = state + np.tanh(z_even)
        # Predict the following odd preactivation without consulting it.
        # Approximation omits W_even @ (state_after_even-state_before_even).
        forecast_odd = z_even + left[idx] @ (right[idx] @ state)
        state = state + np.tanh(forecast_odd)
    return state


def paired_timing(base_fn, candidate_fn):
    base_fn()
    candidate_fn()
    base_ns, candidate_ns = [], []
    for i in range(TRIALS):
        first, second = (base_fn, candidate_fn) if i % 2 == 0 else (candidate_fn, base_fn)
        t0 = time.perf_counter_ns()
        first()
        t1 = time.perf_counter_ns()
        second()
        t2 = time.perf_counter_ns()
        if i % 2 == 0:
            base_ns.append(t1-t0)
            candidate_ns.append(t2-t1)
        else:
            candidate_ns.append(t1-t0)
            base_ns.append(t2-t1)
    return statistics.median(base_ns)/1e6, statistics.median(candidate_ns)/1e6


def screen():
    cases, setup = [], []
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            for regime in REGIMES:
                weights, queries = make_workload(seed, regime)
                for rank in RANKS:
                    start = time.perf_counter_ns()
                    forecasters = fit_forecasters(weights, rank)
                    setup_ms = (time.perf_counter_ns()-start)/1e6
                    setup.append(dict(seed=seed, regime=regime, rank=rank, setup_ms=setup_ms,
                                      correction_max_relative_reconstruction_error=
                                      max(forecasters[2])))
                    for query_id, q in enumerate(queries):
                        base_fn = lambda: full_forward(weights, q)
                        candidate_fn = lambda: predicted_forward(weights, forecasters, q)
                        reference = base_fn()
                        estimate = candidate_fn()
                        absolute_l2 = float(np.linalg.norm(estimate-reference))
                        relative_l2 = absolute_l2/max(float(np.linalg.norm(reference)),1e-12)
                        max_abs = float(np.max(np.abs(estimate-reference)))
                        tb, tc = paired_timing(base_fn, candidate_fn)
                        finite = bool(np.all(np.isfinite(reference)) and np.all(np.isfinite(estimate)) and
                                      all(math.isfinite(x) for x in (absolute_l2,relative_l2,
                                                                      max_abs,tb,tc)))
                        cases.append(dict(
                            seed=seed,regime=regime,rank=rank,query_id=query_id,
                            finite=finite,within_error_limit=finite and relative_l2<=ERROR_LIMIT,
                            relative_l2=relative_l2,max_abs_error=max_abs,
                            full_dense_matvecs=LAYERS,candidate_dense_matvecs=LAYERS//2,
                            candidate_rank_corrections=LAYERS//2,
                            baseline_ms=tb,candidate_ms=tc,speedup=tb/tc))
    if len(cases)!=96 or len(setup)!=12:
        raise AssertionError("G101_CASE_COUNT_DRIFT")
    summary={}
    winners=[]
    for rank in RANKS:
        by_regime={}
        for regime in REGIMES:
            group=[c for c in cases if c["rank"]==rank and c["regime"]==regime]
            if len(group)!=24:
                raise AssertionError("G101_REGIME_COUNT_DRIFT")
            by_regime[regime]=dict(
                count=len(group),all_accurate=all(c["within_error_limit"] for c in group),
                worst_relative_l2=max(c["relative_l2"] for c in group),
                median_speedup=statistics.median(c["speedup"] for c in group))
        qualified=all(by_regime[r]["all_accurate"] and
                      by_regime[r]["median_speedup"]>=SPEEDUP_FLOOR for r in REGIMES)
        summary[str(rank)]=dict(regimes=by_regime,screening_pass=qualified)
        if qualified:
            winners.append(rank)
    return dict(schema=SCHEMA,source_type="synthetic_cpu_residual_network",
                authentic_model="NOT_RUN",gpu_measured="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),ranks=list(RANKS),
                            dimension=DIMENSION,layers=LAYERS,queries=QUERIES,trials=TRIALS,
                            relative_error_limit=ERROR_LIMIT,speedup_floor=SPEEDUP_FLOOR),
                setup=setup,cases=cases,summary=summary,
                decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if winners else "NO_GO_SYNTHETIC_SCREEN",
                caveat="Odd-layer input-state correction intentionally omitted; synthetic paired matrices are not authentic transformer layers; SVD setup excluded from per-inference timing.")


if __name__=="__main__":
    print("G101_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
