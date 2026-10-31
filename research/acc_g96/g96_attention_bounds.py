"""G96 certified attention-block omission; CPU synthetic falsification.

Frozen: docs/research/acc_g91_g106/G96_ATTENTION_BOUNDS_PREREG_20261031.md
No pretrained model/GPU or claim of authentic decoding improvement.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g96.certified_attention_block_cpu_proxy.v1"
SEEDS = (9601, 9602, 9603)
REGIMES = ("iid", "clustered_aligned")
DIMENSION, KEY_ROWS, BLOCK_ROWS, QUERY_COUNT = 64, 1024, 64, 8
BLOCKS = KEY_ROWS // BLOCK_ROWS
TRIALS, ERROR_TOLERANCE, SPEEDUP_FLOOR = 7, 1e-3, 1.15
SAFETY_SLACK, ROUNDING_AUDIT = 1e-10, 1e-9
SCALE = math.sqrt(DIMENSION)


def make_workload(seed, regime):
    rng = np.random.default_rng(seed)
    if regime == "iid":
        keys = rng.standard_normal((KEY_ROWS, DIMENSION))
        queries = rng.standard_normal((QUERY_COUNT, DIMENSION))
    elif regime == "clustered_aligned":
        centers = rng.standard_normal((BLOCKS, DIMENSION))
        keys = (centers[:, None, :] +
                .02 * rng.standard_normal((BLOCKS, BLOCK_ROWS, DIMENSION)))
        keys = keys.reshape(KEY_ROWS, DIMENSION)
        queries = np.asarray(
            [2.5 * centers[0] + .1 * rng.standard_normal(DIMENSION)
             for _ in range(QUERY_COUNT)]
        )
    else:
        raise ValueError("UNKNOWN_REGIME")
    values = rng.standard_normal((KEY_ROWS, DIMENSION))
    return np.ascontiguousarray(keys), np.ascontiguousarray(values), queries


def block_metadata(keys, values):
    key_blocks = keys.reshape(BLOCKS, BLOCK_ROWS, DIMENSION)
    value_blocks = values.reshape(BLOCKS, BLOCK_ROWS, DIMENSION)
    centers = key_blocks.mean(axis=1)
    residual = key_blocks - centers[:, None, :]
    radii = np.sqrt(np.einsum("gij,gij->gi", residual, residual).max(axis=1))
    value_max = np.sqrt(np.einsum("gij,gij->gi", value_blocks, value_blocks).max(axis=1))
    return centers, radii, value_max


def block_upper_bounds(centers, radii, query):
    bound = (centers @ query + radii * np.linalg.norm(query)) / SCALE
    # Inflate the analytical Cauchy-Schwarz bound for finite float64 rounding.
    return bound + SAFETY_SLACK * (1 + np.abs(bound))


def dense_attention(keys, values, query):
    logits = (keys @ query) / SCALE
    midpoint = logits.max()
    weights = np.exp(logits - midpoint)
    return weights @ values / weights.sum()


def certified_attention(keys, values, query, centers, radii, value_max):
    upper = block_upper_bounds(centers, radii, query)
    if not np.all(np.isfinite(upper)):
        raise ArithmeticError("NONFINITE_BLOCK_BOUND")
    order = np.argsort(-upper, kind="stable")
    running_max = -np.inf
    z = 0.
    numerator = np.zeros(DIMENSION, dtype=np.float64)
    cert_error = 0.
    visited = 0
    early = False
    for block in order:
        start = int(block) * BLOCK_ROWS
        finish = start + BLOCK_ROWS
        logits = (keys[start:finish] @ query) / SCALE
        if not np.all(np.isfinite(logits)):
            raise ArithmeticError("NONFINITE_SCORES")
        block_max = float(np.max(logits))
        new_max = max(running_max, block_max)
        adjust = math.exp(running_max - new_max) if visited else 0.
        factors = np.exp(logits - new_max)
        numerator = numerator * adjust + factors @ values[start:finish]
        z = z * adjust + float(factors.sum())
        running_max = new_max
        visited += 1
        if visited == BLOCKS:
            break
        remaining = order[visited:]
        # Normalizer numerator for all unvisited mass (conservatively bounded).
        remaining_upper = upper[remaining]
        mass_upper = BLOCK_ROWS * float(np.exp(remaining_upper - running_max).sum())
        p = numerator / z
        max_norm = float(value_max[remaining].max())
        cert_error = mass_upper / (z + mass_upper) * (float(np.linalg.norm(p)) + max_norm)
        partial_norm = float(np.linalg.norm(p))
        if partial_norm > cert_error and (
            cert_error <= ERROR_TOLERANCE * (partial_norm - cert_error)
        ):
            early = True
            break
    estimate = numerator / z
    if not np.all(np.isfinite(estimate)):
        raise ArithmeticError("NONFINITE_OUTPUT")
    return estimate, dict(
        early_certified=early, certified_absolute_error=cert_error if early else 0.,
        blocks_scored=visited, rows_scored=visited * BLOCK_ROWS,
    )


def paired_timing(base_fn, candidate_fn):
    base_fn()
    candidate_fn()
    base_times, candidate_times = [], []
    for trial in range(TRIALS):
        first, second = (base_fn, candidate_fn) if trial % 2 == 0 else (candidate_fn, base_fn)
        begin = time.perf_counter_ns()
        first()
        midpoint = time.perf_counter_ns()
        second()
        finish = time.perf_counter_ns()
        if trial % 2 == 0:
            base_times.append((midpoint - begin) / 1e6)
            candidate_times.append((finish - midpoint) / 1e6)
        else:
            candidate_times.append((midpoint - begin) / 1e6)
            base_times.append((finish - midpoint) / 1e6)
    return statistics.median(base_times), statistics.median(candidate_times)


def screen():
    cases, setup = [], []
    with threadpool_limits(limits=1):
        for regime in REGIMES:
            for seed in SEEDS:
                keys, values, queries = make_workload(seed, regime)
                start = time.perf_counter_ns()
                centers, radii, value_max = block_metadata(keys, values)
                setup.append(dict(regime=regime, seed=seed,
                                  metadata_setup_ms=(time.perf_counter_ns()-start)/1e6))
                for query_id, q in enumerate(queries):
                    bounds = block_upper_bounds(centers, radii, q)
                    # Audit mathematical bound itself, outside timed screening.
                    actual_max_per_block = np.asarray([
                        float(((keys[b*BLOCK_ROWS:(b+1)*BLOCK_ROWS] @ q)/SCALE).max())
                        for b in range(BLOCKS)
                    ])
                    upper_valid = bool(np.all(actual_max_per_block <= bounds + ROUNDING_AUDIT))
                    reference = dense_attention(keys, values, q)
                    estimated, props = certified_attention(keys, values, q,
                                                             centers, radii, value_max)
                    absolute = float(np.linalg.norm(reference-estimated))
                    relative = absolute / max(float(np.linalg.norm(reference)), 1e-12)
                    max_abs = float(np.max(np.abs(reference-estimated)))
                    cert_valid = bool(absolute <= props["certified_absolute_error"] + ROUNDING_AUDIT)
                    base_fn = lambda: dense_attention(keys, values, q)
                    candidate_fn = lambda: certified_attention(keys, values, q,
                                                                centers, radii, value_max)
                    tb, tc = paired_timing(base_fn, candidate_fn)
                    finite = bool(np.all(np.isfinite(reference)) and np.all(np.isfinite(estimated)) and
                                  all(math.isfinite(x) for x in (relative,max_abs,tb,tc)))
                    cases.append(dict(seed=seed, regime=regime, query_id=query_id,
                                      upper_bound_valid=upper_valid, certificate_valid=cert_valid,
                                      finite=finite, within_error_limit=relative<=ERROR_TOLERANCE,
                                      absolute_l2=absolute, relative_l2=relative,
                                      max_abs_error=max_abs,
                                      baseline_ms=tb,candidate_ms=tc,speedup=tb/tc,
                                      **props))
    if len(cases) != 48:
        raise AssertionError("INCOMPLETE_SCREEN")
    summary = {}
    for regime in REGIMES:
        subset = [c for c in cases if c["regime"] == regime]
        summary[regime] = dict(
            count=len(subset), median_speedup=statistics.median(c["speedup"] for c in subset),
            median_rows=statistics.median(c["rows_scored"] for c in subset),
            certified_skips=sum(c["early_certified"] for c in subset),
            max_relative_l2=max(c["relative_l2"] for c in subset),
            all_correct=all(c["upper_bound_valid"] and c["certificate_valid"] and
                            c["finite"] and c["within_error_limit"] for c in subset),
        )
    passed = all(summary[r]["all_correct"] and
                 summary[r]["median_speedup"] >= SPEEDUP_FLOOR for r in REGIMES)
    return dict(
        schema=SCHEMA,source_type="cpu_numpy_synthetic_certificate_proxy",
        authentic_model="NOT_RUN",gpu_measured="NOT_RUN",scientific_acceptance="NOT_GRANTED",
        environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
        frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),dimension=DIMENSION,
                    key_rows=KEY_ROWS,block_rows=BLOCK_ROWS,query_count=QUERY_COUNT,
                    trials=TRIALS,error_tolerance=ERROR_TOLERANCE,
                    speedup_floor=SPEEDUP_FLOOR,rounding_audit=ROUNDING_AUDIT),
        metadata_initialization=setup,cases=cases,summary=summary,
        decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if passed else "NO_GO_SYNTHETIC_SCREEN",
        caveat="Block preprocessing is excluded from per-query times, optimistically favoring candidate; clustered aligned data does not establish authentic model behavior.")


if __name__ == "__main__":
    print("G96_JSON=" + json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
