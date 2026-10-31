#!/usr/bin/env python3
"""G64 frozen causal CPU resource router — real pretrained GPT-2, research only."""
import collections
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

MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
MODEL_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
PREREG="05be378a4db483cb1fc6763369f807d71b93dcad"
BUDGETS=(2,3)
ARMS=("no_cache","serialized_prefill","conditional_router")
STREAMS={"high_locality":(0,0,0,0,1,1),
         "unique_only":(0,1,2,3,4,5),
         "thrash":(0,1,2,0,1,2)}
REPEATS=2
TOKENS=16
ENTRY_CAP=2
KV_CAP=42_000_000
THRESHOLDS={"b3_high_over_no_cache":1.05,
            "b2_high_over_no_cache":0.98,
            "b3_unique_over_no_cache":0.98,
            "b3_thrash_over_no_cache":0.98,
            "b3_high_over_serial":1.00}
EXPECTED={"high_locality":{2:(False,True,False),3:(False,True)},
          "unique_only":{2:(False,False,False),3:(False,False)},
          "thrash":{2:(False,False,False),3:(False,False)}}

def load(name,relative):
    path=Path(__file__).resolve().parents[1]/relative
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def wave_route(prior,now):
    """May inspect current arrival and previous arrivals; never future traffic."""
    counts=collections.Counter(prior)
    return any(counts[f]>=2 for f in now)

def predicted_routes(pattern,budget):
    history=[]
    result=[]
    for start in range(0,len(pattern),budget):
        now=pattern[start:start+budget]
        result.append(wave_route(history,now))
        history.extend(now)
    return tuple(result)

def overlap(a,b,c,d):
    return max(0.,min(b,d)-max(a,c))

