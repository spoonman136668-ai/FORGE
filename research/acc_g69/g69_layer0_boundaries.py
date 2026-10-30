#!/usr/bin/env python3
"""ACC G69 immutable first-decoder boundary trace; no model modification."""
from __future__ import annotations
import gc
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"acc_g68"))
import g68_hidden_attribution as previous

g67=previous.g67
g63=previous.g63
g64=previous.g64
original=previous.original
G68_SOURCE_GIT_BLOB="541cc88752649b2bc6ffd63cbe684c4f84cccc25"
G68_FINAL_GIT_BLOB="c01294dcc014f683fc9390f1df189d157df3cf9d"
DTYPES=("float16","float32")
MODES=previous.MODES
REPEATS=3
STAGES=("layer0_input","input_layernorm","q_proj","k_proj","v_proj",
        "attention_pre_o_proj","attention_output","post_attention_layernorm",
        "mlp_gate","mlp_up","mlp_down","layer0_output")
RESULT=Path(os.environ.get("G69_RESULT","g69_result.json"))
CORPUS=Path(os.environ.get("G69_CORPUS","g69_wikitext_test.txt"))

def authentic_sources():
    if g64.git_blob(Path(previous.__file__).read_bytes())!=G68_SOURCE_GIT_BLOB:
        raise RuntimeError("G68_ORIGINAL_EXECUTABLE_GIT_BLOB_DRIFT")
    source=Path(__file__).resolve().parents[2]/"docs"/"research"/"ACC-G68-FINAL-20261030.json"
    if not source.is_file() or g64.git_blob(source.read_bytes())!=G68_FINAL_GIT_BLOB:
        raise RuntimeError("G68_FINAL_REPORT_BLOB_DRIFT")
    freeze=Path(__file__).resolve().parents[2]/"docs"/"research"/"ACC-G69-PREEXEC-20261030.md"
    if not freeze.is_file():raise RuntimeError("G69_PREREG_MISSING")
    previous.frozen_identity()
    return {"g68_source_blob":G68_SOURCE_GIT_BLOB,
            "g68_final_blob":G68_FINAL_GIT_BLOB,
            "upstream":previous.frozen_identity()}

def collect_traces(model,prompt,shared,mode):
    import torch
    layer=model.model.layers[0]
    if len(model.model.layers)!=22:
        raise RuntimeError("NOT_ORIGINAL_22_DECODER_LAYERS")
    attention=layer.self_attn
    mlp=layer.mlp
    hooks=[]
    box={"enabled":False,"vectors":{}}
    def save(label,output):
        if not box["enabled"]:return
        x=output[0] if isinstance(output,(tuple,list)) else output
        if not isinstance(x,torch.Tensor) or x.ndim!=3 or x.shape[0]!=1:
            raise RuntimeError("UNEXPECTED_LAYER0_STAGE_OUTPUT:"+label)
        if label in box["vectors"]:
            raise RuntimeError("DUPLICATE_STAGE_OBSERVATION:"+label)
        v=x[:, -1, :].detach().float().cpu().flatten()
        if not torch.isfinite(v).all():raise RuntimeError("NONFINITE_LAYER0_STAGE:"+label)
        box["vectors"][label]=v
    def forward(label):
        def fn(_module,_args,out):save(label,out)
        return fn
    def pre(label):
        def fn(_module,args):save(label,args[0])
        return fn
    hooks.append(layer.register_forward_pre_hook(pre("layer0_input")))
    hooks.append(layer.input_layernorm.register_forward_hook(forward("input_layernorm")))
    hooks.append(attention.q_proj.register_forward_hook(forward("q_proj")))
    hooks.append(attention.k_proj.register_forward_hook(forward("k_proj")))
    hooks.append(attention.v_proj.register_forward_hook(forward("v_proj")))
    hooks.append(attention.o_proj.register_forward_pre_hook(pre("attention_pre_o_proj")))
    hooks.append(attention.o_proj.register_forward_hook(forward("attention_output")))
    hooks.append(layer.post_attention_layernorm.register_forward_hook(forward("post_attention_layernorm")))
    hooks.append(mlp.gate_proj.register_forward_hook(forward("mlp_gate")))
    hooks.append(mlp.up_proj.register_forward_hook(forward("mlp_up")))
    hooks.append(mlp.down_proj.register_forward_hook(forward("mlp_down")))
    hooks.append(layer.register_forward_hook(forward("layer0_output")))
    try:
        if mode=="full_no_cache":
            box["enabled"]=True
            out=model(input_ids=torch.cat((prompt,shared),dim=1),use_cache=False)
        elif mode=="cached_chunk_48":
            box["enabled"]=False
            first=model(input_ids=prompt,use_cache=True)
            box["enabled"]=True
            mask=torch.ones((1,prompt.shape[1]+shared.shape[1]),device=prompt.device,dtype=torch.long)
            out=model(input_ids=shared,past_key_values=first.past_key_values,
                      attention_mask=mask,use_cache=True)
        elif mode=="cached_one_by_one":
            box["enabled"]=False
            first=model(input_ids=prompt,use_cache=True)
            cache=first.past_key_values
            for n in range(shared.shape[1]):
                box["enabled"]=n==shared.shape[1]-1
                mask=torch.ones((1,prompt.shape[1]+n+1),device=prompt.device,dtype=torch.long)
                out=model(input_ids=shared[:,n:n+1],past_key_values=cache,
                          attention_mask=mask,use_cache=True)
                cache=out.past_key_values
        else:raise ValueError("UNKNOWN_CALCULATION_PATH")
        torch.cuda.synchronize(prompt.device)
        if set(box["vectors"])!=set(STAGES):
            raise RuntimeError("MISSING_OR_EXTRA_LAST_CALL_LAYER0_STAGES")
        logits=original.summarize_logits(out.logits[0,-1,:])
        return {"logits":logits,"vectors":box["vectors"]}
    finally:
        for h in hooks:h.remove()

