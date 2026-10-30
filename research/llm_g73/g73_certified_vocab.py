#!/usr/bin/env python3
"""G73 frozen authentic GPT-2 exact vocabulary-head elimination screen.

No science/production acceptance. Separately pre-registered before source.
"""
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

MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REPO="openai/grade-school-math"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_FILE="grade_school_math/data/test.jsonl"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_SIZE=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
PREREG_COMMIT="2ce3ed5a979aeffb2c56e01ad9cfd11b0d1f1063"
HELDOUT_START=48
CASES=12
TOKENS=8
CPU_BUDGET=3
PREFIX_DIM=384
SEED_COUNT=64
FALLBACK_COUNT=8192
PAIRS=5
VOCAB=50257
DIM=768
NUMERIC_GUARD=0.001
THRESHOLDS={"prune_fraction":0.50,"fallback_fraction":0.0,"head_speedup":1.20,
            "amortized_speedup":1.15,"min_pair_ratio":0.80,"rss_ratio":1.10}

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def load_module(name,relative):
    p=Path(__file__).resolve().parents[1]/relative
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def ranked_human(records,n):
    eligible=[]
    for row,item in enumerate(records):
        if not isinstance(item,dict):continue
        question=item.get("instruction","")
        category=item.get("category","")
        if isinstance(question,str) and question.strip() and isinstance(category,str) and category.strip():
            eligible.append((hashlib.sha256(SEED+question.encode()).hexdigest(),row,question,category))
    eligible.sort(key=lambda z:(z[0],z[1]))
    result=[];seen=set()
    for digest,row,question,category in eligible:
        if question in seen:continue
        seen.add(question)
        result.append({"source_row":row,"instruction":question,"category":category,
                       "instruction_sha256":hashlib.sha256(question.encode()).hexdigest(),
                       "rank_sha256":digest})
        if len(result)==n:break
    if len(result)!=n:raise RuntimeError("G73_INSUFFICIENT_ORIGINAL_HUMAN_ROWS")
    return result

def safely_excluded(partial,bound,incumbent):
    """Conservative real-number Cauchy upper-bound rule with numerical slack."""
    if not (math.isfinite(partial) and math.isfinite(bound) and math.isfinite(incumbent)):
        return False
    if bound<0:return False
    guard=NUMERIC_GUARD*(abs(partial)+abs(bound)+abs(incumbent)+1.0)
    return partial+bound+guard<incumbent

def contract():
    assert (HELDOUT_START,CASES,TOKENS,CPU_BUDGET)==(48,12,8,3)
    assert (PREFIX_DIM,SEED_COUNT,FALLBACK_COUNT,PAIRS,VOCAB,DIM)==(384,64,8192,5,50257,768)
    assert THRESHOLDS=={"prune_fraction":0.50,"fallback_fraction":0.0,"head_speedup":1.20,
                        "amortized_speedup":1.15,"min_pair_ratio":0.80,"rss_ratio":1.10}
    assert safely_excluded(-4.0,1.0,0.0)
    assert not safely_excluded(-0.00001,0.0,0.0)
    assert not safely_excluded(float("nan"),0.0,0.0)

def certified_head(h,weight,residual_norms,torch):
    """Returns token, pruned count, exactly-scored count and fallback.

    No reference logits, labels, known token or future hidden state are passed in.
    """
    import torch.nn.functional as F
    partial=torch.mv(weight[:,:PREFIX_DIM],h[:PREFIX_DIM])
    upper_residual=torch.linalg.vector_norm(h[PREFIX_DIM:])*residual_norms
    # Float32 arithmetic: conservative guard; all outputs also externally
    # checked against independent full reference argmax in original experiment.
    seeds=torch.topk(partial,SEED_COUNT,sorted=False).indices
    initial=F.linear(h,weight.index_select(0,seeds))
    incumbent=initial.max()
    guard=NUMERIC_GUARD*(partial.abs()+upper_residual.abs()+incumbent.abs()+1)
    possible=partial+upper_residual+guard>=incumbent
    possible[seeds]=True
    uncertain=int(possible.sum().item())
    if uncertain>FALLBACK_COUNT:
        exact=F.linear(h,weight)
        return int(exact.argmax().item()),0,VOCAB,True
    indices=possible.nonzero(as_tuple=False).reshape(-1)
    exact=F.linear(h,weight.index_select(0,indices))
    # 'indices' sorted ascending and argmax is first-on-tie.
    return int(indices[int(exact.argmax().item())].item()),VOCAB-uncertain,uncertain,False

