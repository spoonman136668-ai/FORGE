"""G91 certified vocabulary-elimination CPU proxy, prereg: docs/research/acc_g91_g106/SCREENING_PREREG_20261031.md.

No pretrained model, GPU, scientific acceptance, or model change. Requires numpy
and threadpoolctl. JSON observations to stdout; no filesystem artifacts written.
"""
import json
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g91.certified_vocab_cpu_proxy.v1"
SEEDS = (9101, 9102, 9103)
REGIMES = ("iid", "clustered")
GROUPS, GROUP_ROWS, DIMENSION = 64, 128, 128
TRIALS = 7
SLACK = 1e-10


def build_case(seed, regime):
    """Independent seeded synthetic matrix and independent/favorable queries."""
    rng = np.random.default_rng(seed)
    if regime == "clustered":
        centers = rng.standard_normal((GROUPS, DIMENSION))
        weights = centers[:, None, :] + .03 * rng.standard_normal(
            (GROUPS, GROUP_ROWS, DIMENSION)
        )
        queries = [rng.standard_normal(DIMENSION) for _ in range(4)]
        queries += [centers[i] + .05 * rng.standard_normal(DIMENSION) for i in range(4)]
        labels = ["random"] * 4 + ["aligned_favorable"] * 4
    elif regime == "iid":
        weights = rng.standard_normal((GROUPS, GROUP_ROWS, DIMENSION))
        queries = [rng.standard_normal(DIMENSION) for _ in range(8)]
        labels = ["random"] * 8
    else:
        raise ValueError("UNKNOWN_REGIME")
    return np.ascontiguousarray(weights), queries, labels


def bounds_setup(weights):
    centers = weights.mean(axis=1)
    residual = weights - centers[:, None, :]
    radii = np.sqrt(np.einsum("gij,gij->gi", residual, residual).max(axis=1))
    return centers, radii


def dense_projection(flat_weights, query):
    logits = flat_weights @ query
    return int(np.argmax(logits)), float(np.max(logits))


def certified_projection(weights, centers, radii, query):
    """Exact maximizer, pruning only when *all* remaining group bounds lose."""
    query_norm = float(np.linalg.norm(query))
    upper = centers @ query + radii * query_norm
    if not np.all(np.isfinite(upper)):
        raise ArithmeticError("NONFINITE_CERTIFICATE")
    order = np.argsort(-upper, kind="stable")
    best_index = -1
    best_score = -np.inf
    visited_groups = 0
    for group in order:
        ceiling = float(upper[group])
        if ceiling + SLACK * (1 + abs(ceiling)) < best_score:
            break
        scores = weights[group] @ query
        if not np.all(np.isfinite(scores)):
            raise ArithmeticError("NONFINITE_SCORES")
        local_index = int(np.argmax(scores))
        idx = int(group) * GROUP_ROWS + local_index
        value = float(scores[local_index])
        if value > best_score or (value == best_score and idx < best_index):
            best_score, best_index = value, idx
        visited_groups += 1
    if best_index < 0:
        raise AssertionError("NO_WINNER")
    return best_index, best_score, visited_groups * GROUP_ROWS


def measure_pair(dense, candidate):
    dense()
    candidate()
    td, tc = [], []
    for trial in range(TRIALS):
        if trial % 2:
            first, second = candidate, dense
        else:
            first, second = dense, candidate
        start = time.perf_counter_ns()
        first()
        middle = time.perf_counter_ns()
        second()
        end = time.perf_counter_ns()
        if trial % 2:
            tc.append((middle - start) / 1e6)
            td.append((end - middle) / 1e6)
        else:
            td.append((middle - start) / 1e6)
            tc.append((end - middle) / 1e6)
    return statistics.median(td), statistics.median(tc)


def screen():
    all_cases = []
    setup = []
    with threadpool_limits(limits=1):
        for regime in REGIMES:
            for seed in SEEDS:
                weights, queries, labels = build_case(seed, regime)
                flat = weights.reshape(-1, DIMENSION)
                t0 = time.perf_counter_ns()
                centers, radii = bounds_setup(weights)
                setup.append(dict(seed=seed, regime=regime, setup_ms=(time.perf_counter_ns()-t0)/1e6))
                for query_id, (q, label) in enumerate(zip(queries, labels)):
                    dense_fn = lambda: dense_projection(flat, q)
                    candidate_fn = lambda: certified_projection(weights, centers, radii, q)
                    dense_idx, dense_max = dense_fn()
                    idx, candidate_max, rows = candidate_fn()
                    if not (np.isfinite(dense_max) and np.isfinite(candidate_max)):
                        raise ArithmeticError("NONFINITE_WINNER")
                    td, tc = measure_pair(dense_fn, candidate_fn)
                    all_cases.append(dict(
                        regime=regime, seed=seed, query_id=query_id, query_kind=label,
                        exact_index=(idx == dense_idx),
                        baseline_index=dense_idx, candidate_index=idx,
                        winning_score_abs_diff=abs(dense_max-candidate_max),
                        scored_rows=rows, scored_fraction=rows/(GROUPS*GROUP_ROWS),
                        baseline_ms=td, candidate_ms=tc,
                        speedup=td/tc if tc else None,
                    ))
    summary = {}
    for regime in REGIMES:
        selected = [c for c in all_cases if c["regime"] == regime]
        summary[regime] = dict(
            cases=len(selected),
            all_exact=all(c["exact_index"] for c in selected),
            median_rows=statistics.median(c["scored_rows"] for c in selected),
            median_speedup=statistics.median(c["speedup"] for c in selected),
        )
    valid = len(all_cases) == 48 and all(c["exact_index"] for c in all_cases)
    go = valid and all(summary[x]["median_speedup"] >= 1.15 for x in REGIMES)
    return dict(
        schema=SCHEMA,
        source_type="seeded_cpu_numpy_synthetic_proxy",
        gpu_model_evidence="NOT_RUN", scientific_acceptance="NOT_GRANTED",
        environment=dict(python=platform.python_version(), numpy=np.__version__, blas_threads=1),
        parameters=dict(seeds=list(SEEDS), regimes=list(REGIMES), groups=GROUPS,
                        rows_per_group=GROUP_ROWS, dimension=DIMENSION, trials=TRIALS,
                        safety_slack=SLACK),
        initialization_ms=setup, cases=all_cases, summary=summary,
        decision="CONDITIONAL_FEASIBILITY_ONLY" if go else "NO_GO_SYNTHETIC_SCREEN",
        caveat="Initialization excluded from per-query times; uncharged setup makes this an optimistic screen. Need authentic-model/GPU evaluation for any performance claim.",
    )


if __name__ == "__main__":
    print(json.dumps(screen(), indent=2, allow_nan=False))
