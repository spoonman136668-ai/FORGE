#!/usr/bin/env python3
"""ACC G68 immutable same-input hidden-state attribution, research only."""
from __future__ import annotations
import gc
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acc_g67"))
import g67_fp32_head as g67

g66 = g67.prior
g63 = g66.g63
g64 = g66.g64
original = g66.original
G67_SOURCE_BLOB = "5faf30781d96a2cefd9d0147ad8928e4eb8faba2"
G67_FINAL_BLOB = "7976395e27489c6bd152ad5d441212d53b1a1f44"
PRECISIONS = ("float16", "float32")
MODES = ("cached_one_by_one", "cached_chunk_48", "full_no_cache")
REPEATS = 3
LAYER_COUNT = 22
STAGES = tuple("layer_%02d" % i for i in range(LAYER_COUNT)) + ("final_norm",)
ORIGINAL_TOKENS = (7866, 29871)
RESULT = Path(os.environ.get("G68_RESULT", "g68_result.json"))
CORPUS = Path(os.environ.get("G68_CORPUS", "g68_wikitext_test.txt"))

def frozen_identity():
    if g64.git_blob(Path(g67.__file__).read_bytes()) != G67_SOURCE_BLOB:
        raise RuntimeError("ORIGINAL_G67_EXECUTABLE_DRIFT")
    final = Path(__file__).resolve().parents[2]/"docs"/"research"/"ACC-G67-FINAL-20261030.json"
    if not final.is_file() or g64.git_blob(final.read_bytes()) != G67_FINAL_BLOB:
        raise RuntimeError("G67_ORIGINAL_FINAL_BLOB_DRIFT")
    pre = Path(__file__).resolve().parents[2]/"docs"/"research"/"ACC-G68-PREEXEC-20261030.md"
    if not pre.is_file():
        raise RuntimeError("G68_PREEXEC_MISSING")
    g67.source_identity()
    if g67.CASES[0] != (.73, "natural_continuation", 1536):
        raise RuntimeError("ORIGINAL_CASE_DRIFT")
    return {"g67_executable_blob":G67_SOURCE_BLOB, "g67_final_blob":G67_FINAL_BLOB,
            "g66_identity":g66.frozen_identity()}

def vector_difference(a, b):
    import torch
    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape:
        raise ValueError("BAD_HIDDEN_STAGE_VECTOR_DIMENSIONS")
    if not torch.isfinite(a).all() or not torch.isfinite(b).all():
        raise ValueError("NONFINITE_STAGE")
    d = a - b
    l2 = float(torch.linalg.vector_norm(d).item())
    ref = float(torch.linalg.vector_norm(b).item())
    max_abs = float(torch.max(torch.abs(d)).item())
    return {"equal_exact":bool(torch.equal(a,b)), "l2":l2,
            "relative_l2":l2/max(ref,1.0e-30), "max_absolute":max_abs}

def pair_summary(vectors):
    if set(vectors) != set(MODES):
        raise ValueError("MISSING_CALCULATION_PATH")
    comparisons = {}
    for other in MODES[1:]:
        base = vectors[MODES[0]]
        right = vectors[other]
        if set(base) != set(STAGES) or set(right) != set(STAGES):
            raise ValueError("MISSING_ONE_OF_23_STAGES")
        measures = {stage:vector_difference(base[stage],right[stage]) for stage in STAGES}
        different = [stage for stage in STAGES if not measures[stage]["equal_exact"]]
        comparisons[other] = {"first_bitwise_different_stage":different[0] if different else None,
                              "all_23_exact":not different, "stage_deltas":measures}
    return comparisons

