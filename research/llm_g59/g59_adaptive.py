#!/usr/bin/env python3
"""G59 frozen adaptive prefix-policy screen on authentic GPT-2 CPU.

No original G51/G54-G58 code is modified. Policies use historical exact-token
prefix identities only; memory budgets are frozen simulated external pressure,
not an actual OS memory monitor. This is not concurrent production inference.
"""
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import time

MODEL_REV = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
MODEL_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
PREREG_COMMIT = "a5280ca7a77ca6e3a2d819d08a05e7a67cba7eb7"
OUTPUT_TOKENS = 16
TRIALS = 3
MAX_CAP = 2
ARMS = ("no_cache", "second_seen", "adaptive")
STREAMS = {
    "high_locality": ((0,0,0,0,1,1,1,1),(2,2,2,2,2,2,2,2)),
    "unique_only": ((0,1,2,3,4,5,6,7),(2,2,2,2,2,2,2,2)),
    "thrash_four": ((0,1,2,0,1,2,3,3),(2,2,2,2,2,2,2,2)),
    "alternating": ((0,1,0,1,0,1,0,1),(2,2,2,2,2,2,2,2)),
    "pressure_shift": ((0,0,0,1,1,1,0,0),(2,2,1,1,0,0,1,1)),
}
THRESHOLDS = {"high_locality":1.15,"unique_only":0.98,"thrash_four":0.97}


def load_module(name, rel):
    path=Path(__file__).resolve().parents[1]/rel
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


class Policy:
    """Causal observation only; cannot observe future requests or model answers."""
    def __init__(self, mode):
        if mode not in ARMS:
            raise ValueError("INVALID_POLICY")
        self.mode=mode
        self.cache=collections.OrderedDict()
        self.history=collections.deque(maxlen=6)
        self.count={"hits":0,"misses":0,"admissions":0,"evictions":0,
                    "max_cache_entries":0}
        self.trace=[]

    def begin(self, key, budget):
        if type(budget) is not int or budget not in (0,1,2):
            raise ValueError("INVALID_FROZEN_CACHE_BUDGET")
        while len(self.cache)>budget:
            self.cache.popitem(last=False)
            self.count["evictions"]+=1
        if key in self.cache:
            if self.mode == "no_cache":
                raise AssertionError("NO_CACHE_ARM_RETAINED_ITEM")
            self.cache.move_to_end(key)
            self.count["hits"]+=1
            return "hit",self.cache[key]
        self.count["misses"]+=1
        if self.mode=="no_cache":
            admit=False
        elif self.mode=="second_seen":
            admit=key in self.history
        else:
            admit=bool(self.history) and (
                self.history[-1]==key or sum(t==key for t in self.history)>=2
            )
        return ("admit" if admit and budget>0 else "skip"),None

    def insert(self, key, value, budget):
        if self.mode=="no_cache" or budget==0 or key in self.cache:
            raise AssertionError("UNAUTHORIZED_POLICY_INSERT")
        self.cache[key]=value
        self.count["admissions"]+=1
        while len(self.cache)>budget:
            self.cache.popitem(last=False)
            self.count["evictions"]+=1
        if len(self.cache)>MAX_CAP:
            raise AssertionError("CAP_VIOLATION")

    def finish(self, key, budget, action):
        self.history.append(key)
        if len(self.cache)>budget:
            raise AssertionError("POLICY_MEMORY_PRESSURE_VIOLATION")
        self.count["max_cache_entries"]=max(self.count["max_cache_entries"],len(self.cache))
        self.trace.append({"action":action,"retained_entries":len(self.cache),"budget":budget})


def dry_run(pattern,budgets,mode):
    if len(pattern)!=len(budgets):
        raise AssertionError("MISMATCHED_STREAM")
    p=Policy(mode)
    for family,b in zip(pattern,budgets):
        action,_=p.begin(family,b)
        if action=="admit":
            p.insert(family,object(),b)
        p.finish(family,b,action)
    return p


