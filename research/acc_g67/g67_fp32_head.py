#!/usr/bin/env python3
"""ACC G67: preregistered FP16 backbone + FP32 output head engineering falsifier.

Research only. Prior G63 generalization correctness FAIL remains immutable.
"""
from __future__ import annotations
import gc
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acc_g66"))
import g66_precision as prior

g63 = prior.g63
g64 = prior.g64
G66_SOURCE_BLOB = "60bfc9e6fa3cc3627d730567eb62cd9d543c2979"
G66_FINAL_BLOB = "5e037725a506f44f485295b26231dc5d34dcf163"
MODEL_VARIANTS = ("fp16_control", "fp16_backbone_fp32_head")
ARMS = ("baseline", "candidate")
CASES = ((.73, "natural_continuation", 1536),
         (.17, "natural_continuation", 512),
         (.17, "source_question", 512),
         (.45, "natural_continuation", 1536),
         (.45, "source_question", 1536))
WARMUPS = 2
PAIRS = 3
LOGIT_REPEATS = 3
MODES = prior.MODES
RESULT = Path(os.getenv("G67_RESULT", "g67_result.json"))
CORPUS = Path(os.getenv("G67_CORPUS", "g67_wikitext_test.txt"))

def source_identity():
    blob = g64.git_blob(Path(prior.__file__).read_bytes())
    if blob != G66_SOURCE_BLOB:
        raise RuntimeError("G66_SOURCE_BLOB_DRIFT")
    final_file = Path(__file__).resolve().parents[2] / "docs" / "research" / "ACC-G66-FINAL-20261030.json"
    if g64.git_blob(final_file.read_bytes()) != G66_FINAL_BLOB:
        raise RuntimeError("G66_FINAL_EVIDENCE_BLOB_DRIFT")
    freeze = Path(__file__).resolve().parents[2] / "docs" / "research" / "ACC-G67-PREEXEC-20261030.md"
    if not freeze.is_file():
        raise RuntimeError("G67_PREEXEC_FREEZE_MISSING")
    return prior.frozen_identity()

def same_tokens(a, b):
    result = prior.first_difference(a, b)
    return {"exact": result["same"], "first_difference": result["index"],
            "baseline_id": result.get("baseline_id"),
            "candidate_id": result.get("candidate_id")}

def project_head_fp32(model):
    """Only the final projection changes; reject weight ties and unexpected dtypes."""
    import torch
    from torch import nn
    import torch.nn.functional as F
    head = model.get_output_embeddings()
    if not isinstance(head, nn.Linear) or head.weight.dtype != torch.float16:
        raise RuntimeError("UNEXPECTED_HEAD_ARCHITECTURE_OR_DTYPE")
    if model.config.tie_word_embeddings or head.weight.data_ptr() == model.get_input_embeddings().weight.data_ptr():
        raise RuntimeError("TIED_OUTPUT_EMBEDDING_UNSAFE")
    class FP32OutputHead(nn.Module):
        def __init__(self, original):
            super().__init__()
            self.weight = nn.Parameter(original.weight.detach().float().clone(), requires_grad=False)
            self.bias = (nn.Parameter(original.bias.detach().float().clone(), requires_grad=False)
                         if original.bias is not None else None)
        def forward(self, hidden):
            return F.linear(hidden.float(), self.weight, self.bias)
    model.set_output_embeddings(FP32OutputHead(head))
    if (model.get_output_embeddings().weight.dtype != torch.float32
        or model.get_output_embeddings().weight.device.type != "cuda"
        or any(p.dtype != torch.float16 for name, p in model.named_parameters()
               if not name.startswith("lm_head."))):
        raise RuntimeError("LOCALIZED_PRECISION_INVARIANT_FAILED")
    return model

