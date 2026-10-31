"""G98 synthetic CPU-only low-rank KV compression falsifier.

Frozen source-independent design:
docs/research/acc_g91_g106/G98_KV_SUBSPACE_PREREG_20261031.md
No authentic TinyLlama, GPU or scientific model acceptance implied.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g98.kv_subspace_cpu_proxy.v1"
SEEDS = (9801, 9802, 9803)
REGIMES = ("iid", "lowrank_favorable")
RANKS = (8, 16, 32)
POSITIONS, DIMENSION, QUERIES = 512, 64, 8
TRIALS, RELATIVE_TOLERANCE, SPEEDUP_FLOOR = 7, 1e-3, 1.15


def workload(seed, regime):
    rng = np.random.default_rng(seed)
    if regime == "iid":
        k = rng.standard_normal((POSITIONS, DIMENSION))
        v = rng.standard_normal((POSITIONS, DIMENSION))
    elif regime == "lowrank_favorable":
        k = ((rng.standard_normal((POSITIONS, 8)) @
              rng.standard_normal((8, DIMENSION))) / math.sqrt(8) +
             .001 * rng.standard_normal((POSITIONS, DIMENSION)))
        v = ((rng.standard_normal((POSITIONS, 8)) @
              rng.standard_normal((8, DIMENSION))) / math.sqrt(8) +
             .001 * rng.standard_normal((POSITIONS, DIMENSION)))
    else:
        raise ValueError("UNKNOWN_REGIME")
    q = rng.standard_normal((QUERIES, DIMENSION))
    return k, v, q


def compress(matrix, rank):
    u, singular, vt = np.linalg.svd(matrix, full_matrices=False)
    # Data-selected basis is computed before queries are used. Values and K
    # are fitted independently; never reuse reference output to train the proxy.
    left = np.ascontiguousarray(u[:, :rank] * singular[:rank])
    right = np.ascontiguousarray(vt[:rank, :])
    residual = float(np.linalg.norm(matrix - left @ right) /
                     max(float(np.linalg.norm(matrix)), 1e-12))
    return left, right, residual


def stable_probs(scores):
    weights = np.exp(scores - np.max(scores))
    return weights / weights.sum()


def dense_attention(keys, values, query):
    weights = stable_probs((keys @ query) / math.sqrt(DIMENSION))
    return weights @ values


def compressed_attention(key_left, key_right, value_left, value_right, query):
    logits = (key_left @ (key_right @ query)) / math.sqrt(DIMENSION)
    weights = stable_probs(logits)
    return (weights @ value_left) @ value_right


def measure_pair(original, compressed):
    original()
    compressed()
    baseline_times, candidate_times = [], []
    for i in range(TRIALS):
        first, second = (original, compressed) if i % 2 == 0 else (compressed, original)
        start = time.perf_counter_ns()
        first()
        mid = time.perf_counter_ns()
        second()
        stop = time.perf_counter_ns()
        if i % 2 == 0:
            baseline_times.append((mid-start)/1e6)
            candidate_times.append((stop-mid)/1e6)
        else:
            candidate_times.append((mid-start)/1e6)
            baseline_times.append((stop-mid)/1e6)
    return statistics.median(baseline_times), statistics.median(candidate_times)


def screen():
    cases, setups = [], []
    with threadpool_limits(limits=1):
        for regime in REGIMES:
            for seed in SEEDS:
                keys, values, queries = workload(seed, regime)
                for rank in RANKS:
                    begin = time.perf_counter_ns()
                    ka, kb, kerror = compress(keys, rank)
                    va, vb, verror = compress(values, rank)
                    setup_ms = (time.perf_counter_ns()-begin)/1e6
                    setups.append(dict(seed=seed, regime=regime, rank=rank,
                                       setup_ms=setup_ms, key_reconstruction_l2=kerror,
                                       value_reconstruction_l2=verror))
                    for query_id, q in enumerate(queries):
                        base_fn = lambda: dense_attention(keys, values, q)
                        cand_fn = lambda: compressed_attention(ka,kb,va,vb,q)
                        base = base_fn()
                        candidate = cand_fn()
                        finite = bool(np.all(np.isfinite(base)) and np.all(np.isfinite(candidate)))
                        difference = float(np.linalg.norm(candidate-base))
                        relative = difference/max(float(np.linalg.norm(base)),1e-12)
                        maxabs = float(np.max(np.abs(candidate-base)))
                        tb,tc = measure_pair(base_fn,cand_fn)
                        cases.append(dict(
                            seed=seed,regime=regime,rank=rank,query_id=query_id,
                            finite=finite,relative_l2=relative,max_abs_error=maxabs,
                            within_tolerance=finite and relative<=RELATIVE_TOLERANCE,
                            baseline_ms=tb,candidate_ms=tc,speedup=tb/tc,
                            key_reconstruction_l2=kerror,value_reconstruction_l2=verror,
                        ))
    if len(cases)!=144 or len(setups)!=18:
        raise AssertionError("CASE_COUNT_DRIFT")
    by_rank={}
    passing=[]
    for rank in RANKS:
        rank_cases=[c for c in cases if c["rank"]==rank]
        by_regime={}
        for regime in REGIMES:
            selected=[c for c in rank_cases if c["regime"]==regime]
            if len(selected)!=24:
                raise AssertionError("REGIME_COUNT_DRIFT")
            by_regime[regime]=dict(
                count=len(selected),all_within_tolerance=all(c["within_tolerance"] for c in selected),
                max_relative_l2=max(c["relative_l2"] for c in selected),
                median_speedup=statistics.median(c["speedup"] for c in selected),
            )
        allowed=all(by_regime[r]["all_within_tolerance"] and
                    by_regime[r]["median_speedup"]>=SPEEDUP_FLOOR for r in REGIMES)
        by_rank[str(rank)]=dict(regimes=by_regime,screening_pass=allowed)
        if allowed:
            passing.append(rank)
    return dict(
        schema=SCHEMA,source_type="seeded_synthetic_cpu_numpy_proxy",
        authentic_checkpoint="NOT_RUN",gpu_measured="NOT_RUN",
        scientific_acceptance="NOT_GRANTED",
        environment=dict(python=platform.python_version(), numpy=np.__version__, blas_threads=1),
        frozen=dict(seeds=list(SEEDS), regimes=list(REGIMES), ranks=list(RANKS),
                    positions=POSITIONS, dimension=DIMENSION,queries=QUERIES,
                    trials=TRIALS,relative_error_limit=RELATIVE_TOLERANCE,
                    median_speedup_floor=SPEEDUP_FLOOR),
        setup=setups,cases=cases,summary=by_rank,
        decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if passing else "NO_GO_SYNTHETIC_SCREEN",
        caveat="Amortized compression setup excluded; favorable tensors manufactured low-rank. Not evidence of actual transformer KV rank or GPU throughput.",
    )


if __name__=="__main__":
    print("G98_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
