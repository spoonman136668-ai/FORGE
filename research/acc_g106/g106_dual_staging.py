"""G106 joint weight+KV cold staging, shared-channel analytic model.

Frozen protocol:
docs/research/acc_g91_g106/G106_DUAL_STAGING_PREREG_20261031.md
Not actual GPU transfer, CUDA timing, or authentic LLM inference.
"""
from collections import Counter, OrderedDict
import hashlib
import json
import math

import numpy as np

SCHEMA="forge.acc.g106.dual_resource_staging_analytic_v1"
SEEDS=(10601,10602,10603)
REGIMES=("iid","coupled_cycle")
POLICIES=("bigram","last_page")
WEIGHT_PAGES,KV_PAGES=32,64
WEIGHT_CAPACITY,KV_CAPACITY=4,8
WEIGHT_BYTES,KV_BYTES=16384,4096
WEIGHT_TRANSFER,KV_TRANSFER=.20,.30
COMPUTE_TIME,PREDICTOR_TIME=1.,.02
TRAIN,EVAL=128,384
SPEEDUP_FLOOR,TRAFFIC_CEILING=1.15,1.20


def make_requests(seed,regime):
    rng=np.random.default_rng(seed)
    if regime=="iid":
        weight=rng.integers(0,WEIGHT_PAGES,TRAIN+EVAL).tolist()
        kv=rng.integers(0,KV_PAGES,TRAIN+EVAL).tolist()
    elif regime=="coupled_cycle":
        weight_pool=[int(x) for x in rng.choice(WEIGHT_PAGES,size=8,replace=False)]
        kv_pool=[int(x) for x in rng.choice(KV_PAGES,size=16,replace=False)]
        woff=int(rng.integers(0,8))
        koff=int(rng.integers(0,16))
        weight=[weight_pool[(woff+i)%8] for i in range(TRAIN+EVAL)]
        kv=[kv_pool[(koff+i)%16] for i in range(TRAIN+EVAL)]
    else:
        raise ValueError("UNKNOWN_REGIME")
    return list(zip(weight,kv))


def digest(sequence):
    return hashlib.sha256(bytes(x for pair in sequence for x in pair)).hexdigest()


def fit_bigram(training,index):
    counts={}
    for current,successor in zip(training,training[1:]):
        a,b=current[index],successor[index]
        counts.setdefault(a,Counter())[b]+=1
    return {old:min(row,key=lambda value:(-row[value],value))
            for old,row in counts.items()}


def predict(policy,current,trained):
    if policy=="last_page":
        return current
    if policy=="bigram":
        return trained.get(current,current)
    raise ValueError("UNKNOWN_POLICY")


def touch(cache,page,capacity):
    hit=page in cache
    if hit:
        cache.move_to_end(page)
        return True,False
    evicted=False
    if len(cache)>=capacity:
        cache.popitem(last=False)
        evicted=True
    cache[page]=None
    return False,evicted


def simulate(test,training,policy=None):
    weight_cache,kv_cache=OrderedDict(),OrderedDict()
    weight_model=fit_bigram(training,0) if policy=="bigram" else {}
    kv_model=fit_bigram(training,1) if policy=="bigram" else {}
    weight_misses=kv_misses=weight_prefetch=kv_prefetch=0
    weight_evictions=kv_evictions=weight_credits=kv_credits=0
    pending_weight=pending_kv=None
    clock=0.
    serviced=[]
    for w,k in test:
        weight_hit=w in weight_cache
        kv_hit=k in kv_cache
        if weight_hit and w==pending_weight:
            weight_credits+=1
        if kv_hit and k==pending_kv:
            kv_credits+=1
        if not weight_hit:
            weight_misses+=1
            clock+=WEIGHT_TRANSFER
        if not kv_hit:
            kv_misses+=1
            clock+=KV_TRANSFER
        touch(weight_cache,w,WEIGHT_CAPACITY)
        touch(kv_cache,k,KV_CAPACITY)
        serviced.append((w,k))
        clock+=COMPUTE_TIME
        if policy is not None:
            clock+=PREDICTOR_TIME
            next_w=predict(policy,w,weight_model)
            next_k=predict(policy,k,kv_model)
            if not (0<=next_w<WEIGHT_PAGES and 0<=next_k<KV_PAGES):
                raise AssertionError("PREFETCH_TARGET_OOB")
            pending_weight=pending_kv=None
            transfer_cost=0.
            if next_w not in weight_cache:
                weight_prefetch+=1
                _,evicted=touch(weight_cache,next_w,WEIGHT_CAPACITY)
                weight_evictions+=int(evicted)
                transfer_cost+=WEIGHT_TRANSFER
                pending_weight=next_w
            if next_k not in kv_cache:
                kv_prefetch+=1
                _,evicted=touch(kv_cache,next_k,KV_CAPACITY)
                kv_evictions+=int(evicted)
                transfer_cost+=KV_TRANSFER
                pending_kv=next_k
            # One shared DMA channel, at most two transfers; only current
            # compute window may overlap, never next event's demand costs.
            clock+=max(0.,transfer_cost-COMPUTE_TIME)
    weight_pages_transferred=weight_misses+weight_prefetch
    kv_pages_transferred=kv_misses+kv_prefetch
    weight_bytes=weight_pages_transferred*WEIGHT_BYTES
    kv_bytes=kv_pages_transferred*KV_BYTES
    return dict(events=len(serviced),exact_service=serviced==list(test),
                weight_demand_misses=weight_misses,kv_demand_misses=kv_misses,
                weight_prefetches=weight_prefetch,kv_prefetches=kv_prefetch,
                weight_prefetch_evictions=weight_evictions,
                kv_prefetch_evictions=kv_evictions,
                weight_next_event_credits=weight_credits,kv_next_event_credits=kv_credits,
                weight_transfer_bytes=weight_bytes,kv_transfer_bytes=kv_bytes,
                total_transfer_bytes=weight_bytes+kv_bytes,
                model_time_units=clock)


