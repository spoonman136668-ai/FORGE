#!/usr/bin/env python3
"""ACC G70: unchanged original Q projection on frozen 1/48/1584 row shapes."""
from __future__ import annotations
import gc
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g69"))
import g69_layer0_boundaries as g69

g63=g69.g63
g64=g69.g64
original=g69.original
G69_SCRIPT_BLOB="3cac3973ba82ebc9b4d23002f98e2903093bbbba"
G69_FINAL_BLOB="cff152ffb115009ca5787095b3f3b5beae2c0dfd"
PRECISIONS=("float16","float32")
MODES=g69.MODES
REPEATS=3
MODE_TO_ROWS={"cached_one_by_one":1,"cached_chunk_48":48,"full_no_cache":1584}
RESULT=Path(os.getenv("G70_RESULT","g70_result.json"))
CORPUS=Path(os.getenv("G70_CORPUS","g70_wikitext_test.txt"))

def source_identity():
    if g64.git_blob(Path(g69.__file__).read_bytes())!=G69_SCRIPT_BLOB:
        raise RuntimeError("ORIGINAL_G69_SOURCE_DRIFT")
    final=Path(__file__).resolve().parents[2]/"docs"/"research"/"ACC-G69-FINAL-20261030.json"
    if not final.is_file() or g64.git_blob(final.read_bytes())!=G69_FINAL_BLOB:
        raise RuntimeError("ORIGINAL_G69_FINAL_DRIFT")
    pre=Path(__file__).resolve().parents[2]/"docs"/"research"/"ACC-G70-PREEXEC-20261030.md"
    if not pre.is_file():raise RuntimeError("G70_PREEXEC_MISSING")
    return {"g69_script_git_blob":G69_SCRIPT_BLOB,
            "g69_final_git_blob":G69_FINAL_BLOB,
            "g69_upstream":g69.authentic_sources()}

def direct_output(model,normed,mode):
    import torch
    if mode not in MODE_TO_ROWS:raise ValueError("UNKNOWN_ORIGINAL_SHAPE")
    count=MODE_TO_ROWS[mode]
    if normed.shape[1]!=1584:raise RuntimeError("ORIGINAL_CONTEXT_NOT_1584")
    x=normed[:,-count:,:]
    y=model.model.layers[0].self_attn.q_proj(x)
    torch.cuda.synchronize(normed.device)
    if y.shape[0]!=1 or y.shape[1]!=count:
        raise RuntimeError("Q_PROJECTOR_SHAPE_INVALID")
    return y[:,-1,:].detach().float().cpu().flatten()

def reference_projection(model,normed):
    import torch
    import torch.nn.functional as F
    weights=model.model.layers[0].self_attn.q_proj
    x=normed[:,-1:,:].float()
    w=weights.weight.float()
    b=weights.bias.float() if weights.bias is not None else None
    ref=F.linear(x,w,b)
    torch.cuda.synchronize(normed.device)
    v=ref[0,-1,:].detach().float().cpu().flatten()
    if not torch.isfinite(v).all():raise RuntimeError("NONFINITE_FP32_ANALYTICAL_PROJECTION")
    return v

def quantify(a,b):
    return g69.previous.vector_difference(a,b)

