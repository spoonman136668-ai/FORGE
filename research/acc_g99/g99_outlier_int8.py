"""G99 outlier-aware INT8 + sparse FP32 corrections, frozen synthetic CPU screen.

Protocol: docs/research/acc_g91_g106/G99_OUTLIER_MIXED_PRECISION_PREREG_20261031.md
This is NOT a CUDA fused kernel nor a genuine pretrained-model throughput test.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g99.outlier_int8_fp32_cpu_proxy.v1"
SEEDS = (9901, 9902, 9903)
REGIMES = ("iid", "injected_outliers")
OUTLIER_K = (0, 2, 8)
ROWS, COLUMNS, QUERIES = 512, 256, 8
INJECTED_PER_ROW, INJECTED_GAIN = 4, 32.
TRIALS, ERROR_LIMIT, SPEEDUP_FLOOR = 7, 1e-2, 1.15
STORAGE_LIMIT = .65


def generate(seed, regime):
    rng = np.random.default_rng(seed)
    weights = (rng.standard_normal((ROWS, COLUMNS)) /
               math.sqrt(COLUMNS)).astype(np.float32)
    queries = rng.standard_normal((QUERIES, COLUMNS)).astype(np.float32)
    if regime == "injected_outliers":
        for row in range(ROWS):
            indices = rng.choice(COLUMNS, size=INJECTED_PER_ROW, replace=False)
            weights[row, indices] *= np.float32(INJECTED_GAIN)
    elif regime != "iid":
        raise ValueError("UNKNOWN_REGIME")
    return weights, queries


def compress(weights, k):
    if k not in OUTLIER_K:
        raise ValueError("UNREGISTERED_OUTLIER_BUDGET")
    base = weights.copy()
    if k:
        columns = np.argsort(-np.abs(weights), axis=1, kind="stable")[:, :k].astype(np.uint16)
        rows = np.arange(ROWS)[:, None]
        residual = weights[rows, columns].astype(np.float32)
        base[rows, columns] = 0.
    else:
        columns = np.empty((ROWS, 0), dtype=np.uint16)
        residual = np.empty((ROWS, 0), dtype=np.float32)
    magnitudes = np.max(np.abs(base), axis=1)
    scales = np.where(magnitudes > 0, magnitudes / np.float32(127.), np.float32(1.)).astype(np.float32)
    codes = np.clip(np.rint(base / scales[:, None]), -127., 127.).astype(np.int8)
    total_bytes = int(codes.nbytes + scales.nbytes + columns.nbytes + residual.nbytes)
    baseline_bytes = int(weights.nbytes)
    if not (codes.shape == (ROWS, COLUMNS) and columns.shape == (ROWS, k)):
        raise AssertionError("INVALID_PACKED_SHAPE")
    if total_bytes != ROWS*COLUMNS + ROWS*4 + ROWS*k*(2+4):
        raise AssertionError("BROKEN_BYTE_ACCOUNTING")
    return dict(codes=codes, scales=scales, columns=columns, residual=residual,
                candidate_bytes=total_bytes, baseline_bytes=baseline_bytes,
                stored_fraction=total_bytes/baseline_bytes)


def reference(weights, query):
    return weights @ query


def mixed_matvec(packed, query):
    # Charged runtime dequantization; intentionally no cached FP32 W.
    decoded = packed["codes"].astype(np.float32) * packed["scales"][:, None]
    result = decoded @ query
    if packed["columns"].shape[1]:
        correction = np.sum(packed["residual"] * query[packed["columns"]],
                            axis=1, dtype=np.float32)
        result = result + correction
    return result


def paired_timing(original, compressed):
    original()
    compressed()
    full, mixed = [], []
    for trial in range(TRIALS):
        first, second = (original, compressed) if trial % 2 == 0 else (compressed, original)
        start = time.perf_counter_ns()
        first()
        midpoint = time.perf_counter_ns()
        second()
        finish = time.perf_counter_ns()
        if trial % 2 == 0:
            full.append((midpoint-start)/1e6)
            mixed.append((finish-midpoint)/1e6)
        else:
            mixed.append((midpoint-start)/1e6)
            full.append((finish-midpoint)/1e6)
    return statistics.median(full), statistics.median(mixed)


def screen():
    cases, setup = [], []
    with threadpool_limits(limits=1):
        for regime in REGIMES:
            for seed in SEEDS:
                weights, queries = generate(seed, regime)
                for k in OUTLIER_K:
                    start = time.perf_counter_ns()
                    packed = compress(weights, k)
                    elapsed = (time.perf_counter_ns()-start)/1e6
                    setup.append(dict(seed=seed, regime=regime, outlier_budget=k,
                                      setup_ms=elapsed,
                                      baseline_bytes=packed["baseline_bytes"],
                                      candidate_bytes=packed["candidate_bytes"],
                                      stored_fraction=packed["stored_fraction"]))
                    for query_id, q in enumerate(queries):
                        base_fn = lambda: reference(weights, q)
                        cand_fn = lambda: mixed_matvec(packed, q)
                        baseline = base_fn()
                        candidate = cand_fn()
                        abs_difference = float(np.linalg.norm(candidate-baseline))
                        rel = abs_difference/max(float(np.linalg.norm(baseline)),1e-12)
                        max_error = float(np.max(np.abs(candidate-baseline)))
                        tb, tc = paired_timing(base_fn, cand_fn)
                        finite = bool(np.all(np.isfinite(candidate)) and np.all(np.isfinite(baseline)) and
                                      all(math.isfinite(z) for z in (rel,max_error,tb,tc)))
                        cases.append(dict(seed=seed, regime=regime, outlier_budget=k,
                                          query_id=query_id, finite=finite,
                                          relative_l2=rel,max_abs_error=max_error,
                                          within_error_limit=finite and rel<=ERROR_LIMIT,
                                          baseline_ms=tb,candidate_ms=tc,speedup=tb/tc,
                                          stored_fraction=packed["stored_fraction"]))
    if len(cases)!=144 or len(setup)!=18:
        raise AssertionError("INCOMPLETE_G99_SCREEN")
    summary={}
    qualifying=[]
    for k in OUTLIER_K:
        group=[c for c in cases if c["outlier_budget"]==k]
        storage=[x["stored_fraction"] for x in setup if x["outlier_budget"]==k]
        if len(group)!=48 or len(storage)!=6:
            raise AssertionError("INVALID_BUDGET_CASES")
        by_regime={}
        for regime in REGIMES:
            subset=[c for c in group if c["regime"]==regime]
            if len(subset)!=24:
                raise AssertionError("INVALID_REGIME_CASES")
            by_regime[regime]=dict(
                count=len(subset),
                all_accurate=all(c["within_error_limit"] for c in subset),
                worst_relative_l2=max(c["relative_l2"] for c in subset),
                median_speedup=statistics.median(c["speedup"] for c in subset),
            )
        storage_ok=all(x<=STORAGE_LIMIT for x in storage)
        passes=storage_ok and all(by_regime[r]["all_accurate"] and
                                  by_regime[r]["median_speedup"]>=SPEEDUP_FLOOR for r in REGIMES)
        summary[str(k)]=dict(stored_fraction=storage[0],storage_ok=storage_ok,
                             regimes=by_regime,screening_pass=passes)
        if passes:
            qualifying.append(k)
    return dict(schema=SCHEMA,source_type="synthetic_cpu_numpy_quantized_weight_proxy",
                authentic_checkpoint="NOT_RUN",gpu_measured="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),outlier_budgets=list(OUTLIER_K),
                            rows=ROWS,columns=COLUMNS,queries=QUERIES,
                            injected_per_row=INJECTED_PER_ROW,injected_gain=INJECTED_GAIN,
                            trials=TRIALS,error_limit=ERROR_LIMIT,
                            speedup_floor=SPEEDUP_FLOOR,storage_fraction_limit=STORAGE_LIMIT),
                setup=setup,cases=cases,summary=summary,
                decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if qualifying else "NO_GO_SYNTHETIC_SCREEN",
                caveat="Weight-only storage excludes padding, memory allocation and temporary decode buffers; favorable outliers are synthetic. CPU decoding performance is not representative of optimized GPU INT8 kernels.")


if __name__=="__main__":
    print("G99_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