def compare(vectors):
    if set(vectors)!=set(MODES):raise ValueError("CALCULATION_PATH_MISSING")
    pairs={}
    for other in MODES[1:]:
        a=vectors[MODES[0]]; b=vectors[other]
        if set(a)!=set(STAGES) or set(b)!=set(STAGES):
            raise ValueError("STAGE_MISSING")
        distances={s:previous.vector_difference(a[s],b[s]) for s in STAGES}
        first=next((s for s in STAGES if not distances[s]["equal_exact"]),None)
        pairs[other]={"earliest_bitwise_difference":first,"all_equal":first is None,
                      "stage_deltas":distances}
    return pairs

def adjudicate(rows):
    if set(rows)!=set(DTYPES):raise ValueError("BOTH_PRECISIONS_REQUIRED")
    expected={"float16":((7866,2),(29871,1),(29871,1)),
              "float32":((29871,1),(29871,1),(29871,1))}
    result={}
    for dtype in DTYPES:
        if set(rows[dtype])!=set(MODES):raise ValueError("THREE_MODES_REQUIRED")
        for mode,(want_id,want_ties) in zip(MODES,expected[dtype]):
            traces=rows[dtype][mode]
            if len(traces)!=REPEATS:raise ValueError("THREE_REPEATS_REQUIRED")
            for item in traces:
                if set(item["vectors"])!=set(STAGES):
                    raise ValueError("TWELVE_ORIGINAL_STAGE_HOOKS_REQUIRED")
                logit=item["logits"]
                if (logit["greedy_argmax_id"],logit["exact_max_tie_count"])!=(want_id,want_ties):
                    raise ValueError("G68_ORIGINAL_ARGMAX_OR_TIE_DRIFT")
                if not math.isfinite(logit["candidate_minus_baseline_logit"]):
                    raise ValueError("NONFINITE_LOGIT_MARGIN")
            for field in ("greedy_argmax_id","exact_max_tie_count","candidate_minus_baseline_logit"):
                if len({t["logits"][field] for t in traces})!=1:
                    raise ValueError("NONDETERMINISTIC_REPEATED_ORIGINAL_TRACE")
        pairs=[compare({m:rows[dtype][m][i]["vectors"] for m in MODES}) for i in range(REPEATS)]
        signatures=[{m:p[m]["earliest_bitwise_difference"] for m in MODES[1:]} for p in pairs]
        if any(x!=signatures[0] for x in signatures[1:]):
            raise ValueError("NONDETERMINISTIC_EARLIEST_BOUNDARY")
        result[dtype]={
            "original_logits":{m:[x["logits"] for x in rows[dtype][m]] for m in MODES},
            "repeat_comparisons":pairs,
            "first_differing_sites":signatures[0]
        }
    return {"classification":"COMPLETE_LAYER0_BOUNDARY_DIAGNOSTIC",
            "stage_count":len(STAGES),"trace_count":len(DTYPES)*len(MODES)*REPEATS,
            "g63_generalization":"FAIL_NO_GO_UNCHANGED",
            "g67_engineering":"NO_GO_ENGINEERING",
            "g68_stage_screen":"COMPLETE_NUMERICAL_ATTRIBUTION_SCREEN",
            "scientific_acceptance":"NOT_GRANTED",
            "data":result}

