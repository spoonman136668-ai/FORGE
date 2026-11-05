#!/usr/bin/env python3
"""G63: preregistered real GPT-2 equal-resource 2-CPU/3-CPU prefix reuse study.

Research-only, fail-closed source identities and exact greedy output parity.
No production serving, scientific acceptance, or controller changes.
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

MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
MODEL_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
PREREG="1ab8bf1648dff11907a9b63494ab6a17cbf19920"
BUDGETS=(2,3)
ARMS=("no_cache","serialized_prefill","overlapped_singleflight")
STREAMS={"high_locality":(0,0,0,0,1,1),
         "unique_only":(0,1,2,3,4,5),
         "thrash":(0,1,2,0,1,2)}
REPEATS=3
TOKENS=16
KV_CAP=42_000_000
ENTRY_CAP=2
THRESHOLDS={"b3_high_over_no_cache":1.05,"b3_high_over_serial":1.05,
            "b2_high_over_no_cache":1.00,"b3_unique_over_no_cache":0.95}

def module(name,relative):
    path=Path(__file__).resolve().parents[1]/relative
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def overlap(a,b,c,d):
    return max(0.0,min(b,d)-max(a,c))

def check_contract():
    assert BUDGETS==(2,3) and TOKENS==16 and REPEATS==3
    assert ARMS==("no_cache","serialized_prefill","overlapped_singleflight")
    assert STREAMS["high_locality"]==(0,0,0,0,1,1)
    assert STREAMS["unique_only"]==(0,1,2,3,4,5)
    assert STREAMS["thrash"]==(0,1,2,0,1,2)
    assert (ENTRY_CAP,KV_CAP)==(2,42_000_000)
    assert THRESHOLDS=={"b3_high_over_no_cache":1.05,"b3_high_over_serial":1.05,
                       "b2_high_over_no_cache":1.00,"b3_unique_over_no_cache":0.95}

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    check_contract()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    g55=module("g55_g63","llm_g55/g55_gpt2_controls.py")
    g58=module("g58_g63","llm_g58/g58_selective_cache.py")
    g59=module("g59_g63","llm_g59/g59_adaptive.py")
    g60=module("g60_g63","llm_g60/g60_concurrent.py")
    g62=module("g62_g63","llm_g62/g62_singleflight.py")
    if not (
        g55.REV==g59.MODEL_REV==g60.REV==g62.REV==MODEL_REV and
        g55.WEIGHT_SHA==g59.MODEL_SHA==g60.WEIGHT_SHA==g62.WEIGHTS_SHA==MODEL_SHA
    ):
        raise RuntimeError("ORIGINAL_MODEL_IDENTITY_DRIFT")
    receipt={
        "gate":"G63","kind":"AUTHENTIC_CPU_AFFINITY_EQUAL_RESOURCE_SCREEN",
        "git_source":os.getenv("GITHUB_SHA","UNSET"),
        "preregistration_commit":PREREG,
        "model_revision":MODEL_REV,"weights_sha256":MODEL_SHA,
        "torch":torch.__version__,"transformers":transformers.__version__,
        "platform":platform.platform(),
        "budgets_cpu_affinity":BUDGETS,"arms":ARMS,"streams":STREAMS,
        "repeats":REPEATS,"tokens_per_request":TOKENS,"thresholds":THRESHOLDS,
        "engineering":"UNVERIFIED","screen":"UNVERIFIED",
        "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
        "limitations":[
            "Single hosted CPU and one authentic GPT-2 checkpoint, synthetic pretokenized inputs",
            "Per-arm scheduling has different decoder pool sizes, as intended to match total forward worker resources",
            "CPU affinity and thread caps match, not equal realized core occupancy or energy",
            "No artificial wave barriers; arrival-order model tasks, future wait may cause head-of-line blocking",
            "Exact retained KV byte cap excludes transient copies/decoder KV allocations",
            "RSS sampled in 10ms increments is not exact peak",
            "No HTTP serving, real batch scheduler, GPU, production latency SLO, native Wingless/Yggdrasil model"
        ]}
    try:
        root,model_files=g55.stage()
        receipt["model_files"]=model_files
        receipt["model_manifest_sha256"]=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,
                                                trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                                                  trust_remote_code=False,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or model.config.is_encoder_decoder or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("GPT2_ARCH_DTYPE_MISMATCH")
        def ids(s):
            return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        prefix=[ids(g55.PREFIX+f" Family {i} has a unique context marker.") for i in range(6)]
        suffix=[ids(f" Request {i}: state the bounded validation requirement.") for i in range(6)]
        keys=[tuple(p.flatten().tolist()) for p in prefix]
        if len(set(keys))!=6:
            raise RuntimeError("TOKEN_PREFIX_COLLISION")
        if max(p.shape[1] for p in prefix)+max(s.shape[1] for s in suffix)+TOKENS>model.config.n_positions:
            raise RuntimeError("GPT2_CONTEXT_EXCEEDED")
        receipt["prefix_sha256"]=[hashlib.sha256(p.numpy().tobytes()).hexdigest() for p in prefix]
        receipt["suffix_sha256"]=[hashlib.sha256(p.numpy().tobytes()).hexdigest() for p in suffix]
        process=psutil.Process()
        if not hasattr(process,"cpu_affinity"):
            raise RuntimeError("CPU_AFFINITY_UNAVAILABLE")
        full_affinity=process.cpu_affinity()
        if len(full_affinity)<max(BUDGETS):
            raise RuntimeError("INSUFFICIENT_AVAILABLE_CPUS_FOR_THREE_CPU_CONTROL")
        receipt["original_allowed_affinity"]=full_affinity

        def prefill(family):
            t0=time.perf_counter()
            with torch.inference_mode():
                past=model(input_ids=prefix[family],use_cache=True).past_key_values
            tend=time.perf_counter()
            size=g58.tensor_nbytes(past)
            expected=g62.planned_cache_bytes(model,len(keys[family]))
            if size!=expected:
                raise RuntimeError("PREFILL_KV_ACTUAL_BYTES_MISMATCH")
            return {"past":past,"start":t0,"end":tend,"bytes":size,"family":family}

        def decode(initial,future,prefix_len,family,arrival):
            start=time.perf_counter()
            copy_s=0.0
            wait_s=0.0
            kw={"input_ids":initial,"use_cache":True}
            context=int(initial.shape[1])+prefix_len
            if future is not None:
                t0=time.perf_counter()
                packet=future.result(timeout=45)
                wait_s=time.perf_counter()-t0
                if packet["family"]!=family:
                    raise RuntimeError("CACHED_FAMILY_IDENTITY_MISMATCH")
                t0=time.perf_counter()
                past=copy.deepcopy(packet["past"])
                copy_s=time.perf_counter()-t0
                kw["past_key_values"]=past
                kw["attention_mask"]=torch.ones((1,context),dtype=torch.long)
            with torch.inference_mode():
                out=model(**kw)
                history,logits=out.past_key_values,out.logits[:,-1,:]
                made=[]
                for step in range(TOKENS):
                    token=logits.argmax(dim=-1,keepdim=True)
                    made.append(token)
                    if step<TOKENS-1:
                        out=model(input_ids=token,past_key_values=history,use_cache=True,
                          attention_mask=torch.ones((1,context+step+1),dtype=torch.long))
                        history,logits=out.past_key_values,out.logits[:,-1,:]
            end=time.perf_counter()
            return torch.cat(made,dim=1),{
                "start_s":start,"end_s":end,"elapsed_s":end-start,
                "from_arrival_s":end-arrival,
                "future_wait_s":wait_s,"kv_copy_s":copy_s,
                "family":family
            }

        def execute(pattern,arm,budget):
            decoder_threads=budget if arm!="overlapped_singleflight" else budget-1
            producer_threads=0 if arm!="overlapped_singleflight" else 1
            if decoder_threads+producer_threads!=budget:
                raise RuntimeError("UNEQUAL_WORKER_RESOURCE_BUDGET")
            if tuple(process.cpu_affinity())!=tuple(full_affinity[:budget]):
                raise RuntimeError("PROCESS_CPU_AFFINITY_NOT_ENFORCED")
            adaptive=g59.Policy("no_cache" if arm=="no_cache" else "adaptive")
            future_per_key={}
            outputs=[None]*len(pattern)
            times=[None]*len(pattern)
            pending=[]
            max_reserve=0
            source_events=[]
            overlap_sum=0.0
            deduped_join=0
            start=time.perf_counter()
            cpu_start=time.process_time()
            with g60.RSSMonitor(process) as monitor, concurrent.futures.ThreadPoolExecutor(max_workers=decoder_threads) as decoding_pool:
                prep_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1) if producer_threads else None
                try:
                    for request_index,family in enumerate(pattern):
                        arrive=time.perf_counter()
                        key=keys[family]
                        action,fut=adaptive.begin(key,ENTRY_CAP)
                        if action=="admit":
                            if key in future_per_key and not future_per_key[key].done():
                                raise RuntimeError("DUPLICATED_IN_FLIGHT_PREFILL")
                            if prep_pool is None:
                                fut=concurrent.futures.Future()
                                try:fut.set_result(prefill(family))
                                except BaseException as e:
                                    fut.set_exception(e)
                                    raise
                            else:
                                fut=prep_pool.submit(prefill,family)
                            future_per_key[key]=fut
                            adaptive.insert(key,fut,ENTRY_CAP)
                        elif action=="hit":
                            if key not in future_per_key or fut is None:
                                raise RuntimeError("MISSING_SINGLEFLIGHT_PREFIX_PRODUCER")
                            if not fut.done():deduped_join+=1
                        elif action!="skip":
                            raise RuntimeError("INVALID_FROZEN_POLICY_ACTION")
                        adaptive.finish(key,ENTRY_CAP,action)
                        planned=sum(g62.planned_cache_bytes(model,len(k)) for k in adaptive.cache)
                        if planned>KV_CAP or len(adaptive.cache)>ENTRY_CAP:
                            raise RuntimeError("KV_CACHE_CAP_EXCEEDED")
                        max_reserve=max(max_reserve,planned)
                        if fut is not None:
                            first=suffix[request_index]
                            ctx=int(prefix[family].shape[1])
                        else:
                            first=torch.cat((prefix[family],suffix[request_index]),dim=1)
                            ctx=0
                        source_events.append({
                            "index":request_index,"family":family,"action":action,
                            "reserved_bytes":planned,"retained_entries":len(adaptive.cache)
                        })
                        pending.append(decoding_pool.submit(decode,first,fut,ctx,family,arrive))
                    for index,task in enumerate(pending):
                        out,timing=task.result(timeout=100)
                        outputs[index]=out
                        times[index]=timing
                    for future in future_per_key.values():
                        future.result(timeout=45)
                finally:
                    if prep_pool is not None:prep_pool.shutdown(wait=True,cancel_futures=False)
                wall=time.perf_counter()-start
                process_cpu=time.process_time()-cpu_start
            prefill_intervals=[{
                "family":a["family"],"start":a["start"],"end":a["end"],
                "duration_s":a["end"]-a["start"],"bytes":a["bytes"]
            } for a in (f.result() for f in future_per_key.values())]
            for p in prefill_intervals:
                for w in times:
                    if w["family"]!=p["family"]:
                        overlap_sum+=overlap(p["start"],p["end"],w["start_s"],w["end_s"])
            if len(outputs)!=len(pattern) or any(x is None for x in outputs):
                raise RuntimeError("MISSING_GENERATED_TOKENS")
            if adaptive.count["hits"]+adaptive.count["misses"]!=len(pattern):
                raise RuntimeError("HIT_MISS_ACCOUNTING_FAILED")
            if adaptive.count["admissions"]!=len(future_per_key):
                raise RuntimeError("NON_SINGLEFLIGHT_PREFILL_COUNT")
            if arm=="no_cache" and (adaptive.count["hits"] or adaptive.count["admissions"] or max_reserve):
                raise RuntimeError("BASELINE_PREFIX_STATE_LEAK")
            if arm=="overlapped_singleflight" and producer_threads!=1:
                raise RuntimeError("CANDIDATE_EXTRA_WORKER_MISSING")
            return outputs,{
                "whole_stream_wall_s":wall,"process_cpu_s":process_cpu,
                "throughput_tokens_per_s":len(pattern)*TOKENS/wall,
                "latency_p50_s":statistics.median(w["from_arrival_s"] for w in times),
                "latency_p95_s":sorted(w["from_arrival_s"] for w in times)[-1],
                "decoder_workers":decoder_threads,"prefill_workers":producer_threads,
                "process_affinity":process.cpu_affinity(),"cpu_budget":budget,
                "cache_counts":dict(adaptive.count),
                "prefix_producers":len(prefill_intervals),
                "pending_singleflight_joiners":deduped_join,
                "max_retained_kv_bytes":max_reserve,
                "final_retained_kv_bytes":sum(g62.planned_cache_bytes(model,len(k)) for k in adaptive.cache),
                "sampled_rss_max_bytes":max(monitor.samples),
                "sampled_rss_count":len(monitor.samples),
                "prefill_unrelated_decoder_overlap_interval_sum_s":overlap_sum,
                "producer_intervals":prefill_intervals,
                "worker_intervals":times,
                "admission_trace":source_events
            }

        def same(a,b,label):
            if len(a)!=len(b) or any(not torch.equal(i,j) for i,j in zip(a,b)):
                raise RuntimeError("GREEDY_OUTPUT_TOKEN_MISMATCH_"+label)
        try:
            for cpu_budget in BUDGETS:
                process.cpu_affinity(full_affinity[:cpu_budget])
                for cohort,pattern in STREAMS.items():
                    baseline,_=execute(pattern,"no_cache",cpu_budget)
                    reference_hash=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in baseline]
                    for arm in ARMS:
                        produced,_=execute(pattern,arm,cpu_budget)
                        same(baseline,produced,"correctness_"+cohort+"_"+arm)
                        execute(pattern,arm,cpu_budget)  # untimed warm-up
                    trials=[]
                    for idx in range(REPEATS):
                        order=list(ARMS[idx:]+ARMS[:idx])
                        if idx%2:order.reverse()
                        results={}
                        for arm in order:
                            outputs,record=execute(pattern,arm,cpu_budget)
                            same(baseline,outputs,cohort+"_"+arm+"_trial"+str(idx))
                            results[arm]=record
                        trials.append({
                            "trial":idx+1,"order":order,"arms":results,
                            "overlap_over_baseline":results["no_cache"]["whole_stream_wall_s"]/results["overlapped_singleflight"]["whole_stream_wall_s"],
                            "overlap_over_serial":results["serialized_prefill"]["whole_stream_wall_s"]/results["overlapped_singleflight"]["whole_stream_wall_s"],
                            "serial_over_baseline":results["no_cache"]["whole_stream_wall_s"]/results["serialized_prefill"]["whole_stream_wall_s"]
                        })
                    receipt.setdefault("cohorts",{}).setdefault(cohort,{})["budget_"+str(cpu_budget)]={
                        "reference_output_sha256":reference_hash,
                        "trials":trials,
                        "median_overlap_over_baseline":statistics.median(t["overlap_over_baseline"] for t in trials),
                        "median_overlap_over_serial":statistics.median(t["overlap_over_serial"] for t in trials),
                        "median_serial_over_baseline":statistics.median(t["serial_over_baseline"] for t in trials)
                    }
        finally:
            process.cpu_affinity(full_affinity)
        for budget in BUDGETS:
            for trial in receipt["cohorts"]["unique_only"]["budget_"+str(budget)]["trials"]:
                for arm in ARMS:
                    if trial["arms"][arm]["prefix_producers"]!=0 or trial["arms"][arm]["max_retained_kv_bytes"]!=0:
                        raise RuntimeError("UNIQUE_PREFIX_FALSE_CACHE_ADMISSION")
        high2=receipt["cohorts"]["high_locality"]["budget_2"]
        high3=receipt["cohorts"]["high_locality"]["budget_3"]
        unique3=receipt["cohorts"]["unique_only"]["budget_3"]
        all_overlaps=[t["arms"]["overlapped_singleflight"]["prefill_unrelated_decoder_overlap_interval_sum_s"]
                      for t in high2["trials"]+high3["trials"]]
        receipt["prefill_overlap_observed"]=max(all_overlaps)>0
        receipt["engineering"]="PASS"
        receipt["screen"]="PASS" if (
            high3["median_overlap_over_baseline"]>=THRESHOLDS["b3_high_over_no_cache"] and
            high3["median_overlap_over_serial"]>=THRESHOLDS["b3_high_over_serial"] and
            high2["median_overlap_over_baseline"]>=THRESHOLDS["b2_high_over_no_cache"] and
            unique3["median_overlap_over_baseline"]>=THRESHOLDS["b3_unique_over_no_cache"] and
            receipt["prefill_overlap_observed"]
        ) else "FAIL"
    except Exception as e:
        receipt["error"]=type(e).__name__+": "+str(e)
        raise
    finally:
        Path("g63_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print(json.dumps({key:receipt.get(key) for key in ("gate","engineering","screen","prefill_overlap_observed","error")}))
        for name,cohort in receipt.get("cohorts",{}).items():
            for budget,row in cohort.items():
                print(json.dumps({"cohort":name,"budget":budget,
                    "overlap_over_no_cache":row["median_overlap_over_baseline"],
                    "overlap_over_serial":row["median_overlap_over_serial"],
                    "serial_over_no_cache":row["median_serial_over_baseline"]},sort_keys=True))
if __name__=="__main__":main()
