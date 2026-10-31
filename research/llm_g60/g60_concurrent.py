#!/usr/bin/env python3
"""G60 pinned GPT-2 two-worker concurrent prefix-cache screen (not serving qualification).

Frozen before execution: docs/research/G60-GPT2-CONCURRENT-PREFIX-PREREG.md
No accepted scientific/native/production state is changed by this program.
"""
import collections
import concurrent.futures
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
WEIGHT_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
PREREG_COMMIT = "3b9707887e73a2e38486c65bcc0da37af2ac9dd3"
ARMS = ("no_cache", "second_seen", "adaptive")
STREAMS = {
    "high_locality": (0, 0, 0, 0, 1, 1),
    "unique_only": (0, 1, 2, 3, 4, 5),
    "thrash": (0, 1, 2, 0, 1, 2),
}
REPEATS = 3
TOKENS = 16
WORKERS = 2
CAP_ENTRIES = 2
CAP_BYTES = 42_000_000
THRESHOLDS = {"high_locality": 1.10, "unique_only": 0.95}


def load(name, location):
    p = Path(__file__).resolve().parents[1] / location
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


class RSSMonitor:
    """Samples true process RSS regularly; not a precise high-water mark."""
    def __init__(self, process):
        self.process = process
        self.done = threading.Event()
        self.samples = []
        self.worker = None

    def __enter__(self):
        self.samples = [self.process.memory_info().rss]
        self.worker = threading.Thread(target=self.poll, daemon=True)
        self.worker.start()
        return self

    def poll(self):
        while not self.done.is_set():
            self.samples.append(self.process.memory_info().rss)
            self.done.wait(.01)

    def __exit__(self, *_):
        self.done.set()
        self.worker.join(timeout=2)
        self.samples.append(self.process.memory_info().rss)


