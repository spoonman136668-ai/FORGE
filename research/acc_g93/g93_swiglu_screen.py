"""G93 SwiGLU dead-zone CPU screening. Authentic model and GPU NOT RUN.

Frozen criteria: docs/research/acc_g91_g106/G93_SWIGLU_PREREG_20261031.md
Use pinned NumPy and threadpoolctl on one BLAS thread; emit all observations to stdout.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g93.swiglu_negative_tail_cpu_v1"
SEEDS = (9301, 9302, 9303)
REGIMES = ("iid", "negative_shifted")
THRESHOLDS = (2., 4., 6.)
DIMENSION, HIDDEN, OUTPUT_DIM = 128, 1024, 128
INPUTS_PER_SEED, PAIRED_TRIALS = 4, 15
ACCURACY_LIMIT, SPEEDUP_FLOOR = 1e-3, 1.15


def make_seed(seed):
    rng = np.random.default_rng(seed)
    wg = (rng.standard_normal((DIMENSION, HIDDEN)) / math.sqrt(DIMENSION)).astype(np.float32)
    wu = (rng.standard_normal((DIMENSION, HIDDEN)) / math.sqrt(DIMENSION)).astype(np.float32)
    wd = (rng.standard_normal((HIDDEN, OUTPUT_DIM)) / math.sqrt(HIDDEN)).astype(np.float32)
    queries = rng.standard_normal((INPUTS_PER_SEED, DIMENSION)).astype(np.float32)
    return wg, wu, wd, queries


def silu(z):
    return z / (1.0 + np.exp(-z))


def dense(q, wg, wu, wd, bias):
    z = q @ wg + np.float32(bias)
    v = silu(z) * (q @ wu)
    return v @ wd


def selective(q, wg, wu, wd, bias, threshold):
    z = q @ wg + np.float32(bias)
    up = q @ wu
    active = z >= -threshold
    values = (silu(z[active]) * up[active])
    return values @ wd[active, :], int(active.sum())


def paired_medians(reference, candidate):
    reference()
    candidate()
    dense_times, candidate_times = [], []
    for k in range(PAIRED_TRIALS):
        first, second = (reference, candidate) if k % 2 == 0 else (candidate, reference)
        a = time.perf_counter_ns()
        first()
        b = time.perf_counter_ns()
        second()
        c = time.perf_counter_ns()
        t1 = (b - a) / 1e6
        t2 = (c - b) / 1e6
        if k % 2 == 0:
            dense_times.append(t1)
            candidate_times.append(t2)
        else:
            dense_times.append(t2)
            candidate_times.append(t1)
    return statistics.median(dense_times), statistics.median(candidate_times)


def screen():
    observations = []
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            wg, wu, wd, queries = make_seed(seed)
            for regime in REGIMES:
                bias = 0. if regime == "iid" else -3.
                for input_id, q in enumerate(queries):
                    for threshold in THRESHOLDS:
                        ref_fn = lambda: dense(q, wg, wu, wd, bias)
                        candidate_fn = lambda: selective(q, wg, wu, wd, bias, threshold)
                        ref = ref_fn()
                        candidate, retained = candidate_fn()
                        if not (np.all(np.isfinite(ref)) and np.all(np.isfinite(candidate))):
                            raise ArithmeticError("NONFINITE_OUTPUT")
                        rel = float(np.linalg.norm(candidate-ref) / max(float(np.linalg.norm(ref)), 1e-12))
                        abs_err = float(np.max(np.abs(candidate-ref)))
                        td, tc = paired_medians(ref_fn, candidate_fn)
                        observations.append(dict(
                            seed=seed, regime=regime, input_id=input_id, threshold=threshold,
                            retained=retained, omitted=HIDDEN-retained,
                            omitted_fraction=(HIDDEN-retained)/HIDDEN,
                            relative_l2=rel, max_abs_error=abs_err,
                            dense_ms=td, candidate_ms=tc, speedup=td/tc,
                        ))
    if len(observations) != 72:
        raise AssertionError("CASE_COUNT_DRIFT")
    threshold_summary = {}
    qualified = []
    for t in THRESHOLDS:
        current = [c for c in observations if c["threshold"] == t]
        if len(current) != 24:
            raise AssertionError("THRESHOLD_CASE_COUNT_DRIFT")
        err_ok = all(c["relative_l2"] <= ACCURACY_LIMIT for c in current)
        by_regime = {}
        for r in REGIMES:
            selected = [c for c in current if c["regime"] == r]
            if len(selected) != 12:
                raise AssertionError("REGIME_CASE_COUNT_DRIFT")
            by_regime[r] = dict(
                count=len(selected),
                median_omitted_fraction=statistics.median(c["omitted_fraction"] for c in selected),
                median_speedup=statistics.median(c["speedup"] for c in selected),
                worst_relative_l2=max(c["relative_l2"] for c in selected),
            )
        passed = err_ok and all(by_regime[r]["median_speedup"] >= SPEEDUP_FLOOR for r in REGIMES)
        threshold_summary[str(int(t))] = dict(
            error_all_pass=err_ok,
            median_regime=by_regime,
            screening_pass=passed,
        )
        if passed:
            qualified.append(t)
    return dict(
        schema=SCHEMA, source_type="seeded_synthetic_cpu_numpy_proxy",
        authentic_checkpoint="NOT_RUN", gpu_measured="NOT_RUN",
        scientific_acceptance="NOT_GRANTED",
        environment=dict(python=platform.python_version(), numpy=np.__version__, blas_threads=1),
        frozen=dict(seeds=list(SEEDS), regimes=list(REGIMES), thresholds=list(THRESHOLDS),
                    d_model=DIMENSION, hidden=HIDDEN, d_out=OUTPUT_DIM,
                    queries_per_seed=INPUTS_PER_SEED, paired_trials=PAIRED_TRIALS,
                    relative_l2_limit=ACCURACY_LIMIT, median_speedup_floor=SPEEDUP_FLOOR),
        threshold_summary=threshold_summary, cases=observations,
        decision="CONDITIONAL_SCREEN_FEASIBILITY" if qualified else "NO_GO_SYNTHETIC_SCREEN",
        caveat="Synthetic CPU only, full gate/up included in both arms; negative-shifted condition is deliberately favorable, not observed in TinyLlama.",
    )


if __name__ == "__main__":
    print("G93_JSON=" + json.dumps(screen(), sort_keys=True, separators=(",", ":"), allow_nan=False))