def run():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from torch.profiler import profile,ProfilerActivity
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False
    receipt={"schema":"forge.acc.g69.layer0-numerical-boundaries.v1",
             "status":"UNVERIFIED","source_sha":os.getenv("GITHUB_SHA",""),
             "torch":torch.__version__,"cuda":torch.version.cuda,
             "transformers":transformers.__version__,"platform":platform.platform(),
             "g63_generalization":"FAIL_NO_GO_UNCHANGED",
             "g67_engineering":"NO_GO_ENGINEERING",
             "scientific_acceptance":"NOT_GRANTED"}
    try:
        receipt["source_custody"]=authentic_sources()
        text=g63.frozen_source(CORPUS)
        if hashlib.sha256(text).hexdigest()!=g64.G63_CORPUS_SHA256:
            raise RuntimeError("ORIGINAL_WIKITEXT_SHA_DRIFT")
        if not torch.cuda.is_available() or torch.version.cuda!="12.8":
            raise RuntimeError("ORIGINAL_CUDA_12_8_DRIFT")
        device=torch.device("cuda:0")
        free,total=torch.cuda.mem_get_info(device)
        name=torch.cuda.get_device_name(device)
        cc=torch.cuda.get_device_capability(device)
        if cc!=(12,0) or "NVIDIA" not in name.upper() or free<7500*1024**2:
            raise RuntimeError("ORIGINAL_GPU_OR_VRAM_DRIFT")
        a=torch.ones((1024,1024),device=device);b=a@a
        torch.cuda.synchronize(device)
        if b.device.type!="cuda" or abs(float(b[0,0])-1024)>1e-4:
            raise RuntimeError("AUTHENTIC_CUDA_MATMUL_FAILED")
        del a,b
        torch.cuda.empty_cache()
        receipt["gpu"]={"name":name,"compute_capability":list(cc),"total_mib":total/1024**2}
        snap=Path(snapshot_download(repo_id=g63.REPO,revision=g63.REV,
                      token=False,allow_patterns=list(g63.FILES)))
        weights=snap/"model.safetensors"
        if not weights.is_file() or weights.stat().st_size!=g63.WEIGHT_SIZE or g64.file_sha256(weights)!=g63.WEIGHT_SHA:
            raise RuntimeError("ORIGINAL_CHECKPOINT_SHA_DRIFT")
        tokenizer=AutoTokenizer.from_pretrained(str(snap),use_fast=True,
                       local_files_only=True,trust_remote_code=False)
        prefix=g63.frozen_sample_tokens(tokenizer,text.decode("utf-8"),.73)
        prompt=g63.case_ids(torch,tokenizer,prefix,"natural_continuation",1536).to(device)
        if original.token_sha(prompt[0].detach().cpu().tolist())!=original.G64_PROMPT_HASH:
            raise RuntimeError("ORIGINAL_1536_TOKEN_PROMPT_DRIFT")
        receipt["prompt_sha256"]=original.G64_PROMPT_HASH
        rows={}
        shared=None
        with torch.inference_mode():
            for dtype_name,dtype in (("float16",torch.float16),("float32",torch.float32)):
                model=AutoModelForCausalLM.from_pretrained(
                    str(snap),torch_dtype=dtype,attn_implementation="sdpa",
                    use_safetensors=True,trust_remote_code=False,local_files_only=True).eval().to(device)
                if (model.config.model_type!="llama" or model.config.num_hidden_layers!=22
                    or model.config._attn_implementation!="sdpa"
                    or next(model.parameters()).dtype!=dtype
                    or next(model.parameters()).device.type!="cuda"):
                    raise RuntimeError("ORIGINAL_LLM_ARCH_OR_DTYPE_DRIFT")
                with profile(activities=[ProfilerActivity.CPU]) as profiler:
                    model(input_ids=prompt[:,:16],use_cache=True)
                    torch.cuda.synchronize(device)
                if "aten::scaled_dot_product_attention" not in [q.key for q in profiler.key_averages()]:
                    raise RuntimeError("REAL_OPTIMIZED_SDPA_NOT_DISPATCHED")
                if dtype_name=="float16":
                    original_outputs=original.validate_orig_outputs(model,prompt,tokenizer)
                    shared=torch.tensor([original_outputs["baseline"]["first_64_token_ids"][:48]],
                                        device=device,dtype=torch.long)
                    receipt["original_fp16_64_token_sha_reproduction"]="PASS"
                if shared is None:raise RuntimeError("MISSING_ORIGINAL_48_TOKEN_PREFIX")
                rows[dtype_name]={m:[] for m in MODES}
                for rep in range(REPEATS):
                    for mode in MODES:
                        measured=collect_traces(model,prompt,shared,mode)
                        rows[dtype_name][mode].append(measured)
                        print("G69_TRACE %s r=%d %s argmax=%d tie=%d"%
                              (dtype_name,rep,mode,
                               measured["logits"]["greedy_argmax_id"],
                               measured["logits"]["exact_max_tie_count"]),flush=True)
                del model
                gc.collect()
                torch.cuda.empty_cache()
        receipt["result"]=adjudicate(rows)
        receipt["status"]="PASS_COMPLETE_ORIGINAL_GPU_BOUNDARY_DIAGNOSTIC"
    except Exception as e:
        receipt.update({"status":"BLOCKED_OR_SOURCE_DRIFT","error":type(e).__name__+": "+str(e)})
        raise
    finally:
        RESULT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G69_STATUS="+receipt["status"],flush=True)
        if receipt.get("result"):
            print("G69_DECISION="+receipt["result"]["classification"],flush=True)
if __name__=="__main__":
    run()
