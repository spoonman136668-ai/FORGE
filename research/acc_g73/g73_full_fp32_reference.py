#!/usr/bin/env python3
"""G73 immutable source, authentic RTX full-model FP32 decoding reference."""
from __future__ import annotations
import gc
import hashlib
import json
import math
import os
import platform
import statistics
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g71"))
import g71_q0_fp32 as parent

g69=parent.g69
g67=g69.g67
prior=g67.prior
original=prior.original
g63=g67.g63
g64=g67.g64
G71_SOURCE_GIT_BLOB="6c38a7c8d3c93782e255f0faff293f6bfd26ae86"
G71_FINAL_GIT_BLOB="565d60d2a08d21313d5bb4bfe3fcf5fa57e8e319"
G72_FINAL_GIT_BLOB="76aed639e03381a53ff506298381276366f8bd89"
SHAKESPEARE_REPO_COMMIT="6f9487a6fe5b420b7ca9afb0d7c078e37c1d1b4e"
SHAKESPEARE_GIT_BLOB="7dcb3a2d4cc3b48b6283dd46870bfeb78f88aac9"
SHAKESPEARE_URL=("https://raw.githubusercontent.com/karpathy/char-rnn/"
                 + SHAKESPEARE_REPO_COMMIT+"/data/tinyshakespeare/input.txt")
FRESH_WINDOWS=((1024,512),(8192,512),(16384,1536),(32768,1536))
VARIANTS=("original_fp16","original_fp32_full")
MEASURED_VARIANTS=VARIANTS
ARMS=g67.ARMS
REPEATS=3
WARMUPS=2
LOGITS_MODES=prior.MODES
RESULT=Path(os.getenv("G73_RESULT","g73_result.json"))
CORPUS=Path(os.getenv("G73_CORPUS","g73_wikitext_test.txt"))
FRESH=Path(os.getenv("G73_FRESH","g73_tinyshakespeare.txt"))

def source_identity():
    if g64.git_blob(Path(parent.__file__).read_bytes())!=G71_SOURCE_GIT_BLOB:
        raise RuntimeError("ORIGINAL_G71_SCRIPT_GIT_BLOB_DRIFT")
    base=Path(__file__).resolve().parents[2]/"docs"/"research"
    f71=base/"ACC-G71-FINAL-20261030.json"
    f72=base/"ACC-G72-FINAL-20261030.json"
    if (not f71.is_file() or g64.git_blob(f71.read_bytes())!=G71_FINAL_GIT_BLOB
        or not f72.is_file() or g64.git_blob(f72.read_bytes())!=G72_FINAL_GIT_BLOB):
        raise RuntimeError("ORIGINAL_G71_G72_FINAL_GIT_BLOB_DRIFT")
    prereg=base/"ACC-G73-PREEXEC-20261030.md"
    if not prereg.is_file():raise RuntimeError("ORIGINAL_G73_PREREG_MISSING")
    return {"g71_source_git_blob":G71_SOURCE_GIT_BLOB,
            "g71_final_git_blob":G71_FINAL_GIT_BLOB,
            "g72_final_git_blob":G72_FINAL_GIT_BLOB,
            "upstream_provenance":parent.source_identity()}

def new_source_bytes():
    from urllib.request import Request,urlopen
    with urlopen(Request(SHAKESPEARE_URL,headers={"User-Agent":"FORGE-ACC-G73-Research/1.0"}),timeout=45) as response:
        payload=response.read(2_000_001)
    if len(payload)<500_000 or len(payload)>2_000_000:
        raise RuntimeError("INDEPENDENT_SHESPEARE_SOURCE_BAD_SIZE")
    if g64.git_blob(payload)!=SHAKESPEARE_GIT_BLOB:
        raise RuntimeError("EXTERNAL_FROZEN_GIT_BLOB_SHA1_DRIFT")
    payload.decode("utf-8",errors="strict")
    if FRESH.exists():raise RuntimeError("FRESH_SOURCE_TEMP_COLLISION")
    FRESH.write_bytes(payload)
    return payload