def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    g55 = load("g55_g60", "llm_g55/g55_gpt2_controls.py")
    g58 = load("g58_g60", "llm_g58/g58_selective_cache.py")
    g59 = load("g59_g60", "llm_g59/g59_adaptive.py")
    if (g55.REV,g55.WEIGHT_SHA,g59.MODEL_REV,g59.MODEL_SHA)!=(REV,WEIGHT_SHA,REV,WEIGHT_SHA):
        raise RuntimeError("FROZEN_GPT2_IDENTITY_MISMATCH")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    report = {
      "gate": "G60", "preregistration_commit": PREREG_COMMIT,
      "git_commit": os.getenv("GITHUB_SHA", "UNSET"),
      "kind": "TWO_WORKER_PARALLEL_CPU_KV_INFERENCE_RESEARCH_ONLY",
      "model_revision": REV, "weight_sha256": WEIGHT_SHA,
      "torch":torch.__version__, "transformers":transformers.__version__,
      "platform":platform.platform(), "trials":REPEATS, "workers":WORKERS,
      "tokens_per_request":TOKENS,"max_entries":CAP_ENTRIES,"max_kv_bytes":CAP_BYTES,
      "arms":ARMS,"streams":STREAMS,"screen_thresholds":THRESHOLDS,
      "correctness":"UNVERIFIED","performance_screen":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "limitations":["Single CPU instance, 2 worker threads, not production HTTP server",
        "Waves of two, deterministic coordinator cache admission, not arbitrary arrival concurrency",
        "Peak sampled RSS at 10ms granularity, not exact process peak",
        "No true OS pressure, GPU, microbatch scheduler, energy or native models",
        "Tokenization and model loading excluded from paired request latencies"]
    }
    try:
        root, files=g55.stage()
        report["model_file_sha256"]=files
        report["manifest_sha256"]=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                                                   trust_remote_code=False,use_safetensors=True).eval()
        if model.config.model_type!="gpt2" or model.config.is_encoder_decoder:
            raise RuntimeError("GPT2_ARCHITECTURE_MISMATCH")

        def ids(txt):
            return tok(txt,add_special_tokens=False,return_tensors="pt")["input_ids"]
        prefix=[ids(g55.PREFIX+f" Family {i} has a unique context marker.") for i in range(6)]
        suffix=[ids(f" Request {i}: state the bounded validation requirement.") for i in range(6)]
        keys=[tuple(x[0].tolist()) for x in prefix]
        if len(set(keys))!=6: raise RuntimeError("PREFIX_IDENTITY_COLLISION")
        if max(p.shape[1] for p in prefix)+max(s.shape[1] for s in suffix)+TOKENS>model.config.n_positions:
            raise RuntimeError("MODEL_CONTEXT_LIMIT_EXCEEDED")
        report["prefix_sha256"]=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in prefix]
        report["suffix_sha256"]=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in suffix]
        proc=psutil.Process()

        def decode(first,past=None,prefix_length=0):
            import copy
            with torch.inference_mode():
                total=first.shape[1]+prefix_length
                kw={"input_ids":first,"use_cache":True}
                if past is not None:
                    kw.update({"past_key_values":copy.deepcopy(past),
                               "attention_mask":torch.ones((1,total),dtype=torch.long)})
                out=model(**kw)
                cached,logits=out.past_key_values,out.logits[:,-1,:]
                output=[]
                for step in range(TOKENS):
                    token=logits.argmax(dim=-1,keepdim=True)
                    output.append(token)
                    if step<TOKENS-1:
                        out=model(input_ids=token,past_key_values=cached,
                                  attention_mask=torch.ones((1,total+step+1),dtype=torch.long),
                                  use_cache=True)
                        cached,logits=out.past_key_values,out.logits[:,-1,:]
                return torch.cat(output,dim=1)

        def run_stream(pattern, arm):
            policy=g59.Policy(arm)
            tokens=[None]*len(pattern)
            metrics=[None]*len(pattern)
            max_retained=0
            events=[]
            stream_start=time.perf_counter()
            cpu_start=time.process_time()
            with RSSMonitor(proc) as monitor, concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
                for wave in range(0,len(pattern),2):
                    barrier=threading.Barrier(WORKERS,timeout=25)
                    jobs=[]
                    for idx in (wave,wave+1):
                        family=pattern[idx]
                        key=keys[family]
                        arrival=time.perf_counter()
                        action,previous=policy.begin(key,CAP_ENTRIES)
                        if action=="admit":
                            with torch.inference_mode():
                                value=model(input_ids=prefix[family],use_cache=True).past_key_values
                            policy.insert(key,value,CAP_ENTRIES)
                            previous=value
                        policy.finish(key,CAP_ENTRIES,action)
                        retained=sum(g58.tensor_nbytes(c) for c in policy.cache.values())
                        # This hard bound is on retained tensors (not transient forwards).
                        while retained>CAP_BYTES and policy.cache:
                            policy.cache.popitem(last=False)
                            policy.count["evictions"]+=1
                            retained=sum(g58.tensor_nbytes(c) for c in policy.cache.values())
                        if retained>CAP_BYTES: raise RuntimeError("HARD_KV_BUDGET_EXCEEDED")
                        if action in ("hit","admit"):
                            if previous is None:
                                raise RuntimeError("CACHED_PATH_MISSING_PAST")
                            input_ids=suffix[idx]
                            plen=int(prefix[family].shape[1])
                        else:
                            input_ids=torch.cat((prefix[family],suffix[idx]),dim=1)
                            plen=0
                        max_retained=max(max_retained,retained)
                        jobs.append((idx,input_ids,previous,plen,action,arrival,retained))
                        events.append({"request":idx,"family":family,"action":action,
                                       "retained_kv_bytes":retained,"cache_entries":len(policy.cache)})
                    def task(args):
                        idx,initial,past,plen,action,arrival,retained=args
                        barrier.wait()
                        started=time.perf_counter()
                        output=decode(initial,past,plen)
                        ended=time.perf_counter()
                        return idx,output,{"action":action,"arrival":arrival,"start":started,
                                           "end":ended,"latency_s":ended-arrival}
                    futures=[pool.submit(task,entry) for entry in jobs]
                    wave_results=[f.result() for f in futures]
                    for idx,out,m in wave_results:
                        tokens[idx]=out
                        metrics[idx]=m
                    intervals=[(m["start"],m["end"]) for _,_,m in wave_results]
                    overlap=min(v[1] for v in intervals)-max(v[0] for v in intervals)
                    if overlap<=0: raise RuntimeError("NO_CONCURRENT_FORWARD_OVERLAP")
                    events[-2]["wave_overlap_s"]=overlap
                    events[-1]["wave_overlap_s"]=overlap
                wall_s=time.perf_counter()-stream_start
                cpu_s=time.process_time()-cpu_start
            info={"wall_s":wall_s,"cpu_s":cpu_s,"sampled_max_rss_bytes":max(monitor.samples),
                  "rss_before_bytes":monitor.samples[0],"rss_after_bytes":monitor.samples[-1],
                  "rss_sample_count":len(monitor.samples),"retained_kv_max_bytes":max_retained,
                  "throughput_tokens_per_s":len(pattern)*TOKENS/wall_s,
                  "request_latency_s":[m["latency_s"] for m in metrics],
                  "request_p95_latency_s":sorted(m["latency_s"] for m in metrics)[-1],
                  "events":events,"policy_counts":dict(policy.count)}
            if len(tokens)!=len(pattern) or any(x is None for x in tokens):
                raise RuntimeError("MISSING_REQUEST_OUTPUT")
            if policy.count["hits"]+policy.count["misses"]!=len(pattern):
                raise RuntimeError("HIT_MISS_ACCOUNTING_MISMATCH")
            if info["retained_kv_max_bytes"]>CAP_BYTES or policy.count["max_cache_entries"]>CAP_ENTRIES:
                raise RuntimeError("CACHE_CAP_EXCEEDED")
            if arm=="no_cache" and (policy.cache or policy.count["hits"] or policy.count["admissions"]):
                raise RuntimeError("BASELINE_INCORRECTLY_CACHED")
            return tokens,info

        def compare(reference,candidate,what):
            if len(reference)!=len(candidate) or any(not torch.equal(a,b) for a,b in zip(reference,candidate)):
                raise RuntimeError("TOKEN_OUTPUT_MISMATCH_"+what)

        for scenario,pattern in STREAMS.items():
            baseline,info=run_stream(pattern,"no_cache")
            all_sha=[hashlib.sha256(t.numpy().tobytes()).hexdigest() for t in baseline]
            for arm in ARMS[1:]:
                alt,_=run_stream(pattern,arm)
                compare(baseline,alt,scenario+"_correctness_"+arm)
            for arm in ARMS: run_stream(pattern,arm)   # untimed warmup
            trials=[]
            for rep in range(REPEATS):
                order=list(ARMS[rep:]+ARMS[:rep])
                if rep%2:order.reverse()
                results={}
                for arm in order:
                    out,dat=run_stream(pattern,arm)
                    compare(baseline,out,scenario+"_"+arm+"_"+str(rep))
                    results[arm]=dat
                trials.append({
                    "trial":rep+1,"order":order,"arms":results,
                    "adaptive_speedup":results["no_cache"]["wall_s"]/results["adaptive"]["wall_s"],
                    "second_seen_speedup":results["no_cache"]["wall_s"]/results["second_seen"]["wall_s"]
                })
            row={"reference_output_sha256":all_sha,"trials":trials,
                 "median_adaptive_speedup":statistics.median(t["adaptive_speedup"] for t in trials),
                 "median_second_seen_speedup":statistics.median(t["second_seen_speedup"] for t in trials),
                 "median_adaptive_throughput_tokens_s":statistics.median(t["arms"]["adaptive"]["throughput_tokens_per_s"] for t in trials),
                 "median_no_cache_throughput_tokens_s":statistics.median(t["arms"]["no_cache"]["throughput_tokens_per_s"] for t in trials)}
            report.setdefault("scenarios",{})[scenario]=row
        unique=report["scenarios"]["unique_only"]["trials"]
        for t in unique:
            if t["arms"]["adaptive"]["retained_kv_max_bytes"]!=0:
                raise RuntimeError("UNIQUE_FAMILY_NONZERO_CACHE_BYTES")
        report["correctness"]="PASS"
        report["performance_screen"]="PASS" if all(
            report["scenarios"][name]["median_adaptive_speedup"] >= limit
            for name,limit in THRESHOLDS.items()) else "FAIL"
    except Exception as exc:
        report["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g60_result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        print(json.dumps({key:report.get(key) for key in ("gate","correctness","performance_screen","error")},sort_keys=True))
        for name,row in report.get("scenarios",{}).items():
            print(json.dumps({"scenario":name,"adaptive":row["median_adaptive_speedup"],
                         "second_seen":row["median_second_seen_speedup"],
                         "adaptive_tokens_s":row["median_adaptive_throughput_tokens_s"]},sort_keys=True))


if __name__=="__main__":
    main()