def assess(rows):
    import torch
    if set(rows)!=set(PRECISIONS):raise ValueError("BOTH_PRECISIONS_REQUIRED")
    output={}
    all_match=True
    for precision in PRECISIONS:
        if set(rows[precision])!=set(MODES):raise ValueError("EXPECTED_ALL_SHAPES")
        output[precision]={"shapes":{},"pairs":[]}
        for mode in MODES:
            samples=rows[precision][mode]
            if len(samples)!=REPEATS:raise ValueError("EXPECTED_THREE_REPEATS")
            first=samples[0]
            for x in samples:
                if not torch.equal(x["direct"],first["direct"]) or not torch.equal(x["hooked"],first["hooked"]):
                    raise ValueError("NONDETERMINISTIC_Q_VECTOR")
                if x["logits"]!=first["logits"]:
                    raise ValueError("NONDETERMINISTIC_ORIGINAL_LOGITS")
                if not x["input_norm_matches"]:
                    raise ValueError("ORIGINAL_NORMALIZED_INPUT_DRIFT")
                if x["direct_matches_hook"]!=first["direct_matches_hook"]:
                    raise ValueError("NONDETERMINISTIC_Q_MATCH_CLASSIFICATION")
            all_match &= all(x["direct_matches_hook"] for x in samples)
            output[precision]["shapes"][mode]={
                "batch_rows":MODE_TO_ROWS[mode],
                "direct_matches_original_q_hook":bool(all(x["direct_matches_hook"] for x in samples)),
                "original_logits":[x["logits"] for x in samples],
                "direct_minus_hook_distances":[quantify(x["direct"],x["hooked"]) for x in samples],
                "direct_minus_fp32_reference_distances":[x["reference_delta"] for x in samples]}
        for repeat in range(REPEATS):
            vals={m:rows[precision][m][repeat]["direct"] for m in MODES}
            output[precision]["pairs"].append({
                m:quantify(vals["cached_one_by_one"],vals[m])
                for m in MODES[1:]})
    fp16_shape_effect=all(
        not p["cached_chunk_48"]["equal_exact"]
        for p in output["float16"]["pairs"])
    label=("DIRECT_QPROJECTION_SHAPE_REPRODUCED" if all_match and fp16_shape_effect
           else "SHAPE_ISOLATION_INCONCLUSIVE")
    return {"diagnostic":label,"repeats":REPEATS,"full_model_traces":len(PRECISIONS)*len(MODES)*REPEATS,
            "isolated_q_projections":len(PRECISIONS)*len(MODES)*REPEATS,
            "all_same_shape_direct_match_original":all_match,
            "fp16_isolated_q_batch_shape_effect":fp16_shape_effect,
            "g63_original_generalization":"FAIL_NO_GO_UNCHANGED",
            "g67_original_engineering":"NO_GO_ENGINEERING",
            "g69_original_stage":"COMPLETE_LAYER0_BOUNDARY_DIAGNOSTIC",
            "scientific_acceptance":"NOT_GRANTED",
            "numerical":output}

