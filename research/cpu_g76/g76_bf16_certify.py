#!/usr/bin/env python3
"""Original CPU GPT-2 G76 BF16 propose + FP32 certify/repair head-only falsifier."""
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

PREREG_COMMIT="c5d854eeed8e0b7ebbc9448454dd652f72edf2e2"
MODEL_REV="607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA="248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV="3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA="3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_FILE="grade_school_math/data/test.jsonl"
DATA_BYTES=749738
SEED=b"G68-GPT2-HELDOUT-20261030:"
OFFSET=72
CASES=12
TOKENS=8
PAIRS=5
CPU_BUDGET=3
WIDTH=768
VOCAB=50257
NUMERICAL_MARGIN=0.01
U32=2**-24
GAMMA=WIDTH*U32/(1-WIDTH*U32)
LIMITS={"median_head_speedup":1.20,"amortized_speedup":1.10,
        "certified_fraction":0.80,"min_pair_ratio":0.80,"rss_ratio":1.15}

def load_module(name,path):
    p=Path(__file__).resolve().parents[1]/path
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def hash_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def rank_human(records,n):
    ranked=[]
    for row,x in enumerate(records):
        question=x.get("instruction","")
        category=x.get("category","")
        if isinstance(question,str) and question.strip() and isinstance(category,str) and category.strip():
            ranked.append((hashlib.sha256(SEED+question.encode()).hexdigest(),row,question,category))
    ranked.sort(key=lambda x:(x[0],x[1]))
    seen=set();result=[]
    for digest,row,question,category in ranked:
        if question in seen:continue
        seen.add(question)
        result.append({"source_row":row,"instruction":question,"category":category,
           "instruction_sha256":hashlib.sha256(question.encode()).hexdigest(),"rank_sha256":digest})
        if len(result)==n:break
    if len(result)!=n:raise RuntimeError("G76_MISSING_ORIGINAL_HUMAN_INPUTS")
    return result

def contract():
    assert (OFFSET,CASES,TOKENS,PAIRS,CPU_BUDGET,WIDTH,VOCAB)==(72,12,8,5,3,768,50257)
    assert LIMITS=={"median_head_speedup":1.20,"amortized_speedup":1.10,
                    "certified_fraction":0.80,"min_pair_ratio":0.80,"rss_ratio":1.15}
    assert NUMERICAL_MARGIN==0.01 and 0<GAMMA<0.001

def build_candidate_index(W,torch):
    if tuple(W.shape)!=(VOCAB,WIDTH) or W.dtype!=torch.float32:
        raise RuntimeError("G76_WRONG_ORIGINAL_LM_HEAD")
    Wb=W.to(torch.bfloat16).contiguous()
    full_norm=torch.linalg.vector_norm(W,dim=1)
    diff_norm=torch.linalg.vector_norm(W-Wb.float(),dim=1)
    cheap_norm=torch.linalg.vector_norm(Wb.float(),dim=1)
    if any(not bool(torch.isfinite(x).all()) for x in (Wb.float(),full_norm,diff_norm,cheap_norm)):
        raise RuntimeError("G76_NONFINITE_PRECOMPUTED_INDEX")
    bytes_=int(Wb.numel()*Wb.element_size()+
        sum(x.numel()*x.element_size() for x in (full_norm,diff_norm,cheap_norm)))
    return (Wb,full_norm,diff_norm,cheap_norm),bytes_

