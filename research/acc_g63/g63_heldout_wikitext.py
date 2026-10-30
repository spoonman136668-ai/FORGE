#!/usr/bin/env python3
"""ACC G63: authentic 1.1B RTX SDPA speculation on externally sourced WikiText-2."""
from __future__ import annotations
import hashlib, json, math, os, platform, statistics, time, urllib.request
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g62"))
from g62_prompt_lookup import audited_continuation, sha256 as file_sha256

CORPUS_REV="acc295dc7b90714f1bf47f06004fc19a7fe235c4"
CORPUS_PATH="word_language_model/data/wikitext-2/test.txt"
CORPUS_URL=f"https://raw.githubusercontent.com/pytorch/examples/{CORPUS_REV}/{CORPUS_PATH}"
CORPUS_BLOB="6f3fc88e4cd88456ea892971f9f12243e8428624"
CORPUS_SIZE=1256449
REPO="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
REV="c13e4efb205d7a8e5d13c088aa10a9dabac9b96a"
WEIGHT_SHA="6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933"
WEIGHT_SIZE=2200119864
FILES=("config.json","generation_config.json","model.safetensors",
       "tokenizer.json","tokenizer_config.json","special_tokens_map.json")
ANCHORS=(.17,.45,.73)
TASKS=("natural_continuation","source_question")
CONTEXTS=(512,1536)
Q_SUFFIX="Question: Based on the passage, state the main distinction and why it matters. Answer in your own words:\n"
GEN=64
WARMUPS=2
PAIRS=5
OUT=Path(os.getenv("G63_OUTPUT","g63_result.json"))
CORPUS_FILE=Path(os.environ.get("G63_CORPUS_PATH","g63_wikitext_test.txt"))

