"""G104 collision-safe activation fingerprint reuse; synthetic CPU proxy.

Frozen before implementation:
docs/research/acc_g91_g106/G104_FINGERPRINT_PREREG_20261031.md
"""
import hashlib
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g104.fingerprint_exact_match_cpu_proxy.v1"
SEEDS = (10401, 10402, 10403)
REGIMES = ("identical", "near_collision")
ROWS, DIMENSION, PAIRS, TRIALS = 512, 256, 8, 11
PERTURBATION = .001
ERROR_LIMIT, SPEEDUP_FLOOR = 1e-12, 1.15
DIGEST_SIZE = 8


def make_workload(seed):
    rng = np.random.default_rng(seed)
    weights = rng.standard_normal((ROWS, DIMENSION)) / math.sqrt(DIMENSION)
    # Inputs at integer centers, always at least .499 away from quantization edge.
    inputs = (2 * rng.integers(-4, 5, size=(PAIRS, DIMENSION))).astype(np.float64)
    return weights, inputs


def second_input(first, pair_id, regime):
    other = first.copy()
    if regime == "near_collision":
        other[pair_id % DIMENSION] += PERTURBATION
    elif regime != "identical":
        raise ValueError("UNKNOWN_REGIME")
    return other


def fingerprint(x):
    coarse = np.rint(2*x).astype(np.int32)
    return hashlib.blake2b(coarse.tobytes(), digest_size=DIGEST_SIZE).digest()


def baseline(weights, first, second):
    return weights @ first, weights @ second


def cached_pair(weights, first, second):
    # First result must be computed. Checking both coarse hashes AND the full
    # input is essential: quantized hashes are not correctness proofs.
    original = weights @ first
    collided = fingerprint(first) == fingerprint(second)
    exact = bool(collided and np.array_equal(first, second))
    subsequent = original.copy() if exact else weights @ second
    return original, subsequent, collided, exact


def time_pair(base_fn, candidate_fn):
    base_fn()
    candidate_fn()
    baseline_ms, candidate_ms = [], []
    for i in range(TRIALS):
        first, second = (base_fn, candidate_fn) if i % 2 == 0 else (candidate_fn, base_fn)
        start = time.perf_counter_ns()
        first()
        middle = time.perf_counter_ns()
        second()
        stop = time.perf_counter_ns()
        if i % 2 == 0:
            baseline_ms.append((middle - start) / 1e6)
            candidate_ms.append((stop - middle) / 1e6)
        else:
            candidate_ms.append((middle - start) / 1e6)
            baseline_ms.append((stop - middle) / 1e6)
    return statistics.median(baseline_ms), statistics.median(candidate_ms)


def screen():
    cases = []
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            weights, inputs = make_workload(seed)
            for regime in REGIMES:
                for pair_id, first in enumerate(inputs):
                    second = second_input(first, pair_id, regime)
                    base_fn = lambda: baseline(weights, first, second)
                    candidate_fn = lambda: cached_pair(weights, first, second)
                    reference = base_fn()
                    candidate = candidate_fn()
                    deltas = [a-b for a,b in zip(reference, candidate[:2])]
                    absolute = math.sqrt(sum(float(np.vdot(d,d)) for d in deltas))
                    base_norm = math.sqrt(sum(float(np.vdot(a,a)) for a in reference))
                    relative = absolute / max(base_norm, 1e-12)
                    max_abs = max(float(np.max(np.abs(d))) for d in deltas)
                    finite = bool(all(np.all(np.isfinite(v)) for v in
                                      (*reference, candidate[0],candidate[1])) and
                                  all(math.isfinite(z) for z in (relative,max_abs)))
                    tb,tc = time_pair(base_fn,candidate_fn)
                    reuse_expected = regime == "identical"
                    collide_expected = True
                    valid = (finite and relative <= ERROR_LIMIT and
                             candidate[2] == collide_expected and
                             candidate[3] == reuse_expected)
                    cases.append(dict(
                        seed=seed,regime=regime,pair_id=pair_id,
                        quantized_digest_match=bool(candidate[2]),
                        actual_exact_input_match=bool(np.array_equal(first,second)),
                        reused=bool(candidate[3]),
                        expected_reuse=reuse_expected,
                        false_reuse=bool(candidate[3] and not np.array_equal(first,second)),
                        finite=finite,relative_l2=relative,max_abs_error=max_abs,
                        within_all_frozen_correctness_checks=valid,
                        baseline_ms=tb,candidate_ms=tc,speedup=tb/tc,
                    ))
    if len(cases)!=48:
        raise AssertionError("INCOMPLETE_CASES")
    summary={}
    qualified=True
    for regime in REGIMES:
        group=[c for c in cases if c["regime"]==regime]
        if len(group)!=24:
            raise AssertionError("INCOMPLETE_REGIME")
        med=statistics.median(c["speedup"] for c in group)
        good=all(c["within_all_frozen_correctness_checks"] for c in group)
        summary[regime]=dict(
            cases=len(group),all_correct=good,
            hash_collisions=sum(c["quantized_digest_match"] for c in group),
            exact_reuses=sum(c["reused"] for c in group),
            false_reuses=sum(c["false_reuse"] for c in group),
            max_relative_l2=max(c["relative_l2"] for c in group),
            median_speedup=med)
        qualified=qualified and good and med>=SPEEDUP_FLOOR
    return dict(schema=SCHEMA,source_type="seeded_synthetic_cpu_activation_replay",
                authentic_model="NOT_RUN",gpu_measured="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),rows=ROWS,dimension=DIMENSION,
                            pairs=PAIRS,trials=TRIALS,perturbation=PERTURBATION,
                            quantization_scale=2,digest_size=DIGEST_SIZE,
                            relative_error_limit=ERROR_LIMIT,speedup_floor=SPEEDUP_FLOOR),
                cases=cases,summary=summary,
                decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if qualified else "NO_GO_SYNTHETIC_SCREEN",
                caveat="Full exact input equality required even after fingerprint hit. Artificial identical inputs do not establish real activation recurrence or GPU throughput.")


if __name__=="__main__":
    print("G104_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