def inspect_margin(model, norm_vector):
    import torch
    head = model.get_output_embeddings()
    if head.weight.shape[0] <= max(ORIGINAL_TOKENS):
        raise RuntimeError("ORIGINAL_VOCAB_MISSING")
    if norm_vector.ndim != 1 or norm_vector.shape[0] != head.weight.shape[1]:
        raise RuntimeError("FINAL_HIDDEN_WIDTH_MISMATCH")
    with torch.no_grad():
        w = head.weight[list(ORIGINAL_TOKENS)].detach().float().cpu()
        v = norm_vector.float()
        margin = torch.dot(w[1]-w[0], v)
        if head.bias is not None:
            b = head.bias[list(ORIGINAL_TOKENS)].detach().float().cpu()
            margin += b[1]-b[0]
        value = float(margin.item())
    if not math.isfinite(value):
        raise RuntimeError("NONFINITE_PROJECTED_MARGIN")
    return value

def traced_model_last_call(model, prompt, shared, mode):
    import torch
    slots = {"enabled":False, "vectors":{}}
    hooks = []
    def capture(label):
        def hook(_module, _inputs, output):
            if not slots["enabled"]:
                return
            hidden = output[0] if isinstance(output, (tuple,list)) else output
            if hidden.ndim != 3 or hidden.shape[0] != 1:
                raise RuntimeError("UNEXPECTED_TRANSFORMER_LAYER_TENSOR")
            if label in slots["vectors"]:
                raise RuntimeError("DUPLICATE_FINAL_STAGE_HOOK")
            slots["vectors"][label] = hidden[:, -1, :].detach().float().cpu().flatten()
        return hook
    for n, layer in enumerate(model.model.layers):
        hooks.append(layer.register_forward_hook(capture("layer_%02d" % n)))
    hooks.append(model.model.norm.register_forward_hook(capture("final_norm")))
    try:
        if mode == "full_no_cache":
            slots["enabled"] = True
            out = model(input_ids=torch.cat((prompt, shared), dim=1), use_cache=False)
        elif mode in ("cached_chunk_48","cached_one_by_one"):
            out = model(input_ids=prompt, use_cache=True)
            cache = out.past_key_values
            if mode == "cached_chunk_48":
                slots["enabled"] = True
                mask = torch.ones((1, prompt.shape[1]+48), device=prompt.device, dtype=torch.long)
                out = model(input_ids=shared, past_key_values=cache, attention_mask=mask, use_cache=True)
            else:
                for i in range(48):
                    slots["enabled"] = i == 47
                    mask = torch.ones((1, prompt.shape[1]+i+1), device=prompt.device, dtype=torch.long)
                    out = model(input_ids=shared[:,i:i+1],past_key_values=cache,
                                attention_mask=mask,use_cache=True)
                    cache = out.past_key_values
        else:
            raise ValueError("UNKNOWN_FROZEN_MODE")
        torch.cuda.synchronize(prompt.device)
        if set(slots["vectors"]) != set(STAGES):
            raise RuntimeError("MISSING_OR_DUPLICATE_23_HIDDEN_STAGES")
        logits = out.logits[0,-1,:]
        observed = original.summarize_logits(logits)
        projected = inspect_margin(model, slots["vectors"]["final_norm"])
        observed["head_fp32_projected_margin"] = projected
        observed["observed_minus_fp32_projection"] = (
            observed["candidate_minus_baseline_logit"]-projected)
        if not all(math.isfinite(float(observed[k])) for k in
                   ("candidate_minus_baseline_logit",
                    "head_fp32_projected_margin", "observed_minus_fp32_projection")):
            raise RuntimeError("NONFINITE_LOGIT_OR_PROJECTION")
        return observed, slots["vectors"]
    finally:
        for hook in hooks:
            hook.remove()