def git_blob_sha1(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def frozen_source(p:Path)->bytes:
    if not p.is_file():
        with urllib.request.urlopen(CORPUS_URL,timeout=40) as stream:
            raw=stream.read(CORPUS_SIZE+1)
        if len(raw)!=CORPUS_SIZE or git_blob_sha1(raw)!=CORPUS_BLOB:
            raise RuntimeError("WIKITEXT_SOURCE_OR_GIT_BLOB_DRIFT")
        p.write_bytes(raw)
    raw=p.read_bytes()
    if len(raw)!=CORPUS_SIZE or git_blob_sha1(raw)!=CORPUS_BLOB:
        raise RuntimeError("WIKITEXT_SOURCE_OR_GIT_BLOB_DRIFT")
    return raw

def paired_order(i:int):
    return ("baseline","candidate") if i%2==0 else ("candidate","baseline")

def trigram_overlap(prompt_tokens:list[int],output_tokens:list[int])->float:
    if len(output_tokens)<3:
        return 0.
    seen=set(zip(prompt_tokens,prompt_tokens[1:],prompt_tokens[2:]))
    gs=list(zip(output_tokens,output_tokens[1:],output_tokens[2:]))
    return sum(x in seen for x in gs)/len(gs)

def frozen_sample_tokens(tok,text:str,anchor_fraction:float):
    anchor=int(anchor_fraction*len(text))
    if anchor>=len(text) or anchor<0:raise RuntimeError("INVALID_ANCHOR")
    excerpt=text[anchor:anchor+30000]
    ids=tok(excerpt,add_special_tokens=False,truncation=True,
            max_length=max(CONTEXTS),return_tensors="pt")["input_ids"][0]
    if ids.shape[0]<max(CONTEXTS):
        raise RuntimeError(f"WIKITEXT_ANCHOR_TOO_SHORT:{anchor_fraction}")
    return ids

def case_ids(torch,tok,anchor_tokens,task,ctx):
    if task=="natural_continuation":
        ids=anchor_tokens[:ctx].clone()
    elif task=="source_question":
        suffix=tok(Q_SUFFIX,add_special_tokens=False,return_tensors="pt")["input_ids"][0]
        if suffix.numel()>=ctx:raise RuntimeError("QUESTION_SUFFIX_TOO_LONG")
        ids=torch.cat((anchor_tokens[:ctx-suffix.numel()],suffix),0)
    else:
        raise ValueError("UNKNOWN_CASE")
    if ids.numel()!=ctx:raise RuntimeError("PROMPT_LENGTH_DRIFT")
    return ids.reshape(1,-1)

def decision(cases):
    if len(cases)!=12:raise ValueError("EXPECTED_TWELVE_CASES")
    all_ratio=[x["ratio_baseline_over_candidate"] for x in cases]
    q=[x["ratio_baseline_over_candidate"] for x in cases if x["task"]=="source_question"]
    if len(q)!=6:raise ValueError("SIX_QUESTION_CASES_REQUIRED")
    geo=math.exp(sum(math.log(x) for x in all_ratio)/len(all_ratio))
    qgeo=math.exp(sum(math.log(x) for x in q)/len(q))
    qual=(geo>=1.15 and qgeo>=1.0 and min(q)>=.85 and
      all(x["tokens_exact"] and
          x["candidate_peak_allocated_mib"]<=1.10*x["baseline_peak_allocated_mib"]
          for x in cases))
    return ("GO_EXTERNAL_CORPUS_ENGINEERING" if qual else "NO_GO_GENERALIZATION",geo,qgeo)

def run():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    report={"schema":"forge.acc.g63.heldout_wikitext2_sdpa_speculation.v1",
            "gate":"ACC-G63","status":"UNVERIFIED",
            "head_sha":os.environ.get("GITHUB_SHA",""),
            "platform":platform.platform(),"torch":torch.__version__,
            "cuda_runtime":torch.version.cuda,"transformers":transformers.__version__,
            "corpus_repo":"pytorch/examples","corpus_git_revision":CORPUS_REV,
            "corpus_blob_expected":CORPUS_BLOB,
            "model_repo":REPO,"model_revision":REV,"expected_weight_sha256":WEIGHT_SHA,
            "science_acceptance":"NOT_GRANTED","novel_mechanism":False,
            "production_optimized_serving":False,
            "heldout_scope":"held-out from G62 acceleration selection, not assured absent from pretraining"}
    try:
        raw=frozen_source(CORPUS_FILE)
        report["corpus_git_blob_actual"]=git_blob_sha1(raw)
        report["corpus_sha256"]=hashlib.sha256(raw).hexdigest()
        report["corpus_bytes"]=len(raw)
        corpus=raw.decode("utf-8")
        if not torch.cuda.is_available() or not torch.version.cuda or tuple(map(int,torch.version.cuda.split(".")[:2]))<(12,8):
            raise RuntimeError("CUDA_12_8_MISSING_NO_CPU_FALLBACK")
        device=torch.device("cuda:0")
        gpu=torch.cuda.get_device_name(device)
        cc=torch.cuda.get_device_capability(device)
        free,total=torch.cuda.mem_get_info(device)
        if cc!=(12,0) or "NVIDIA" not in gpu.upper() or free<7000*1024**2:
            raise RuntimeError("REAL_RTX_GPU_ADMISSION_FAILED")
        x=torch.ones((1024,1024),device=device);y=x@x
        torch.cuda.synchronize(device)
        if y.device.type!="cuda" or abs(y[0,0].item()-1024)>.001:
            raise RuntimeError("REAL_CUDA_KERNEL_FAILED")
        del x,y;torch.cuda.empty_cache()
        report["gpu"]={"name":gpu,"capability":list(cc),
           "free_mib":free//1024**2,"total_mib":total//1024**2}
        snapshot=Path(snapshot_download(repo_id=REPO,revision=REV,token=False,allow_patterns=list(FILES)))
        weight=snapshot/"model.safetensors"
        if not weight.is_file() or weight.stat().st_size!=WEIGHT_SIZE or file_sha256(weight)!=WEIGHT_SHA:
            raise RuntimeError("AUTHENTIC_TINYLLAMA_WEIGHT_DRIFT")
        report["actual_weight_sha256"]=file_sha256(weight)
        tok=AutoTokenizer.from_pretrained(str(snapshot),use_fast=True,local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(
            str(snapshot),torch_dtype=torch.float16,attn_implementation="sdpa",
            use_safetensors=True,trust_remote_code=False,local_files_only=True).eval().to(device)
        if model.config.model_type!="llama" or model.config.num_hidden_layers!=22 or model.config._attn_implementation!="sdpa":
            raise RuntimeError("MODEL_OR_OPTIMIZED_SDPA_ARCH_DRIFT")
        from torch.profiler import profile,ProfilerActivity
        with torch.inference_mode(),profile(activities=[ProfilerActivity.CPU]) as prof:
            model(input_ids=torch.tensor([[1,10,20,30]],dtype=torch.long,device=device),use_cache=True)
            torch.cuda.synchronize(device)
        if "aten::scaled_dot_product_attention" not in [e.key for e in prof.key_averages()]:
            raise RuntimeError("ACTUAL_OPTIMIZED_SDPA_OPERATOR_MISSING")
        report["optimized_attention_operator_proof"]="PASS"

        def generate(ids,arm):
            calls={"n":0}
            def hook(*_args,**_kwargs):calls["n"]+=1
            handle=model.register_forward_pre_hook(hook)
            kwargs=dict(input_ids=ids,do_sample=False,num_beams=1,use_cache=True,
                        max_new_tokens=GEN,eos_token_id=-1,pad_token_id=tok.eos_token_id)
            if arm=="candidate":
                kwargs.update(prompt_lookup_num_tokens=5,max_matching_ngram_size=3)
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
            start=time.perf_counter()
            try:
                result=model.generate(**kwargs)
            finally:
                handle.remove()
            torch.cuda.synchronize(device)
            elapsed=time.perf_counter()-start
            sequence=result[0,ids.shape[1]:].detach().cpu().tolist()
            normalized,raw_count=audited_continuation(sequence,arm)
            return {"seconds":elapsed,"token_ids":normalized,"raw_count":raw_count,
                    "forward_calls":calls["n"],
                    "extra_generated_tokens_charged":raw_count-GEN,
                    "peak_allocated_mib":torch.cuda.max_memory_allocated(device)/1024**2,
                    "peak_reserved_mib":torch.cuda.max_memory_reserved(device)/1024**2}

        cases=[]
        begin=time.perf_counter()
        with torch.inference_mode():
            for idx,fraction in enumerate(ANCHORS):
                source_tokens=frozen_sample_tokens(tok,corpus,fraction)
                for task in TASKS:
                    for ctx in CONTEXTS:
                        prompt_ids=case_ids(torch,tok,source_tokens,task,ctx).to(device)
                        if ctx+GEN+5>model.config.max_position_embeddings:
                            raise RuntimeError("OVER_MODEL_POSITION_LIMIT")
                        for arm in ("baseline","candidate"):
                            for _ in range(WARMUPS):
                                generate(prompt_ids,arm)
                        pairs={"baseline":[],"candidate":[]}
                        for i in range(PAIRS):
                            current={}
                            for arm in paired_order(i):
                                obs=generate(prompt_ids,arm)
                                current[arm]=obs
                                pairs[arm].append(obs)
                            if current["baseline"]["token_ids"]!=current["candidate"]["token_ids"]:
                                raise RuntimeError(f"CORPUS_TOKEN_PARITY_FAILED:{idx}:{task}:{ctx}:{i}")
                        baseline_s=statistics.median(x["seconds"] for x in pairs["baseline"])
                        candidate_s=statistics.median(x["seconds"] for x in pairs["candidate"])
                        if min(baseline_s,candidate_s)<=0:raise RuntimeError("NONPOSITIVE_REAL_GPU_TIMING")
                        overlap=trigram_overlap(prompt_ids[0].cpu().tolist(),pairs["baseline"][0]["token_ids"])
                        keep=("seconds","raw_count","extra_generated_tokens_charged","forward_calls",
                              "peak_allocated_mib","peak_reserved_mib")
                        case={"anchor_index":idx,"anchor_fraction":fraction,
                              "task":task,"context_tokens":ctx,"generated_tokens":GEN,
                              "baseline_median_s":baseline_s,
                              "candidate_median_s":candidate_s,
                              "ratio_baseline_over_candidate":baseline_s/candidate_s,
                              "baseline_forward_calls_median":statistics.median(x["forward_calls"] for x in pairs["baseline"]),
                              "candidate_forward_calls_median":statistics.median(x["forward_calls"] for x in pairs["candidate"]),
                              "baseline_peak_allocated_mib":max(x["peak_allocated_mib"] for x in pairs["baseline"]),
                              "candidate_peak_allocated_mib":max(x["peak_allocated_mib"] for x in pairs["candidate"]),
                              "baseline_peak_reserved_mib":max(x["peak_reserved_mib"] for x in pairs["baseline"]),
                              "candidate_peak_reserved_mib":max(x["peak_reserved_mib"] for x in pairs["candidate"]),
                              "baseline_runs":[{k:v[k] for k in keep} for v in pairs["baseline"]],
                              "candidate_runs":[{k:v[k] for k in keep} for v in pairs["candidate"]],
                              "tokens_exact":True,
                              "generated_trigram_overlap_with_prompt":overlap,
                              "generated_token_sha256":hashlib.sha256(
                                  json.dumps(pairs["baseline"][0]["token_ids"]).encode()).hexdigest()}
                        cases.append(case)
                        print(f"G63_CASE anchor={idx} task={task} ctx={ctx} ratio={case['ratio_baseline_over_candidate']:.4f} overlap={overlap:.3f}",flush=True)
        disposition,geo,qgeo=decision(cases)
        report.update({"cases":cases,"status":"PASS_AUTHENTIC_EXTERNAL_CORPUS_GPU_SCREEN",
                       "disposition":disposition,"geomean_all":geo,
                       "geomean_source_question":qgeo,
                       "gpu_benchmark_wall_s":time.perf_counter()-begin})
    except Exception as e:
        report.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
        raise
    finally:
        OUT.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G63_STATUS="+report["status"],flush=True)
        if report.get("disposition"):print("G63_DISPOSITION="+report["disposition"],flush=True)
if __name__=="__main__":run()
