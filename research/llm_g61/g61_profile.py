#!/usr/bin/env python3
"""G61: original-model parallel-vs-serial prefix-cache cost attribution.

Source/prereg frozen; NOT a new inference optimization or acceptance gate.
The measurements partition coordinator prefill, copy, initial+incremental model
forward, scheduling, and whole-run wall/CPU. Overlapping stage sums should not
be mistaken for an exclusive wall-time decomposition.
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
PREREG="cb2974f99345025c3e08b553e1ceda376dbddbb7"
ARMS=("no_cache","second_seen","adaptive")
STREAMS={"high_locality":(0,0,0,0,1,1),"unique_only":(0,1,2,3,4,5)}
CONCURRENCY=(1,2)
REPEATS=2
TOKENS=16
CAP_ENTRIES=2
CAP_BYTES=42_000_000

def mod(name,relative):
    p=Path(__file__).resolve().parents[1]/relative
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m

def pure_contract():
    assert len(set(ARMS))==3 and CONCURRENCY==(1,2) and REPEATS==2 and TOKENS==16
    assert all(len(p)==6 for p in STREAMS.values())
    assert STREAMS["high_locality"]==(0,0,0,0,1,1)
    assert STREAMS["unique_only"]==(0,1,2,3,4,5)
    assert CAP_ENTRIES==2 and CAP_BYTES==42_000_000

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer

    g55=mod("g55_61","llm_g55/g55_gpt2_controls.py")
    g58=mod("g58_61","llm_g58/g58_selective_cache.py")
    g59=mod("g59_61","llm_g59/g59_adaptive.py")
    g60=mod("g60_61","llm_g60/g60_concurrent.py")
    if not (g55.REV==g59.MODEL_REV==g60.REV==REV and
            g55.WEIGHT_SHA==g59.MODEL_SHA==g60.WEIGHT_SHA==WEIGHTS_SHA):
        raise RuntimeError("FROZEN_GPT2_MODEL_MISMATCH")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    receipt={"gate":"G61","kind":"DIAGNOSTIC_CONCURRENT_CACHE_ATTRIBUTION_ONLY",
             "source_sha":os.getenv("GITHUB_SHA","NOT_SET"),
             "prereg_commit":PREREG,"model_revision":REV,"weight_sha256":WEIGHTS_SHA,
             "torch":torch.__version__,"transformers":transformers.__version__,
             "platform":platform.platform(),"concurrency":CONCURRENCY,
             "repetitions":REPEATS,"tokens":TOKENS,"streams":STREAMS,"arms":ARMS,
             "retained_kv_entry_cap":CAP_ENTRIES,"retained_kv_byte_cap":CAP_BYTES,
             "original_g60_high_locality_adaptive_speedup":0.903500105110561,
             "correctness":"UNVERIFIED","diagnostic":"UNVERIFIED",
             "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
             "limitations":[
                "One hosted CPU and pretrained GPT-2, no production HTTP service",
                "Pre-tokenized same synthetic public test strings, no tokenizer service cost",
                "Deterministic synchronized waves of two; not a production scheduler",
                "Phase wall sums overlap and do not equal critical path wall time",
                "10ms sampled RSS is not true process high-water or dynamic memory pressure",
                "No original native Wingless or Yggdrasil learning, GPU, energy or optimized serving"
             ]}
    try:
        pure_contract()
        root,files=g55.stage()
        receipt["source_artifacts"]=files
        receipt["original_manifest_sha256"]=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),use_safetensors=True,
                   local_files_only=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or model.config.is_encoder_decoder:
            raise RuntimeError("FROZEN_MODEL_ARCH_MISMATCH")
        def ids(s):
            return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        pre=[ids(g55.PREFIX+f" Family {k} has a unique context marker.") for k in range(6)]
        suff=[ids(f" Request {k}: state the bounded validation requirement.") for k in range(6)]
        keys=[tuple(t.flatten().tolist()) for t in pre]
        if len(set(keys))!=6:
            raise RuntimeError("PREFIX_COLLISION")
        if max(t.shape[1] for t in pre)+max(t.shape[1] for t in suff)+TOKENS>model.config.n_positions:
            raise RuntimeError("GPT2_CONTEXT_OVERFLOW")
        receipt["prefix_sha256"]=[hashlib.sha256(t.numpy().tobytes()).hexdigest() for t in pre]
        receipt["suffix_sha256"]=[hashlib.sha256(t.numpy().tobytes()).hexdigest() for t in suff]
        proc=psutil.Process()

        def decode(initial,past,plen,barrier,arrival):
            with torch.inference_mode():
                if barrier is not None:
                    barrier.wait(timeout=30)
                started=time.perf_counter()
                total=int(initial.shape[1])+plen
                copied=None
                cp_start=time.perf_counter()
                if past is not None:
                    copied=copy.deepcopy(past)
                cp_time=time.perf_counter()-cp_start
                opts={"input_ids":initial,"use_cache":True}
                if copied is not None:
                    opts["past_key_values"]=copied
                    opts["attention_mask"]=torch.ones((1,total),dtype=torch.long)
                a=time.perf_counter()
                out=model(**opts)
                first_forward=time.perf_counter()-a
                kv,logits=out.past_key_values,out.logits[:,-1,:]
                made=[]
                inc=0.0
                for k in range(TOKENS):
                    token=logits.argmax(dim=-1,keepdim=True)
                    made.append(token)
                    if k+1<TOKENS:
                        t0=time.perf_counter()
                        out=model(input_ids=token,past_key_values=kv,
                                 attention_mask=torch.ones((1,total+k+1),dtype=torch.long),
                                 use_cache=True)
                        inc+=time.perf_counter()-t0
                        kv,logits=out.past_key_values,out.logits[:,-1,:]
                end=time.perf_counter()
                return torch.cat(made,dim=1),{
                    "start_s":started,"end_s":end,"arrival_to_start_s":started-arrival,
                    "deepcopy_s":cp_time,"first_forward_s":first_forward,
                    "incremental_forward_s":inc,
                    "worker_end_to_end_s":end-started,
                    "request_from_arrival_s":end-arrival
                }

        def run(pattern,arm,workers):
            policy=g59.Policy(arm)
            outputs=[None]*len(pattern)
            records=[None]*len(pattern)
            wave_overlaps=[]
            retained_max=0
            coordinator_prefill=0.0
            coordinator_policy=0.0
            coordinator_kv_count=0
            events=[]
            started=time.perf_counter()
            cpu_start=time.process_time()
            with g60.RSSMonitor(proc) as mon,concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                for offset in range(0,len(pattern),workers):
                    barrier=threading.Barrier(workers,timeout=30) if workers==2 else None
                    tasks=[]
                    for k in range(offset,min(offset+workers,len(pattern))):
                        fam=pattern[k]
                        before=time.perf_counter()
                        key=keys[fam]
                        action,cache=policy.begin(key,CAP_ENTRIES)
                        coordinator_policy+=time.perf_counter()-before
                        if action=="admit":
                            t0=time.perf_counter()
                            with torch.inference_mode():
                                cache=model(input_ids=pre[fam],use_cache=True).past_key_values
                            coordinator_prefill+=time.perf_counter()-t0
                            insert_start=time.perf_counter()
                            policy.insert(key,cache,CAP_ENTRIES)
                            coordinator_policy+=time.perf_counter()-insert_start
                        t0=time.perf_counter()
                        policy.finish(key,CAP_ENTRIES,action)
                        retained=sum(g58.tensor_nbytes(c) for c in policy.cache.values())
                        if retained>CAP_BYTES or len(policy.cache)>CAP_ENTRIES:
                            raise RuntimeError("RETAINED_KV_CACHE_BUDGET_EXCEEDED")
                        retained_max=max(retained_max,retained)
                        coordinator_kv_count+=1
                        coordinator_policy+=time.perf_counter()-t0
                        if action in ("admit","hit"):
                            if cache is None:
                                raise RuntimeError("POLICY_CACHED_WITHOUT_TENSOR")
                            token_input=suff[k]; plen=int(pre[fam].shape[1])
                        else:
                            token_input=torch.cat((pre[fam],suff[k]),dim=1); plen=0
                        tasks.append((k,token_input,cache,plen,barrier,time.perf_counter()))
                        events.append({"request":k,"family":fam,"action":action,
                                       "retained_kv_bytes":retained,
                                       "cache_entries":len(policy.cache)})
                    pending=[pool.submit(decode,inp,past,plen,br,arr)
                             for k,inp,past,plen,br,arr in tasks]
                    finished=[future.result() for future in pending]
                    for task,(output,profile) in zip(tasks,finished):
                        k=task[0]
                        outputs[k]=output
                        records[k]=profile
                    if workers==2:
                        overlap=min(x[1]["end_s"] for x in finished)-max(x[1]["start_s"] for x in finished)
                        if overlap<=0:
                            raise RuntimeError("NO_TRUE_TWO_WORKER_OVERLAP")
                        wave_overlaps.append(overlap)
                wall=time.perf_counter()-started
                cpu=time.process_time()-cpu_start
            if policy.count["hits"]+policy.count["misses"]!=len(pattern):
                raise RuntimeError("POLICY_HIT_ACCOUNTING_MISMATCH")
            if len(outputs)!=len(pattern) or any(t is None for t in outputs):
                raise RuntimeError("MISSING_OUTPUT")
            if arm=="no_cache" and (policy.count["hits"] or policy.count["admissions"] or policy.cache):
                raise RuntimeError("BASELINE_RETAINED_CACHE")
            # Two-worker and one-worker profiles use the same model/decoder and
            # history-driven policy but different synchronization/overlap.
            profile={
                "wall_s":wall,"process_cpu_s":cpu,"tokens_per_s":len(pattern)*TOKENS/wall,
                "count":dict(policy.count),
                "prefill_coordinator_s":coordinator_prefill,
                "policy_and_cache_accounting_s":coordinator_policy,
                "n_cache_accounting_samples":coordinator_kv_count,
                "sum_deepcopy_s":sum(r["deepcopy_s"] for r in records),
                "sum_first_forward_s":sum(r["first_forward_s"] for r in records),
                "sum_incremental_forward_s":sum(r["incremental_forward_s"] for r in records),
                "median_request_latency_s":statistics.median(r["request_from_arrival_s"] for r in records),
                "max_retained_kv_bytes":retained_max,
                "rss_sampled_max_bytes":max(mon.samples),
                "rss_first_bytes":mon.samples[0],"rss_last_bytes":mon.samples[-1],
                "rss_sample_count":len(mon.samples),
                "wave_overlap_s":wave_overlaps,"request_profiles":records,
                "policy_trace":events
            }
            if workers==2 and len(wave_overlaps)!=3:
                raise RuntimeError("TWO_WORKER_OVERLAP_NOT_VERIFIED")
            return outputs,profile

        def identical(a,b,kind):
            if len(a)!=len(b) or any(not torch.equal(x,y) for x,y in zip(a,b)):
                raise RuntimeError("EXACT_TOKEN_FAILURE_"+kind)

        for cohort,pattern in STREAMS.items():
            ref,_=run(pattern,"no_cache",1)
            token_sha=[hashlib.sha256(t.numpy().tobytes()).hexdigest() for t in ref]
            for workers in CONCURRENCY:
                for arm in ARMS:
                    out,_=run(pattern,arm,workers)
                    identical(ref,out,"preflight_"+cohort+"_"+arm+"_"+str(workers))
                    run(pattern,arm,workers) # untimed warmup
                trials=[]
                for idx in range(REPEATS):
                    order=list(ARMS[idx:]+ARMS[:idx])
                    if idx%2:order.reverse()
                    result={}
                    for arm in order:
                        out,data=run(pattern,arm,workers)
                        identical(ref,out,"trial_"+cohort+"_"+arm+"_"+str(workers))
                        result[arm]=data
                    trials.append({
                        "trial":idx+1,"order":order,"arms":result,
                        "adaptive_speedup":result["no_cache"]["wall_s"]/result["adaptive"]["wall_s"],
                        "second_seen_speedup":result["no_cache"]["wall_s"]/result["second_seen"]["wall_s"]
                    })
                receipt.setdefault("cohorts",{}).setdefault(cohort,{})["workers_"+str(workers)]={
                    "reference_tokens_sha256":token_sha,
                    "trials":trials,
                    "median_adaptive_speedup":statistics.median(t["adaptive_speedup"] for t in trials),
                    "median_second_seen_speedup":statistics.median(t["second_seen_speedup"] for t in trials),
                    "median_baseline_wall_s":statistics.median(t["arms"]["no_cache"]["wall_s"] for t in trials),
                    "median_adaptive_wall_s":statistics.median(t["arms"]["adaptive"]["wall_s"] for t in trials),
                    "median_adaptive_sum_copy_s":statistics.median(t["arms"]["adaptive"]["sum_deepcopy_s"] for t in trials),
                    "median_adaptive_prefill_s":statistics.median(t["arms"]["adaptive"]["prefill_coordinator_s"] for t in trials),
                    "median_adaptive_sum_first_s":statistics.median(t["arms"]["adaptive"]["sum_first_forward_s"] for t in trials),
                    "median_adaptive_sum_incremental_s":statistics.median(t["arms"]["adaptive"]["sum_incremental_forward_s"] for t in trials),
                    "median_adaptive_tokens_per_s":statistics.median(t["arms"]["adaptive"]["tokens_per_s"] for t in trials)
                }
        if any(
            t["arms"]["adaptive"]["max_retained_kv_bytes"]!=0 or
            t["arms"]["second_seen"]["max_retained_kv_bytes"]!=0
            for n,d in receipt["cohorts"]["unique_only"].items()
            for t in d["trials"]
        ):
            raise RuntimeError("UNIQUE_PREFIX_MEMORY_LEAK")
        receipt["correctness"]="PASS"
        receipt["diagnostic"]="PASS_MEASURED_NOT_ACCEPTANCE"
        receipt["cross_workers_high_locality_adaptive_regression_reproduced"]=(
          receipt["cohorts"]["high_locality"]["workers_1"]["median_adaptive_speedup"]>1.0
          and receipt["cohorts"]["high_locality"]["workers_2"]["median_adaptive_speedup"]<1.0
        )
    except Exception as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g61_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print(json.dumps({k:receipt.get(k) for k in
            ("gate","correctness","diagnostic","error","cross_workers_high_locality_adaptive_regression_reproduced")},sort_keys=True))
        for name,d in receipt.get("cohorts",{}).items():
            for workers,row in d.items():
                print(json.dumps({"cohort":name,"workers":workers,
                    "median_adaptive_speedup":row["median_adaptive_speedup"],
                    "median_second_seen_speedup":row["median_second_seen_speedup"],
                    "median_adaptive_copy_s":row["median_adaptive_sum_copy_s"],
                    "median_adaptive_prefill_s":row["median_adaptive_prefill_s"],
                    "median_adaptive_first_forward_sum_s":row["median_adaptive_sum_first_s"],
                    "median_adaptive_incremental_forward_sum_s":row["median_adaptive_sum_incremental_s"]
                },sort_keys=True))

if __name__=="__main__":
    main()
