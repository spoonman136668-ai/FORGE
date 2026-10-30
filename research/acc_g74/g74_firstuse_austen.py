#!/usr/bin/env python3
"""G74 immutable source, first-use Austen precision-generalization and direct cost screen."""
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
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g73"))
import g73_full_fp32_reference as parent

g69=parent.g69
g67=g69.g67
prior=g67.prior
original=prior.original
g63=g67.g63
g64=g67.g64
G73_SOURCE_GIT_BLOB="1c954f333b03621d1914795bb152ed6c8f26d701"
G73_FINAL_GIT_BLOB="219220163d073783c7351e3b608327274e926c00"
AUSTEN_REPO_COMMIT="81db45c9c48c592f0b77f01fc59e677ad0a5634e"
AUSTEN_GIT_BLOB="0a7d439c2f34b0dfacb88b7116429a9575b5735c"
AUSTEN_URL=("https://raw.githubusercontent.com/GITenberg/Pride-and-Prejudice_1342/"
            + AUSTEN_REPO_COMMIT + "/1342.txt")
FRESH_WINDOWS=((24576,512),(49152,512),(98304,1536),(196608,1536))
VARIANTS=("original_fp16","original_fp32_full")
MEASURED_VARIANTS=VARIANTS
ARMS=g67.ARMS
REPEATS=3
WARMUPS=2
LOGITS_MODES=prior.MODES
RESULT=Path(os.getenv("G74_RESULT","g74_result.json"))
CORPUS=Path(os.getenv("G74_CORPUS","g74_wikitext_test.txt"))
FRESH=Path(os.getenv("G74_FRESH","g74_austen.txt"))

def source_identity():
    if g64.git_blob(Path(parent.__file__).read_bytes())!=G73_SOURCE_GIT_BLOB:
        raise RuntimeError("ORIGINAL_G73_SOURCE_GIT_BLOB_DRIFT")
    base=Path(__file__).resolve().parents[2]/"docs"/"research"
    final=base/"ACC-G73-FINAL-20261030.json"
    pre=base/"ACC-G74-PREEXEC-20261030.md"
    if not final.is_file() or g64.git_blob(final.read_bytes())!=G73_FINAL_GIT_BLOB:
        raise RuntimeError("ORIGINAL_G73_FINAL_GIT_BLOB_DRIFT")
    if not pre.is_file():raise RuntimeError("G74_PREEXEC_NOT_FROZEN")
    return {"g73_source_git_blob":G73_SOURCE_GIT_BLOB,
            "g73_final_git_blob":G73_FINAL_GIT_BLOB,
            "upstream_provenance":parent.source_identity()}

def new_source_bytes():
    from urllib.request import Request,urlopen
    with urlopen(Request(AUSTEN_URL,headers={"User-Agent":"FORGE-ACC-G74-Research/1.0"}),timeout=45) as response:
        payload=response.read(900001)
    if len(payload)<600000 or len(payload)>900000:
        raise RuntimeError("INDEPENDENT_AUSTEN_SOURCE_BAD_SIZE")
    if g64.git_blob(payload)!=AUSTEN_GIT_BLOB:
        raise RuntimeError("FIRSTUSE_AUSTEN_PINNED_GIT_BLOB_DRIFT")
    payload.decode("utf-8",errors="strict")
    if FRESH.exists():raise RuntimeError("FRESH_AUSTEN_TEMP_COLLISION")
    FRESH.write_bytes(payload)
    return payload