def main():
    contract()
    import psutil
    import torch
    import torch.nn.functional as F
    import transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    receipt={
      "schema":"forge.llm-evaluation.g73.original-vocab-head.v1",
      "gate":"G73","source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "preregistration_commit":PREREG_COMMIT,"model_revision":MODEL_REV,
      "weights_sha256":WEIGHTS_SHA,"dataset_revision":DATA_REV,
      "dataset_sha256":DATA_SHA,"dataset_license":"MIT",
      "toolchain":{"torch":torch.__version__,"transformers":transformers.__version__,
                   "platform":platform.platform()},
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "classification":"AUTHENTIC_GPT2_HEAD_ONLY_RESEARCH_NOT_FULL_DECODER",
      "engineering":"UNVERIFIED","correctness":"UNVERIFIED","performance":"UNVERIFIED",
      "limitations":["Output-head only; cannot claim full-decoder acceleration",
                     "One physical CPU environment and twelve disjoint human GSM8K questions",
                     "Sampled process RSS, not physical peak; full model and index resident",
                     "Numerical slack is conservative, not an independently formal IEEE interval proof",
                     "No scientific or production accepted-ref promotion"]}
    proc=psutil.Process()
    initial_affinity=None
    try:
        raw=Path("g73_gsm8k_original_pinned.jsonl")
        url="https://raw.githubusercontent.com/"+DATA_REPO+"/"+DATA_REV+"/"+DATA_FILE
        request=urllib.request.Request(url,headers={"User-Agent":"FORGE-G73-Original-GPT2-Research/1"})
        with urllib.request.urlopen(request,timeout=45) as stream,raw.open("xb") as out:
            count=0
            while True:
                chunk=stream.read(1024*1024)
                if not chunk:break
                count+=len(chunk)
                if count>800000:raise RuntimeError("G73_GSM8K_SIZE_CAP")
                out.write(chunk)
        if raw.stat().st_size!=DATA_SIZE or sha256_file(raw)!=DATA_SHA:
            raise RuntimeError("G73_AUTHENTIC_DATASET_IDENTITY_FAILED")
        with raw.open(encoding="utf-8") as stream:
            records=[{"instruction":o["question"],"category":"math_word_problem"}
                     for o in (json.loads(l) for l in stream if l.strip())]
        ranking=ranked_human(records,60)
        g68=load_module("g73_original_g68","llm_g68/g68_gsm8k_http.py")
        g70=load_module("g73_original_g70","llm_g70/g70_gsm8k_locality.py")
        g72=load_module("g73_original_g72_heldout","llm_g70/g70_gsm8k_locality.py")
        if (g68.select_heldout(records)!=ranking[0:12] or
            g70.select_heldout(records)!=ranking[12:24] or
            len({z["source_row"] for z in ranking})!=60):
            raise RuntimeError("G73_FROZEN_PRIOR_RANKING_IDENTITY_DRIFT")
        # Preserve G71/G72 rank partitions without importing closed unmerged sources.
        receipt["prior_ranks"]={"G68":[z["source_row"] for z in ranking[0:12]],
                                "G70":[z["source_row"] for z in ranking[12:24]],
                                "G71":[z["source_row"] for z in ranking[24:36]],
                                "G72":[z["source_row"] for z in ranking[36:48]]}
        selected=ranking[48:60]
        receipt["heldout"]=[{k:v for k,v in z.items() if k!="instruction"} for z in selected]
        g55=load_module("g73_original_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G73_FROZEN_G55_MODEL_MISMATCH")
        start_stage=time.perf_counter()
        root,manifest=g55.stage()
        receipt["model_stage_wall_s"]=time.perf_counter()-start_stage
        receipt["model_file_manifest"]=manifest
        receipt["model_manifest_sha256"]=sha256_file(root/"manifest.json")
        tokenizer=AutoTokenizer.from_pretrained(str(root),trust_remote_code=False,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(root),use_safetensors=True,
                         trust_remote_code=False,local_files_only=True).eval()
        if (model.config.model_type!="gpt2" or model.config.n_embd!=DIM or
            model.config.vocab_size!=VOCAB or next(model.parameters()).dtype!=torch.float32):
            raise RuntimeError("G73_WRONG_MODEL_ARCH_OR_DTYPE")
        weight=model.lm_head.weight.detach()
        if tuple(weight.shape)!=(VOCAB,DIM):
            raise RuntimeError("G73_HEAD_WEIGHT_SHAPE_MISMATCH")
        if not hasattr(proc,"cpu_affinity"):
            raise RuntimeError("G73_CPU_AFFINITY_UNAVAILABLE")
        initial_affinity=proc.cpu_affinity()
        if len(initial_affinity)<CPU_BUDGET:
            raise RuntimeError("G73_INSUFFICIENT_CPUS")
        proc.cpu_affinity(initial_affinity[:CPU_BUDGET])
        receipt["affinity_fixed"]=proc.cpu_affinity()
        # Precompute costs are NOT hidden from the amortized candidate decision.
        t0=time.perf_counter()
        with torch.inference_mode():
            residual_norms=torch.linalg.vector_norm(weight[:,PREFIX_DIM:],dim=1)
        norm_seconds=time.perf_counter()-t0
        receipt["norm_construction_s"]=norm_seconds
        receipt["norm_index_bytes"]=int(residual_norms.numel()*residual_norms.element_size())
        if not torch.isfinite(residual_norms).all():
            raise RuntimeError("G73_NORM_INDEX_NONFINITE")
        def ids(s):
            return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        public=ids("A public nonheldout vocabulary screening phrase.")
        with torch.inference_mode():
            warm=model(input_ids=public,use_cache=True)
            warm_hidden=model.transformer(input_ids=public,use_cache=True).last_hidden_state[0,-1,:]
            if int(warm.logits[0,-1,:].argmax())!=int(F.linear(warm_hidden,weight).argmax()):
                raise RuntimeError("G73_PUBLIC_REFERENCE_HIDDEN_PARITY_FAILED")
            certified_head(warm_hidden,weight,residual_norms,torch)
        # Freeze real model-produced continuation states before timing heads.
        states=[]
        hidden_source_wall_start=time.perf_counter()
        with torch.inference_mode():
            for selected_item in selected:
                suffix=ids(selected_item["instruction"])[:,:64]
                prefix=ids(g55.PREFIX)
                full=torch.cat((prefix,suffix),dim=1)
                if int(full.shape[1])+TOKENS>model.config.n_positions:
                    raise RuntimeError("G73_CONTEXT_TOO_LONG")
                past=None;cur=full;steps=[]
                for j in range(TOKENS):
                    out=model.transformer(input_ids=cur,past_key_values=past,use_cache=True)
                    h=out.last_hidden_state[0,-1,:].detach().clone()
                    baseline_token=int(F.linear(h,weight).argmax().item())
                    if j==0:
                        whole=model(input_ids=full,use_cache=True)
                        if int(whole.logits[0,-1,:].argmax().item())!=baseline_token:
                            raise RuntimeError("G73_FIRST_HELDOUT_REFERENCE_MISMATCH")
                    states.append({"hidden":h,"expected":baseline_token,
                                   "row":selected_item["source_row"],"step":j})
                    steps.append(baseline_token)
                    past=out.past_key_values
                    cur=torch.tensor([[baseline_token]],dtype=torch.long)
                receipt.setdefault("per_prompt_token_sha256",[]).append({
                    "source_row":selected_item["source_row"],
                    "token_sha256":hashlib.sha256(json.dumps(steps,separators=(",",":")).encode()).hexdigest(),
                    "input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest()})
        receipt["hidden_collection_wall_s"]=time.perf_counter()-hidden_source_wall_start
        if len(states)!=CASES*TOKENS:raise RuntimeError("G73_NOT_96_REAL_HIDDEN_STATES")
        receipt["hidden_states"]=len(states)
        receipts=[];rss_baseline=[];rss_candidate=[]
        with torch.inference_mode():
            for sample_index,state in enumerate(states):
                hidden=state["hidden"]
                for rep in range(PAIRS):
                    # AB/BA alternation: equal original tensor and model.
                    order=("candidate","full") if (rep+sample_index)%2==0 else ("full","candidate")
                    entry={"sample":sample_index,"row":state["row"],"step":state["step"],
                           "rep":rep+1,"order":order}
                    observed={}
                    for arm in order:
                        cpu0=time.process_time_ns()
                        wall0=time.perf_counter_ns()
                        if arm=="candidate":
                            tok,pruned,scored,fallback=certified_head(hidden,weight,residual_norms,torch)
                        else:
                            tok=int(F.linear(hidden,weight).argmax().item())
                        dt=time.perf_counter_ns()-wall0
                        dc=time.process_time_ns()-cpu0
                        rss=int(proc.memory_info().rss)
                        observed[arm]={"token":tok,"wall_ns":dt,"cpu_ns":dc,"rss":rss}
                        if arm=="candidate":
                            observed[arm].update({"pruned":pruned,"scored":scored,"fallback":fallback})
                            rss_candidate.append(rss)
                        else:rss_baseline.append(rss)
                    if any(v["token"]!=state["expected"] for v in observed.values()):
                        raise RuntimeError("G73_ORIGINAL_EXACT_NEXT_TOKEN_MISMATCH_SAMPLE_"+str(sample_index))
                    entry["measure"]=observed
                    receipts.append(entry)
        if len(receipts)!=CASES*TOKENS*PAIRS:
            raise RuntimeError("G73_MISSING_PAIRED_MEASURES")
        baseline_ns=sum(z["measure"]["full"]["wall_ns"] for z in receipts)
        candidate_ns=sum(z["measure"]["candidate"]["wall_ns"] for z in receipts)
        ratios=[z["measure"]["full"]["wall_ns"]/max(1,z["measure"]["candidate"]["wall_ns"])
                for z in receipts]
        med_base=statistics.median(z["measure"]["full"]["wall_ns"] for z in receipts)
        med_cand=statistics.median(z["measure"]["candidate"]["wall_ns"] for z in receipts)
        prune_fractions=[z["measure"]["candidate"]["pruned"]/VOCAB for z in receipts]
        fallback_fraction=sum(int(z["measure"]["candidate"]["fallback"]) for z in receipts)/len(receipts)
        amortized_ratio=(baseline_ns/1e9)/(candidate_ns/1e9+norm_seconds)
        rss_ratio=max(rss_candidate)/max(rss_baseline)
        receipt["measurements"]=receipts
        receipt["summary"]={"paired_calls":len(receipts),
           "median_baseline_head_ns":med_base,"median_candidate_head_ns":med_cand,
           "median_head_speedup":med_base/max(1,med_cand),
           "amortized_wall_speedup":amortized_ratio,
           "minimum_individual_pair_ratio":min(ratios),
           "median_pruned_fraction":statistics.median(prune_fractions),
           "fallback_fraction":fallback_fraction,
           "sampled_rss_ratio":rss_ratio,
           "median_scored_tokens":statistics.median(z["measure"]["candidate"]["scored"] for z in receipts)}
        receipt["correctness"]="PASS";receipt["engineering"]="PASS"
        summary=receipt["summary"]
        receipt["performance"]="GO" if (
          summary["median_pruned_fraction"]>=THRESHOLDS["prune_fraction"]
          and summary["fallback_fraction"]<=THRESHOLDS["fallback_fraction"]
          and summary["median_head_speedup"]>=THRESHOLDS["head_speedup"]
          and summary["amortized_wall_speedup"]>=THRESHOLDS["amortized_speedup"]
          and summary["minimum_individual_pair_ratio"]>=THRESHOLDS["min_pair_ratio"]
          and summary["sampled_rss_ratio"]<=THRESHOLDS["rss_ratio"]) else "NO_GO"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2000:]
        raise
    finally:
        if initial_affinity is not None:
            receipt["affinity_after"]=proc.cpu_affinity()
            proc.cpu_affinity(initial_affinity)
        Path("g73_original_result.json").write_text(
          json.dumps(receipt,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in
            ("gate","engineering","correctness","performance","error","summary")},sort_keys=True),flush=True)

if __name__=="__main__":
    main()