def run():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from huggingface_hub import snapshot_download
    from torch.profiler import profile,ProfilerActivity
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    receipt={"schema":"forge.acc.g70.original-q-gemm-batching-shape.v1",
             "status":"UNVERIFIED","source_commit":os.getenv("GITHUB_SHA",""),
             "torch":torch.__version__,"cuda":torch.version.cuda,
             "transformers":transformers.__version__,"platform":platform.platform(),
             "scientific_acceptance":"NOT_GRANTED",
             "g63_original_generalization":"FAIL_NO_GO_UNCHANGED",
             "g67_original_engineering":"NO_GO_ENGINEERING"}
    try:
        receipt["original_sources"]=source_identity()
        corpus=g63.frozen_source(CORPUS)
        if hashlib.sha256(corpus).hexdigest()!=g64.G63_CORPUS_SHA256:
            raise RuntimeError("ORIGINAL_CORPUS_SHA_DRIFT")
        if not torch.cuda.is_available() or torch.version.cuda!="12.8":
            raise RuntimeError("CUDA_12_8_REQUIRED")
        device=torch.device("cuda:0")
        free,total=torch.cuda.mem_get_info(device)
        gpu=torch.cuda.get_device_name(device)
        if (torch.cuda.get_device_capability(device)!=(12,0)
            or "NVIDIA" not in gpu.upper() or free < 7500*1024**2):
            raise RuntimeError("ORIGINAL_RTX_NOT_AVAILABLE")
        a=torch.ones((1024,1024),device=device)
        b=a@a;torch.cuda.synchronize(device)
        if b.device.type!="cuda" or abs(float(b[0,0])-1024)>1e-4:
            raise RuntimeError("AUTHENTIC_CUDA_MATMUL_FAILED")
        del a,b
        torch.cuda.empty_cache()
        receipt["gpu"]={"name":gpu,"compute_capability":[12,0],"total_mib":total/1024**2}
        snap=Path(snapshot_download(repo_id=g63.REPO,revision=g63.REV,token=False,
                     allow_patterns=list(g63.FILES)))
        weights=snap/"model.safetensors"
        if (not weights.is_file() or weights.stat().st_size!=g63.WEIGHT_SIZE
            or g64.file_sha256(weights)!=g63.WEIGHT_SHA):
            raise RuntimeError("ORIGINAL_MODEL_CHECKPOINT_DRIFT")
        tokenizer=AutoTokenizer.from_pretrained(str(snap),use_fast=True,
                             local_files_only=True,trust_remote_code=False)
        tokens=g63.frozen_sample_tokens(tokenizer,corpus.decode("utf-8"),.73)
        prompt=g63.case_ids(torch,tokenizer,tokens,"natural_continuation",1536).to(device)
        if original.token_sha(prompt[0].detach().cpu().tolist())!=original.G64_PROMPT_HASH:
            raise RuntimeError("ORIGINAL_G64_PROMPT_DRIFT")
        receipt["prompt_sha256"]=original.G64_PROMPT_HASH
        shared=None;rows={}
        with torch.inference_mode():
            for dtype_name,dtype in (("float16",torch.float16),("float32",torch.float32)):
                model=AutoModelForCausalLM.from_pretrained(
                    str(snap),torch_dtype=dtype,attn_implementation="sdpa",
                    use_safetensors=True,trust_remote_code=False,local_files_only=True).eval().to(device)
                if (model.config.model_type!="llama" or model.config.num_hidden_layers!=22
                    or model.config._attn_implementation!="sdpa"
                    or next(model.parameters()).dtype!=dtype
                    or next(model.parameters()).device.type!="cuda"):
                    raise RuntimeError("ORIGINAL_LLAMA_CONFIG_CHANGED")
                with profile(activities=[ProfilerActivity.CPU]) as prof:
                    model(input_ids=prompt[:,:16],use_cache=True)
                    torch.cuda.synchronize(device)
                if "aten::scaled_dot_product_attention" not in [x.key for x in prof.key_averages()]:
                    raise RuntimeError("SDPA_OPERATOR_NOT_USED")
                if dtype_name=="float16":
                    control=original.validate_orig_outputs(model,prompt,tokenizer)
                    shared=torch.tensor([control["baseline"]["first_64_token_ids"][:48]],
                                        device=device,dtype=torch.long)
                    receipt["original_fp16_g64_generation_sha"]="PASS"
                if shared is None:raise RuntimeError("FROZEN_SHARED_PREFIX_MISSING")
                full=torch.cat((prompt,shared),dim=1)
                normed=model.model.layers[0].input_layernorm(model.model.embed_tokens(full))
                if normed.shape[1]!=1584 or normed.dtype!=dtype or normed.device.type!="cuda":
                    raise RuntimeError("G70_ORIGINAL_LAYER0_NORMALIZED_INPUT_DRIFT")
                analytical=reference_projection(model,normed)
                rows[dtype_name]={m:[] for m in MODES}
                for rep in range(REPEATS):
                    for mode in MODES:
                        hooked=g69.collect_traces(model,prompt,shared,mode)
                        obs=hooked["logits"]
                        # Strict original path identity, not a new target picked after results.
                        expected_id=7866 if dtype_name=="float16" and mode=="cached_one_by_one" else 29871
                        expected_tie=2 if dtype_name=="float16" and mode=="cached_one_by_one" else 1
                        if (obs["greedy_argmax_id"],obs["exact_max_tie_count"])!=(expected_id,expected_tie):
                            raise RuntimeError("ORIGINAL_G69_ARGMAX_TIE_DRIFT")
                        original_q=hooked["vectors"]["q_proj"]
                        norm_match=torch.equal(normed[0,-1].detach().float().cpu(),
                                              hooked["vectors"]["input_layernorm"])
                        independent=direct_output(model,normed,mode)
                        match=torch.equal(independent,original_q)
                        row={"logits":obs,"hooked":original_q,"direct":independent,
                             "input_norm_matches":bool(norm_match),
                             "direct_matches_hook":bool(match),
                             "reference_delta":quantify(independent,analytical)}
                        rows[dtype_name][mode].append(row)
                        print("G70_TRACE dtype=%s rep=%d mode=%s q_same=%s last_input_same=%s" %
                              (dtype_name,rep,mode,match,norm_match),flush=True)
                del model,normed
                gc.collect()
                torch.cuda.empty_cache()
        receipt["classification"]=assess(rows)
        receipt["status"]="PASS_COMPLETE_ORIGINAL_Q_SHAPE_DIAGNOSTIC"
    except Exception as exc:
        receipt.update({"status":"BLOCKED_OR_SOURCE_DRIFT",
                        "error":type(exc).__name__+": "+str(exc)})
        raise
    finally:
        RESULT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G70_STATUS="+receipt["status"],flush=True)
        if receipt.get("classification"):
            print("G70_DECISION="+receipt["classification"]["diagnostic"],flush=True)

if __name__=="__main__":
    run()
