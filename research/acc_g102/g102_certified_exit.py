"""G102 deterministic certified early exit, synthetic recurrent CPU proxy only.

Frozen:
docs/research/acc_g91_g106/G102_CERTIFIED_EARLY_EXIT_PREREG_20261031.md
"""
import json
import math
import platform
import statistics
import time

import numpy as np
from threadpoolctl import threadpool_limits

SCHEMA="forge.acc.g102.certified_early_exit_cpu_proxy.v1"
SEEDS=(10201,10202,10203)
REGIMES=("iid","early_dominant")
LAYERS,DIMENSION,VOCAB,QUERIES=12,64,128,8
TRIALS,SPEEDUP_FLOOR=7,1.15
ROUNDING_SLACK=1e-10
SCALE=math.sqrt(DIMENSION)


def workload(seed,regime):
    rng=np.random.default_rng(seed)
    hidden=rng.standard_normal((LAYERS,DIMENSION,DIMENSION))/SCALE
    output=rng.standard_normal((LAYERS,VOCAB,DIMENSION))/SCALE
    if regime=="early_dominant":
        output[1:]*=1e-6
    elif regime!="iid":
        raise ValueError("UNREGISTERED_REGIME")
    starts=rng.standard_normal((QUERIES,DIMENSION))
    return hidden,output,starts


def setup_bounds(output):
    norms=np.linalg.norm(output,axis=-1)*SCALE
    max_per_layer=np.max(norms,axis=1)
    suffix=np.zeros(LAYERS,dtype=np.float64)
    running=0.
    for l in range(LAYERS-1,-1,-1):
        suffix[l]=running
        running+=max_per_layer[l]
    return suffix


def full_decode(hidden,output,initial):
    state=initial.copy()
    logits=np.zeros(VOCAB,dtype=np.float64)
    for l in range(LAYERS):
        state=np.tanh(hidden[l] @ state)
        logits=logits+output[l] @ state
    return int(np.argmax(logits)),logits


def certified_decode(hidden,output,initial,suffix):
    state=initial.copy()
    logits=np.zeros(VOCAB,dtype=np.float64)
    for layer in range(LAYERS):
        state=np.tanh(hidden[layer] @ state)
        logits=logits+output[layer] @ state
        # Full sort is intentionally charged; tie behavior is unambiguous
        # because the certificate uses strictly positive margin.
        best_indices=np.argsort(-logits,kind="stable")
        margin=float(logits[best_indices[0]]-logits[best_indices[1]])
        bound=float(suffix[layer])
        inflated=bound+ROUNDING_SLACK*(1.+bound)
        if margin>2.*inflated or layer+1==LAYERS:
            return int(best_indices[0]),dict(
                layers_evaluated=layer+1, certified=margin>2.*inflated,
                stop_margin=margin, remaining_absolute_score_bound=inflated,
            )
    raise AssertionError("UNREACHABLE_EXIT")


def timing(base,candidate):
    base()
    candidate()
    tb,tc=[],[]
    for i in range(TRIALS):
        first,second=(base,candidate) if i%2==0 else (candidate,base)
        a=time.perf_counter_ns()
        first()
        b=time.perf_counter_ns()
        second()
        c=time.perf_counter_ns()
        if i%2==0:
            tb.append((b-a)/1e6)
            tc.append((c-b)/1e6)
        else:
            tc.append((b-a)/1e6)
            tb.append((c-b)/1e6)
    return statistics.median(tb),statistics.median(tc)


def screen():
    cases,setup=[],[]
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            for regime in REGIMES:
                hidden,output,starts=workload(seed,regime)
                start=time.perf_counter_ns()
                suffix=setup_bounds(output)
                setup.append(dict(seed=seed,regime=regime,
                                  bounds_setup_ms=(time.perf_counter_ns()-start)/1e6))
                for query_id,q in enumerate(starts):
                    base_fn=lambda:full_decode(hidden,output,q)
                    cand_fn=lambda:certified_decode(hidden,output,q,suffix)
                    exact,full_logits=base_fn()
                    choice,prop=cand_fn()
                    top=np.argsort(-full_logits,kind="stable")
                    full_margin=float(full_logits[top[0]]-full_logits[top[1]])
                    tb,tc=timing(base_fn,cand_fn)
                    finite=bool(np.all(np.isfinite(full_logits)) and
                                all(math.isfinite(v) for v in
                                    (full_margin,tb,tc,prop["stop_margin"],
                                     prop["remaining_absolute_score_bound"])))
                    cases.append(dict(
                        seed=seed,regime=regime,query_id=query_id,
                        correct=finite and choice==exact,finite=finite,
                        greedy_reference=exact,candidate_choice=choice,
                        full_reference_top2_gap=full_margin,
                        baseline_ms=tb,candidate_ms=tc,speedup=tb/tc,
                        **prop))
    if len(cases)!=48 or len(setup)!=6:
        raise AssertionError("G102_CASE_COUNT_DRIFT")
    summary={}
    for regime in REGIMES:
        data=[c for c in cases if c["regime"]==regime]
        if len(data)!=24:
            raise AssertionError("G102_REGIME_CASE_COUNT")
        summary[regime]=dict(
            cases=len(data),all_exact=all(c["correct"] for c in data),
            median_speedup=statistics.median(c["speedup"] for c in data),
            median_layers=statistics.median(c["layers_evaluated"] for c in data),
            certified_early_exits=sum(c["certified"] and c["layers_evaluated"]<LAYERS for c in data))
    qualified=all(summary[r]["all_exact"] and
                  summary[r]["median_speedup"]>=SPEEDUP_FLOOR for r in REGIMES)
    return dict(schema=SCHEMA,source_type="synthetic_cpu_recurrent_score_network",
                authentic_model="NOT_RUN",gpu_measured="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                environment=dict(python=platform.python_version(),numpy=np.__version__,blas_threads=1),
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),
                            layers=LAYERS,dimension=DIMENSION,vocab=VOCAB,queries=QUERIES,
                            trials=TRIALS,exact_greedy_required=True,speedup_floor=SPEEDUP_FLOOR),
                setup=setup,cases=cases,summary=summary,
                decision="CONDITIONAL_CPU_FEASIBILITY_ONLY" if qualified else "NO_GO_SYNTHETIC_SCREEN",
                caveat="Uses conservative future-layer norm bounds on artificial network, not real transformer; no model/GPU throughput measured.")


if __name__=="__main__":
    print("G102_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