def propose_and_certify(h,W,index,torch):
    """Return exact baseline fallback or conservative candidate. No reference logits passed."""
    import torch.nn.functional as F
    if h.dtype!=torch.float32 or tuple(h.shape)!=(WIDTH,) or not bool(torch.isfinite(h).all()):
        raise RuntimeError("G76_INVALID_CURRENT_HIDDEN")
    Wb,normW,dnormW,normWb=index
    hb=h.to(torch.bfloat16)
    approx=F.linear(hb,Wb).to(torch.float32)
    if not bool(torch.isfinite(approx).all()):
        return int(F.linear(h,W).argmax().item()),False,True,VOCAB
    k=int(approx.argmax().item())
    exact_candidate=torch.dot(h,W[k])
    delta_h=torch.linalg.vector_norm(h-hb.float())
    norm_hb=torch.linalg.vector_norm(hb.float())
    error=delta_h*normW+norm_hb*dnormW+(GAMMA*norm_hb)*normWb
    guard=NUMERICAL_MARGIN*(approx.abs()+error.abs()+exact_candidate.abs()+1)
    upper=approx+error+guard
    if (not bool(torch.isfinite(exact_candidate)) or
        not bool(torch.isfinite(error).all()) or not bool(torch.isfinite(upper).all())):
        return int(F.linear(h,W).argmax().item()),False,True,VOCAB
    upper[k]=-float("inf")
    uncertain=int(torch.count_nonzero(upper >= exact_candidate).item())
    if uncertain:
        return int(F.linear(h,W).argmax().item()),False,True,uncertain
    return k,True,False,0