def generate_cases(torch,tokenizer,original_bytes,external_bytes,device):
    originals=g63.frozen_sample_tokens(tokenizer,original_bytes.decode("utf-8"),.73)
    known=g63.case_ids(torch,tokenizer,originals,"natural_continuation",1536).to(device)
    if prior.sha_ids(known[0].detach().cpu().tolist())!=original.G64_PROMPT_HASH:
        raise RuntimeError("ORIGINAL_G64_PROMPT_HASH_DRIFT")
    prose=external_bytes.decode("utf-8",errors="strict")
    out=[{"source":"original_exposed_wikitext2","position":None,"context_tokens":1536,
          "ids":known}]
    for start,ctx in FRESH_WINDOWS:
        if len(prose)<start+20000:raise RuntimeError("FIRSTUSE_AUSTEN_CHARACTER_WINDOW_SHORT")
        # Character offsets frozen before any G74 evaluation; tokenize 20K-char
        # continuation to avoid slicing tokens out of unrelated text positions.
        tokens=tokenizer(prose[start:start+20000],add_special_tokens=False)["input_ids"]
        if len(tokens)<ctx+64:raise RuntimeError("FIRSTUSE_AUSTEN_TOKEN_WINDOW_SHORT")
        ids=torch.tensor([tokens[:ctx]],device=device,dtype=torch.long)
        if ids.shape!=(1,ctx) or ctx+64>2048:
            raise RuntimeError("FIRSTUSE_PROMPT_CONTEXT_INVALID")
        out.append({"source":"g74_firstuse_austen_git_pin","position":start,
                    "context_tokens":ctx,"ids":ids})
    hashes=[prior.sha_ids(x["ids"][0].detach().cpu().tolist()) for x in out]
    if len(hashes)!=5 or len(set(hashes))!=5:
        raise RuntimeError("FIRSTUSE_PROMPT_COLLISION")
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
        raise ValueError("MISSING_CANARY_FIRSTUSE_CASE_OR_CONTROL")
    if not forced_pass(forced["original_fp16"],"original_fp16"):
        raise ValueError("ORIGINAL_FP16_LOGIT_SIGNATURE_DRIFT")
    if not forced_pass(forced["original_fp32_full"],"original_fp32_full"):
        raise ValueError("ORIGINAL_FP32_LOGIT_SIGNATURE_DRIFT")
    for i,c in enumerate(cases):
        if set(c["variants"])!=set(VARIANTS):
            raise ValueError("MISSING_PRECISION_VARIANT")
        for v in VARIANTS:
            s=c["variants"][v]
            if set(s["runs"])!=set(ARMS) or any(len(s["runs"][arm])!=REPEATS for arm in ARMS):
                raise ValueError("INSUFFICIENT_ORIGINAL_PAIR_REPETITIONS")
            if any(not math.isfinite(s["median_seconds"][arm]) or s["median_seconds"][arm]<=0
                   for arm in ARMS):
                raise ValueError("INVALID_SOURCE_TIMING")
        if i>0 and c.get("source")!="g74_firstuse_austen_git_pin":
            raise ValueError("FRESH_SOURCE_FAMILY_DRIFT")
    if (cases[0]["source"]!="original_exposed_wikitext2"
        or cases[0]["variants"]["original_fp16"]["comparison"]["exact"]
        or not cases[0]["variants"]["original_fp32_full"]["comparison"]["exact"]):
        raise ValueError("ORIGINAL_G63_OR_G73_CANARY_DRIFT")
    fresh=cases[1:]
    exact=all(c["variants"]["original_fp32_full"]["comparison"]["exact"] for c in fresh)
    memory=all(c["variants"]["original_fp32_full"]["peak_allocated_mib"]["candidate"]<=
               2.5*c["variants"]["original_fp16"]["peak_allocated_mib"]["candidate"] for c in fresh)
    latency=all(c["variants"]["original_fp32_full"]["median_seconds"]["baseline"]<=
                2.5*c["variants"]["original_fp16"]["median_seconds"]["baseline"] for c in fresh)
    fp32_ratio=[c["variants"]["original_fp32_full"]["median_seconds"]["baseline"]/
                c["variants"]["original_fp32_full"]["median_seconds"]["candidate"] for c in fresh]
    cross_ratio=[c["variants"]["original_fp16"]["median_seconds"]["baseline"]/
                 c["variants"]["original_fp32_full"]["median_seconds"]["candidate"] for c in fresh]
    if any(not math.isfinite(x) or x<=0 for x in fp32_ratio+cross_ratio):
        raise ValueError("FIRSTUSE_SPEED_INVALID")
    fp32_geo=math.exp(statistics.mean(math.log(x) for x in fp32_ratio))
    cross_geo=math.exp(statistics.mean(math.log(x) for x in cross_ratio))
    within=fp32_geo>=1.15 and min(fp32_ratio)>=.85
    cross_speed=cross_geo>=1.15 and min(cross_ratio)>=.85
    # These hashes come from the greedy/baseline arm, not speculative candidate.
    equivalent=all(c["variants"]["original_fp16"]["baseline_sha256"]==
                   c["variants"]["original_fp32_full"]["baseline_sha256"] for c in fresh)
    ref_pass=exact and memory and latency and within
    cross_pass=ref_pass and equivalent and cross_speed
    return {"firstuse_fp32_reference_screen":"FRESH_FP32_REFERENCE_PASS_ONLY" if ref_pass else "NO_GO_REFERENCE",
            "cross_precision_practical_screen":"CROSS_PRECISION_PRACTICAL_PASS_ONLY" if cross_pass else "NO_GO_CROSS_PRECISION",
            "firstuse_fp32_exact_64_tokens_4_of_4":exact,
            "firstuse_fp32_memory_lte_2p5_fp16":memory,
            "firstuse_fp32_greedy_latency_lte_2p5_fp16":latency,
            "firstuse_fp32_internal_candidate_speed_geomean":fp32_geo,
            "firstuse_fp32_internal_four_ratios":fp32_ratio,
            "firstuse_fp32_internal_speed_bounds":within,
            "firstuse_fp16_fp32_greedy_equivalence_4_of_4":equivalent,
            "firstuse_fp16_greedy_over_fp32_candidate_geomean":cross_geo,
            "firstuse_cross_four_ratios":cross_ratio,
            "firstuse_cross_speed_bounds":cross_speed,
            "original_g63":"FAIL_NO_GO_UNCHANGED",
            "original_g73":"REFERENCE_ONLY_PASS_NOT_SCIENTIFIC",
            "scientific_acceptance":"NOT_GRANTED",
            "qualified_novel_acceleration":False,
            "pretraining_heldout_proven":False}

def run():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from huggingface_hub import snapshot_download
    from torch.profiler import profile,ProfilerActivity
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    receipt={"schema":"forge.acc.g74.firstuse-austen-direct-cost.v1",
             "status":"UNVERIFIED","source_sha":os.getenv("GITHUB_SHA",""),
             "torch":torch.__version__,"transformers":transformers.__version__,
             "cuda":torch.version.cuda,"platform":platform.platform(),
             "original_g63_generalization":"FAIL_NO_GO_UNCHANGED",
             "original_g67":"NO_GO_ENGINEERING",
             "original_g71":"NO_GO_ENGINEERING",
             "original_g72":"NO_GO_ENGINEERING",
             "original_g73":"REFERENCE_ONLY_PASS_NOT_SCIENTIFIC",
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
                        print("G74_MEASURED variant=%s case=%d parity=%s"%
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
        print("G74_STATUS="+receipt["status"],flush=True)
        if receipt.get("classification"):
            print("G74_REFERENCE="+receipt["classification"]["firstuse_fp32_reference_screen"],flush=True)
            print("G74_CROSS_PRECISION="+receipt["classification"]["cross_precision_practical_screen"],flush=True)

if __name__=="__main__":
    run()
