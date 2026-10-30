#!/usr/bin/env python3
"""ACC G60: real RTX CUDA, authenticated pretrained GPT-2, measured GPU cached decoding.

Unmerged research only. Preregistered BEFORE code at ACC-G60-PREEXEC-20261030.md.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import time

REPO = "openai-community/gpt2"
REV = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHT_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
FILES = ("config.json", "generation_config.json", "merges.txt", "model.safetensors",
         "tokenizer.json", "tokenizer_config.json", "vocab.json")
CONTEXTS = (128, 384)
GENERATED = 32
REPS = 5
OUTPUT = Path(os.getenv("G60_OUTPUT_PATH", "g60_result.json"))
PROMPT = (
    "The purpose of this reproducible experiment is to measure the computational cost "
    "of generating a continuation from an already trained language model. We separate "
    "the initial prompt processing from incremental cached decoding and preserve the "
    "exact model identity. No conclusion about language quality or novel acceleration "
    "is warranted from these timing measurements. "
) * 50

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def pack(rows):
    return {k: statistics.median(r[k] for r in rows)
            for k in ("prefill_s", "decode_32_s", "full_inference_s")}

def main():
    import torch
    import transformers
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    receipt = {
        "gate": "ACC-G60", "schema": "forge.acc.g60.real-cuda-causal-lm.v1",
        "status": "UNVERIFIED", "source_commit": os.getenv("GITHUB_SHA", ""),
        "platform": platform.platform(), "torch": torch.__version__,
        "torch_cuda": torch.version.cuda, "transformers": transformers.__version__,
        "model_repo": REPO, "revision": REV, "expected_weight_sha256": WEIGHT_SHA,
        "scientific_acceptance": "NOT_GRANTED",
        "model_training_performed": False, "novel_acceleration_established": False,
        "production_optimized_baseline": False
    }
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA_NOT_AVAILABLE_NO_CPU_FALLBACK")
        if not torch.version.cuda or tuple(map(int, torch.version.cuda.split(".")[:2])) < (12, 8):
            raise RuntimeError("BLACKWELL_RUNTIME_UNSUPPORTED")
        dev = torch.device("cuda:0")
        name = torch.cuda.get_device_name(dev)
        capability = torch.cuda.get_device_capability(dev)
        free, total = torch.cuda.mem_get_info(dev)
        if capability != (12, 0) or "NVIDIA" not in name.upper() or free < 5000*1024*1024:
            raise RuntimeError(f"GPU_ADMISSION_REJECTED cap={capability} free={free} name={name}")
        receipt["gpu"] = {
            "name": name, "compute_capability": list(capability),
            "memory_free_mib_before": free // (1024*1024),
            "memory_total_mib": total // (1024*1024)
        }
        x = torch.linspace(-1, 1, 1024*1024, device=dev, dtype=torch.float32).reshape(1024,1024)
        t0 = time.perf_counter()
        y = x @ x
        torch.cuda.synchronize(dev)
        if y.device.type != "cuda" or not torch.isfinite(y).all().item():
            raise RuntimeError("CUDA_MATMUL_KERNEL_INVALID")
        receipt["cuda_matmul_1024x1024"] = {
            "status": "PASS", "elapsed_s": time.perf_counter()-t0,
            "device": str(y.device), "sum": float(y.sum().item())
        }
        del x, y
        torch.cuda.empty_cache()

        root = Path(os.environ["G60_MODEL_ROOT"])
        root.mkdir(parents=True, exist_ok=False)
        manifest = []
        for name in FILES:
            fp = Path(hf_hub_download(repo_id=REPO, revision=REV, filename=name, token=False))
            dest = root / name
            shutil.copyfile(fp, dest)
            manifest.append({"path":name, "sha256":sha256(dest), "bytes":dest.stat().st_size})
        observed = next(x["sha256"] for x in manifest if x["path"] == "model.safetensors")
        if observed != WEIGHT_SHA:
            raise RuntimeError(f"AUTHENTIC_MODEL_WEIGHT_MISMATCH {observed}")
        receipt["files"] = manifest
        tok = AutoTokenizer.from_pretrained(
            str(root), local_files_only=True, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(
            str(root), local_files_only=True, trust_remote_code=False,
            use_safetensors=True).eval()
        if model.config.model_type != "gpt2" or model.config.is_encoder_decoder:
            raise RuntimeError("PINNED_CAUSAL_MODEL_MISMATCH")
        token_ids = tok(PROMPT, add_special_tokens=False, return_tensors="pt")["input_ids"]
        if token_ids.shape[1] < max(CONTEXTS) + GENERATED:
            raise RuntimeError("AUTHORED_PROMPT_TOO_SHORT")
        receipt["model_architecture"] = {
            "type": model.config.model_type,
            "parameters": sum(p.numel() for p in model.parameters()),
            "max_positions": model.config.n_positions,
            "weight_dtype": str(next(model.parameters()).dtype)
        }

        def synchronize(device):
            if device.type == "cuda":
                torch.cuda.synchronize(device)

        def infer(net, ids, device):
            synchronize(device)
            t0 = time.perf_counter()
            out = net(input_ids=ids.to(device), use_cache=True)
            synchronize(device)
            t1 = time.perf_counter()
            state = out.past_key_values
            logits = out.logits[:, -1, :]
            first_logits = logits.detach().cpu()
            toks = []
            for n in range(GENERATED):
                next_token = logits.argmax(-1, keepdim=True)
                toks.append(next_token)
                if n < GENERATED - 1:
                    am = torch.ones((1, ids.shape[1]+n+1), device=device, dtype=torch.long)
                    out = net(input_ids=next_token, past_key_values=state,
                              attention_mask=am, use_cache=True)
                    state, logits = out.past_key_values, out.logits[:, -1, :]
            synchronize(device)
            t2 = time.perf_counter()
            return {
                "tokens": torch.cat(toks, dim=1).cpu().tolist()[0],
                "first_logits": first_logits,
                "prefill_s": t1-t0,
                "decode_32_s": t2-t1,
                "full_inference_s": t2-t0
            }

        rows = []
        infer_cpu_tokens = {}
        cpu_first_logits = {}
        with torch.inference_mode():
            for length in CONTEXTS:
                ids = token_ids[:, :length].clone()
                if length+GENERATED > model.config.n_positions:
                    raise RuntimeError("CONTEXT_OVERFLOW")
                cpu = infer(model, ids, torch.device("cpu"))
                infer_cpu_tokens[length] = cpu["tokens"]
                cpu_first_logits[length] = cpu["first_logits"]
                rows.append({"context_tokens":length,"cpu": {
                    k:cpu[k] for k in ("prefill_s","decode_32_s","full_inference_s")}})
            model.to(dev)
            if next(model.parameters()).device.type != "cuda":
                raise RuntimeError("MODEL_CPU_FALLBACK")
            for row in rows:
                length = row["context_tokens"]
                ids = token_ids[:, :length].clone()
                # Exactly two unmetered warmup runs, then five individually measured runs.
                for _ in range(2):
                    infer(model, ids, dev)
                measured = []
                torch.cuda.reset_peak_memory_stats(dev)
                for _ in range(REPS):
                    measurement = infer(model, ids, dev)
                    if measurement["tokens"] != infer_cpu_tokens[length]:
                        raise RuntimeError("CPU_CUDA_GREEDY_OUTPUT_MISMATCH")
                    measured.append(measurement)
                row["gpu_runs"] = [
                    {k:m[k] for k in ("prefill_s","decode_32_s","full_inference_s")}
                    for m in measured
                ]
                row["gpu_median_s"] = pack(measured)
                row["gpu_peak_allocated_mib"] = (
                    torch.cuda.max_memory_allocated(dev) / (1024**2))
                row["gpu_peak_reserved_mib"] = (
                    torch.cuda.max_memory_reserved(dev) / (1024**2))
                row["greedy_output_match_cpu"] = True
                row["first_token_logit_max_abs_diff"] = float(
                    (measured[0]["first_logits"]-cpu_first_logits[length]).abs().max())
                row["gpu_repeats"] = REPS
        receipt["results"] = rows
        receipt["status"] = "PASS_REAL_CUDA_AUTHENTIC_MODEL"
    except Exception as e:
        receipt.update({"status":"FAIL_OR_BLOCKED","error":f"{type(e).__name__}: {e}"})
        raise
    finally:
        OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n",
                          encoding="utf-8")
        print("G60_RECEIPT="+json.dumps({
            k:receipt.get(k) for k in ("status","torch_cuda","gpu","error")
        }), flush=True)

if __name__ == "__main__":
    main()