def main():
    import psutil
    import torch
    import torch.nn.functional as F
    import transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    p=psutil.Process()
    prior_affinity=None
    receipt={"schema":"forge.cpu-llm-evaluation.g76.original-bf16-certify.v1",
      "gate":"CPU_G76","source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "preregistration_commit":PREREG_COMMIT,
      "model_revision":MODEL_REV,"original_weights_sha256":WEIGHTS_SHA,
      "original_data_revision":DATA_REV,"original_data_sha256":DATA_SHA,
      "runtime":{"python":platform.python_version(),"platform":platform.platform(),
                 "torch":torch.__version__,"transformers":transformers.__version__},
      "classification":"ORIGINAL_GPT2_BF16_PROPOSE_FP32_CERTIFY_HEAD_ONLY",
      "scientific_acceptance":"NOT_GRANTED","promotion_allowed":False,
      "correctness":"UNVERIFIED","engineering":"UNVERIFIED","performance":"UNVERIFIED",
      "caveats":["Output head only; not whole decoder or network latency",
        "Error bound is conservative engineering guard, not formally certified all IEEE devices",
        "Original human GSM8K corpus, newly disjoint 12 examples, same source family",
        "Single pinned CPU host and sampled RSS, not physical peak or energy",
        "BF16 weight/norm precompute charged across 480 timed candidate calls",
        "GPU ACC, FORGE native model/autonomy and accepted main untouched"]}
    try:
        url="https://raw.githubusercontent.com/openai/grade-school-math/"+DATA_REV+"/"+DATA_FILE
        file=Path("g76_authentic_gsm8k_pinned.jsonl")
        req=urllib.request.Request(url,headers={"User-Agent":"FORGE-CPU-G76-GPT2-Certified-BF16/1"})
        with urllib.request.urlopen(req,timeout=45) as stream,file.open("xb") as out:
            total=0
            while True:
                b=stream.read(1<<20)
                if not b:break
                total+=len(b)
                if total>800000:raise RuntimeError("G76_RAW_SOURCE_TOO_LARGE")
                out.write(b)
        if file.stat().st_size!=DATA_BYTES or hash_file(file)!=DATA_SHA:
            raise RuntimeError("G76_ORIGINAL_DATASET_SHA_OR_LENGTH_MISMATCH")
        with file.open(encoding="utf-8") as f:
            rows=[{"instruction":v["question"],"category":"math_word_problem"}
                  for v in (json.loads(x) for x in f if x.strip())]
        ranked=rank_human(rows,OFFSET+CASES)
        g68=load_module("g76_g68_source","llm_g68/g68_gsm8k_http.py")
        g70=load_module("g76_g70_source","llm_g70/g70_gsm8k_locality.py")
        if ranked[:12]!=g68.select_heldout(rows) or ranked[12:24]!=g70.select_heldout(rows):
            raise RuntimeError("G76_ORIGINAL_RANK_SPLIT_IDENTITY_MISMATCH")
        if len({v["source_row"] for v in ranked})!=OFFSET+CASES:
            raise RuntimeError("G76_RANKS_DUPLICATED")
        selected=ranked[OFFSET:OFFSET+CASES]
        receipt["prior_splits"]={"G68":[0,11],"G70":[12,23],"G71":[24,35],
          "G72":[36,47],"G73":[48,59],"G74":[60,71],"G76":[72,83]}
        receipt["selected"]=[{k:v for k,v in z.items() if k!="instruction"} for z in selected]
        g55=load_module("g76_g55_source","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G76_ORIGINAL_PRETRAINED_MODEL_DRIFT")
        stage_start=time.perf_counter()
        root,manifest=g55.stage()
        receipt["model_stage_s"]=time.perf_counter()-stage_start
        receipt["staged_manifest_sha256"]=hash_file(root/"manifest.json")
        receipt["model_files"]=manifest
        tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                  use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G76_MODEL_ARCH_DTYPE_MISMATCH")
        W=model.lm_head.weight.detach()
        if tuple(W.shape)!=(VOCAB,WIDTH):raise RuntimeError("G76_WRONG_HEAD_DIMENSIONS")
        if not hasattr(p,"cpu_affinity"):raise RuntimeError("G76_NO_CPU_AFFINITY")
        prior_affinity=p.cpu_affinity()
        if len(prior_affinity)<CPU_BUDGET:raise RuntimeError("G76_INSUFFICIENT_CORES")
        p.cpu_affinity(prior_affinity[:CPU_BUDGET])
        receipt["fixed_affinity"]=p.cpu_affinity()
        begin=time.perf_counter()
        with torch.inference_mode():
            index,bytes_=build_candidate_index(W,torch)
        build_s=time.perf_counter()-begin
        receipt["index_precompute_s"]=build_s
        receipt["index_retained_logical_bytes"]=bytes_
        def ids(t):return tokenizer(t,return_tensors="pt",add_special_tokens=False)["input_ids"]
        # Public warmup, never use the heldout query or output as prior answer.
        public=ids("A public nonheldout demonstration of exact token inference.")
        with torch.inference_mode():
            warm=model.transformer(input_ids=public,use_cache=True).last_hidden_state[0,-1,:]
            propose_and_certify(warm,W,index,torch)
            F.linear(warm,W)
        raw_states=[]
        collect_t0=time.perf_counter()
        with torch.inference_mode():
            for question in selected:
                full=torch.cat((ids(g55.PREFIX),ids(question["instruction"])[:,:64]),dim=1)
                if full.shape[1]+TOKENS>model.config.n_positions:
                    raise RuntimeError("G76_CONTEXT_EXCEEDS_GPT2")
                past=None;current=full;out_ids=[]
                for step in range(TOKENS):
                    transformer=model.transformer(input_ids=current,past_key_values=past,use_cache=True)
                    h=transformer.last_hidden_state[0,-1,:].clone().detach()
                    original=int(F.linear(h,W).argmax().item())
                    if step==0:
                        original_model=model(input_ids=full,use_cache=True)
                        if int(original_model.logits[0,-1,:].argmax().item())!=original:
                            raise RuntimeError("G76_ORIGINAL_MODEL_FIRST_TOKEN_DRIFT")
                    raw_states.append((h,original,question["source_row"],step))
                    out_ids.append(original)
                    past=transformer.past_key_values
                    current=torch.tensor([[original]],dtype=torch.long)
                receipt.setdefault("per_question_output",[]).append({
                  "source_row":question["source_row"],
                  "input_sha256":hashlib.sha256(full.numpy().tobytes()).hexdigest(),
                  "greedy_ids_sha256":hashlib.sha256(json.dumps(out_ids,separators=(",",":")).encode()).hexdigest()})
        receipt["hidden_collection_s"]=time.perf_counter()-collect_t0
        if len(raw_states)!=CASES*TOKENS:raise RuntimeError("G76_MISSING_ORIGINAL_HIDDEN_STATES")
        receipt["real_hidden_state_count"]=len(raw_states)
        trials=[];rss_candidate=[];rss_ref=[]
        with torch.inference_mode():
            for i,(h,expected,row,step) in enumerate(raw_states):
                for rep in range(PAIRS):
                    order=("candidate","reference") if (i+rep)%2==0 else ("reference","candidate")
                    result={}
                    for arm in order:
                        start_cpu=time.process_time_ns()
                        start_wall=time.perf_counter_ns()
                        if arm=="candidate":
                            token,certified,fallback,uncertain=propose_and_certify(h,W,index,torch)
                        else:
                            token=int(F.linear(h,W).argmax().item())
                        duration=time.perf_counter_ns()-start_wall
                        process_ns=time.process_time_ns()-start_cpu
                        rss=p.memory_info().rss
                        result[arm]={"token":token,"wall_ns":duration,"cpu_ns":process_ns,"rss_sampled":rss}
                        if arm=="candidate":
                            result[arm].update({"certified":certified,"fallback":fallback,
                                                "unresolved_competitors":uncertain})
                            rss_candidate.append(rss)
                        else:rss_ref.append(rss)
                    if (result["candidate"]["token"]!=expected or result["reference"]["token"]!=expected):
                        raise RuntimeError("G76_REAL_GPT2_TOKEN_PARITY_FAILURE_"+str(i))
                    trials.append({"sample":i,"source_row":row,"token_step":step,
                                   "rep":rep+1,"order":order,"measure":result})
        if len(trials)!=CASES*TOKENS*PAIRS:
            raise RuntimeError("G76_INCOMPLETE_PAIRED_SAMPLES")
        full_ns=[t["measure"]["reference"]["wall_ns"] for t in trials]
        cand_ns=[t["measure"]["candidate"]["wall_ns"] for t in trials]
        ratios=[x/max(1,y) for x,y in zip(full_ns,cand_ns)]
        certified=sum(int(t["measure"]["candidate"]["certified"]) for t in trials)/len(trials)
        summary={"sample_count":len(trials),
                 "median_reference_ns":statistics.median(full_ns),
                 "median_candidate_ns":statistics.median(cand_ns),
                 "median_head_speedup":statistics.median(full_ns)/statistics.median(cand_ns),
                 "amortized_head_speedup":(sum(full_ns)/1e9)/(sum(cand_ns)/1e9+build_s),
                 "certified_fraction":certified,"fallback_fraction":1-certified,
                 "minimum_paired_speedup":min(ratios),
                 "sampled_rss_ratio":max(rss_candidate)/max(rss_ref)}
        receipt["measurements"]=trials
        receipt["summary"]=summary
        receipt["correctness"]="PASS"
        receipt["engineering"]="PASS"
        receipt["performance"]="GO" if (
           summary["median_head_speedup"]>=LIMITS["median_head_speedup"]
           and summary["amortized_head_speedup"]>=LIMITS["amortized_speedup"]
           and summary["certified_fraction"]>=LIMITS["certified_fraction"]
           and summary["minimum_paired_speedup"]>=LIMITS["min_pair_ratio"]
           and summary["sampled_rss_ratio"]<=LIMITS["rss_ratio"]) else "NO_GO"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2600:]
        raise
    finally:
        if prior_affinity is not None:
            receipt["affinity_end"]=p.cpu_affinity()
            p.cpu_affinity(prior_affinity)
        Path("cpu_g76_original_result.json").write_text(
          json.dumps(receipt,sort_keys=True,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({key:receipt.get(key) for key in
          ("gate","engineering","correctness","performance","summary","error")},sort_keys=True),flush=True)

if __name__=="__main__":main()