def self_test():
    assert ARMS==("no_cache","serialized_prefill","conditional_router")
    assert BUDGETS==(2,3) and TOKENS==16 and REPEATS==2
    assert (ENTRY_CAP,KV_CAP)==(2,42_000_000)
    for name,pattern in STREAMS.items():
        for budget in BUDGETS:
            assert predicted_routes(pattern,budget)==EXPECTED[name][budget]
    assert not wave_route([0],(0,))
    assert wave_route([0,0],(0,1))
    assert THRESHOLDS=={"b3_high_over_no_cache":1.05,
       "b2_high_over_no_cache":0.98,"b3_unique_over_no_cache":0.98,
       "b3_thrash_over_no_cache":0.98,"b3_high_over_serial":1.00}

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    self_test()
    g55=load("g55_64","llm_g55/g55_gpt2_controls.py")
    g59=load("g59_64","llm_g59/g59_adaptive.py")
    g60=load("g60_64","llm_g60/g60_concurrent.py")
    g62=load("g62_64","llm_g62/g62_singleflight.py")
    if not (g55.REV==g59.MODEL_REV==g60.REV==g62.REV==MODEL_REV
            and g55.WEIGHT_SHA==g59.MODEL_SHA==g60.WEIGHT_SHA==g62.WEIGHTS_SHA==MODEL_SHA):
        raise RuntimeError("AUTHENTIC_PRETRAINED_GPT2_IDENTITY_MISMATCH")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    result={
        "gate":"G64","kind":"SOURCE_FROZEN_CAUSAL_CPU_RESOURCE_ROUTER_RESEARCH_ONLY",
        "git_sha":os.getenv("GITHUB_SHA","UNSET"),
        "preregistration_commit":PREREG,
        "model_revision":MODEL_REV,"model_weights_sha256":MODEL_SHA,
        "torch":torch.__version__,"transformers":transformers.__version__,
        "host":platform.platform(),"budgets":BUDGETS,"arms":ARMS,"streams":STREAMS,
        "repeats":REPEATS,"tokens_per_request":TOKENS,
        "expected_router_routes":EXPECTED,"thresholds":THRESHOLDS,
        "correctness":"UNVERIFIED","performance_screen":"UNVERIFIED",
        "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
        "limitations":[
            "Single hosted CPU inference environment and synthetic pretokenized GPT-2",
            "Batch arrival waves bounded to available logical CPU budget",
            "Other concurrent CPU activity and energy are not controlled",
            "RSS samples at 10ms intervals are not process high-water",
            "No multi-user serving, optimized paged-KV, GPU, OS pressure or native model transfer"
        ]}
    try:
        model_dir,files=g55.stage()
        result["model_files"]=files
        result["model_manifest_sha256"]=hashlib.sha256((model_dir/"manifest.json").read_bytes()).hexdigest()
        tokenizer=AutoTokenizer.from_pretrained(str(model_dir),
                              trust_remote_code=False,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(model_dir),use_safetensors=True,
                                local_files_only=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("GPT2_ORIGINAL_DTYPE_OR_ARCH_DRIFT")
        def ids(s):
            return tokenizer(s,add_special_tokens=False,return_tensors="pt")["input_ids"]
        prefixes=[ids(g55.PREFIX+f" Family {n} has a unique context marker.") for n in range(6)]
        suffixes=[ids(f" Request {n}: state the bounded validation requirement.") for n in range(6)]
        keys=[tuple(p.flatten().tolist()) for p in prefixes]
        if len(set(keys))!=6:
            raise RuntimeError("PREFIX_TOKEN_COLLISION")
        if max(p.shape[1] for p in prefixes)+max(s.shape[1] for s in suffixes)+TOKENS>model.config.n_positions:
            raise RuntimeError("CONTEXT_LIMIT_VIOLATED")
        result["prefix_sha256"]=[hashlib.sha256(p.numpy().tobytes()).hexdigest() for p in prefixes]
        process=psutil.Process()
        if not hasattr(process,"cpu_affinity"):
            raise RuntimeError("CPU_AFFINITY_UNAVAILABLE")
        all_allowed=process.cpu_affinity()
        if len(all_allowed)<3:
            raise RuntimeError("CPU_BUDGET_UNAVAILABLE")
        result["allowed_cpu_affinity_before"]=all_allowed

        def prefill(family):
            start=time.perf_counter()
            with torch.inference_mode():
                cached=model(input_ids=prefixes[family],use_cache=True).past_key_values
            end=time.perf_counter()
            n=g62.planned_cache_bytes(model,len(keys[family]))
            if sum(x.numel()*x.element_size() for layer in cached for x in layer)!=n:
                raise RuntimeError("KV_PREFILL_FLOAT32_BYTE_MISMATCH")
            return {"past":cached,"family":family,"start":start,"end":end,"nbytes":n}

        def decode(initial,future,plen,family,arrival):
            start=time.perf_counter()
            future_wait=0.
            copy_seconds=0.
            kw={"input_ids":initial,"use_cache":True}
            total=initial.shape[1]+plen
            if future is not None:
                t=time.perf_counter()
                item=future.result(timeout=90)
                future_wait=time.perf_counter()-t
                if item["family"]!=family:raise RuntimeError("PREFIX_FUTURE_FAMILY_ERROR")
                t=time.perf_counter()
                kw["past_key_values"]=copy.deepcopy(item["past"])
                copy_seconds=time.perf_counter()-t
                kw["attention_mask"]=torch.ones((1,total),dtype=torch.long)
            with torch.inference_mode():
                out=model(**kw)
                state,logits=out.past_key_values,out.logits[:,-1,:]
                made=[]
                for n in range(TOKENS):
                    chosen=logits.argmax(-1,keepdim=True)
                    made.append(chosen)
                    if n<TOKENS-1:
                        out=model(input_ids=chosen,past_key_values=state,
                                  attention_mask=torch.ones((1,total+n+1),dtype=torch.long),
                                  use_cache=True)
                        state,logits=out.past_key_values,out.logits[:,-1,:]
            end=time.perf_counter()
            return torch.cat(made,dim=1),{
                "start":start,"end":end,"latency_from_arrival_s":end-arrival,
                "family":family,"cached_future_wait_s":future_wait,"kv_copy_s":copy_seconds}

        def execute(pattern,arm,budget):
            if arm not in ARMS or budget not in BUDGETS:
                raise RuntimeError("UNFROZEN_REQUEST_MODE")
            if process.cpu_affinity()!=all_allowed[:budget]:
                raise RuntimeError("CPU_AFFINITY_MISMATCH")
            policy=g59.Policy("no_cache" if arm=="no_cache" else "adaptive")
            outputs=[None]*len(pattern)
            times=[None]*len(pattern)
            cached_futures=[]
            trace=[]
            prev_history=[]
            max_kv=0
            switching_seconds=0.
            setup_seconds=0.
            teardown_seconds=0.
            prefill_intervals=[]
            maximum_forward_workers=0
            last_active=False
            start=time.perf_counter()
            cpu_start=time.process_time()
            with g60.RSSMonitor(process) as rss:
                for begin in range(0,len(pattern),budget):
                    current=pattern[begin:begin+budget]
                    decision_start=time.perf_counter()
                    active=(arm=="conditional_router" and wave_route(prev_history,current))
                    if active != last_active:
                        if last_active and not active:
                            # Switching off releases all retained prefix entries.
                            policy.count["evictions"]+=len(policy.cache)
                            policy.cache.clear()
                        switching_seconds+=time.perf_counter()-decision_start
                    last_active=active
                    if arm=="conditional_router" and not active and policy.cache:
                        raise RuntimeError("OFF_WAVE_HAS_RETAINED_CACHE")
                    decode_threads=(budget-1 if active else budget)
                    producer_threads=(1 if active else 0)
                    if decode_threads+producer_threads!=budget:
                        raise RuntimeError("TOTAL_FORWARD_WORKERS_NOT_MATCHED")
                    maximum_forward_workers=max(maximum_forward_workers,decode_threads+producer_threads)
                    decision_seconds=time.perf_counter()-decision_start
                    wave_start=time.perf_counter()
                    dec_pool=concurrent.futures.ThreadPoolExecutor(max_workers=decode_threads)
                    pref_pool=(concurrent.futures.ThreadPoolExecutor(max_workers=1)
                               if producer_threads else None)
                    setup_seconds+=time.perf_counter()-wave_start
                    pending=[]
                    try:
                        for idx in range(begin,min(begin+budget,len(pattern))):
                            family=pattern[idx]
                            key=keys[family]
                            arrival=time.perf_counter()
                            act,future=policy.begin(key,ENTRY_CAP)
                            admit_allowed=(arm=="serialized_prefill" or active)
                            if act=="admit" and admit_allowed:
                                if pref_pool:
                                    future=pref_pool.submit(prefill,family)
                                else:
                                    future=concurrent.futures.Future()
                                    try:future.set_result(prefill(family))
                                    except BaseException as err:
                                        future.set_exception(err)
                                        raise
                                cached_futures.append(future)
                                policy.insert(key,future,ENTRY_CAP)
                            elif act=="admit":
                                # Deliberate no-cache off wave; keep only observed causal history.
                                future=None
                                act="skip"
                            elif act=="hit":
                                if not admit_allowed or future is None:
                                    raise RuntimeError("OFF_WAVE_UNEXPECTED_CACHE_HIT")
                            elif act!="skip":
                                raise RuntimeError("UNRECOGNIZED_POLICY_ACTION")
                            policy.finish(key,ENTRY_CAP,act)
                            retained=sum(g62.planned_cache_bytes(model,len(p)) for p in policy.cache)
                            if retained>KV_CAP or len(policy.cache)>ENTRY_CAP:
                                raise RuntimeError("RETAINED_CACHE_BUDGET_BREACH")
                            max_kv=max(max_kv,retained)
                            if future is not None:
                                first=suffixes[idx]
                                plen=int(prefixes[family].shape[1])
                            else:
                                first=torch.cat((prefixes[family],suffixes[idx]),dim=1)
                                plen=0
                            trace.append({"index":idx,"family":family,"route_active":active,
                                "action":act,"retained_entries":len(policy.cache),
                                "retained_kv_bytes":retained,"decoder_workers":decode_threads,
                                "prefill_workers":producer_threads})
                            pending.append(dec_pool.submit(decode,first,future,plen,family,arrival))
                        for j,task in enumerate(pending):
                            output,prof=task.result(timeout=150)
                            index=begin+j
                            outputs[index]=output
                            times[index]=prof
                    finally:
                        td=time.perf_counter()
                        dec_pool.shutdown(wait=True,cancel_futures=False)
                        if pref_pool:
                            pref_pool.shutdown(wait=True,cancel_futures=False)
                        teardown_seconds+=time.perf_counter()-td
                    prev_history.extend(current)
                wall=time.perf_counter()-start
                cpu_used=time.process_time()-cpu_start
            for f in cached_futures:
                p=f.result()
                prefill_intervals.append({"family":p["family"],"start":p["start"],
                    "end":p["end"],"bytes":p["nbytes"],"wall_s":p["end"]-p["start"]})
            prefix_overlap=sum(overlap(p["start"],p["end"],d["start"],d["end"])
                for p in prefill_intervals for d in times if d["family"]!=p["family"])
            if any(v is None for v in outputs):
                raise RuntimeError("MISSING_GENERATED_OUTPUT")
            if policy.count["hits"]+policy.count["misses"]!=len(pattern):
                raise RuntimeError("HIT_MISS_ACCOUNTING_ERROR")
            if max_kv>KV_CAP or maximum_forward_workers>budget:
                raise RuntimeError("CAPACITY_BROKEN")
            if arm=="no_cache" and (policy.count["hits"] or policy.count["admissions"] or max_kv):
                raise RuntimeError("NO_CACHE_BASELINE_CONTAMINATED")
            if arm=="conditional_router" and any(t["route_active"] for t in trace):
                if not any(p["prefill_workers"]==1 for p in trace):
                    raise RuntimeError("ROUTING_ACTIVE_BUT_NO_PRODUCER_BUDGET")
            return outputs,{
                "wall_s":wall,"cpu_s":cpu_used,"throughput_tokens_s":len(pattern)*TOKENS/wall,
                "sampled_max_rss_bytes":max(rss.samples),"rss_samples":len(rss.samples),
                "median_request_latency_s":statistics.median(t["latency_from_arrival_s"] for t in times),
                "max_request_latency_s":max(t["latency_from_arrival_s"] for t in times),
                "max_kv_bytes":max_kv,"total_worker_budget":budget,
                "maximum_forward_workers":maximum_forward_workers,
                "prefill_producers":len(prefill_intervals),
                "prefill_unrelated_decoder_overlap_s":prefix_overlap,
                "switching_s":switching_seconds,"pool_setup_s":setup_seconds,
                "pool_shutdown_s":teardown_seconds,
                "policy_counts":dict(policy.count),"per_request":times,
                "trace":trace,"producer_intervals":prefill_intervals,
                "route_by_wave":tuple(
                    trace[n]["route_active"] for n in range(0,len(trace),budget))
            }
        def identical(a,b,context):
            if len(a)!=len(b) or any(not torch.equal(x,y) for x,y in zip(a,b)):
                raise RuntimeError("OUTPUT_TOKEN_PARITY_FAIL_"+context)
        try:
            for budget in BUDGETS:
                process.cpu_affinity(all_allowed[:budget])
                for name,pattern in STREAMS.items():
                    reference,_=execute(pattern,"no_cache",budget)
                    digests=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in reference]
                    for arm in ARMS:
                        alt,info=execute(pattern,arm,budget)
                        identical(reference,alt,name+"_"+arm+"_correctness")
                        execute(pattern,arm,budget) # untimed warm-up
                    records=[]
                    for i in range(REPEATS):
                        order=list(ARMS[i:]+ARMS[:i])
                        if i%2:order.reverse()
                        recorded={}
                        for arm in order:
                            out,data=execute(pattern,arm,budget)
                            identical(reference,out,name+"_"+arm+"_trial"+str(i))
                            if data["total_worker_budget"]!=budget or data["maximum_forward_workers"]!=budget:
                                raise RuntimeError("CPU_MODEL_FORWARD_WORKERS_INVALID")
                            if arm=="conditional_router":
                                if data["route_by_wave"]!=EXPECTED[name][budget]:
                                    raise RuntimeError("WRONG_CAUSAL_ROUTING_DECISIONS")
                                if not any(data["route_by_wave"]):
                                    if data["prefill_producers"] or data["max_kv_bytes"] or any(t["prefill_workers"] for t in data["trace"]):
                                        raise RuntimeError("NO_REUSE_WASTED_PREFILL_WORKERS")
                            recorded[arm]=data
                        records.append({"trial":i+1,"order":order,"arms":recorded,
                            "conditional_over_no_cache":recorded["no_cache"]["wall_s"]/recorded["conditional_router"]["wall_s"],
                            "conditional_over_serial":recorded["serialized_prefill"]["wall_s"]/recorded["conditional_router"]["wall_s"]})
                    result.setdefault("cohorts",{}).setdefault(name,{})["budget_"+str(budget)]={
                        "reference_output_sha256":digests,"trials":records,
                        "median_conditional_over_no_cache":statistics.median(r["conditional_over_no_cache"] for r in records),
                        "median_conditional_over_serial":statistics.median(r["conditional_over_serial"] for r in records),
                        "route_expected":EXPECTED[name][budget]}
        finally:
            process.cpu_affinity(all_allowed)
        h2=result["cohorts"]["high_locality"]["budget_2"]
        h3=result["cohorts"]["high_locality"]["budget_3"]
        u3=result["cohorts"]["unique_only"]["budget_3"]
        t3=result["cohorts"]["thrash"]["budget_3"]
        result["correctness"]="PASS"
        result["performance_screen"]="PASS" if (
            h3["median_conditional_over_no_cache"]>=THRESHOLDS["b3_high_over_no_cache"]
            and h2["median_conditional_over_no_cache"]>=THRESHOLDS["b2_high_over_no_cache"]
            and u3["median_conditional_over_no_cache"]>=THRESHOLDS["b3_unique_over_no_cache"]
            and t3["median_conditional_over_no_cache"]>=THRESHOLDS["b3_thrash_over_no_cache"]
            and h3["median_conditional_over_serial"]>=THRESHOLDS["b3_high_over_serial"]
        ) else "FAIL"
    except Exception as exc:
        result["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g64_result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print(json.dumps({k:result.get(k) for k in
            ("gate","correctness","performance_screen","error")},sort_keys=True))
        for name,budgets in result.get("cohorts",{}).items():
            for budget,record in budgets.items():
                print(json.dumps({"cohort":name,"budget":budget,
                    "conditional_over_no_cache":record["median_conditional_over_no_cache"],
                    "conditional_over_serial":record["median_conditional_over_serial"]},sort_keys=True))

if __name__=="__main__":
    main()