def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    g55=load_module("g55_g59","llm_g55/g55_gpt2_controls.py")
    g58=load_module("g58_g59","llm_g58/g58_selective_cache.py")
    if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,MODEL_SHA):
        raise RuntimeError("FROZEN_ORIGINAL_MODEL_IDENTITY_MISMATCH")
    torch.set_num_threads(1)
    receipt={
      "gate":"G59","model_revision":MODEL_REV,"weights_sha256":MODEL_SHA,
      "preregistration_commit":PREREG_COMMIT,
      "source_sha":os.getenv("GITHUB_SHA","NOT_SET"),
      "torch":torch.__version__,"transformers":transformers.__version__,
      "platform":platform.platform(),
      "output_tokens":OUTPUT_TOKENS,"repetitions":TRIALS,
      "streams":STREAMS,"arms":ARMS,"thresholds":THRESHOLDS,
      "engineering":"UNVERIFIED","screen":"UNVERIFIED",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "memory_pressure":"EXOGENOUS_FROZEN_ENTRY_BUDGET_SIMULATION",
      "limitations":["Sequential pretokenized requests only","Not real OS pressure reaction",
       "RSS point samples are not peak RSS","No optimized concurrent or batched serving",
       "No GPU, energy, model-start overhead in paired timings",
       "No native FORGE Wingless Yggdrasil model execution"]
    }
    try:
        t_start=time.perf_counter()
        root,records=g55.stage()
        receipt["model_file_records"]=records
        receipt["stage_and_load_wall_seconds"]=None
        tok=AutoTokenizer.from_pretrained(str(root),local_files_only=True,
                                          trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                 trust_remote_code=False,use_safetensors=True).eval()
        receipt["stage_and_load_wall_seconds"]=time.perf_counter()-t_start
        receipt["manifest_sha256"]=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        if model.config.model_type!="gpt2" or model.config.is_encoder_decoder:
            raise RuntimeError("MODEL_ARCH_MISMATCH")
        def ids(s):
            return tok(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        prefix=[ids(g55.PREFIX+f" Family {i} has a unique context marker.") for i in range(8)]
        suffix=[ids(f" Request {i}: state the bounded validation requirement.") for i in range(8)]
        keys=[tuple(p.flatten().tolist()) for p in prefix]
        if len(set(keys))!=8:
            raise RuntimeError("EXACT_PREFIX_COLLISION")
        max_prompt=max(p.shape[1] for p in prefix)+max(s.shape[1] for s in suffix)
        if max_prompt+OUTPUT_TOKENS>model.config.n_positions:
            raise RuntimeError("MODEL_CONTEXT_EXCEEDED")
        receipt["prefix_token_counts"]=[len(k) for k in keys]
        receipt["suffix_token_counts"]=[int(s.shape[1]) for s in suffix]
        receipt["prefix_sha256"]=[hashlib.sha256(p.numpy().tobytes()).hexdigest() for p in prefix]
        process=psutil.Process()

        def decode(initial,past=None,prefix_len=0):
            import copy
            n=int(initial.shape[1])+prefix_len
            kw={"input_ids":initial,"use_cache":True}
            if past is not None:
                kw.update({"past_key_values":copy.deepcopy(past),
                           "attention_mask":torch.ones((1,n),dtype=torch.long)})
            out=model(**kw)
            cache,logits=out.past_key_values,out.logits[:,-1,:]
            made=[]
            for i in range(OUTPUT_TOKENS):
                next_id=logits.argmax(-1,keepdim=True)
                made.append(next_id)
                if i+1<OUTPUT_TOKENS:
                    out=model(input_ids=next_id,past_key_values=cache,
                        attention_mask=torch.ones((1,n+i+1),dtype=torch.long),use_cache=True)
                    cache,logits=out.past_key_values,out.logits[:,-1,:]
            return torch.cat(made,dim=1)

        def execute(pattern,budgets,mode):
            p=Policy(mode)
            tokens=[]
            maximum_kv=0
            max_rss_sampled=0
            bytes_each=[]
            for i,(family,budget) in enumerate(zip(pattern,budgets)):
                key=keys[family]
                action,existing=p.begin(key,budget)
                if action=="hit":
                    generated=decode(suffix[i],existing,len(key))
                elif action=="admit":
                    cached=model(input_ids=prefix[family],use_cache=True).past_key_values
                    p.insert(key,cached,budget)
                    generated=decode(suffix[i],cached,len(key))
                else:
                    generated=decode(torch.cat((prefix[family],suffix[i]),dim=1))
                p.finish(key,budget,action)
                kv_bytes=sum(g58.tensor_nbytes(v) for v in p.cache.values())
                maximum_kv=max(maximum_kv,kv_bytes)
                max_rss_sampled=max(max_rss_sampled,process.memory_info().rss)
                bytes_each.append(kv_bytes)
                tokens.append(generated)
            info=dict(p.count)
            info.update({"trace":p.trace,"maximum_retained_kv_bytes":maximum_kv,
                         "per_request_retained_kv_bytes":bytes_each,
                         "max_sampled_rss_bytes":max_rss_sampled,
                         "final_retained_kv_bytes":bytes_each[-1]})
            return tokens,info

        def measured(pattern,budgets,mode):
            cpu_start=time.process_time()
            wall_start=time.perf_counter()
            out,info=execute(pattern,budgets,mode)
            info.update({"wall_s":time.perf_counter()-wall_start,
                         "process_cpu_s":time.process_time()-cpu_start})
            return out,info

        def equal(a,b,context):
            if len(a)!=len(b) or any(not torch.equal(x,y) for x,y in zip(a,b)):
                raise RuntimeError("OUTPUT_TOKEN_PARITY_FAILURE_"+context)

        with torch.inference_mode():
            for name,(pattern,budgets) in STREAMS.items():
                baseline,binfo=execute(pattern,budgets,"no_cache")
                baseline_sha=[hashlib.sha256(t.numpy().tobytes()).hexdigest() for t in baseline]
                for mode in ARMS:
                    dry=dry_run(pattern,budgets,mode)
                    output,info=execute(pattern,budgets,mode)
                    equal(baseline,output,name+"_"+mode)
                    if info["trace"]!=dry.trace or any(info[k]!=dry.count[k] for k in dry.count):
                        raise RuntimeError("POLICY_TRACE_MISMATCH_"+name+"_"+mode)
                    if any(z["retained_entries"]>z["budget"] for z in info["trace"]):
                        raise RuntimeError("MEMORY_PRESSURE_CAP_VIOLATION")
                for mode in ARMS:
                    execute(pattern,budgets,mode)  # untimed warm-up
                trials=[]
                for t in range(TRIALS):
                    order=list(ARMS[t:]+ARMS[:t])
                    if t%2:
                        order.reverse()
                    results={}
                    for mode in order:
                        generated,metrics=measured(pattern,budgets,mode)
                        equal(baseline,generated,name+"_trial_"+str(t)+"_"+mode)
                        if metrics["trace"]!=dry_run(pattern,budgets,mode).trace:
                            raise RuntimeError("REPEATED_POLICY_TRACE_DRIFT")
                        results[mode]=metrics
                    trials.append({
                       "trial":t+1,"order":order,"results":results,
                       "second_seen_speedup":results["no_cache"]["wall_s"]/results["second_seen"]["wall_s"],
                       "adaptive_speedup":results["no_cache"]["wall_s"]/results["adaptive"]["wall_s"],
                       "adaptive_cpu_speedup":results["no_cache"]["process_cpu_s"]/results["adaptive"]["process_cpu_s"],
                    })
                row={
                  "median_second_seen_speedup":statistics.median(t["second_seen_speedup"] for t in trials),
                  "median_adaptive_speedup":statistics.median(t["adaptive_speedup"] for t in trials),
                  "median_adaptive_cpu_speedup":statistics.median(t["adaptive_cpu_speedup"] for t in trials),
                  "expected_adaptive_trace":dry_run(pattern,budgets,"adaptive").trace,
                  "reference_token_sha256":baseline_sha,
                  "trials":trials
                }
                receipt.setdefault("scenarios",{})[name]=row
            unique=receipt["scenarios"]["unique_only"]["trials"][0]["results"]["adaptive"]
            if unique["admissions"]!=0 or unique["hits"]!=0 or unique["maximum_retained_kv_bytes"]!=0:
                raise RuntimeError("UNIQUE_PREFIX_NONZERO_CACHE_FAILURE")
            pressure=receipt["scenarios"]["pressure_shift"]["trials"][0]["results"]["adaptive"]
            if any(v!=0 for v,b in zip(pressure["per_request_retained_kv_bytes"],STREAMS["pressure_shift"][1]) if b==0):
                raise RuntimeError("PRESSURE_ZERO_BUDGET_BYTES_FAILURE")
            receipt["engineering"]="PASS"
            receipt["screen"]="PASS" if all(
               receipt["scenarios"][scenario]["median_adaptive_speedup"]>=threshold
               for scenario,threshold in THRESHOLDS.items()) else "FAIL"
    except Exception as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        raise
    finally:
        Path("g59_result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
        print(json.dumps({k:receipt.get(k) for k in
              ("gate","engineering","screen","error")},sort_keys=True))
        for name,item in receipt.get("scenarios",{}).items():
            print(json.dumps({"scenario":name,
                "adaptive":item["median_adaptive_speedup"],
                "second_seen":item["median_second_seen_speedup"],
                "adaptive_cpu":item["median_adaptive_cpu_speedup"],
                "max_retained_kv_bytes":max(t["results"]["adaptive"]["maximum_retained_kv_bytes"]
                    for t in item["trials"])},sort_keys=True))


if __name__=="__main__":
    main()