def adjudicate(rows):
    if set(rows) != set(PRECISIONS):
        raise ValueError("NOT_BOTH_PRECISIONS")
    for dtype in PRECISIONS:
        if set(rows[dtype]) != set(MODES):
            raise ValueError("NOT_THREE_MODES")
        for m in MODES:
            if len(rows[dtype][m]) != REPEATS:
                raise ValueError("NOT_THREE_REPEATS")
            for x in rows[dtype][m]:
                if set(x["vectors"]) != set(STAGES):
                    raise ValueError("NOT_23_STAGES")
            samples = [x["logits"] for x in rows[dtype][m]]
            for label in ("greedy_argmax_id","exact_max_tie_count",
                          "candidate_minus_baseline_logit","head_fp32_projected_margin"):
                if len({x[label] for x in samples}) != 1:
                    raise ValueError("NONDETERMINISTIC_REPEATED_PATH_"+label)
    expected = {"float16":[(7866,2),(29871,1),(29871,1)],
                "float32":[(29871,1),(29871,1),(29871,1)]}
    for dtype in PRECISIONS:
        for mode,(argmax,tie) in zip(MODES,expected[dtype]):
            row = rows[dtype][mode][0]["logits"]
            if (row["greedy_argmax_id"],row["exact_max_tie_count"]) != (argmax,tie):
                raise ValueError("ORIGINAL_G66_NUMERIC_REPRODUCTION_DRIFT")
    report = {}
    for dtype in PRECISIONS:
        report[dtype] = {"paths":{m:[] for m in MODES},"comparisons":[]}
        for m in MODES:
            for x in rows[dtype][m]:
                report[dtype]["paths"][m].append(x["logits"])
        for repetition in range(REPEATS):
            vectors = {m: rows[dtype][m][repetition]["vectors"] for m in MODES}
            report[dtype]["comparisons"].append(pair_summary(vectors))
    return {"screen":"COMPLETE_NUMERICAL_ATTRIBUTION_SCREEN",
            "g63_original_generalization":"FAIL_NO_GO_UNCHANGED",
            "g67_original_engineering":"NO_GO_ENGINEERING",
            "scientific_acceptance":"NOT_GRANTED",
            "repeats":REPEATS, "traces":len(PRECISIONS)*len(MODES)*REPEATS,
            "stages_per_trace":len(STAGES),
            "numerical":report}