def generate_cases(torch,tokenizer,original_bytes,external_bytes,device):
    originals=g63.frozen_sample_tokens(tokenizer,original_bytes.decode("utf-8"),.73)
    known=g63.case_ids(torch,tokenizer,originals,"natural_continuation",1536).to(device)
    if prior.sha_ids(known[0].detach().cpu().tolist())!=original.G64_PROMPT_HASH:
        raise RuntimeError("ORIGINAL_G64_PROMPT_HASH_DRIFT")
    fresh_tokens=tokenizer(external_bytes.decode("utf-8"),add_special_tokens=False)["input_ids"]
    out=[{"source":"original_exposed_wikitext2","position":None,"context_tokens":1536,
          "ids":known}]
    for start,ctx in FRESH_WINDOWS:
        if len(fresh_tokens)<start+ctx:raise RuntimeError("FRESH_SOURCE_TOKEN_COUNT_DRIFT")
        ids=torch.tensor([fresh_tokens[start:start+ctx]],device=device,dtype=torch.long)
        if ids.shape!=(1,ctx) or ctx+64>2048:
            raise RuntimeError("FRESH_PROMPT_INVALID_LENGTH")
        out.append({"source":"new_shakespeare_pinned_git","position":start,
                    "context_tokens":ctx,"ids":ids})
    hashes=[prior.sha_ids(x["ids"][0].detach().cpu().tolist()) for x in out]
    if len(set(hashes))!=5:raise RuntimeError("FROZEN_PROMPTS_DUPLICATED")
    for i,row in enumerate(out):row["sha256"]=hashes[i]
    return out

def record_forced(model,prompt,shared):
    import torch
    summary={m:[] for m in LOGITS_MODES}
    for repeat in range(REPEATS):
        for mode in LOGITS_MODES:
            logits=prior.logits_forced_prefix(model,prompt,shared,mode)
            torch.cuda.synchronize(prompt.device)
            row=original.summarize_logits(logits)
            row["repeat"]=repeat
            summary[mode].append(row)
    return summary

def forced_pass(rows,want):
    if set(rows)!=set(LOGITS_MODES) or any(len(rows[m])!=REPEATS for m in LOGITS_MODES):
        raise ValueError("MISSING_NINE_FROZEN_TRACES")
    for mode in LOGITS_MODES:
        rows_mode=rows[mode]
        signature={(x["greedy_argmax_id"],x["exact_max_tie_count"],
                    x["candidate_minus_baseline_logit"]) for x in rows_mode}
        if len(signature)!=1:raise ValueError("NUMERICAL_NONDETERMINISM")
    if want=="original_fp16":
        expected={"cached_one_by_one":(7866,2),"cached_chunk_48":(29871,1),
                  "full_no_cache":(29871,1)}
    else:expected={m:(29871,1) for m in LOGITS_MODES}
    return all((x["greedy_argmax_id"],x["exact_max_tie_count"])==expected[mode]
               for mode in LOGITS_MODES for x in rows[mode])

def adjudicate(cases,forced):
    if len(cases)!=5 or set(forced)!=set(VARIANTS):
        raise ValueError("MISSING_FROZEN_FIVE_CASES_OR_TWO_MODEL_CONTROLS")
    if not forced_pass(forced["original_fp16"],"original_fp16"):
        raise ValueError("ORIGINAL_FP16_NUMERICAL_REFERENCE_DRIFT")
    if not forced_pass(forced["original_fp32_full"],"original_fp32_full"):
        raise ValueError("ORIGINAL_FP32_NUMERICAL_REFERENCE_DRIFT")
    for case in cases:
        if set(case["variants"])!=set(VARIANTS):
            raise ValueError("MISSING_ORIGINAL_PRECISION_VARIANT")
        for v in VARIANTS:
            measurements=case["variants"][v]
            if set(measurements["runs"])!=set(ARMS) or any(len(measurements["runs"][a])!=REPEATS for a in ARMS):
                raise ValueError("INCOMPLETE_ORIGINAL_REPEAT_BUDGET")
            if (not math.isfinite(measurements["median_seconds"]["baseline"])
                or measurements["median_seconds"]["baseline"]<=0):
                raise ValueError("NONPOSITIVE_ORIGINAL_LATENCY")
    if cases[0]["variants"]["original_fp16"]["comparison"]["exact"]:
        raise ValueError("ORIGINAL_G63_FP16_FAIL_NOT_REPRODUCED")
    exact=all(case["variants"]["original_fp32_full"]["comparison"]["exact"] for case in cases)
    memory=all(case["variants"]["original_fp32_full"]["peak_allocated_mib"]["candidate"]<=
               2.5*case["variants"]["original_fp16"]["peak_allocated_mib"]["candidate"]
               for case in cases)
    latency=all(case["variants"]["original_fp32_full"]["median_seconds"]["baseline"]<=
                2.5*case["variants"]["original_fp16"]["median_seconds"]["baseline"]
                for case in cases)
    ratios=[case["variants"]["original_fp32_full"]["median_seconds"]["baseline"]/
            case["variants"]["original_fp32_full"]["median_seconds"]["candidate"] for case in cases[1:]]
    if any(not math.isfinite(x) or x<=0 for x in ratios):
        raise ValueError("BAD_MATCHED_PRECISION_RATIO")
    geometric=math.exp(statistics.mean(math.log(x) for x in ratios))
    speed=geometric>=1.15 and min(ratios)>=.85
    reference=exact and memory and latency and speed
    return {"reference_screen":"REFERENCE_PRECISION_SCREEN_PASS_ONLY" if reference else "NO_GO_REFERENCE",
            "fp32_all_5_exact_64_token_parity":exact,
            "fp32_original_forced_9_unique_top1":forced_pass(forced["original_fp32_full"],"original_fp32_full"),
            "fp32_candidate_gpu_memory_lte_2p5_fp16":memory,
            "fp32_greedy_median_latency_lte_2p5_fp16":latency,
            "fp32_exposed_four_case_candidate_vs_same_precision_greedy_speed_geomean":geometric,
            "fp32_exposed_four_case_ratios":ratios,
            "fp32_exposed_four_case_speed_thresholds":speed,
            "prior_g63_original_generalization":"FAIL_NO_GO_UNCHANGED",
            "prior_g67_output_head":"NO_GO_ENGINEERING",
            "prior_g71_q0_fp32":"NO_GO_ENGINEERING",
            "prior_g72_rowwise_q0":"NO_GO_ENGINEERING",
            "scientific_acceptance":"NOT_GRANTED",
            "qualified_novel_acceleration":False}

