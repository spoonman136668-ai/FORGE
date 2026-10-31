"""G105 token-conditional FP32 projection with FP64 fallback: CPU proxy.

Preregistered at docs/research/acc_g91_g106/G105_PRECISION_ROUTING_PREREG_20261031.md
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA = "forge.acc.g105.precision_routing_cpu_proxy.v1"
SEEDS = (10501, 10502, 10503)
REGIMES = ("iid", "hard_near_tie")
ROWS, COLUMNS, QUERIES, TRIALS = 512, 256, 8, 9
SPEEDUP_FLOOR = 1.15
EPS = float(np.finfo(np.float32).eps)
GAMMA = (COLUMNS * EPS) / (1 - COLUMNS * EPS)


def make_workload(seed, regime):
    rng = np.random.default_rng(seed)
    weights = rng.standard_normal((ROWS, COLUMNS)) / math.sqrt(COLUMNS)
    biases = np.zeros(ROWS, dtype=np.float64)
    if regime == "hard_near_tie":
        # Manufacture ambiguous rows 0/1 so the candidate normally needs
        # a full-precision fallback, without seeing a baseline prediction.
        weights[0] = rng.standard_normal(COLUMNS) * .01
        weights[1] = weights[0] + rng.standard_normal(COLUMNS) * 1e-7
        weights[2:] *= .01
        biases[0:2] = 10.
    elif regime != "iid":
        raise ValueError("UNREGISTERED_REGIME")
    inputs = rng.standard_normal((QUERIES, COLUMNS))
    return weights, biases, inputs


def setup_bound(weights):
    return float(np.abs(weights).sum(axis=1).max())


def exact(weights, biases, query):
    logits = weights @ query + biases
    return int(np.argmax(logits)), logits


def routed(weights, biases, query, weight_norm):
    # This conversion/approximate dense matvec is deliberately charged every
    # token. No uncharged cached FP32 matrix or reference output peek.
    approx = (weights.astype(np.float32) @ query.astype(np.float32)).astype(np.float64) + biases
    rank = np.argsort(-approx,kind="stable")
    margin = float(approx[rank[0]] - approx[rank[1]])
    max_bound = 4 * GAMMA * weight_norm * float(np.max(np.abs(query))) + 1e-10
    if margin > 2 * max_bound:
        return int(rank[0]), dict(
            chosen_precision="float32",fell_back=False,
            approximate_margin=margin,rounding_budget=max_bound)
    token, _ = exact(weights, biases, query)
    return token, dict(
        chosen_precision="float64",fell_back=True,
        approximate_margin=margin,rounding_budget=max_bound)


def time_pair(baseline, candidate):
    baseline()
    candidate()
    bt, ct = [], []
    for t in range(TRIALS):
        first, second = (baseline,candidate) if t%2==0 else (candidate,baseline)
        begin=time.perf_counter_ns()
        first()
        middle=time.perf_counter_ns()
        second()
        finish=time.perf_counter_ns()
        if t%2==0:
            bt.append((middle-begin)/1e6)
            ct.append((finish-middle)/1e6)
        else:
            ct.append((middle-begin)/1e6)
            bt.append((finish-middle)/1e6)
    return statistics.median(bt),statistics.median(ct)


def screen():
    cases, setup = [], []
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            for regime in REGIMES:
                weights,biases,inputs = make_workload(seed,regime)
                start=time.perf_counter_ns()
                weight_norm=setup_bound(weights)
                setup.append(dict(seed=seed,regime=regime,
                                  max_row_l1_norm=weight_norm,
                                  norm_setup_ms=(time.perf_counter_ns()-start)/1e6))
                for query_id,q in enumerate(inputs):
                    baseline=lambda: exact(weights,biases,q)
                    candidate=lambda: routed(weights,biases,q,weight_norm)
                    answer, ref_logits=baseline()
                    guess, props=candidate()
                    tb,tc=time_pair(baseline,candidate)
                    finite=bool(np.all(np.isfinite(ref_logits)) and
                                all(math.isfinite(z) for z in
                                    (props["approximate_margin"],props["rounding_budget"],tb,tc)))
                    cases.append(dict(
                        seed=seed,regime=regime,query_id=query_id,
                        correct=finite and guess==answer,
                        finite=finite,baseline_greedy=answer,candidate_greedy=guess,
                        baseline_ms=tb,candidate_ms=tc,speedup=tb/tc,**props))
    if len(cases)!=48 or len(setup)!=6:
        raise AssertionError("G105_CASE_COUNT_DRIFT")
    summary={}
    qualified=True
    for regime in REGIMES:
        selected=[x for x in cases if x["regime"]==regime]
        if len(selected)!=24:
            raise AssertionError("G105_REGIME_COUNT_DRIFT")
        median=statistics.median(x["speedup"] for x in selected)
        exact_all=all(x["correct"] for x in selected)
        summary[regime]=dict(cases=24,all_exact=exact_all,
                            fp32_routes=sum(not x["fell_back"] for x in selected),
                            fp64_fallbacks=sum(x["fell_back"] for x in selected),
                            median_speedup=median)
        qualified=qualified and exact_all and median>=SPEEDUP_FLOOR
    return dict(schema=SCHEMA,source_type="float32_float64_numpy_cpu_proxy",
                authentic_model="NOT_RUN",gpu_measured="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),
                            rows=ROWS,columns=COLUMNS,queries=QUERIES,trials=TRIALS,
                            speedup_floor=SPEEDUP_FLOOR,epsilon_fp32=EPS,gamma_256=GAMMA),
                setup=setup,cases=cases,summary=summary,
                decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if qualified else "NO_GO_SYNTHETIC_SCREEN",
                caveat="CPU float32 route plus float64 fallback; a conservative bound heuristic is NOT a formal IEEE proof; numerical correctness independently checked on every case. No GPU mixed-precision claim.")


if __name__=="__main__":
    print("G105_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
