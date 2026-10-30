#!/usr/bin/env python3
"""ACC G61: authentic pretrained TinyLlama 1.1B on real RTX, eager-vs-optimized SDPA.

Research-only; this measures STANDARD PyTorch SDPA, not an original new method.
Pre-execution decisions committed at docs/research/ACC-G61-PREEXEC-20261030.md.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import time

REPO = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
REV = "c13e4efb205d7a8e5d13c088aa10a9dabac9b96a"
WEIGHT_SHA = "6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933"
WEIGHT_SIZE = 2200119864
FILES = ("config.json", "generation_config.json", "model.safetensors",
         "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json")
CONTEXTS = (128, 512, 1536)
GENERATED = 32
REPEATS = 5
BACKENDS = ("eager", "sdpa")
RESULT = Path(os.getenv("G61_RESULT", "g61_result.json"))
PROMPT = (
    "A computational research report should distinguish improvements that were actually "
    "measured from architectural estimates. Attention operations read queries, keys and "
    "values while projections and feedforward blocks also contribute to total latency. "
    "Measurements require identical model weights, prompts and numerical output checks "
    "before making a performance comparison. "
) * 120

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def median_times(rows: list[dict]) -> dict:
    return {k: statistics.median(r[k] for r in rows)
            for k in ("prefill_s", "decode_32_s", "total_s")}

def repetition_order(i: int) -> tuple[str, str]:
    return ("eager", "sdpa") if i % 2 == 0 else ("sdpa", "eager")

def source_guard(weight_path: Path) -> dict:
    if weight_path.stat().st_size != WEIGHT_SIZE:
        raise RuntimeError("AUTHENTIC_SAFETENSORS_SIZE_MISMATCH")
    actual = sha256_file(weight_path)
    if actual != WEIGHT_SHA:
        raise RuntimeError("AUTHENTIC_SAFETENSORS_SHA256_MISMATCH")
    return {"name":"model.safetensors", "sha256":actual, "bytes":WEIGHT_SIZE}

def main():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer, AutoModelForCausalLM

    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    result = {
      "schema":"forge.acc.g61.tinyllama-1b-eager-sdpa.v1",
      "gate":"ACC-G61", "status":"UNVERIFIED",
      "head_commit":os.getenv("GITHUB_SHA", ""), "platform":platform.platform(),
      "torch":torch.__version__, "cuda_runtime":torch.version.cuda,
      "transformers":transformers.__version__,
      "model_repo":REPO,"model_revision":REV,
      "expected_weights_sha256":WEIGHT_SHA,
      "scientific_acceptance":"NOT_GRANTED",
      "new_acceleration_discovered":False,
      "baseline_type":"optimized PyTorch SDPA; not optimized production serving",
      "model_training_performed":False
    }
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA_UNAVAILABLE_NO_CPU_FALLBACK")
        if not torch.version.cuda or tuple(int(v) for v in torch.version.cuda.split(".")[:2]) < (12,8):
            raise RuntimeError("CUDA_RUNTIME_TOO_OLD_FOR_BLACKWELL")
        dev = torch.device("cuda:0")
        gpu = torch.cuda.get_device_name(dev)
        cap = torch.cuda.get_device_capability(dev)
        free,total = torch.cuda.mem_get_info(dev)
        if cap!=(12,0) or free < 7000 * 1024**2 or "NVIDIA" not in gpu.upper():
            raise RuntimeError("REAL_NVIDIA_GPU_ADMISSION_FAILED")
        result["gpu"] = {
          "name":gpu,"compute_capability":list(cap),
          "free_mib_before":free//1024**2,"total_mib":total//1024**2
        }
        # A real GPU multiply rules out a purely synthetic device inventory.
        a=torch.ones((1024,1024),device=dev,dtype=torch.float32)
        z=a@a
        torch.cuda.synchronize(dev)
        if z.device.type!="cuda" or abs(float(z[0,0])-1024)>1e-5:
            raise RuntimeError("CUDA_MATRIX_MULTIPLY_FAILED")
        result["real_cuda_matmul"] = "PASS"
        del a,z
        torch.cuda.empty_cache()

        snapshot = Path(snapshot_download(
            repo_id=REPO, revision=REV, token=False, allow_patterns=list(FILES)))
        model_file=snapshot/"model.safetensors"
        if not model_file.is_file():
            raise RuntimeError("PUBLIC_CHECKPOINT_NOT_DOWNLOADED")
        result["model_weight_receipt"]=source_guard(model_file)
        result["manifest"]=[
          {"path":x,"bytes":(snapshot/x).stat().st_size,
           "sha256":sha256_file(snapshot/x)}
          for x in FILES if (snapshot/x).is_file()
        ]
        if not (snapshot/"tokenizer.json").is_file():
            raise RuntimeError("PINNED_TOKENIZER_JSON_MISSING")
        tok=AutoTokenizer.from_pretrained(
            str(snapshot),use_fast=True,local_files_only=True,
            trust_remote_code=False)
        complete=tok(PROMPT,add_special_tokens=False,truncation=True,
                     max_length=max(CONTEXTS),return_tensors="pt")["input_ids"]
        if complete.shape[1] != max(CONTEXTS):
            raise RuntimeError("PROMPT_TOO_SHORT_FOR_FROZEN_CONTEXTS")
        if complete.shape[1]+GENERATED>2048:
            raise RuntimeError("MODEL_POSITION_LIMIT_EXCEEDED")

        models={}
        for backend in BACKENDS:
            m=AutoModelForCausalLM.from_pretrained(
                str(snapshot),local_files_only=True,trust_remote_code=False,
                use_safetensors=True,torch_dtype=torch.float16,
                attn_implementation=backend).eval().to(dev)
            if m.config.model_type != "llama" or m.config.num_hidden_layers!=22:
                raise RuntimeError("MODEL_ARCHITECTURE_DRIFT")
            impl=m.config._attn_implementation
            kind=type(m.model.layers[0].self_attn).__name__
            if impl!=backend or ((backend=="sdpa") != ("Sdpa" in kind)):
                raise RuntimeError(f"ATTENTION_BACKEND_NOT_REALIZED:{backend}:{impl}:{kind}")
            if next(m.parameters()).device.type!="cuda":
                raise RuntimeError("GPU_MODEL_CPU_FALLBACK")
            models[backend]=m
            result.setdefault("backends",{})[backend]={
                "implementation":impl,"attention_class":kind,
                "dtype":str(next(m.parameters()).dtype),
                "parameters":sum(p.numel() for p in m.parameters())}
        torch.cuda.synchronize(dev)
        torch.cuda.reset_peak_memory_stats(dev)

        def infer(model, ids):
            torch.cuda.synchronize(dev)
            t0=time.perf_counter()
            out=model(input_ids=ids,use_cache=True)
            torch.cuda.synchronize(dev)
            t1=time.perf_counter()
            state=out.past_key_values
            logits=out.logits[:,-1,:]
            first=logits.detach().float().cpu()
            predicted=[]
            for index in range(GENERATED):
                token=logits.argmax(-1,keepdim=True)
                predicted.append(int(token.item()))
                if index < GENERATED-1:
                    # Exact prior-token count; all keys remain in the cache.
                    mask=torch.ones((1,ids.shape[1]+index+1),
                                    dtype=torch.long,device=dev)
                    out=model(input_ids=token,past_key_values=state,
                              attention_mask=mask,use_cache=True)
                    state=out.past_key_values
                    logits=out.logits[:,-1,:]
            torch.cuda.synchronize(dev)
            t2=time.perf_counter()
            return {"tokens":predicted,"first_logits":first,
                    "prefill_s":t1-t0,"decode_32_s":t2-t1,"total_s":t2-t0}

        result["cases"]=[]
        with torch.inference_mode():
            for ctx in CONTEXTS:
                ids=complete[:,:ctx].to(dev).contiguous()
                # Warm up both backends on exactly the same context.
                for backend in BACKENDS:
                    for _ in range(2):infer(models[backend],ids)
                runs={backend:[] for backend in BACKENDS}
                logits_differences=[]
                for i in range(REPEATS):
                    observations={}
                    for backend in repetition_order(i):
                        observations[backend]=infer(models[backend],ids)
                        runs[backend].append(observations[backend])
                    if observations["eager"]["tokens"]!=observations["sdpa"]["tokens"]:
                        raise RuntimeError(f"ATTENTION_KERNEL_GREEDY_OUTPUT_DIVERGENCE:{ctx}:{i}")
                    logits_differences.append(
                        float((observations["eager"]["first_logits"]-
                               observations["sdpa"]["first_logits"]).abs().max()))
                    if any(x<=0 or not (x<1000) for backend in BACKENDS
                           for x in (observations[backend]["prefill_s"],
                                     observations[backend]["decode_32_s"],
                                     observations[backend]["total_s"])):
                        raise RuntimeError("INVALID_GPU_LATENCY")
                summary={k:median_times(runs[k]) for k in BACKENDS}
                result["cases"].append({
                  "prompt_tokens":ctx,"generated_tokens":GENERATED,
                  "paired_trials":REPEATS,
                  "order_rule":"alternating eager/sdpa and sdpa/eager",
                  "eager_trials":[{k:v[k] for k in ("prefill_s","decode_32_s","total_s")} for v in runs["eager"]],
                  "sdpa_trials":[{k:v[k] for k in ("prefill_s","decode_32_s","total_s")} for v in runs["sdpa"]],
                  "median_s":summary,
                  "eager_over_sdpa_ratio":{
                    k:summary["eager"][k]/summary["sdpa"][k] for k in ("prefill_s","decode_32_s","total_s")},
                  "gpu_peak_allocated_mib":torch.cuda.max_memory_allocated(dev)/(1024**2),
                  "gpu_peak_reserved_mib":torch.cuda.max_memory_reserved(dev)/(1024**2),
                  "max_first_logits_abs_difference":max(logits_differences),
                  "all_greedy_outputs_equal":True,
                  "greedy_token_hash":hashlib.sha256(
                      json.dumps(runs["sdpa"][0]["tokens"]).encode()).hexdigest()
                })
        result["status"]="PASS_REAL_GPU_LARGER_PRETRAINED_MODEL_OPTIMIZED_SDPA_BASELINE"
    except Exception as e:
        result.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
        raise
    finally:
        RESULT.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("G61_RESULT_STATUS="+result["status"],flush=True)
        if result.get("error"):
            print("G61_ERROR="+result["error"],flush=True)

if __name__=="__main__":main()
