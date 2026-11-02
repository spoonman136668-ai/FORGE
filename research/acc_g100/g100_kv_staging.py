"""G100 synthetic causal cold-KV staging cost model; not measured GPU time.

Frozen: docs/research/acc_g91_g106/G100_KV_STAGING_PREREG_20261031.md
"""
from collections import Counter, OrderedDict
import hashlib
import json
import math

import numpy as np

SCHEMA="forge.acc.g100.cold_kv_staging_analytic_v1"
SEEDS=(10001,10002,10003)
REGIMES=("iid","cycle16")
POLICIES=("bigram","last_page")
PAGES=64
PAGE_BYTES=4096
CACHE_CAPACITY=8
TRAIN=128
EVAL=384
TRANSFER_TIME=.30
COMPUTE_TIME=1.
PREDICTOR_COST=.01
SPEEDUP_FLOOR=1.15
TRANSFER_CEILING=1.20


def make_requests(seed,regime):
    rng=np.random.default_rng(seed)
    if regime=="iid":
        events=rng.integers(0,PAGES,TRAIN+EVAL).tolist()
    elif regime=="cycle16":
        cycle=[int(x) for x in rng.choice(PAGES,size=16,replace=False)]
        offset=int(rng.integers(0,16))
        events=[cycle[(offset+i)%16] for i in range(TRAIN+EVAL)]
    else:
        raise ValueError("UNKNOWN_REGIME")
    return events


def digest(pages):
    return hashlib.sha256(bytes(pages)).hexdigest()


def fit_bigram(train):
    counts={}
    for current,successor in zip(train,train[1:]):
        counts.setdefault(current,Counter())[successor]+=1
    return {page:min(row,key=lambda next_page:(-row[next_page],next_page))
            for page,row in counts.items()}


def predict(policy,current,learned):
    if policy=="last_page":
        return current
    if policy=="bigram":
        return learned.get(current,current)
    raise ValueError("UNREGISTERED_POLICY")


def touch(cache,page):
    """Exact eight-slot LRU: do not evict until full, no hidden oracle."""
    was_present=page in cache
    if was_present:
        cache.move_to_end(page)
    else:
        if len(cache)>=CACHE_CAPACITY:
            cache.popitem(last=False)
        cache[page]=None
    return was_present


def simulate(requests,train,policy=None):
    cache=OrderedDict()
    learned=fit_bigram(train) if policy is not None else None
    total_time=0.
    misses=0
    prefetches=0
    credits=0
    pending_credit=None
    served=[]
    eviction_count=0
    for pos,page in enumerate(requests):
        had_page=page in cache
        if pending_credit is not None and page==pending_credit and had_page:
            credits+=1
        if not had_page:
            misses+=1
            total_time+=TRANSFER_TIME
        touch(cache,page)
        served.append(page)
        total_time+=COMPUTE_TIME
        if policy is not None:
            total_time+=PREDICTOR_COST
            next_page=predict(policy,page,learned)
            if not (0<=next_page<PAGES):
                raise AssertionError("INVALID_PREFETCH_TARGET")
            pending_credit=None
            if next_page not in cache:
                prefetches+=1
                if len(cache)>=CACHE_CAPACITY:
                    eviction_count+=1
                touch(cache,next_page)
                # At most one transfer per event; only remaining uncovered
                # part of prefetch costs extra outside this compute window.
                total_time+=max(0.,TRANSFER_TIME-COMPUTE_TIME)
                pending_credit=next_page
    transfers=misses+prefetches
    return dict(
        served_exactly=served==list(requests),events=len(served),
        demand_misses=misses,prefetch_transfers=prefetches,
        next_event_prefetch_hits=credits, speculative_evictions=eviction_count,
        transfer_pages=transfers,transfer_bytes=transfers*PAGE_BYTES,
        model_time_units=total_time,
    )


def screen():
    cases=[]
    frozen_digests=[]
    for seed in SEEDS:
        for regime in REGIMES:
            stream=make_requests(seed,regime)
            training=stream[:TRAIN]
            heldout=stream[TRAIN:]
            assert len(heldout)==EVAL
            baseline=simulate(heldout,training)
            frozen_digests.append(dict(
                seed=seed,regime=regime,training_sha256=digest(training),
                heldout_sha256=digest(heldout),
            ))
            for policy in POLICIES:
                candidate=simulate(heldout,training,policy)
                parity=(baseline["served_exactly"] and candidate["served_exactly"] and
                        baseline["events"]==EVAL and candidate["events"]==EVAL)
                amplification=candidate["transfer_bytes"]/max(baseline["transfer_bytes"],1)
                speedup=baseline["model_time_units"]/candidate["model_time_units"]
                exact=bool(parity and all(math.isfinite(x) for x in (speedup,amplification)))
                cases.append(dict(
                    seed=seed,regime=regime,policy=policy,
                    training_sha256=digest(training),heldout_sha256=digest(heldout),
                    exact_service_parity=exact,
                    baseline=baseline,candidate=candidate,
                    speedup_model_units=speedup,
                    transfer_amplification=amplification,
                    byte_budget_met=amplification<=TRANSFER_CEILING,
                ))
    if len(cases)!=12 or len(frozen_digests)!=6:
        raise AssertionError("CASE_COUNT_DRIFT")
    summary={}
    passing=[]
    for policy in POLICIES:
        same=[c for c in cases if c["policy"]==policy]
        grouped={}
        for regime in REGIMES:
            subset=[c for c in same if c["regime"]==regime]
            if len(subset)!=3:
                raise AssertionError("REGIME_COUNT_DRIFT")
            grouped[regime]=dict(
                cases=3,
                median_modeled_speedup=float(np.median([c["speedup_model_units"] for c in subset])),
                max_transfer_amplification=max(c["transfer_amplification"] for c in subset),
                exact_page_parity=all(c["exact_service_parity"] for c in subset),
                byte_budget_met=all(c["byte_budget_met"] for c in subset),
            )
        qualified=all(grouped[r]["exact_page_parity"] and
                      grouped[r]["byte_budget_met"] and
                      grouped[r]["median_modeled_speedup"]>=SPEEDUP_FLOOR for r in REGIMES)
        summary[policy]=dict(regimes=grouped,screening_pass=qualified)
        if qualified:
            passing.append(policy)
    return dict(schema=SCHEMA,source_type="deterministic_cost_model_not_wall_time",
                genuine_gpu_transfer="NOT_MEASURED",authentic_model="NOT_RUN",
                scientific_acceptance="NOT_GRANTED",
                frozen=dict(seeds=list(SEEDS),regimes=list(REGIMES),policies=list(POLICIES),
                            page_count=PAGES,page_bytes=PAGE_BYTES,cache_capacity=CACHE_CAPACITY,
                            training_events=TRAIN,heldout_events=EVAL,compute_time_units=COMPUTE_TIME,
                            transfer_time_units=TRANSFER_TIME,predictor_cost_units=PREDICTOR_COST,
                            modeled_speedup_floor=SPEEDUP_FLOOR,
                            transfer_amplification_ceiling=TRANSFER_CEILING),
                digests=frozen_digests,cases=cases,summary=summary,
                decision="CONDITIONAL_ANALYTIC_FEASIBILITY_ONLY" if passing else "NO_GO_ANALYTICAL",
                caveat="A simulated cost model with one speculative DMA transfer overlapped per event; actual DMA, cache coherency, contention and GPU token time NOT measured.")


if __name__=="__main__":
    print("G100_JSON="+json.dumps(screen(),sort_keys=True,separators=(",",":"),allow_nan=False))