def measure(model, ids, tokenizer, arm):
    import torch
    calls = {"count": 0}
    def forward_hook(*unused):
        calls["count"] += 1
    h = model.register_forward_pre_hook(forward_hook)
    kwargs = dict(input_ids=ids, do_sample=False, num_beams=1, use_cache=True,
                  max_new_tokens=64, eos_token_id=-1, pad_token_id=tokenizer.eos_token_id)
    if arm == "candidate":
        kwargs.update(prompt_lookup_num_tokens=5, max_matching_ngram_size=3)
    torch.cuda.synchronize(ids.device)
    torch.cuda.reset_peak_memory_stats(ids.device)
    start = time.perf_counter()
    try:
        output = model.generate(**kwargs)
        torch.cuda.synchronize(ids.device)
    finally:
        h.remove()
    seconds = time.perf_counter() - start
    ids_out = output[0, ids.shape[1]:].detach().cpu().tolist()
    accepted, raw_count = g64.audited_continuation(ids_out, arm)
    if seconds <= 0 or len(accepted) != 64:
        raise RuntimeError("BAD_TIMING_OR_GENERATED_LENGTH")
    metrics = {"seconds": seconds,
               "accepted_sha256": prior.sha_ids(accepted),
               "raw_tokens": raw_count,
               "extra_raw_tokens_charged": raw_count - 64,
               "forward_calls": calls["count"],
               "allocated_mib": torch.cuda.max_memory_allocated(ids.device) / 1024**2,
               "reserved_mib": torch.cuda.max_memory_reserved(ids.device) / 1024**2}
    return accepted, metrics

def case_summary(measured):
    first = {arm: measured[arm][0][0] for arm in ARMS}
    for arm in ARMS:
        if any(x[0] != first[arm] for x in measured[arm]):
            raise RuntimeError("REPEATED_GREEDY_TOKEN_NONDETERMINISM")
    return {
        "baseline_sha256": prior.sha_ids(first["baseline"]),
        "candidate_sha256": prior.sha_ids(first["candidate"]),
        "comparison": same_tokens(first["baseline"], first["candidate"]),
        "median_seconds": {arm: statistics.median(row["seconds"] for _, row in measured[arm])
                           for arm in ARMS},
        "peak_allocated_mib": {arm: max(row["allocated_mib"] for _, row in measured[arm])
                              for arm in ARMS},
        "runs": {arm: [row for _, row in measured[arm]] for arm in ARMS}
    }

def classify(cases, forced):
    if len(cases) != len(CASES):
        raise ValueError("MISSING_FROZEN_CASE")
    if set(forced) != set(MODES) or any(len(forced[mode]) != LOGIT_REPEATS for mode in MODES):
        raise ValueError("MISSING_FROZEN_LOGIT_REPEAT")
    unique = all(row["greedy_argmax_id"] == prior.original.CANDIDATE_ID and
                 row["exact_max_tie_count"] == 1
                 for mode in MODES for row in forced[mode])
    numerical = unique and cases[0]["variants"][MODEL_VARIANTS[1]]["comparison"]["exact"]
    parity = all(case["variants"][MODEL_VARIANTS[1]]["comparison"]["exact"] for case in cases)
    memory = all(
        c["variants"][MODEL_VARIANTS[1]]["peak_allocated_mib"]["candidate"] <=
        1.20*c["variants"][MODEL_VARIANTS[0]]["peak_allocated_mib"]["candidate"]
        for c in cases)
    latency = all(
        c["variants"][MODEL_VARIANTS[1]]["median_seconds"]["baseline"] <=
        1.25*c["variants"][MODEL_VARIANTS[0]]["median_seconds"]["baseline"]
        for c in cases)
    ratios = [c["variants"][MODEL_VARIANTS[1]]["median_seconds"]["baseline"] /
              c["variants"][MODEL_VARIANTS[1]]["median_seconds"]["candidate"]
              for c in cases[1:]]
    if any(not math.isfinite(x) or x <= 0 for x in ratios):
        raise ValueError("BAD_LATENCY_RATIO")
    geomean = math.exp(sum(math.log(x) for x in ratios)/len(ratios))
    speed = geomean >= 1.15 and min(ratios) >= .85
    passed = numerical and parity and memory and latency and speed
    return {
        "numerical_localized_fix": "PASS" if numerical else "NUMERICAL_HYPOTHESIS_REJECTED",
        "all_five_hybrid_exact": parity,
        "bounded_gpu_memory": memory,
        "bounded_hybrid_greedy_latency": latency,
        "independent_diagnostic_case_speedup_geomean": geomean,
        "independent_diagnostic_case_speedups": ratios,
        "bounded_candidate_speed": speed,
        "engineering_screen": "TECHNICAL_SCREEN_PASS_ONLY" if passed else "NO_GO_ENGINEERING",
        "prior_g63_generalization": "FAIL_NO_GO_UNCHANGED",
        "scientific_acceptance": "NOT_GRANTED"
    }