def screen():
    cases,digests=[],[]
    for seed in SEEDS:
        for regime in REGIMES:
            requests=make_requests(seed,regime)
            training,heldout=requests[:TRAIN],requests[TRAIN:]
            if len(heldout)!=EVAL:
                raise AssertionError("HELDOUT_COUNT_DRIFT")
            fingerprints=dict(seed=seed,regime=regime,
                              train_sha256=digest(training),
                              heldout_sha256=digest(heldout))
            digests.append(fingerprints)
            baseline=simulate(heldout,training)
            for policy in POLICIES:
                candidate=simulate(heldout,training,policy)
                if not baseline["weight_transfer_bytes"] or not baseline["kv_transfer_bytes"]:
                    raise AssertionError("NO_NEGATIVE_BASELINE_DEMAND")
                weight_amp=candidate["weight_transfer_bytes"]/baseline["weight_transfer_bytes"]
                kv_amp=candidate["kv_transfer_bytes"]/baseline["kv_transfer_bytes"]
                total_amp=candidate["total_transfer_bytes"]/baseline["total_transfer_bytes"]
                speedup=baseline["model_time_units"]/candidate["model_time_units"]
                valid=bool(baseline["exact_service"] and candidate["exact_service"] and
                           baseline["events"]==EVAL and candidate["events"]==EVAL and
                           all(math.isfinite(z) for z in (weight_amp,kv_amp,total_amp,speedup)))
                cases.append(dict(
                    **fingerprints,policy=policy,exact_service_parity=valid,
                    baseline=baseline,candidate=candidate,
                    speedup_model_units=speedup,weight_traffic_amplification=weight_amp,
                    kv_traffic_amplification=kv_amp,total_traffic_amplification=total_amp,
                    byte_budgets_met=all(z<=TRAFFIC_CEILING for z in
                                         (weight_amp,kv_amp,total_amp))))
    if len(cases)!=12 or len(digests)!=6:
        raise AssertionError("G106_CASE_COUNT_DRIFT")
    summary={}
    qualifies=False
    for policy in POLICIES:
        grouped={}
        for regime in REGIMES:
            data=[c for c in cases if c["policy"]==policy and c["regime"]==regime]
            if len(data)!=3:
                raise AssertionError("G106_REGIME_COUNT")
            grouped[regime]=dict(
                count=3,exact_service_parity=all(c["exact_service_parity"] for c in data),
                traffic_budget_met=all(c["byte_budgets_met"] for c in data),
                max_total_amplification=max(c["total_traffic_amplification"] for c in data),
                max_weight_amplification=max(c["weight_traffic_amplification"] for c in data),
                max_kv_amplification=max(c["kv_traffic_amplification"] for c in data),
                median_modeled_speedup=float(np.median([c["speedup_model_units"] for c in data])))
        qualifies_policy=all(grouped[r]["exact_service_parity"] and
                             grouped[r]["traffic_budget_met"] and
                             grouped[r]["median_modeled_speedup"]>=SPEEDUP_FLOOR
                             for r in REGIMES)
        summary[policy]=dict(regimes=grouped,screening_pass=qualifies_policy)
        qualifies=qualifies or qualifies_policy
    return dict(schema=SCHEMA,source_type="synthetic_two_resource_cache_cost_model",
                authentic_model="NOT_RUN",gpu_dma_timing="NOT_MEASURED",
                scientific_acceptance="NOT_GRANTED",
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),policies=list(POLICIES),
                            weight_pages=WEIGHT_PAGES,kv_pages=KV_PAGES,
                            weight_capacity=WEIGHT_CAPACITY,kv_capacity=KV_CAPACITY,
                            weight_page_bytes=WEIGHT_BYTES,kv_page_bytes=KV_BYTES,
                            weight_transfer_units=WEIGHT_TRANSFER,
                            kv_transfer_units=KV_TRANSFER,compute_time_units=COMPUTE_TIME,
                            predictor_time_units=PREDICTOR_TIME,
                            training_events=TRAIN,heldout_events=EVAL,
                            speedup_floor=SPEEDUP_FLOOR,traffic_ceiling=TRAFFIC_CEILING),
                digests=digests,cases=cases,summary=summary,
                decision="CONDITIONAL_ANALYTIC_FEASIBILITY_ONLY" if qualifies else "NO_GO_ANALYTICAL",
                caveat="Synthetic optimistic two-cache, single-DMA-lane normalized cost model; no real GPU, DMA, PCIe or model latency measured.")


if __name__=="__main__":
    print("G106_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
