#!/usr/bin/env python3
"""Independent CPU G74 layer-major batching comparison. No promotion."""
import concurrent.futures
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
PREREG="000ed3607eaa0b55313f9d0f5387a0f87262bdc1"
SEED=b"G68-GPT2-HELDOUT-20261030:"
SELECT_OFFSET=60
CASES=12
WAVE=3
TOKENS=8
REPEATS=3
CPU_BUDGET=3
ARMS=("solo_serial","solo_parallel","hf_batched","layer_major")
THRESHOLDS={"median_speedup":1.15,"min_wave_ratio":0.90,"p95_wave_ratio":1.20,"sampled_rss_ratio":1.10}

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def load_module(name,relative):
    path=Path(__file__).resolve().parents[1]/relative
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def rank_original_human(records,n):
    eligible=[]
    for row,record in enumerate(records):
        if not isinstance(record,dict):continue
        question=record.get("instruction","")
        category=record.get("category","")
        if isinstance(question,str) and question.strip() and isinstance(category,str) and category.strip():
            eligible.append((hashlib.sha256(SEED+question.encode()).hexdigest(),row,question,category))
    eligible.sort(key=lambda z:(z[0],z[1]))
    seen=set();ranked=[]
    for digest,row,question,category in eligible:
        if question in seen:continue
        seen.add(question)
        ranked.append({"source_row":row,"instruction":question,"category":category,
                       "rank_sha256":digest,
                       "instruction_sha256":hashlib.sha256(question.encode()).hexdigest()})
        if len(ranked)==n:break
    if len(ranked)!=n:raise RuntimeError("G74_INSUFFICIENT_AUTHENTIC_HUMAN_QUESTIONS")
    return ranked

def left_padded_tokens(sequences,pad_id):
    """Pure-data reference for per-request distinct original prompt positions."""
    longest=max(len(x) for x in sequences)
    values=[];masks=[];positions=[]
    for seq in sequences:
        if not seq: raise ValueError("G74_EMPTY_PROMPT")
        left=longest-len(seq)
        values.append([pad_id]*left+list(seq))
        masks.append([0]*left+[1]*len(seq))
        positions.append([0]*left+list(range(len(seq))))
    return values,masks,positions

def p95(values):
    return sorted(values)[max(0,math.ceil(len(values)*0.95)-1)]

def contract():
    assert (SELECT_OFFSET,CASES,WAVE,TOKENS,REPEATS,CPU_BUDGET)==(60,12,3,8,3,3)
    assert ARMS==("solo_serial","solo_parallel","hf_batched","layer_major")
    assert THRESHOLDS=={"median_speedup":1.15,"min_wave_ratio":0.90,
                        "p95_wave_ratio":1.20,"sampled_rss_ratio":1.10}
    v,m,p=left_padded_tokens([[7,8],[4],[2,3,4]],0)
    assert v==[[0,7,8],[0,0,4],[2,3,4]]
    assert m==[[0,1,1],[0,0,1],[1,1,1]]
    assert p==[[0,0,1],[0,0,0],[0,1,2]]
    assert p95(list(range(12)))==11