def run():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from huggingface_hub import snapshot_download
    from torch.profiler import profile, ProfilerActivity
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    receipt = {"schema": "forge.acc.g67.fp16-backbone-fp32-head.research-screen.v1",
               "status": "UNVERIFIED",
               "run_source_sha": os.getenv("GITHUB_SHA", ""),
               "torch": torch.__version__, "cuda": torch.version.cuda,
               "transformers": transformers.__version__, "platform": platform.platform(),
               "g63_generalization": "FAIL_NO_GO_UNCHANGED",
               "scientific_acceptance": "NOT_GRANTED",
               "novel_acceleration": False,
               "cases": []}
    try:
        receipt["source_provenance"] = source_identity()
        source = g63.frozen_source(CORPUS)
        if hashlib.sha256(source).hexdigest() != g64.G63_CORPUS_SHA256:
            raise RuntimeError("ORIGINAL_CORPUS_SHA_DRIFT")
        if not torch.cuda.is_available() or torch.version.cuda != "12.8":
            raise RuntimeError("CUDA_12_8_GPU_REQUIRED")
        device = torch.device("cuda:0")
        gpu_name = torch.cuda.get_device_name(device)
        free, total = torch.cuda.mem_get_info(device)
        if (torch.cuda.get_device_capability(device) != (12, 0)
            or "NVIDIA" not in gpu_name.upper() or free < 7500*1024**2):
            raise RuntimeError("AUTHENTIC_GPU_IDENTITY_OR_MEMORY_UNAVAILABLE")
        a = torch.ones((1024,1024), device=device)
        b = a @ a
        torch.cuda.synchronize(device)
        if b.device.type != "cuda" or abs(float(b[0,0])-1024)>1e-4:
            raise RuntimeError("CUDA_MATMUL_PROOF_FAILED")
        del a, b
        torch.cuda.empty_cache()
        receipt["gpu"] = {"name":gpu_name,"compute_capability":[12,0],
                          "initial_free_mib": free/1024**2, "total_mib":total/1024**2}
        snapshot = Path(snapshot_download(repo_id=g63.REPO, revision=g63.REV,
                                          token=False, allow_patterns=list(g63.FILES)))
        weights = snapshot/"model.safetensors"
        if (not weights.is_file() or weights.stat().st_size != g63.WEIGHT_SIZE
            or g64.file_sha256(weights) != g63.WEIGHT_SHA):
            raise RuntimeError("AUTHENTIC_MODEL_WEIGHTS_SHA_DRIFT")
        receipt["weights_sha256"] = g64.file_sha256(weights)
        tokenizer = AutoTokenizer.from_pretrained(str(snapshot), use_fast=True,
                                                    local_files_only=True, trust_remote_code=False)
        prompts = []
        for anchor, task, ctx in CASES:
            source_ids = g63.frozen_sample_tokens(tokenizer, source.decode("utf-8"), anchor)
            ids = g63.case_ids(torch, tokenizer, source_ids, task, ctx).to(device)
            if ids.shape[1] != ctx or ctx + 69 > 2048:
                raise RuntimeError("SOURCE_PROMPT_LENGTH_DRIFT")
            prompts.append(ids)
        hashes = [prior.sha_ids(ids[0].detach().cpu().tolist()) for ids in prompts]
        if hashes[0] != prior.original.G64_PROMPT_HASH:
            raise RuntimeError("ORIGINAL_G64_PROMPT_SHA_DRIFT")
        receipt["prompt_sha256"] = hashes
        control_first = None
        forced = {}
        with torch.inference_mode():
            for variant in MODEL_VARIANTS:
                model = AutoModelForCausalLM.from_pretrained(
                    str(snapshot), torch_dtype=torch.float16, attn_implementation="sdpa",
                    use_safetensors=True, trust_remote_code=False, local_files_only=True).eval().to(device)
                if (model.config.model_type != "llama"
                    or model.config.num_hidden_layers != 22
                    or model.config._attn_implementation != "sdpa"
                    or next(model.parameters()).device.type != "cuda"
                    or next(model.parameters()).dtype != torch.float16):
                    raise RuntimeError("G67_ARCHITECTURE_DTYPE_OR_DEVICE_DRIFT")
                if variant == MODEL_VARIANTS[1]:
                    model = project_head_fp32(model)
                with profile(activities=[ProfilerActivity.CPU]) as prof:
                    model(input_ids=prompts[0][:,:16], use_cache=True)
                    torch.cuda.synchronize(device)
                if "aten::scaled_dot_product_attention" not in [r.key for r in prof.key_averages()]:
                    raise RuntimeError("ACTUAL_SDPA_OPERATOR_NOT_USED")
                if variant == MODEL_VARIANTS[0]:
                    validated = prior.original.validate_orig_outputs(model, prompts[0], tokenizer)
                    control_first = validated["baseline"]["first_64_token_ids"]
                    receipt["original_fp16_hash_reproduction"] = "PASS"
                else:
                    if control_first is None:
                        raise RuntimeError("MISSING_PRIOR_CONTROL_TOKENS")
                    shared = torch.tensor([control_first[:48]], dtype=torch.long, device=device)
                    for mode in MODES:
                        forced[mode] = []
                    for repetition in range(LOGIT_REPEATS):
                        for mode in MODES:
                            logits = prior.logits_forced_prefix(model, prompts[0], shared, mode)
                            torch.cuda.synchronize(device)
                            row = prior.original.summarize_logits(logits)
                            row["repeat"] = repetition
                            forced[mode].append(row)
                for i, prompt in enumerate(prompts):
                    for arm in ARMS:
                        for _ in range(WARMUPS):
                            measure(model, prompt, tokenizer, arm)
                    measured = {arm: [] for arm in ARMS}
                    for repeat in range(PAIRS):
                        for arm in g63.paired_order(repeat):
                            measured[arm].append(measure(model, prompt, tokenizer, arm))
                    summary = case_summary(measured)
                    if variant == MODEL_VARIANTS[0] and i == 0:
                        if (summary["baseline_sha256"] != prior.original.BASELINE_SHA
                            or summary["candidate_sha256"] != prior.original.CANDIDATE_SHA
                            or summary["comparison"]["first_difference"] != 48
                            or summary["comparison"]["baseline_id"] != 7866
                            or summary["comparison"]["candidate_id"] != 29871):
                            raise RuntimeError("ORIGINAL_G63_FAILURE_REFERENCE_DRIFT")
                    if variant == MODEL_VARIANTS[0]:
                        receipt["cases"].append({"case_index":i,"anchor":CASES[i][0],
                            "task":CASES[i][1],"context_tokens":CASES[i][2],
                            "prompt_sha256": hashes[i],"variants":{variant:summary}})
                    else:
                        receipt["cases"][i]["variants"][variant] = summary
                del model
                gc.collect()
                torch.cuda.empty_cache()
        receipt["forced_shared_prefix_fp32_head"] = forced
        receipt["classification"] = classify(receipt["cases"], forced)
        receipt["status"] = "PASS_COMPLETE_MEASUREMENT"
    except Exception as e:
        receipt.update({"status":"BLOCKED_INVALID_EVIDENCE",
                        "error":f"{type(e).__name__}: {e}"})
        raise
    finally:
        RESULT.write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print("G67_STATUS="+receipt["status"], flush=True)
        if receipt.get("classification"):
            print("G67_ENGINEERING="+receipt["classification"]["engineering_screen"], flush=True)

if __name__ == "__main__":
    run()
