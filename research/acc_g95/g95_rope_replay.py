"""G95 RoPE position-shift replay CPU synthetic falsifier.

Frozen preregistration:
docs/research/acc_g91_g106/G95_ROPE_PREREG_20261031.md

No claim that token-text recurrence implies equal contextualized Q/K.
"""
import json
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g95.rope_exact_replay_cpu_v1"
SEEDS = (9501, 9502, 9503)
REGIMES = ("identical_pre_rope", "context_drift")
SHIFTS = (17, 73, 511, 4097)
DIMENSION, MOTIF_LENGTH, TRIALS = 64, 16, 15
MAX_ABS_ERROR, SPEEDUP_FLOOR = 1e-9, 1.15


def seed_workloads(seed):
    rng = np.random.default_rng(seed)
    queries = rng.standard_normal((MOTIF_LENGTH, DIMENSION))
    keys = rng.standard_normal((MOTIF_LENGTH, DIMENSION))
    # Independent contextual drift, one pair per shift, in fixed source order.
    drift = [
        (rng.standard_normal((MOTIF_LENGTH, DIMENSION)),
         rng.standard_normal((MOTIF_LENGTH, DIMENSION)))
        for _ in SHIFTS
    ]
    return queries, keys, drift


def rope(x, offset):
    """Rotate successive pairs, using absolute positions and canonical frequencies."""
    positions = offset + np.arange(MOTIF_LENGTH, dtype=np.float64)
    freqs = np.power(10000., -2 * np.arange(DIMENSION // 2, dtype=np.float64) / DIMENSION)
    angles = np.multiply.outer(positions, freqs)
    cosine, sine = np.cos(angles), np.sin(angles)
    pairs = x.reshape(MOTIF_LENGTH, DIMENSION // 2, 2)
    real = pairs[:, :, 0] * cosine - pairs[:, :, 1] * sine
    imag = pairs[:, :, 0] * sine + pairs[:, :, 1] * cosine
    return np.stack((real, imag), axis=-1).reshape(MOTIF_LENGTH, DIMENSION)


def score(q, k, offset):
    return rope(q, offset) @ rope(k, offset).T


def baseline(q0, k0, q1, k1, shift):
    first = score(q0, k0, 0)
    second = score(q1, k1, shift)
    return first, second


def candidate(q0, k0, q1, k1, shift):
    first = score(q0, k0, 0)
    exact_reuse = np.array_equal(q0, q1) and np.array_equal(k0, k1)
    second = first.copy() if exact_reuse else score(q1, k1, shift)
    return first, second, bool(exact_reuse)


def time_pair(base_fn, candidate_fn):
    base_fn()
    candidate_fn()
    base_ns, candidate_ns = [], []
    for trial in range(TRIALS):
        first, second = (base_fn, candidate_fn) if trial % 2 == 0 else (candidate_fn, base_fn)
        start = time.perf_counter_ns()
        first()
        mid = time.perf_counter_ns()
        second()
        end = time.perf_counter_ns()
        if trial % 2 == 0:
            base_ns.append(mid - start)
            candidate_ns.append(end - mid)
        else:
            candidate_ns.append(mid - start)
            base_ns.append(end - mid)
    return statistics.median(base_ns) / 1e6, statistics.median(candidate_ns) / 1e6


def screen():
    cases = []
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            q0, k0, drift = seed_workloads(seed)
            for regime in REGIMES:
                for i, shift in enumerate(SHIFTS):
                    q1, k1 = (q0, k0) if regime == "identical_pre_rope" else drift[i]
                    base_fn = lambda: baseline(q0, k0, q1, k1, shift)
                    candidate_fn = lambda: candidate(q0, k0, q1, k1, shift)
                    original = base_fn()
                    replay = candidate_fn()
                    finite = bool(all(np.all(np.isfinite(a)) for a in (*original, replay[0], replay[1])))
                    max_abs = float(max(np.max(np.abs(a-b)) for a,b in zip(original, replay[:2])))
                    tb, tc = time_pair(base_fn, candidate_fn)
                    cases.append(dict(
                        seed=seed, regime=regime, shift=shift,
                        exact_input_match=bool(replay[2]),
                        is_finite=finite, max_abs_error=max_abs,
                        within_error_limit=finite and max_abs <= MAX_ABS_ERROR,
                        baseline_ms=tb, candidate_ms=tc, speedup=tb/tc,
                    ))
    if len(cases) != 24:
        raise AssertionError("INCOMPLETE_CASES")
    summary = {}
    for regime in REGIMES:
        subset = [x for x in cases if x["regime"] == regime]
        expected_hit = regime == "identical_pre_rope"
        summary[regime] = dict(
            cases=len(subset),
            median_speedup=statistics.median(x["speedup"] for x in subset),
            max_abs_error=max(x["max_abs_error"] for x in subset),
            all_correct=all(x["within_error_limit"] and x["exact_input_match"] == expected_hit for x in subset),
            cache_hits=sum(x["exact_input_match"] for x in subset),
        )
    go = all(summary[r]["all_correct"] and summary[r]["median_speedup"] >= SPEEDUP_FLOOR
             for r in REGIMES)
    return dict(
        schema=SCHEMA,
        source_type="synthetic_cpu_rope_exact_contextual_values",
        authentic_model="NOT_RUN", gpu_performance="NOT_RUN",
        scientific_acceptance="NOT_GRANTED",
        environment=dict(python=platform.python_version(), numpy=np.__version__, blas_threads=1),
        frozen=dict(seeds=list(SEEDS), regimes=list(REGIMES), shifts=list(SHIFTS),
                    dimension=DIMENSION, motif_length=MOTIF_LENGTH,
                    alternating_trials=TRIALS, max_abs_error=MAX_ABS_ERROR,
                    speedup_floor=SPEEDUP_FLOOR),
        summary=summary, cases=cases,
        decision="CONDITIONAL_FEASIBILITY_ONLY" if go else "NO_GO_SYNTHETIC_SCREEN",
        caveat="Identical pre-RoPE Q/K is an intentionally favorable synthetic assumption; contextualized LLM Q/K may differ even when the original token strings repeat.",
    )


if __name__ == "__main__":
    print("G95_JSON=" + json.dumps(screen(), sort_keys=True, separators=(",", ":"), allow_nan=False))
