"""G103 fixed shape-adaptive matvec dispatch: synthetic CPU proxy.

Frozen prereg:
docs/research/acc_g91_g106/G103_SHAPE_DISPATCH_PREREG_20261031.md
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g103.shape_dispatch_cpu_proxy.v1"
SEEDS = (10301, 10302, 10303)
SHAPES = (("tiny", 32, 32), ("skinny", 2048, 32),
          ("wide", 64, 2048), ("balanced", 512, 512))
REGIMES = ("dense_iid", "sparse_zero")
QUERIES, TRIALS = 8, 9
SMALL_SIZE_LIMIT = 4096
SPARSE_ZERO_RATE = .9
ERROR_LIMIT, SPEEDUP_FLOOR = 1e-10, 1.15


def make_workload(seed, shape_id, regime):
    shape_index = next((i for i, (name, _, _) in enumerate(SHAPES)
                        if name == shape_id), None)
    if shape_index is None or regime not in REGIMES:
        raise ValueError("UNREGISTERED_CASE")
    _, rows, columns = SHAPES[shape_index]
    rng = np.random.default_rng(np.random.SeedSequence([seed, shape_index]))
    weights = rng.standard_normal((rows, columns)) / math.sqrt(columns)
    inputs = rng.standard_normal((QUERIES, columns))
    if regime == "sparse_zero":
        weights = weights.copy()
        weights[rng.random((rows, columns)) < SPARSE_ZERO_RATE] = 0.
    return weights, inputs


def baseline(weights, query):
    return weights @ query


def dispatched(weights, query):
    # A runtime shape check, dispatch branch and the selected full kernel are
    # all charged on every invocation. No benchmark-driven lookup or tuning.
    rows, columns = weights.shape
    if rows * columns <= SMALL_SIZE_LIMIT:
        return np.einsum("ij,j->i", weights, query, optimize=False)
    return weights @ query


def paired_timing(ref_fn, cand_fn):
    ref_fn()
    cand_fn()
    ref_times, cand_times = [], []
    for trial in range(TRIALS):
        first, second = (ref_fn, cand_fn) if trial % 2 == 0 else (cand_fn, ref_fn)
        t0 = time.perf_counter_ns()
        first()
        t1 = time.perf_counter_ns()
        second()
        t2 = time.perf_counter_ns()
        if trial % 2 == 0:
            ref_times.append((t1-t0)/1e6)
            cand_times.append((t2-t1)/1e6)
        else:
            cand_times.append((t1-t0)/1e6)
            ref_times.append((t2-t1)/1e6)
    return statistics.median(ref_times), statistics.median(cand_times)


def screen():
    cases = []
    with threadpool_limits(limits=1):
        for name, rows, columns in SHAPES:
            for seed in SEEDS:
                for regime in REGIMES:
                    weights, inputs = make_workload(seed, name, regime)
                    path = "einsum" if rows*columns <= SMALL_SIZE_LIMIT else "blas"
                    for query_id, query in enumerate(inputs):
                        base_fn = lambda: baseline(weights, query)
                        cand_fn = lambda: dispatched(weights, query)
                        ref, cand = base_fn(), cand_fn()
                        finite = bool(np.all(np.isfinite(ref)) and np.all(np.isfinite(cand)))
                        rel = float(np.linalg.norm(ref-cand) /
                                    max(float(np.linalg.norm(ref)), 1e-12))
                        abs_error = float(np.max(np.abs(ref-cand)))
                        tb, tc = paired_timing(base_fn, cand_fn)
                        finite = finite and all(math.isfinite(z) for z in (tb, tc, rel, abs_error))
                        cases.append(dict(seed=seed,shape=name,rows=rows,columns=columns,
                                          regime=regime,query_id=query_id,selected_kernel=path,
                                          finite=finite,relative_l2=rel,max_abs_error=abs_error,
                                          within_error_limit=finite and rel <= ERROR_LIMIT,
                                          baseline_ms=tb,candidate_ms=tc,speedup=tb/tc))
    if len(cases)!=192:
        raise AssertionError("G103_CASE_COUNT_DRIFT")
    summary={}
    passing=True
    for name, _, _ in SHAPES:
        grouped={}
        for regime in REGIMES:
            subset=[case for case in cases if case["shape"]==name and case["regime"]==regime]
            if len(subset)!=24:
                raise AssertionError("G103_GROUP_CASE_COUNT_DRIFT")
            grouped[regime]=dict(
                count=len(subset),
                all_accurate=all(x["within_error_limit"] for x in subset),
                worst_relative_l2=max(x["relative_l2"] for x in subset),
                median_speedup=statistics.median(x["speedup"] for x in subset),
                kernel=subset[0]["selected_kernel"])
            passing = passing and grouped[regime]["all_accurate"] and (
                grouped[regime]["median_speedup"] >= SPEEDUP_FLOOR)
        summary[name]=grouped
    return dict(schema=SCHEMA,source_type="seeded_numpy_cpu_kernel_dispatch_proxy",
                authentic_model="NOT_RUN",gpu_measured="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),shapes=[dict(name=n,rows=r,columns=c) for n,r,c in SHAPES],
                            regimes=list(REGIMES),queries=QUERIES,trials=TRIALS,
                            small_size_limit=SMALL_SIZE_LIMIT,sparse_zero_rate=SPARSE_ZERO_RATE,
                            relative_error_limit=ERROR_LIMIT,speedup_floor=SPEEDUP_FLOOR),
                cases=cases,summary=summary,
                decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if passing else "NO_GO_SYNTHETIC_SCREEN",
                caveat="CPU NumPy primitive only; shape-tuned pre-registered branch does not demonstrate GPU kernel speedup or real model throughput.")


if __name__ == "__main__":
    print("G103_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
