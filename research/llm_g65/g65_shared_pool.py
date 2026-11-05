#!/usr/bin/env python3
"""G65 authentic GPT-2: reclaim prefill worker slots inside matched CPU waves.

The shared B-worker executor runs both prefix producers and decoders, so a
producer's freed slot can run a waiting decoder in the SAME wave. All costs
and failures are retained; no scientific, production or controller authority.
"""
import concurrent.futures
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import threading
import time

REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
PREREG_SHA="c5c9ad2b8f08b561bd7d077366707554b9e436a1"
BUDGETS=(2,3)
ARMS=("no_cache","serialized_prefill","fixed_reserved","shared_forward_pool")
STREAMS={"high_locality":(0,0,0,0,1,1),
         "unique_only":(0,1,2,3,4,5),
         "thrash":(0,1,2,0,1,2)}
REPEATS=2
TOKENS=16
ENTRY_CAP=2
KV_BYTES_CAP=42_000_000
THRESHOLDS={"high_b3_vs_no_cache":1.05,"high_b3_vs_fixed_reserved":1.05,
            "high_b2_vs_no_cache":0.98,"unique_b3_vs_no_cache":0.98,
            "thrash_b3_vs_no_cache":0.98}
EXPECTED={"high_locality":{2:(False,True,False),3:(False,True)},
          "unique_only":{2:(False,False,False),3:(False,False)},
          "thrash":{2:(False,False,False),3:(False,False)}}

def load_module(name,relative):
    p=Path(__file__).resolve().parents[1]/relative
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def overlap(a,b,c,d):
    return max(0.0,min(b,d)-max(a,c))

class TaskTracker:
    """Actual executing task concurrency; counts prefix and decoder forwards."""
    def __init__(self):
        self.lock=threading.Lock()
        self.running=0
        self.maximum=0
        self.events=[]
    def start(self,kind,request):
        with self.lock:
            self.running+=1
            self.maximum=max(self.maximum,self.running)
            return time.perf_counter()
    def end(self,kind,request,begin):
        ended=time.perf_counter()
        with self.lock:
            self.running-=1
            if self.running<0:
                raise RuntimeError("TASK_CONCURRENCY_COUNTER_UNDERFLOW")
            self.events.append({"kind":kind,"request":request,
                                "start":begin,"end":ended})
        return ended

def route_at_wave(history,current):
    import collections
    counted=collections.Counter(history)
    return any(counted[f]>=2 for f in current)

def expected_routes(pattern,budget):
    seen=[]
    routes=[]
    for start in range(0,len(pattern),budget):
        now=pattern[start:start+budget]
        routes.append(route_at_wave(seen,now))
        seen.extend(now)
    return tuple(routes)