def run():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from torch.profiler import profile, ProfilerActivity
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    receipt = {"schema":"forge.acc.g68.stagewise-cuda-numerics-diagnostic.v1",
               "status":"UNVERIFIED","source_sha":os.environ.get("GITHUB_SHA",""),
               "torch":torch.__version__, "transformers":transformers.__version__,
               "cuda":torch.version.cuda,"platform":platform.platform(),
               "g63_original_generalization":"FAIL_NO_GO_UNCHANGED",
               "g67_original_engineering":"NO_GO_ENGINEERING",
               "scientific_acceptance":"NOT_GRANTED"}
    try:
        receipt["source_identity"] = frozen_identity()
        text = g63.frozen_source(CORPUS)
        if hashlib.sha256(text).hexdigest() != g64.G63_CORPUS_SHA256:
            raise RuntimeError("ORIGINAL_WIKITEXT_SHA_DRIFT")
        if not torch.cuda.is_available() or torch.version.cuda != "12.8":
            raise RuntimeError("ORIGINAL_CUDA_RUNTIME_DRIFT")
        device = torch.device("cuda:0")
        free,total = torch.cuda.mem_get_info(device)
        name,cc = torch.cuda.get_device_name(device),torch.cuda.get_device_capability(device)
        if "NVIDIA" not in name.upper() or cc != (12,0) or free < 7500*1024**2:
            raise RuntimeError("ORIGINAL_GPU_IDENTITY_OR_MEMORY_DRIFT")
        a=torch.ones((1024,1024),device=device)
        b=a@a
        torch.cuda.synchronize(device)
        if b.device.type!="cuda" or abs(float(b[0,0])-1024)>1e-4:
            raise RuntimeError("ACTUAL_CUDA_MATMUL_FAILED")
        del a,b
        torch.cuda.empty_cache()
        receipt["gpu"]={"name":name,"compute_capability":list(cc),"free_mib":free/1024**2,
                        "total_mib":total/1024**2}
        snapshot=Path(snapshot_download(repo_id=g63.REPO,revision=g63.REV,
              token=False,allow_patterns=list(g63.FILES)))
        weights=snapshot/"model.safetensors"
        if (not weights.is_file() or weights.stat().st_size!=g63.WEIGHT_SIZE
            or g64.file_sha256(weights)!=g63.WEIGHT_SHA):
            raise RuntimeError("ORIGINAL_AUTHENTIC_MODEL_WEIGHTS_DRIFT")
        tokenizer=AutoTokenizer.from_pretrained(str(snapshot), use_fast=True,
             local_files_only=True,trust_remote_code=False)
        tokens=g63.frozen_sample_tokens(tokenizer,text.decode("utf-8"),.73)
        prompt=g63.case_ids(torch,tokenizer,tokens,"natural_continuation",1536).to(device)
        if original.token_sha(prompt[0].detach().cpu().tolist()) != original.G64_PROMPT_HASH:
            raise RuntimeError("ORIGINAL_1536_PROMPT_IDENTITY_DRIFT")
        receipt["prompt_sha256"]=original.G64_PROMPT_HASH
        saved_shared=None
        rows={}
        with torch.inference_mode():
            for dtype_name, dtype in (("float16",torch.float16),("float32",torch.float32)):
                model=AutoModelForCausalLM.from_pretrained(
                    str(snapshot),torch_dtype=dtype,attn_implementation="sdpa",
                    local_files_only=True,trust_remote_code=False,use_safetensors=True).eval().to(device)
                if (model.config.model_type!="llama" or model.config.num_hidden_layers!=22
                    or model.config._attn_implementation!="sdpa"
                    or next(model.parameters()).dtype!=dtype or next(model.parameters()).device.type!="cuda"
                    or len(model.model.layers)!=LAYER_COUNT):
                    raise RuntimeError("ORIGINAL_ARCHITECTURE_DTYPE_DRIFT")
                with profile(activities=[ProfilerActivity.CPU]) as prof:
                    model(input_ids=prompt[:,:16],use_cache=True)
                    torch.cuda.synchronize(device)
                if "aten::scaled_dot_product_attention" not in [q.key for q in prof.key_averages()]:
                    raise RuntimeError("OPTIMIZED_SDPA_NOT_EXECUTED")
                if dtype_name=="float16":
                    control=original.validate_orig_outputs(model,prompt,tokenizer)
                    shared_tokens=control["baseline"]["first_64_token_ids"][:48]
                    saved_shared=torch.tensor([shared_tokens],device=device,dtype=torch.long)
                    receipt["original_fp16_generation_hashes"]="PASS"
                if saved_shared is None:
                    raise RuntimeError("FROZEN_SHARED_PREFIX_MISSING")
                rows[dtype_name]={m:[] for m in MODES}
                for rep in range(REPEATS):
                    for mode in MODES:
                        logits, vectors = traced_model_last_call(model,prompt,saved_shared,mode)
                        rows[dtype_name][mode].append({"logits":logits,"vectors":vectors})
                        print("G68_TRACE dtype=%s rep=%d path=%s argmax=%d ties=%d" %
                              (dtype_name,rep,mode,logits["greedy_argmax_id"],
                               logits["exact_max_tie_count"]),flush=True)
                del model
                gc.collect()
                torch.cuda.empty_cache()
        result=adjudicate(rows)
        receipt["diagnostic"]=result
        receipt["status"]="PASS_COMPLETE_ORIGINAL_GPU_DIAGNOSTIC"
    except Exception as exc:
        receipt.update({"status":"BLOCKED_OR_SOURCE_DRIFT",
                         "error":type(exc).__name__+": "+str(exc)})
        raise
    finally:
        RESULT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G68_STATUS="+receipt["status"],flush=True)
        if "diagnostic" in receipt:
            print("G68_CLASSIFICATION="+receipt["diagnostic"]["screen"],flush=True)
if __name__=="__main__":
    run()
