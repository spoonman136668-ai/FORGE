#!/usr/bin/env python3
"""Original GPT-2 whole 8-token decode: no-mask cached state vs best controls."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time
import traceback
import urllib.request

PREREG="5b0ad0551ed0a7027eca9bfba2ceba3cdbb64fb7"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_SIZE=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=108
CASES=12
TOKENS=8
REPEATS=4
CPU_BUDGET=3
ARMS=("explicit_mask","hf_generate","minimal_state")
FROZEN={"median_speedup":1.15,"minimum_paired_ratio":0.80,
        "p95_ratio_max":1.10,"rss_ratio_max":1.10}

def contract():
    assert (OFFSET,CASES,TOKENS,REPEATS,CPU_BUDGET)==(108,12,8,4,3)
    assert ARMS==("explicit_mask","hf_generate","minimal_state")
    assert FROZEN=={"median_speedup":1.15,"minimum_paired_ratio":0.80,
                   "p95_ratio_max":1.10,"rss_ratio_max":1.10}

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def load_module(name,path):
    p=Path(__file__).resolve().parents[1]/path
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def rank_original(records,n):
    rows=[]
    for row,item in enumerate(records):
        q=item.get("instruction","")
        c=item.get("category","")
        if isinstance(q,str) and q.strip() and isinstance(c,str) and c.strip():
            rows.append((hashlib.sha256(SEED+q.encode()).hexdigest(),row,q,c))
    rows.sort(key=lambda x:(x[0],x[1]))
    seen=set();out=[]
    for digest,row,q,c in rows:
        if q in seen:continue
        seen.add(q)
        out.append({"source_row":row,"instruction":q,"category":c,
                    "instruction_sha256":hashlib.sha256(q.encode()).hexdigest(),
                    "rank_sha256":digest})
        if len(out)==n:break
    if len(out)!=n:raise RuntimeError("G79_INSUFFICIENT_UNSEEN_ORIGINAL_INPUTS")
    return out

def p95(values):
    return sorted(values)[max(0,math.ceil(len(values)*.95)-1)]

def order_for(sample,rep):
    order=list(ARMS[(sample+rep)%len(ARMS):]+ARMS[:(sample+rep)%len(ARMS)])
    if rep%2:order.reverse()
    return tuple(order)

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    proc=psutil.Process();old_aff=None
    receipt={"schema":"forge.cpu-llm-evaluation.g79.original-minstate-full-decode.v1",
       "gate":"CPU_G79","preregistration_commit":PREREG,
       "source_sha":os.getenv("GITHUB_SHA","UNSET"),
       "original_model_revision":MODEL_REV,
       "original_weight_sha256":WEIGHTS_SHA,
       "original_data_revision":DATA_REV,
       "original_data_sha256":DATA_SHA,
       "environment":{"torch":torch.__version__,"transformers":transformers.__version__,
          "python":platform.python_version(),"platform":platform.platform()},
       "engineering":"UNVERIFIED","correctness":"UNVERIFIED","performance":"UNVERIFIED",
       "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
       "limitations":["Single original GPT-2 FP32 Linux CPU, no RTX GPU or batch throughput extrapolation",
         "Whole original 8-token decode, not localhost HTTP service or natural network arrivals",
         "Same GSM8K original corpus family, new unused heldout question ranks",
         "Sampled RSS is not true physical memory peak; no energy measurement",
         "No accepted model, FORGE controller, Wingless/Yggdrasil or production activation"]}
    try:
        raw=Path("cpu_g79_original_gsm8k.jsonl")
        req=urllib.request.Request(
           "https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/grade_school_math/data/test.jsonl",
           headers={"User-Agent":"FORGE-CPU-G79-Original-GPT2-State-Minimization/1"})
        with urllib.request.urlopen(req,timeout=45) as inp,raw.open("xb") as out:
            count=0
            while True:
                b=inp.read(1<<20)
                if not b:break
                count+=len(b)
                if count>800000:raise RuntimeError("G79_ORIGINAL_DATASET_TOO_LARGE")
                out.write(b)
        if raw.stat().st_size!=DATA_SIZE or sha256_file(raw)!=DATA_SHA:
            raise RuntimeError("G79_ORIGINAL_DATA_SHA_LENGTH_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":v["question"],"category":"math_word_problem"}
                    for v in (json.loads(line) for line in f if line.strip())]
        ranked=rank_original(records,OFFSET+CASES)
        g68=load_module("g79_orig_g68","llm_g68/g68_gsm8k_http.py")
        g70=load_module("g79_orig_g70","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(records) or ranked[12:24]!=g70.select_heldout(records):
            raise RuntimeError("G79_ORIGINAL_RANK_HISTORY_DRIFT")
        if len({x["source_row"] for x in ranked})!=OFFSET+CASES:
            raise RuntimeError("G79_ORIGINAL_HELDOUT_NOT_UNIQUE")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["heldout_ranks"]=[OFFSET,OFFSET+CASES-1]
        receipt["heldout"]=[{k:v for k,v in x.items() if k!="instruction"} for x in selected]
        g55=load_module("g79_original_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G79_ORIGINAL_G55_SOURCE_DRIFT")
        stage_t0=time.perf_counter()
        root,files=g55.stage()
        receipt["model_stage_s"]=time.perf_counter()-stage_t0
        receipt["model_manifest_sha256"]=sha256_file(root/"manifest.json")
        receipt["model_files"]=files
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),use_safetensors=True,
                    local_files_only=True,trust_remote_code=False).eval()
        if (model.config.model_type!="gpt2" or model.config.is_encoder_decoder
            or next(model.parameters()).dtype!=torch.float32):
            raise RuntimeError("G79_WRONG_ORIGINAL_MODEL_ARCH_OR_DTYPE")
        if not hasattr(proc,"cpu_affinity"):raise RuntimeError("G79_AFFINITY_UNAVAILABLE")
        old_aff=proc.cpu_affinity()
        if len(old_aff)<CPU_BUDGET:raise RuntimeError("G79_INSUFFICIENT_CORES")
        proc.cpu_affinity(old_aff[:CPU_BUDGET])
        receipt["fixed_affinity"]=proc.cpu_affinity()
        receipt["torch_num_threads"]=torch.get_num_threads()
        receipt["torch_num_interop_threads"]=torch.get_num_interop_threads()
        def ids(x):return tokenizer(x,return_tensors="pt",add_special_tokens=False)["input_ids"]

        def explicit_mask(full):
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                length=int(full.shape[1])
                chosen=[]
                for step in range(TOKENS):
                    token=logits.argmax(-1,keepdim=True)
                    chosen.append(token)
                    if step+1<TOKENS:
                        mask=torch.ones((1,length+step+1),dtype=torch.long)
                        out=model(input_ids=token,past_key_values=past,
                                  attention_mask=mask,use_cache=True)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                return torch.cat(chosen,dim=1).flatten().tolist()

        def hf_generate(full):
            with torch.inference_mode():
                out=model.generate(input_ids=full,attention_mask=torch.ones_like(full),
                    pad_token_id=tokenizer.eos_token_id,eos_token_id=None,
                    max_new_tokens=TOKENS,min_new_tokens=TOKENS,
                    num_beams=1,do_sample=False,use_cache=True)
                return out[:,full.shape[1]:].flatten().tolist()

        def minimal_state(full):
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                response=torch.empty((1,TOKENS),dtype=torch.long)
                for step in range(TOKENS):
                    next_token=logits.argmax(-1,keepdim=True)
                    response[:,step]=next_token[:,0]
                    if step+1<TOKENS:
                        # Original GPT-2 implicit attention mask + cached positions.
                        # No user mask, no estimated output / alternate model.
                        out=model(input_ids=next_token,past_key_values=past,use_cache=True)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                return response.flatten().tolist()

        funcs={"explicit_mask":explicit_mask,"hf_generate":hf_generate,"minimal_state":minimal_state}
        public=ids("A public nonheldout example of original language decoding.")
        with torch.inference_mode():
            expected=explicit_mask(public)
            for name in ARMS:
                observed=funcs[name](public)
                if observed!=expected:
                    raise RuntimeError("G79_PUBLIC_ORIGINAL_GREEDY_TOKEN_PARITY_"+name)
        prompts=[]
        for selected_item in selected:
            full=torch.cat((ids(g55.PREFIX),ids(selected_item["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>model.config.n_positions:
                raise RuntimeError("G79_ORIGINAL_CONTEXT_CAP")
            prompts.append((selected_item["source_row"],full))
        trials=[]
        with torch.inference_mode():
            for sample,(row,full) in enumerate(prompts):
                independent_ref=explicit_mask(full)
                if len(independent_ref)!=TOKENS:raise RuntimeError("G79_ORIGINAL_TOKEN_COUNT")
                for rep in range(REPEATS):
                    order=order_for(sample,rep)
                    values={}
                    for arm in order:
                        cpu0=time.process_time_ns()
                        wall0=time.perf_counter_ns()
                        output=funcs[arm](full)
                        elapsed=time.perf_counter_ns()-wall0
                        proc_ns=time.process_time_ns()-cpu0
                        if output!=independent_ref:
                            raise RuntimeError("G79_ORIGINAL_HELDOUT_TOKEN_MISMATCH_"+arm+"_"+str(sample)+"_"+str(rep))
                        if len(output)!=TOKENS:raise RuntimeError("G79_OUTPUT_LENGTH_DRIFT")
                        values[arm]={"wall_ns":elapsed,"process_cpu_ns":proc_ns,
                            "rss_sampled_bytes":proc.memory_info().rss,
                            "original_greedy_token_sha256":hashlib.sha256(json.dumps(output,separators=(",",":")).encode()).hexdigest()}
                    trials.append({"sample_index":sample,"source_row":row,"rep":rep+1,
                        "original_input_tokens":int(full.shape[1]),
                        "input_id_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                        "order":order,"measure":values})
        if len(trials)!=CASES*REPEATS or len(trials)*len(ARMS)!=144:
            raise RuntimeError("G79_MISSING_ORIGINAL_PAIRED_RESPONSES")
        summaries={}
        for arm in ARMS:
            vals=[t["measure"][arm]["wall_ns"] for t in trials]
            summaries[arm]={"median_wall_ns":statistics.median(vals),
                "p95_wall_ns":p95(vals),
                "sampled_max_rss_bytes":max(t["measure"][arm]["rss_sampled_bytes"] for t in trials),
                "timed_original_responses":len(vals)}
        fastest=min(("explicit_mask","hf_generate"),key=lambda a:summaries[a]["median_wall_ns"])
        ratios=[t["measure"][fastest]["wall_ns"]/max(1,t["measure"]["minimal_state"]["wall_ns"]) for t in trials]
        summary={"timed_original_responses":len(trials)*len(ARMS),
            "original_greedy_tokens":len(trials)*len(ARMS)*TOKENS,
            "unique_original_heldout_requests":CASES,"repetitions_per_arm":REPEATS,
            "fastest_other_arm":fastest,"median_speedup_vs_fastest":summaries[fastest]["median_wall_ns"]/summaries["minimal_state"]["median_wall_ns"],
            "minimum_paired_speedup":min(ratios),
            "p95_ratio_vs_fastest":summaries["minimal_state"]["p95_wall_ns"]/summaries[fastest]["p95_wall_ns"],
            "sampled_rss_ratio_vs_fastest":summaries["minimal_state"]["sampled_max_rss_bytes"]/summaries[fastest]["sampled_max_rss_bytes"]}
        receipt["original_pairs"]=trials;receipt["arm_summaries"]=summaries;receipt["summary"]=summary
        receipt["correctness"]="PASS";receipt["engineering"]="PASS"
        receipt["performance"]="GO" if (
          summary["median_speedup_vs_fastest"]>=FROZEN["median_speedup"]
          and summary["minimum_paired_speedup"]>=FROZEN["minimum_paired_ratio"]
          and summary["p95_ratio_vs_fastest"]<=FROZEN["p95_ratio_max"]
          and summary["sampled_rss_ratio_vs_fastest"]<=FROZEN["rss_ratio_max"]) else "NO_GO"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2300:]
        raise
    finally:
        if old_aff is not None:
            receipt["affinity_after"]=proc.cpu_affinity()
            proc.cpu_affinity(old_aff)
        Path("cpu_g79_original_result.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({key:receipt.get(key) for key in
          ("gate","engineering","correctness","performance","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__": main()
