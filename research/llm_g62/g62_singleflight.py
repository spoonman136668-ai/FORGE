#!/usr/bin/env python3
"""G62: authenticated GPT-2 bounded single-flight prefill under two-worker inference.

Pre-registered original source, exact tokens and negative controls. This does
not perform model training, scientific acceptance or FORGE controller changes.
"""
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

REV = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
PREREG = "d4103586279946381b91d6636100c508591adb1b"
ARMS = ("no_cache","serialized_prefill","overlapped_singleflight")
STREAMS = {
    "high_locality": (0,0,0,0,1,1),
    "unique_only": (0,1,2,3,4,5),
    "thrash": (0,1,2,0,1,2),
}
REPEATS = 3
TOKENS = 16
DECODE_WORKERS = 2
PREFILL_WORKERS = 1
CAP_ENTRIES = 2
CAP_BYTES = 42_000_000
THRESHOLDS = {"overlap_over_serial":1.05,
              "overlap_over_no_cache":1.00,
              "unique_over_no_cache":0.95}

def load(name,rel):
    p=Path(__file__).resolve().parents[1]/rel
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m

def planned_cache_bytes(model,prefix_tokens):
    # GPT-2 original exact float32 K and V: layers, dim, positions, bytes
    return 2*model.config.n_layer*model.config.n_embd*prefix_tokens*4

def intervals_overlap(a,b,c,d):
    return max(0.0,min(b,d)-max(a,c))