def test_contract():
    assert BUDGETS==(2,3) and REPEATS==2 and TOKENS==16
    assert len(ARMS)==4 and len(STREAMS)==3
    assert (ENTRY_CAP,KV_BYTES_CAP)==(2,42_000_000)
    assert THRESHOLDS=={"high_b3_vs_no_cache":1.05,
            "high_b3_vs_fixed_reserved":1.05,
            "high_b2_vs_no_cache":0.98,
            "unique_b3_vs_no_cache":0.98,
            "thrash_b3_vs_no_cache":0.98}
    assert all(expected_routes(p,b)==EXPECTED[n][b]
               for n,p in STREAMS.items() for b in BUDGETS)
    assert overlap(1,3,2,4)==1.0
    assert overlap(0,1,2,3)==0.0

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoTokenizer, AutoModelForCausalLM
    test_contract()
    g55=load_module("g55_g65","llm_g55/g55_gpt2_controls.py")
    g59=load_module("g59_g65","llm_g59/g59_adaptive.py")
    g60=load_module("g60_g65","llm_g60/g60_concurrent.py")
    g62=load_module("g62_g65","llm_g62/g62_singleflight.py")
    g64=load_module("g64_g65","llm_g64/g64_conditional.py")
    if not (g55.REV==g59.MODEL_REV==g60.REV==g62.REV==g64.MODEL_REV==REV and
            g55.WEIGHT_SHA==g59.MODEL_SHA==g60.WEIGHT_SHA==g62.WEIGHTS_SHA==g64.MODEL_SHA==WEIGHTS_SHA):
        raise RuntimeError("FROZEN_GPT2_IDENTITY_DRIFT")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    receipt={
        "gate":"G65","classification":"MATCHED_CPU_BUDGET_SHARED_POOL_RESEARCH_ONLY",
        "source_sha":os.getenv("GITHUB_SHA","UNSET"),
        "preregistration_commit":PREREG_SHA,
        "model_revision":REV,"model_safetensors_sha256":WEIGHTS_SHA,
        "torch":torch.__version__,"transformers":transformers.__version__,
        "platform":platform.platform(),"budgets":BUDGETS,
        "arms":ARMS,"streams":STREAMS,"repetitions":REPEATS,
        "tokens_per_request":TOKENS,
        "retained_prefix_kv_cap_bytes":KV_BYTES_CAP,"entry_cap":ENTRY_CAP,
        "thresholds":THRESHOLDS,"expected_routes":EXPECTED,
        "correctness":"UNVERIFIED","engineering":"UNVERIFIED",
        "performance_screen":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED",
        "promotion_allowed":False,
        "limitations":[
            "One hosted Linux CPU instance; affinity is logical CPU allocation, not energy budget",
            "Wave-completion scheduler and synthetic pretokenized prompts, not production continuous batching",
            "PyTorch threads capped to 1, total CPU system load beyond process not controlled",
            "Sampled RSS is not exact peak RSS; KV limit includes retained prefix tensors only",
            "No natural request holdout, independently replicated host, GPU or native Wingless/Yggdrasil model"
        ]
    }
    try:
        root,file_records=g55.stage()
        receipt["model_files"]=file_records
        receipt["model_manifest_sha256"]=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                    trust_remote_code=False,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("GPT2_ARCHITECTURE_OR_FLOAT32_MISMATCH")
        def input_ids(text):
            return tokenizer(text,add_special_tokens=False,return_tensors="pt")["input_ids"]
        prefix=[input_ids(g55.PREFIX+f" Family {i} has a unique context marker.") for i in range(6)]
        suffix=[input_ids(f" Request {i}: state the bounded validation requirement.") for i in range(6)]
        keys=[tuple(p.flatten().tolist()) for p in prefix]
        if len(set(keys))!=6:
            raise RuntimeError("EXACT_PREFIX_COLLISION")
        if max(x.shape[1] for x in prefix)+max(x.shape[1] for x in suffix)+TOKENS>model.config.n_positions:
            raise RuntimeError("GPT2_CONTEXT_LIMIT")
        receipt["prefix_sha256"]=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in prefix]
        proc=psutil.Process()
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("CPU_AFFINITY_UNAVAILABLE")
        allowed=proc.cpu_affinity()
        if len(allowed)<3:raise RuntimeError("INSUFFICIENT_CPU_AFFINITY")
        receipt["initial_cpu_affinity"]=allowed

        def prefix_bytes(family):
            return g62.planned_cache_bytes(model,len(keys[family]))
        def prefill(family,req,tracker):
            started=tracker.start("prefill",req)
            try:
                with torch.inference_mode():
                    cache=model(input_ids=prefix[family],use_cache=True).past_key_values
                actual=sum(x.numel()*x.element_size() for layer in cache for x in layer)
                if actual!=prefix_bytes(family):raise RuntimeError("KV_BYTE_IDENTITY_MISMATCH")
                ended=time.perf_counter()
                return {"family":family,"cache":cache,"start":started,"end":ended,
                        "bytes":actual,"request":req}
            finally:
                tracker.end("prefill",req,started)

        def decode(first,future,plen,family,req,arrival,tracker):
            started=tracker.start("decoder",req)
            try:
                opts={"input_ids":first,"use_cache":True}
                context=int(first.shape[1])+plen
                waited=0.0
                copied=0.0
                if future is not None:
                    t=time.perf_counter()
                    payload=future.result(timeout=60)
                    waited=time.perf_counter()-t
                    if payload["family"]!=family:
                        raise RuntimeError("FUTURE_PREFIX_FAMILY_MISMATCH")
                    t=time.perf_counter()
                    opts["past_key_values"]=copy.deepcopy(payload["cache"])
                    copied=time.perf_counter()-t
                    opts["attention_mask"]=torch.ones((1,context),dtype=torch.long)
                with torch.inference_mode():
                    out=model(**opts)
                    past,logits=out.past_key_values,out.logits[:,-1,:]
                    tokens=[]
                    for step in range(TOKENS):
                        next_id=logits.argmax(-1,keepdim=True)
                        tokens.append(next_id)
                        if step+1<TOKENS:
                            out=model(input_ids=next_id,past_key_values=past,
                                attention_mask=torch.ones((1,context+step+1),dtype=torch.long),
                                use_cache=True)
                            past,logits=out.past_key_values,out.logits[:,-1,:]
                ended=time.perf_counter()
                return torch.cat(tokens,dim=1),{
                    "request":req,"family":family,"start":started,"end":ended,
                    "arrival":arrival,"latency_s":ended-arrival,
                    "future_wait_s":waited,"kv_copy_s":copied
                }
            finally:
                tracker.end("decoder",req,started)

        def run_stream(pattern,arm,budget):
            if arm not in ARMS or budget not in BUDGETS:
                raise RuntimeError("OUT_OF_FROZEN_SCOPE")
            if proc.cpu_affinity()!=allowed[:budget]:
                raise RuntimeError("CPU_AFFINITY_CONTROL_FAILURE")
            policy=g59.Policy("no_cache" if arm=="no_cache" else "adaptive")
            tracker=TaskTracker()
            outputs=[None]*len(pattern)
            request_profile=[None]*len(pattern)
            arrival_history=[]
            route_decisions=[]
            pending_count=0
            reserved_peak=0
            cache_trace=[]
            switching_cost=0.0
            pool_setup=0.0
            pool_teardown=0.0
            producers=[]
            observations=[]
            baseline_start=time.perf_counter()
            cpu_start=time.process_time()
            with g60.RSSMonitor(proc) as rss:
                for wave in range(0,len(pattern),budget):
                    arrivals=pattern[wave:wave+budget]
                    decision_start=time.perf_counter()
                    active=arm in ("fixed_reserved","shared_forward_pool") and route_at_wave(arrival_history,arrivals)
                    if arm in ("fixed_reserved","shared_forward_pool") and not active:
                        policy.count["evictions"]+=len(policy.cache)
                        policy.cache.clear()
                    switching_cost+=time.perf_counter()-decision_start
                    route_decisions.append(active)
                    fixed=arm=="fixed_reserved" and active
                    shared=arm=="shared_forward_pool" and active
                    decoder_workers=budget-1 if fixed else budget
                    producer_workers=1 if fixed else 0
                    if arm=="shared_forward_pool" and active:
                        # One B-slot task pool handles all model forwards;
                        # prefix work has NO permanently reserved worker slot.
                        decoder_workers=budget
                        producer_workers=0
                    if decoder_workers+producer_workers!=budget:
                        raise RuntimeError("UNEQUAL_FORWARD_WORKER_ALLOCATION")
                    if arm=="shared_forward_pool" and active and decoder_workers!=budget:
                        raise RuntimeError("SLOT_RELEASE_NOT_ALLOCATED")
                    setup_at=time.perf_counter()
                    decode_pool=concurrent.futures.ThreadPoolExecutor(max_workers=decoder_workers)
                    prefill_pool=(concurrent.futures.ThreadPoolExecutor(max_workers=1)
                                  if fixed else None)
                    pool_setup+=time.perf_counter()-setup_at
                    wave_pending=[]
                    wave_prefills=[]
                    wave_events=[]
                    try:
                        for req in range(wave,min(wave+budget,len(pattern))):
                            family=pattern[req]
                            key=keys[family]
                            arrived=time.perf_counter()
                            action,future=policy.begin(key,ENTRY_CAP)
                            can_admit=arm=="serialized_prefill" or active
                            if action=="admit" and can_admit:
                                if any(f["key"]==key and not f["future"].done() for f in wave_prefills):
                                    raise RuntimeError("DUPLICATE_IN_FLIGHT_PREFIX_PRODUCER")
                                if fixed:
                                    new_future=prefill_pool.submit(prefill,family,req,tracker)
                                elif shared:
                                    # Crucial ordering: producer enqueued BEFORE
                                    # decoder that could need to wait on it.
                                    new_future=decode_pool.submit(prefill,family,req,tracker)
                                else:
                                    new_future=concurrent.futures.Future()
                                    try:new_future.set_result(prefill(family,req,tracker))
                                    except BaseException as exc:
                                        new_future.set_exception(exc);raise
                                future=new_future
                                wave_prefills.append({"key":key,"future":future,"req":req})
                                producers.append(future)
                                policy.insert(key,future,ENTRY_CAP)
                            elif action=="admit":
                                future=None
                                action="skip"
                            elif action=="hit":
                                if future is None or not can_admit:
                                    raise RuntimeError("ILLEGAL_CACHE_HIT")
                            elif action!="skip":
                                raise RuntimeError("UNKNOWN_ADMISSION_ACTION")
                            policy.finish(key,ENTRY_CAP,action)
                            planned=sum(g62.planned_cache_bytes(model,len(k)) for k in policy.cache.keys())
                            if planned>KV_BYTES_CAP or len(policy.cache)>ENTRY_CAP:
                                raise RuntimeError("RETAINED_KV_CAP_BREACH")
                            reserved_peak=max(reserved_peak,planned)
                            if future is not None:
                                first=suffix[req]
                                plen=len(key)
                            else:
                                first=torch.cat((prefix[family],suffix[req]),dim=1)
                                plen=0
                            submitted=time.perf_counter()
                            fut=decode_pool.submit(decode,first,future,plen,family,req,arrived,tracker)
                            wave_pending.append({"future":fut,"req":req,"submitted":submitted,
                                                 "family":family,"action":action})
                            cache_trace.append({"request":req,"family":family,"route":active,
                                               "action":action,"entries":len(policy.cache),
                                               "retained_kv_bytes":planned,
                                               "decoder_pool_size":decoder_workers,
                                               "separate_prefill_pool_size":producer_workers})
                        for entry in wave_pending:
                            out,profile=entry["future"].result(timeout=150)
                            outputs[entry["req"]]=out
                            request_profile[entry["req"]]=profile
                            wave_events.append({"request":entry["req"],
                                                "submitted":entry["submitted"],
                                                "start":profile["start"],"end":profile["end"],
                                                "family":profile["family"]})
                        for producer in wave_prefills:
                            payload=producer["future"].result(timeout=60)
                            observations.append({"request":producer["req"],"family":payload["family"],
                                "start":payload["start"],"end":payload["end"],
                                "actual_bytes":payload["bytes"],
                                "wave":wave})
                    finally:
                        t=time.perf_counter()
                        decode_pool.shutdown(wait=True,cancel_futures=False)
                        if prefill_pool is not None:
                            prefill_pool.shutdown(wait=True,cancel_futures=False)
                        pool_teardown+=time.perf_counter()-t
                    # Mechanical evidence that a queued decoder can occupy a
                    # forward slot AFTER a prefix producer released its slot.
                    for p in observations:
                        if p["wave"]!=wave:continue
                        overlapping=[v for v in wave_events if v["family"]!=p["family"] and
                            overlap(p["start"],p["end"],v["start"],v["end"])>0]
                        if overlapping:
                            pending_count+=1
                        # A decoder submitted before this producer finishes but
                        # starting AFTER its end illustrates slot reuse.
                        released=[v for v in wave_events
                            if v["submitted"]<p["end"]<=v["start"]
                            and v["start"]<max(x["end"] for x in wave_events)]
                        if shared and overlapping and released:
                            observations[-1]["released_slot_used_by_decoder"]=True
                    arrival_history.extend(arrivals)
                wall=time.perf_counter()-baseline_start
                process_cpu=time.process_time()-cpu_start
            if tracker.running!=0 or tracker.maximum>budget:
                raise RuntimeError("MODEL_FORWARD_WORKER_BUDGET_EXCEEDED")
            if not all(x is not None for x in outputs):
                raise RuntimeError("MISSING_GREEDY_OUTPUT")
            if policy.count["hits"]+policy.count["misses"]!=len(pattern):
                raise RuntimeError("HIT_MISS_ACCOUNTING_INVALID")
            if arm=="no_cache" and (policy.count["admissions"] or policy.count["hits"] or reserved_peak):
                raise RuntimeError("NO_CACHE_BASELINE_CONTAMINATION")
            if any(x["retained_kv_bytes"]>KV_BYTES_CAP or x["entries"]>ENTRY_CAP for x in cache_trace):
                raise RuntimeError("PREFIX_CACHE_RESOURCE_LIMIT")
            if arm in ("fixed_reserved","shared_forward_pool"):
                actual=tuple(route_decisions)
                if actual!=expected_routes(pattern,budget):
                    raise RuntimeError("ROUTER_DECISION_MISMATCH")
                if not any(actual):
                    if observations or reserved_peak or any(x["separate_prefill_pool_size"] for x in cache_trace):
                        raise RuntimeError("NEGATIVE_WAVE_WASTED_PREFILL")
            released=any(x.get("released_slot_used_by_decoder",False) for x in observations)
            return outputs,{
                "whole_wall_s":wall,"process_cpu_s":process_cpu,
                "throughput_generated_tokens_s":len(pattern)*TOKENS/wall,
                "affinity":proc.cpu_affinity(),"forward_worker_budget":budget,
                "maximum_observed_active_forward_tasks":tracker.maximum,
                "task_intervals":tracker.events,
                "sampled_rss_max_bytes":max(rss.samples),"rss_sample_count":len(rss.samples),
                "max_retained_prefix_kv_bytes":reserved_peak,
                "cache_counts":dict(policy.count),"route_by_wave":route_decisions,
                "cache_trace":cache_trace,
                "producer_count":len(observations),"prefix_intervals":observations,
                "observed_unrelated_prefill_decoder_overlap":pending_count>0,
                "released_pool_slot_used_in_wave":released,
                "switching_wall_s":switching_cost,
                "pool_setup_wall_s":pool_setup,"pool_shutdown_wall_s":pool_teardown,
                "per_request":request_profile,
                "median_latency_s":statistics.median(x["latency_s"] for x in request_profile),
                "p95_sample_latency_s":max(x["latency_s"] for x in request_profile)
            }

        def same_tokens(baseline,other,context):
            if len(baseline)!=len(other) or any(not torch.equal(x,y) for x,y in zip(baseline,other)):
                raise RuntimeError("GREEDY_GENERATION_TOKEN_MISMATCH_"+context)

        try:
            for budget in BUDGETS:
                proc.cpu_affinity(allowed[:budget])
                for name,pattern in STREAMS.items():
                    baseline,_=run_stream(pattern,"no_cache",budget)
                    sha=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in baseline]
                    for arm in ARMS:
                        out,_=run_stream(pattern,arm,budget)
                        same_tokens(baseline,out,"correctness_"+name+"_"+arm)
                        run_stream(pattern,arm,budget)   # warmed before timed trials
                    trials=[]
                    for repetition in range(REPEATS):
                        order=list(ARMS[repetition:]+ARMS[:repetition])
                        if repetition%2:order.reverse()
                        trial={}
                        for arm in order:
                            out,info=run_stream(pattern,arm,budget)
                            same_tokens(baseline,out,name+"_"+arm+"_trial_"+str(repetition))
                            if info["affinity"]!=allowed[:budget] or info["forward_worker_budget"]!=budget:
                                raise RuntimeError("CPU_AFFINITY_NOT_MATCHED")
                            trial[arm]=info
                        trials.append({"trial":repetition+1,"order":order,"arms":trial,
                            "shared_over_no_cache":trial["no_cache"]["whole_wall_s"]/trial["shared_forward_pool"]["whole_wall_s"],
                            "shared_over_fixed_reserved":trial["fixed_reserved"]["whole_wall_s"]/trial["shared_forward_pool"]["whole_wall_s"],
                            "shared_over_serial":trial["serialized_prefill"]["whole_wall_s"]/trial["shared_forward_pool"]["whole_wall_s"]})
                    receipt.setdefault("cohorts",{}).setdefault(name,{})["budget_"+str(budget)]={
                        "reference_tokens_sha256":sha,"trials":trials,
                        "median_shared_over_no_cache":statistics.median(t["shared_over_no_cache"] for t in trials),
                        "median_shared_over_fixed_reserved":statistics.median(t["shared_over_fixed_reserved"] for t in trials),
                        "median_shared_over_serial":statistics.median(t["shared_over_serial"] for t in trials)}
        finally:
            proc.cpu_affinity(allowed)
        h2=receipt["cohorts"]["high_locality"]["budget_2"]
        h3=receipt["cohorts"]["high_locality"]["budget_3"]
        u3=receipt["cohorts"]["unique_only"]["budget_3"]
        t3=receipt["cohorts"]["thrash"]["budget_3"]
        observed_release=any(t["arms"]["shared_forward_pool"]["released_pool_slot_used_in_wave"] for t in h3["trials"])
        observed_overlap=any(t["arms"]["shared_forward_pool"]["observed_unrelated_prefill_decoder_overlap"] for t in h3["trials"])
        receipt["released_slot_observed"]=observed_release
        receipt["independent_prefill_decode_overlap_observed"]=observed_overlap
        receipt["correctness"]="PASS"
        receipt["engineering"]="PASS" if observed_release and observed_overlap else "FAIL"
        receipt["performance_screen"]="PASS" if (
            receipt["engineering"]=="PASS" and
            h3["median_shared_over_no_cache"]>=THRESHOLDS["high_b3_vs_no_cache"] and
            h3["median_shared_over_fixed_reserved"]>=THRESHOLDS["high_b3_vs_fixed_reserved"] and
            h2["median_shared_over_no_cache"]>=THRESHOLDS["high_b2_vs_no_cache"] and
            u3["median_shared_over_no_cache"]>=THRESHOLDS["unique_b3_vs_no_cache"] and
            t3["median_shared_over_no_cache"]>=THRESHOLDS["thrash_b3_vs_no_cache"]
        ) else "FAIL"
    except Exception as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g65_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print(json.dumps({k:receipt.get(k) for k in
            ("gate","correctness","engineering","performance_screen",
             "released_slot_observed","independent_prefill_decode_overlap_observed","error")},sort_keys=True))
        for name,budgets in receipt.get("cohorts",{}).items():
            for budget,row in budgets.items():
                print(json.dumps({"cohort":name,"budget":budget,
                    "shared_over_no_cache":row["median_shared_over_no_cache"],
                    "shared_over_fixed_reserved":row["median_shared_over_fixed_reserved"],
                    "shared_over_serial":row["median_shared_over_serial"]},sort_keys=True))

if __name__=="__main__":
    main()