def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoTokenizer,AutoModelForCausalLM
    contract()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    proc=psutil.Process()
    before_affinity=None
    receipt={
      "schema":"forge.llm-evaluation.g74.original-layer-major.v1",
      "gate":"G74","preregistration_commit":PREREG,
      "source_sha":os.getenv("GITHUB_SHA","UNSET"),
      "classification":"CPU_GPT2_LAYER_MAJOR_DIRECT_BATCH_VS_HF_BATCHED_AND_SOLO",
      "model_revision":MODEL_REV,"model_safetensors_sha256":WEIGHTS_SHA,
      "dataset_revision":DATA_REV,"dataset_sha256":DATA_SHA,"dataset_license":"MIT",
      "torch":torch.__version__,"transformers":transformers.__version__,
      "platform":platform.platform(),"cpu_budget":CPU_BUDGET,
      "arms":ARMS,"repeats":REPEATS,"wave":WAVE,
      "correctness":"UNVERIFIED","engineering":"UNVERIFIED",
      "performance":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED",
      "promotion_allowed":False,
      "limitations":["Original GPT2 CPU, predeclared artificial arrival waves, not actual network traffic",
                     "Original GSM8K is same corpus family as G68–G73 (disjoint questions)",
                     "Layer-major means ordinary batch forward, not independently novel kernel",
                     "HF generate is a strong library batching control, not an external optimized server",
                     "Sampled process RSS is not true peak, no energy or GPU evaluation",
                     "No Wingless/Yggdrasil or production adoption"]}
    try:
        raw=Path("g74_original_gsm8k.jsonl")
        url="https://raw.githubusercontent.com/"+DATA_REPO+"/"+DATA_REV+"/"+DATA_FILE
        request=urllib.request.Request(url,headers={"User-Agent":"FORGE-G74-Authentic-Layer-Major/1"})
        with urllib.request.urlopen(request,timeout=45) as stream,raw.open("xb") as out:
            total=0
            while True:
                chunk=stream.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>800000:raise RuntimeError("G74_ORIGINAL_SOURCE_SIZE_CAP")
                out.write(chunk)
        if raw.stat().st_size!=DATA_SIZE or sha256_file(raw)!=DATA_SHA:
            raise RuntimeError("G74_AUTHENTIC_GSM8K_SOURCE_IDENTITY_FAILURE")
        receipt["original_source_verification"]="PASS"
        with raw.open(encoding="utf-8") as f:
            records=[{"instruction":item["question"],"category":"math_word_problem"}
                     for item in (json.loads(line) for line in f if line.strip())]
        ranking=rank_original_human(records,SELECT_OFFSET+CASES)
        g68=load_module("g74_original_g68","llm_g68/g68_gsm8k_http.py")
        g70=load_module("g74_original_g70","llm_g70/g70_gsm8k_locality.py")
        if (g68.select_heldout(records)!=ranking[:12] or
            g70.select_heldout(records)!=ranking[12:24] or
            len({x["source_row"] for x in ranking})!=72):
            raise RuntimeError("G74_ORIGINAL_RANK_DISJOINTNESS_VIOLATION")
        selected=ranking[60:72]
        receipt["prior_rank_rows"]={
            "G68":[x["source_row"] for x in ranking[:12]],
            "G70":[x["source_row"] for x in ranking[12:24]],
            "G71":[x["source_row"] for x in ranking[24:36]],
            "G72":[x["source_row"] for x in ranking[36:48]],
            "G73":[x["source_row"] for x in ranking[48:60]]
        }
        receipt["selected"]=[{k:v for k,v in item.items() if k!="instruction"} for item in selected]
        g55=load_module("g74_original_g55","llm_g55/g55_gpt2_controls.py")
        if (g55.REV,g55.WEIGHT_SHA)!=(MODEL_REV,WEIGHTS_SHA):
            raise RuntimeError("G74_AUTHENTIC_MODEL_IDENTITY_DRIFT")
        t0=time.perf_counter()
        root,files=g55.stage()
        receipt["model_stage_s"]=time.perf_counter()-t0
        receipt["model_manifest_sha256"]=sha256_file(root/"manifest.json")
        receipt["model_files"]=files
        tokenizer=AutoTokenizer.from_pretrained(str(root),trust_remote_code=False,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
                         use_safetensors=True,trust_remote_code=False).eval()
        if model.config.model_type!="gpt2" or next(model.parameters()).dtype!=torch.float32:
            raise RuntimeError("G74_UNEXPECTED_ORIGINAL_MODEL")
        def ids(s):
            return tokenizer(s,return_tensors="pt",add_special_tokens=False)["input_ids"]
        prefix=ids(g55.PREFIX)
        inputs=[]
        for row in selected:
            full=torch.cat((prefix,ids(row["instruction"])[:,:64]),dim=1)
            if full.shape[1]+TOKENS>model.config.n_positions:raise RuntimeError("G74_CONTEXT_EXCEEDED")
            inputs.append(full)
        receipt["input_hashes"]=[hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in inputs]
        receipt["lengths"]=[int(x.shape[1]) for x in inputs]
        if not hasattr(proc,"cpu_affinity"):
            raise RuntimeError("G74_CPU_AFFINITY_NOT_SUPPORTED")
        before_affinity=proc.cpu_affinity()
        if len(before_affinity)<CPU_BUDGET:raise RuntimeError("G74_INSUFFICIENT_LOGICAL_CPUS")
        proc.cpu_affinity(before_affinity[:CPU_BUDGET])
        receipt["affinity_applied"]=proc.cpu_affinity()

        def manual_one(full):
            with torch.inference_mode():
                out=model(input_ids=full,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                count=int(full.shape[1]);chosen=[]
                for j in range(TOKENS):
                    tok=logits.argmax(-1,keepdim=True)
                    chosen.append(tok)
                    if j+1<TOKENS:
                        out=model(input_ids=tok,past_key_values=past,use_cache=True,
                            attention_mask=torch.ones((1,count+j+1),dtype=torch.long))
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                return torch.cat(chosen,dim=1).flatten().tolist()

        def make_batch(wave):
            sequences=[x.flatten().tolist() for x in wave]
            ids_arr,attn_arr,pos_arr=left_padded_tokens(sequences,tokenizer.eos_token_id)
            inp=torch.tensor(ids_arr,dtype=torch.long)
            attn=torch.tensor(attn_arr,dtype=torch.long)
            pos=torch.tensor(pos_arr,dtype=torch.long)
            original_lengths=torch.tensor([len(x) for x in sequences],dtype=torch.long)
            return inp,attn,pos,original_lengths

        def batched_manual(wave):
            inp,attn,pos,lengths=make_batch(wave)
            with torch.inference_mode():
                out=model(input_ids=inp,attention_mask=attn,position_ids=pos,use_cache=True)
                past,logits=out.past_key_values,out.logits[:,-1,:]
                generated=[]
                for j in range(TOKENS):
                    next_tok=logits.argmax(dim=-1,keepdim=True)
                    generated.append(next_tok)
                    if j+1<TOKENS:
                        attn=torch.cat((attn,torch.ones((WAVE,1),dtype=torch.long)),dim=1)
                        current_pos=(lengths+j).reshape(WAVE,1)
                        out=model(input_ids=next_tok,past_key_values=past,
                                  attention_mask=attn,position_ids=current_pos,use_cache=True)
                        past,logits=out.past_key_values,out.logits[:,-1,:]
                return torch.cat(generated,dim=1).tolist()

        def batched_hf(wave):
            inp,attn,_,_=make_batch(wave)
            with torch.inference_mode():
                results=model.generate(input_ids=inp,attention_mask=attn,
                    pad_token_id=tokenizer.eos_token_id,eos_token_id=None,
                    max_new_tokens=TOKENS,min_new_tokens=TOKENS,
                    num_beams=1,do_sample=False,use_cache=True)
            return results[:,inp.shape[1]:].tolist()

        def run_arm(arm,wave):
            if arm=="solo_serial":
                return [manual_one(x) for x in wave]
            if arm=="solo_parallel":
                with concurrent.futures.ThreadPoolExecutor(max_workers=WAVE) as pool:
                    futures=[pool.submit(manual_one,x) for x in wave]
                    return [f.result(timeout=90) for f in futures]
            if arm=="hf_batched":return batched_hf(wave)
            if arm=="layer_major":return batched_manual(wave)
            raise RuntimeError("G74_UNKNOWN_ARM")

        public=ids("A public nonheldout example of original language generation.")
        with torch.inference_mode():
            sample=[public,public,public]
            expected=run_arm("solo_serial",sample)
            for arm in ARMS:
                obtained=run_arm(arm,sample)
                if obtained!=expected:raise RuntimeError("G74_PUBLIC_BATCH_POSITION_PARITY_"+arm)

        all_trials=[]
        with torch.inference_mode():
            for wave_i in range(CASES//WAVE):
                wave=inputs[wave_i*WAVE:(wave_i+1)*WAVE]
                expected=run_arm("solo_serial",wave)
                for rep in range(REPEATS):
                    order=list(ARMS[(rep+wave_i)%len(ARMS):]+ARMS[:(rep+wave_i)%len(ARMS)])
                    if rep%2:order.reverse()
                    measures={}
                    for arm in order:
                        start_cpu=time.process_time_ns()
                        start_wall=time.perf_counter_ns()
                        decoded=run_arm(arm,wave)
                        wall_ns=time.perf_counter_ns()-start_wall
                        cpu_ns=time.process_time_ns()-start_cpu
                        if decoded!=expected:
                            raise RuntimeError("G74_ORIGINAL_GENERATION_PARITY_"+arm+"_"+str(wave_i)+"_"+str(rep))
                        if len(decoded)!=WAVE or any(len(z)!=TOKENS for z in decoded):
                            raise RuntimeError("G74_INVALID_REQUEST_LENGTH")
                        measures[arm]={"wave_wall_ns":wall_ns,"wave_cpu_ns":cpu_ns,
                                     "process_rss_bytes_sample":int(proc.memory_info().rss),
                                     "output_sha256":[hashlib.sha256(json.dumps(z,separators=(",",":")).encode()).hexdigest() for z in decoded]}
                    all_trials.append({"wave":wave_i,"rep":rep+1,"order":order,"measure":measures})
        if len(all_trials)!=12 or len(all_trials)*WAVE*len(ARMS)!=144:
            raise RuntimeError("G74_MISSING_ORIGINAL_TIMED_RESPONSES")
        summaries={}
        for arm in ARMS:
            times=[t["measure"][arm]["wave_wall_ns"] for t in all_trials]
            summaries[arm]={"median_wall_ns":statistics.median(times),"p95_wall_ns":p95(times),
                            "sampled_max_rss_bytes":max(t["measure"][arm]["process_rss_bytes_sample"] for t in all_trials)}
        others=("solo_serial","solo_parallel","hf_batched")
        fastest=min(others,key=lambda a:summaries[a]["median_wall_ns"])
        speedup=summaries[fastest]["median_wall_ns"]/summaries["layer_major"]["median_wall_ns"]
        paired=[z["measure"][fastest]["wave_wall_ns"]/max(1,z["measure"]["layer_major"]["wave_wall_ns"]) for z in all_trials]
        p95_ratio=summaries["layer_major"]["p95_wall_ns"]/summaries[fastest]["p95_wall_ns"]
        rss_ratio=summaries["layer_major"]["sampled_max_rss_bytes"]/summaries[fastest]["sampled_max_rss_bytes"]
        receipt["trials"]=all_trials;receipt["arms_summary"]=summaries
        receipt["summary"]={"fastest_other_arm":fastest,"median_wave_speedup":speedup,
                            "minimum_wave_pair_ratio":min(paired),"p95_wave_ratio":p95_ratio,
                            "sampled_rss_ratio":rss_ratio,"timed_response_count":144,
                            "total_original_output_tokens":144*TOKENS}
        receipt["correctness"]="PASS";receipt["engineering"]="PASS"
        receipt["performance"]="GO" if (
            speedup>=THRESHOLDS["median_speedup"]
            and min(paired)>=THRESHOLDS["min_wave_ratio"]
            and p95_ratio<=THRESHOLDS["p95_wave_ratio"]
            and rss_ratio<=THRESHOLDS["sampled_rss_ratio"]
        ) else "NO_GO"
    except BaseException as exc:
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-2200:]
        raise
    finally:
        if before_affinity is not None:
            receipt["affinity_end"]=proc.cpu_affinity()
            proc.cpu_affinity(before_affinity)
        Path("g74_original_result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:receipt.get(k) for k in ("gate","engineering","correctness","performance","error","summary")},sort_keys=True),flush=True)

if __name__=="__main__":main()