def self_test():
    assert len(set(ARMS))==3 and len(STREAMS)==3
    assert (REPEATS,TOKENS,DECODE_WORKERS,PREFILL_WORKERS)==(3,16,2,1)
    assert (CAP_ENTRIES,CAP_BYTES)==(2,42_000_000)
    assert THRESHOLDS=={"overlap_over_serial":1.05,
                        "overlap_over_no_cache":1.00,
                        "unique_over_no_cache":0.95}
    assert intervals_overlap(1,3,2,4)==1
    assert intervals_overlap(1,2,3,4)==0

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    g55=load("g55_62","llm_g55/g55_gpt2_controls.py")
    g58=load("g58_62","llm_g58/g58_selective_cache.py")
    g59=load("g59_62","llm_g59/g59_adaptive.py")
    g60=load("g60_62","llm_g60/g60_concurrent.py")
    if not (g55.REV==g59.MODEL_REV==g60.REV==REV and
            g55.WEIGHT_SHA==g59.MODEL_SHA==g60.WEIGHT_SHA==WEIGHTS_SHA):
        raise RuntimeError("PINNED_MODEL_SOURCE_DRIFT")
    self_test()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    result={
        "gate":"G62","source_sha":os.getenv("GITHUB_SHA","NOT_SET"),
        "preregistration_commit":PREREG,
        "classification":"FROZEN_CPU_TWO_DECODER_ONE_PREFILL_WORKER_SCREEN",
        "model_revision":REV,"weights_sha256":WEIGHTS_SHA,
        "torch":torch.__version__,"transformers":transformers.__version__,
        "platform":platform.platform(),"arms":ARMS,"streams":STREAMS,
        "repeats":REPEATS,"tokens_per_request":TOKENS,
        "decoder_workers":DECODE_WORKERS,
        "extra_candidate_prefill_worker":PREFILL_WORKERS,
        "retained_kv_entries_limit":CAP_ENTRIES,"retained_kv_bytes_limit":CAP_BYTES,
        "thresholds":THRESHOLDS,"correctness":"UNVERIFIED",
        "screen":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED",
        "promotion_allowed":False,
        "limitations":[
            "Candidate overlaps prefill on extra worker, so available CPU execution resources are not strictly equal",
            "Frozen two-request waves, not real HTTP serving or dynamic batching",
            "Shared pretrained GPT-2, pretokenized synthetic public strings",
            "RSS samples are not true process high-water",
            "No OS memory-pressure test, GPU, energy, scaling, native Wingless/Yggdrasil model"
        ]
    }
    try:
        staged,records=g55.stage()
        result["model_file_hashes"]=records
        result["model_manifest_sha256"]=hashlib.sha256((staged/"manifest.json").read_bytes()).hexdigest()
        tokenizer=AutoTokenizer.from_pretrained(str(staged),trust_remote_code=False,
                                                 local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(staged),local_files_only=True,
                                                 trust_remote_code=False,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("ORIGINAL_ARCH_DTYPE_MISMATCH")
        def ids(text):
            return tokenizer(text,add_special_tokens=False,return_tensors="pt")["input_ids"]
        prefixes=[ids(g55.PREFIX+f" Family {family} has a unique context marker.") for family in range(6)]
        suffixes=[ids(f" Request {i}: state the bounded validation requirement.") for i in range(6)]
        keys=[tuple(v.flatten().tolist()) for v in prefixes]
        if len(set(keys))!=6:
            raise RuntimeError("PREFIX_KEY_COLLISION")
        if max(v.shape[1] for v in prefixes)+max(v.shape[1] for v in suffixes)+TOKENS>model.config.n_positions:
            raise RuntimeError("CONTEXT_OVERFLOW")
        result["prefix_token_counts"]=[len(k) for k in keys]
        result["prefix_sha256"]=[hashlib.sha256(v.numpy().tobytes()).hexdigest() for v in prefixes]
        proc=psutil.Process()

        def prefill(family):
            start=time.perf_counter()
            with torch.inference_mode():
                past=model(input_ids=prefixes[family],use_cache=True).past_key_values
            end=time.perf_counter()
            nbytes=g58.tensor_nbytes(past)
            planned=planned_cache_bytes(model,len(keys[family]))
            if nbytes!=planned:
                raise RuntimeError("ACTUAL_CACHE_BYTE_IDENTITY_MISMATCH")
            return {"past":past,"start":start,"end":end,"bytes":nbytes,"family":family}

        def decode(first,past_future,prefix_count,barrier,arrive,expected_family,action):
            if barrier is not None:
                barrier.wait(timeout=25)
            start=time.perf_counter()
            waiting=0.0
            copy_time=0.0
            future_ready_at=None
            kwargs={"input_ids":first,"use_cache":True}
            total=first.shape[1]+prefix_count
            if past_future is not None:
                t0=time.perf_counter()
                packet=past_future.result(timeout=30)
                waiting=time.perf_counter()-t0
                future_ready_at=packet["end"]
                if packet["family"]!=expected_family:
                    raise RuntimeError("PREFIX_SINGLEFLIGHT_KEY_MISMATCH")
                t0=time.perf_counter()
                cloned=copy.deepcopy(packet["past"])
                copy_time=time.perf_counter()-t0
                kwargs["past_key_values"]=cloned
                kwargs["attention_mask"]=torch.ones((1,total),dtype=torch.long)
            with torch.inference_mode():
                out=model(**kwargs)
                cached,logits=out.past_key_values,out.logits[:,-1,:]
                outputs=[]
                for j in range(TOKENS):
                    chosen=logits.argmax(dim=-1,keepdim=True)
                    outputs.append(chosen)
                    if j<TOKENS-1:
                        out=model(input_ids=chosen,past_key_values=cached,
                                  attention_mask=torch.ones((1,total+j+1),dtype=torch.long),
                                  use_cache=True)
                        cached,logits=out.past_key_values,out.logits[:,-1,:]
                output=torch.cat(outputs,dim=1)
            end=time.perf_counter()
            return output,{
                "family":expected_family,"action":action,
                "start":start,"end":end,"worker_wall_s":end-start,
                "request_arrival_to_end_s":end-arrive,
                "cached_future_wait_s":waiting,"kv_deepcopy_s":copy_time,
                "future_ready_at":future_ready_at
            }

        def execute(pattern,arm):
            if arm not in ARMS:raise RuntimeError("ARM_NOT_FROZEN")
            policy=g59.Policy("no_cache" if arm=="no_cache" else "adaptive")
            cached_size={}
            outputs=[None]*len(pattern)
            request_timings=[None]*len(pattern)
            producers={}
            admitted_future_count=0
            max_reserved_bytes=0
            cache_occupancy=[]
            wave_overlaps=[]
            deduped_waits=0
            all_futures={}
            started=time.perf_counter()
            process_cpu_started=time.process_time()
            with g60.RSSMonitor(proc) as mon,concurrent.futures.ThreadPoolExecutor(max_workers=DECODE_WORKERS) as decode_pool,concurrent.futures.ThreadPoolExecutor(max_workers=PREFILL_WORKERS) as prefill_pool:
                for wave in range(0,len(pattern),DECODE_WORKERS):
                    arrivals=[]
                    barrier=threading.Barrier(DECODE_WORKERS,timeout=25)
                    for i in (wave,wave+1):
                        family=pattern[i]
                        key=keys[family]
                        arrive=time.perf_counter()
                        action,future=policy.begin(key,CAP_ENTRIES)
                        if action=="admit":
                            if key in all_futures and not all_futures[key].done():
                                # This is a new admission after a capacity eviction.
                                # That would be duplicate concurrent work: fail closed.
                                raise RuntimeError("DUPLICATE_INFLIGHT_PREFILL")
                            if arm=="serialized_prefill":
                                future=concurrent.futures.Future()
                                try:
                                    future.set_result(prefill(family))
                                except BaseException as e:
                                    future.set_exception(e)
                                    raise
                            else:
                                future=prefill_pool.submit(prefill,family)
                            all_futures[key]=future
                            policy.insert(key,future,CAP_ENTRIES)
                            admitted_future_count+=1
                        elif action=="hit":
                            if future is None or key not in all_futures:
                                raise RuntimeError("CACHE_HIT_WITHOUT_PRODUCER")
                            if not future.done():
                                deduped_waits+=1
                        elif action!="skip":
                            raise RuntimeError("UNSUPPORTED_POLICY_ACTION")
                        policy.finish(key,CAP_ENTRIES,action)
                        reserved=sum(planned_cache_bytes(model,len(keyitem)) for keyitem in policy.cache.keys())
                        if reserved>CAP_BYTES or len(policy.cache)>CAP_ENTRIES:
                            raise RuntimeError("RETAINED_CACHE_BYTE_BUDGET_EXCEEDED")
                        max_reserved_bytes=max(max_reserved_bytes,reserved)
                        cache_occupancy.append({"request":i,"action":action,
                                                "entries":len(policy.cache),
                                                "reserved_bytes":reserved})
                        if future is None:
                            first=torch.cat((prefixes[family],suffixes[i]),dim=1)
                            context=0
                        else:
                            first=suffixes[i]
                            context=int(prefixes[family].shape[1])
                        arrivals.append((i,first,future,context,barrier,arrive,family,action))
                    work=[decode_pool.submit(decode,*args[1:]) for args in arrivals]
                    measured=[w.result() for w in work]
                    for args,(output,metrics) in zip(arrivals,measured):
                        index=args[0]
                        outputs[index]=output
                        request_timings[index]=metrics
                    overlap=intervals_overlap(measured[0][1]["start"],measured[0][1]["end"],
                                              measured[1][1]["start"],measured[1][1]["end"])
                    if overlap<=0:
                        raise RuntimeError("DECODER_THREAD_OVERLAP_MISSING")
                    wave_overlaps.append(overlap)
                # Wait for all possible prefills and verify actual retained bytes.
                producers={key:future.result(timeout=30) for key,future in all_futures.items()}
                for key,future in policy.cache.items():
                    if future.result()["bytes"]!=planned_cache_bytes(model,len(key)):
                        raise RuntimeError("RETAINED_CACHE_ACTUAL_SIZE_MISMATCH")
                wall=time.perf_counter()-started
                cpu=time.process_time()-process_cpu_started
            all_prefix_intervals=[{"family":v["family"],"start":v["start"],
                                   "end":v["end"],"wall_s":v["end"]-v["start"],
                                   "bytes":v["bytes"]} for v in producers.values()]
            # Actual overlap of prefilling and a decoder that does not depend on
            # the corresponding future; exact timestamps, not inferred costs.
            overlapped_total=0.0
            for v in all_prefix_intervals:
                for k,prof in enumerate(request_timings):
                    if prof["family"]==v["family"] and prof["action"] in ("hit","admit"):
                        continue
                    overlapped_total+=intervals_overlap(v["start"],v["end"],
                                                        prof["start"],prof["end"])
            if len(outputs)!=len(pattern) or any(t is None for t in outputs):
                raise RuntimeError("INCOMPLETE_OUTPUT")
            if policy.count["hits"]+policy.count["misses"]!=len(pattern):
                raise RuntimeError("CACHE_ACCOUNTING_FAILURE")
            if policy.count["admissions"]!=admitted_future_count:
                raise RuntimeError("DUPLICATE_PREFILL_ACCOUNTING")
            if max_reserved_bytes>CAP_BYTES or max(v["entries"] for v in cache_occupancy)>CAP_ENTRIES:
                raise RuntimeError("BAD_CACHE_BUDGET")
            if arm=="no_cache" and (all_futures or max_reserved_bytes>0 or policy.count["hits"]>0):
                raise RuntimeError("NO_CACHE_ARM_RETAINED_STATE")
            return outputs,{
                "wall_s":wall,"cpu_s":cpu,"tokens_per_s":len(pattern)*TOKENS/wall,
                "policy_count":dict(policy.count),
                "prefill_producers":len(all_prefix_intervals),
                "deduplicated_pending_waits":deduped_waits,
                "producer_intervals":all_prefix_intervals,
                "producer_sum_wall_s":sum(v["wall_s"] for v in all_prefix_intervals),
                "prefill_over_unrelated_decode_s":overlapped_total,
                "wave_decode_overlap_s":wave_overlaps,
                "reserved_cache_peak_bytes":max_reserved_bytes,
                "final_retained_cache_bytes":sum(planned_cache_bytes(model,len(k)) for k in policy.cache),
                "sampled_rss_max_bytes":max(mon.samples),
                "rss_sample_count":len(mon.samples),
                "cache_occupancy":cache_occupancy,
                "request_timings":request_timings,
                "total_future_wait_s":sum(v["cached_future_wait_s"] for v in request_timings),
                "total_kv_copy_s":sum(v["kv_deepcopy_s"] for v in request_timings),
            }

        def equal(a,b,label):
            if len(a)!=len(b) or any(not torch.equal(x,y) for x,y in zip(a,b)):
                raise RuntimeError("GREEDY_TOKEN_PARITY_FAILURE_"+label)

        for cohort,pattern in STREAMS.items():
            base,_=execute(pattern,"no_cache")
            for arm in ARMS[1:]:
                alt,_=execute(pattern,arm)
                equal(base,alt,cohort+"_"+arm)
            for arm in ARMS:execute(pattern,arm)
            pairs=[]
            for n in range(REPEATS):
                ordered=list(ARMS[n:]+ARMS[:n])
                if n%2:ordered.reverse()
                timings={}
                for arm in ordered:
                    output,info=execute(pattern,arm)
                    equal(base,output,cohort+"_trial_"+str(n)+"_"+arm)
                    timings[arm]=info
                pairs.append({
                    "trial":n+1,"order":ordered,"arms":timings,
                    "overlap_over_serial":timings["serialized_prefill"]["wall_s"]/timings["overlapped_singleflight"]["wall_s"],
                    "overlap_over_no_cache":timings["no_cache"]["wall_s"]/timings["overlapped_singleflight"]["wall_s"],
                    "serial_over_no_cache":timings["no_cache"]["wall_s"]/timings["serialized_prefill"]["wall_s"]
                })
            result.setdefault("cohorts",{})[cohort]={
                "reference_sha256":[hashlib.sha256(t.numpy().tobytes()).hexdigest() for t in base],
                "pairs":pairs,
                "median_overlap_over_serial":statistics.median(t["overlap_over_serial"] for t in pairs),
                "median_overlap_over_no_cache":statistics.median(t["overlap_over_no_cache"] for t in pairs),
                "median_serial_over_no_cache":statistics.median(t["serial_over_no_cache"] for t in pairs)
            }
        unique=result["cohorts"]["unique_only"]
        for t in unique["pairs"]:
            for arm in ARMS:
                if t["arms"][arm]["prefill_producers"]!=0 or t["arms"][arm]["reserved_cache_peak_bytes"]!=0:
                    raise RuntimeError("UNIQUE_PREFIX_CACHE_NONZERO")
        high=result["cohorts"]["high_locality"]
        overlaps=[t["arms"]["overlapped_singleflight"]["prefill_over_unrelated_decode_s"]
                  for t in high["pairs"]]
        result["correctness"]="PASS"
        result["overlap_observed"]=max(overlaps)>0
        result["screen"]="PASS" if (
            high["median_overlap_over_serial"]>=THRESHOLDS["overlap_over_serial"]
            and high["median_overlap_over_no_cache"]>=THRESHOLDS["overlap_over_no_cache"]
            and unique["median_overlap_over_no_cache"]>=THRESHOLDS["unique_over_no_cache"]
            and result["overlap_observed"]
        ) else "FAIL"
    except Exception as exc:
        result["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g62_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps({k:result.get(k) for k in
            ("gate","correctness","screen","overlap_observed","error")},sort_keys=True))
        for name,data in result.get("cohorts",{}).items():
            print(json.dumps({"cohort":name,
                "overlap_over_serial":data["median_overlap_over_serial"],
                "overlap_over_no_cache":data["median_overlap_over_no_cache"],
                "serial_over_no_cache":data["median_serial_over_no_cache"]
            },sort_keys=True))

if __name__=="__main__":
    main()