def run():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from huggingface_hub import snapshot_download
    from torch.profiler import profile,ProfilerActivity
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    receipt={"schema":"forge.acc.g73.full-fp32-reference-pinned-original.v1",
             "status":"UNVERIFIED","source_sha":os.getenv("GITHUB_SHA",""),
             "torch":torch.__version__,"transformers":transformers.__version__,
             "cuda":torch.version.cuda,"platform":platform.platform(),
             "original_g63_generalization":"FAIL_NO_GO_UNCHANGED",
             "original_g67":"NO_GO_ENGINEERING",
             "original_g71":"NO_GO_ENGINEERING",
             "original_g72":"NO_GO_ENGINEERING",
             "scientific_acceptance":"NOT_GRANTED","cases":[]}
    try:
        receipt["upstream_identity"]=source_identity()
        data=g63.frozen_source(CORPUS)
        if hashlib.sha256(data).hexdigest()!=g64.G63_CORPUS_SHA256:
            raise RuntimeError("ORIGINAL_WIKITEXT_SOURCE_DRIFT")
        unseen=new_source_bytes()
        receipt["external_sha256"]=hashlib.sha256(unseen).hexdigest()
        receipt["external_git_blob_sha1"]=SHAKESPEARE_GIT_BLOB
        if not torch.cuda.is_available() or torch.version.cuda!="12.8":
            raise RuntimeError("ORIGINAL_CUDA_12_8_UNAVAILABLE")
        device=torch.device("cuda:0")
        free,total=torch.cuda.mem_get_info(device)
        gpu=torch.cuda.get_device_name(device)
        if (torch.cuda.get_device_capability(device)!=(12,0)
            or "NVIDIA" not in gpu.upper() or free < 7500*1024**2):
            raise RuntimeError("ORIGINAL_RTX_5070_TI_UNAVAILABLE")
        a=torch.ones((1024,1024),device=device)
        b=a@a
        torch.cuda.synchronize(device)
        if b.device.type!="cuda" or abs(float(b[0,0])-1024)>1e-4:
            raise RuntimeError("ORIGINAL_CUDA_MATMUL_NOT_PROVEN")
        del a,b
        torch.cuda.empty_cache()
        receipt["gpu"]={"name":gpu,"capability":[12,0],"total_mib":total/1024**2}
        snap=Path(snapshot_download(repo_id=g63.REPO,revision=g63.REV,token=False,
                          allow_patterns=list(g63.FILES)))
        weights=snap/"model.safetensors"
        if (not weights.is_file() or weights.stat().st_size!=g63.WEIGHT_SIZE
            or g64.file_sha256(weights)!=g63.WEIGHT_SHA):
            raise RuntimeError("ORIGINAL_TINYLLAMA_CHECKPOINT_DRIFT")
        tokenizer=AutoTokenizer.from_pretrained(str(snap),use_fast=True,
                        local_files_only=True,trust_remote_code=False)
        frozen=generate_cases(torch,tokenizer,data,unseen,device)
        receipt["prompt_hashes_sha256"]=[x["sha256"] for x in frozen]
        shared=None
        forced={}
        with torch.inference_mode():
            for variant in VARIANTS:
                dtype=torch.float32 if variant=="original_fp32_full" else torch.float16
                model=AutoModelForCausalLM.from_pretrained(
                    str(snap),torch_dtype=dtype,attn_implementation="sdpa",
                    local_files_only=True,trust_remote_code=False,
                    use_safetensors=True).eval().to(device)
                if (model.config.model_type!="llama" or model.config.num_hidden_layers!=22
                    or model.config._attn_implementation!="sdpa"
                    or next(model.parameters()).dtype!=dtype
                    or next(model.parameters()).device.type!="cuda"):
                    raise RuntimeError("ORIGINAL_ARCHITECTURE_OR_PRECISION_DRIFT")
                if variant not in VARIANTS:
                    raise RuntimeError("UNDECLARED_MODEL_VARIANT")
                with profile(activities=[ProfilerActivity.CPU]) as prof:
                    model(input_ids=frozen[0]["ids"][:,:16],use_cache=True)
                    torch.cuda.synchronize(device)
                if "aten::scaled_dot_product_attention" not in [x.key for x in prof.key_averages()]:
                    raise RuntimeError("ORIGINAL_OPTIMIZED_SDPA_OPERATOR_MISSING")
                if variant=="original_fp16":
                    validated=original.validate_orig_outputs(model,frozen[0]["ids"],tokenizer)
                    shared=torch.tensor([validated["baseline"]["first_64_token_ids"][:48]],
                                        dtype=torch.long,device=device)
                    receipt["original_g64_generation_sha_repro"]="PASS"
                if shared is None:raise RuntimeError("ORIGINAL_48_TOKEN_PREFIX_MISSING")
                forced[variant]=record_forced(model,frozen[0]["ids"],shared)
                if not forced_pass(forced[variant],variant):
                    raise RuntimeError("ORIGINAL_PINNED_PRECISION_NUMERICS_DRIFT")
                if variant in MEASURED_VARIANTS:
                    for i,c in enumerate(frozen):
                        for arm in ARMS:
                            for _ in range(WARMUPS):
                                g67.measure(model,c["ids"],tokenizer,arm)
                        measurements={a:[] for a in ARMS}
                        for rep in range(REPEATS):
                            for arm in g63.paired_order(rep):
                                measurements[arm].append(g67.measure(model,c["ids"],tokenizer,arm))
                        summary=g67.case_summary(measurements)
                        if variant=="original_fp16" and i==0:
                            if (summary["baseline_sha256"]!=original.BASELINE_SHA
                                or summary["candidate_sha256"]!=original.CANDIDATE_SHA
                                or summary["comparison"]["first_difference"]!=48
                                or summary["comparison"]["baseline_id"]!=7866
                                or summary["comparison"]["candidate_id"]!=29871):
                                raise RuntimeError("ORIGINAL_G63_FAILED_OUTPUT_REFERENCE_DRIFT")
                        if variant=="original_fp16":
                            receipt["cases"].append({"index":i,"source":c["source"],
                                 "start_offset":c["position"],"context_tokens":c["context_tokens"],
                                 "prompt_sha256":c["sha256"],"variants":{variant:summary}})
                        else:receipt["cases"][i]["variants"][variant]=summary
                        print("G73_MEASURED variant=%s case=%d parity=%s"%
                              (variant,i,summary["comparison"]["exact"]),flush=True)
                del model
                gc.collect()
                torch.cuda.empty_cache()
        receipt["original_forced_logits"]=forced
        receipt["classification"]=adjudicate(receipt["cases"],forced)
        receipt["status"]="PASS_COMPLETE_FROZEN_ORIGINAL_GPU_MEASUREMENT"
    except Exception as exc:
        receipt.update({"status":"BLOCKED_INVALID_EVIDENCE","error":type(exc).__name__+": "+str(exc)})
        raise
    finally:
        RESULT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G73_STATUS="+receipt["status"],flush=True)
        if receipt.get("classification"):
            print("G73_REFERENCE="+receipt["classification"]["reference_screen"],flush=True)

if __name__=="__main__":
    run()
