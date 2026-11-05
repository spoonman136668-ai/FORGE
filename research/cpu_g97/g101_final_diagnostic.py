#!/usr/bin/env python3
"""Final G101 falsification: real original GPT-2 exact KV, SDPA vs eager.

Already-consumed development ranks only. This is a correctness/mechanism
experiment, not a latency/throughput qualification or protected first use.
"""
import hashlib
import json
import os
import platform
import re
import sys
import traceback
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
G96 = HERE.parent / "cpu_g96"
if str(G96) not in sys.path:
    sys.path.insert(0, str(G96))
from g96_original_adapter import assert_parity
from g100_development_original import _g95, select_cohort
from research.cpu_g97.g101_original_parity import (
    PATTERN, SUFFIX_RANKS, ForwardCounter, check_pattern, verify_forward_calls)
from research.cpu_g97.g101_original_adapter import run_g101
from research.cpu_g97.g101_prefix_capture import capture_prefix_from_full_prefill

BACKENDS = ("sdpa", "eager")
SUFFIX_OFFSETS = (0, 5)
PAIRS_PER_BACKEND = 10
TENSORS_PER_PAIR = 24
MAX_RESIDENT_BYTES = 86114304
SCHEMA = "forge.cpu-g101.final-kv-falsification.v1"


def tensor_report(reference, captured, torch):
    """Compare actual FP32 bit patterns, not approximate tensor equality."""
    if reference.shape != captured.shape or reference.dtype != captured.dtype:
        raise RuntimeError("G101_FINAL_KV_LAYOUT_DRIFT")
    if reference.dtype != torch.float32:
        raise RuntimeError("G101_FINAL_FP32_DRIFT")
    if not bool(torch.isfinite(reference).all()) or not bool(torch.isfinite(captured).all()):
        raise RuntimeError("G101_FINAL_NONFINITE_KV")
    a = reference.contiguous().view(torch.int32).to(torch.int64)
    b = captured.contiguous().view(torch.int32).to(torch.int64)
    changed = int(torch.count_nonzero(a != b).item())
    # IEEE754 ordered-int view: inspect ULP distances, preserving bitwise
    # mismatch counts (including any differing sign of signed zero).
    base = -(1 << 31)
    ai = torch.where(a < 0, base - a, a)
    bi = torch.where(b < 0, base - b, b)
    ulp_max = int((ai - bi).abs().max().item())
    abs_max = float((reference - captured).abs().max().item())
    return {"elements": int(reference.numel()), "bit_mismatches": changed,
            "exact": changed == 0, "max_ulp": ulp_max,
            "max_abs": abs_max}


def pair_report(standalone, full, prefix_tokens, torch):
    if len(standalone) != 12 or len(full) != 12:
        raise RuntimeError("G101_FINAL_LAYER_COUNT_DRIFT")
    layers = []
    for layer_index, (short, long) in enumerate(zip(standalone, full)):
        if len(short) != 2 or len(long) != 2:
            raise RuntimeError("G101_FINAL_KV_PAIR_DRIFT")
        vectors = []
        for a, b in zip(short, long):
            vectors.append(tensor_report(a, b[..., :prefix_tokens, :], torch))
        layers.append({"layer": layer_index, "key": vectors[0], "value": vectors[1]})
    return {"layers": layers, "tensors": 24,
            "exact": all(item[k]["exact"] for item in layers for k in ("key", "value")),
            "bit_mismatches": sum(item[k]["bit_mismatches"]
                                  for item in layers for k in ("key", "value")),
            "max_abs": max(item[k]["max_abs"] for item in layers for k in ("key", "value")),
            "max_ulp": max(item[k]["max_ulp"] for item in layers for k in ("key", "value"))}


def final_verdict(arms):
    if set(arms) != set(BACKENDS):
        raise RuntimeError("G101_FINAL_MISSING_BACKEND")
    feasible = []
    for backend in BACKENDS:
        record = arms[backend]
        if len(record.get("pairs", [])) != PAIRS_PER_BACKEND:
            raise RuntimeError("G101_FINAL_INCOMPLETE_PAIR_MATRIX")
        if record.get("generated_token_parity") is not True:
            raise RuntimeError("G101_FINAL_TOKEN_PARITY_FAIL")
        if record.get("model_calls") != len(PATTERN) * 8:
            raise RuntimeError("G101_FINAL_FORWARD_COUNT_FAIL")
        if record.get("extra_prefix_forwards") != 0:
            raise RuntimeError("G101_FINAL_HIDDEN_PREFIX_COMPUTE")
        if record.get("max_resident_kv_bytes", MAX_RESIDENT_BYTES + 1) > MAX_RESIDENT_BYTES:
            raise RuntimeError("G101_FINAL_MEMORY_CAP_FAIL")
        if all(pair["exact"] for pair in record["pairs"]):
            feasible.append(backend)
    return ("EXACT_CAPTURE_FEASIBLE" if feasible else "RETIRE_G101_EXACT_CAPTURE"), feasible


def main():
    if os.getenv("G101_FINAL_DEVELOPMENT_ONLY") != "1":
        raise RuntimeError("G101_FINAL_DEVELOPMENT_GUARD")
    source_sha = os.getenv("GITHUB_SHA", "")
    if not re.fullmatch("[0-9a-f]{40}", source_sha):
        raise RuntimeError("G101_FINAL_SOURCE_SHA_MISSING")
    receipt = {
        "schema": SCHEMA, "source_sha": source_sha, "phase": "DEVELOPMENT_ONLY",
        "heldout_executed": False, "promotion_allowed": False,
        "scientific_acceptance": "NOT_GRANTED",
        "performance_verdict": "NOT_EVALUATED",
        "decision": "UNVERIFIED", "arms": {},
        "development_ranks": list(range(276, 286)),
    }
    try:
        import psutil
        import torch
        import transformers
        from transformers import AutoTokenizer, AutoModelForCausalLM
        g = _g95()
        if (platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64")
                or torch.__version__ != "2.5.1+cpu"
                or transformers.__version__ != "4.48.3"
                or torch.version.cuda is not None):
            raise RuntimeError("G101_FINAL_PINNED_RUNTIME_DRIFT")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        proc = psutil.Process()
        previous = proc.cpu_affinity()
        if len(previous) < 3:
            raise RuntimeError("G101_FINAL_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(previous[:3])
        try:
            receipt.update({
                "model_revision": g.MODEL_REV, "weights_sha256": g.WEIGHTS_SHA,
                "data_revision": g.DATA_REV, "data_sha256": g.DATA_SHA,
                "model_configured_threads": [2, 1],
                "affinity": proc.cpu_affinity(), "pattern": list(PATTERN),
                "pattern_coverage": check_pattern(),
                "backends": list(BACKENDS),
            })
            req = urllib.request.Request(
                "https://raw.githubusercontent.com/openai/grade-school-math/"
                + g.DATA_REV + "/grade_school_math/data/test.jsonl",
                headers={"User-Agent": "FORGE-G101-FINAL-DEVELOPMENT/1"})
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read(800001)
            if len(data) != g.DATA_BYTES or hashlib.sha256(data).hexdigest() != g.DATA_SHA:
                raise RuntimeError("G101_FINAL_DATASET_IDENTITY_DRIFT")
            records = [{"instruction": item["question"], "category": "math_word_problem"}
                       for item in (json.loads(line) for line in data.decode().splitlines()
                                    if line.strip())]
            selected = select_cohort(records, "development")
            receipt["question_hashes"] = [selected[i]["instruction_sha256"]
                                          for i in SUFFIX_RANKS]
            g55 = g.module("g101_final_g55", "llm_g55/g55_gpt2_controls.py")
            if (g55.REV, g55.WEIGHT_SHA) != (g.MODEL_REV, g.WEIGHTS_SHA):
                raise RuntimeError("G101_FINAL_MODEL_IDENTITY_DRIFT")
            root, manifest = g55.stage()
            receipt["model_manifest_sha256"] = g.sha_file(root / "manifest.json")
            tokenizer = AutoTokenizer.from_pretrained(
                str(root), local_files_only=True, trust_remote_code=False)
            def encode(text):
                return tokenizer(text, return_tensors="pt", add_special_tokens=False)["input_ids"]
            prefixes = [encode(x) for x in g.PREFIX_TEXTS]
            prefixes.append(encode(g.PREFIX_TEXTS[0] + " [G96_OVERFLOW_00]"))
            suffixes = [encode(selected[i]["instruction"]) for i in SUFFIX_RANKS]
            tok_fp = hashlib.sha256("".join(x["sha256"] for x in manifest).encode()).hexdigest()
            keys = [g.key_for(x, tok_fp) for x in prefixes]
            if len(set(keys)) != 5:
                raise RuntimeError("G101_FINAL_PREFIX_KEYS_NOT_UNIQUE")
            for backend in BACKENDS:
                model = AutoModelForCausalLM.from_pretrained(
                    str(root), local_files_only=True, use_safetensors=True,
                    trust_remote_code=False, attn_implementation=backend).eval()
                actual = model.config._attn_implementation
                if actual != backend:
                    raise RuntimeError("G101_FINAL_ATTN_BACKEND_DRIFT_"+str(actual))
                pairs, kv_sizes = [], []
                with torch.inference_mode():
                    for pid, prefix in enumerate(prefixes):
                        prefix_len = int(prefix.shape[1])
                        oracle = model(input_ids=prefix, use_cache=True).past_key_values
                        budget = g.tensor_tree_bytes(oracle)
                        if budget <= 0 or budget > MAX_RESIDENT_BYTES:
                            raise RuntimeError("G101_FINAL_PREFIX_BUDGET")
                        kv_sizes.append(budget)
                        for suffix_offset in SUFFIX_OFFSETS:
                            suffix = suffixes[pid + suffix_offset]
                            full = torch.cat((prefix, suffix), dim=1)
                            if int(full.shape[1]) + g.TOKENS > model.config.n_positions:
                                raise RuntimeError("G101_FINAL_CONTEXT_OVERFLOW")
                            full_past = model(input_ids=full, use_cache=True).past_key_values
                            captured = capture_prefix_from_full_prefill(
                                full_past, prefix_len, expected_bytes=budget)
                            check = pair_report(oracle, captured, prefix_len, torch)
                            pairs.append({
                                "prefix_id": pid, "suffix_rank": pid + suffix_offset,
                                "prefix_tokens": prefix_len,
                                "suffix_tokens": int(suffix.shape[1]),
                                **check,
                            })
                    stream = [
                        {"prefix_id": pid, "suffix": suffixes[i],
                         "source_row": selected[i]["source_row"],
                         "prefix_kv_bytes": kv_sizes[pid]}
                        for i, pid in enumerate(PATTERN)
                    ]
                    baseline = {}
                    for i, request in enumerate(stream):
                        full = torch.cat((
                            prefixes[request["prefix_id"]], request["suffix"]), dim=1)
                        baseline[i], _ = g.baseline_request(
                            model, full, g.TOKENS, torch, proc)
                    counter = ForwardCounter(model)
                    candidate, metrics = run_g101(
                        counter, stream, prefixes, keys, torch, proc)
                assert_parity(baseline, candidate)
                flags = [r["hit"] for r in metrics["rows"]]
                verify_forward_calls(counter.calls, stream, prefixes, g.TOKENS, flags)
                frozen = check_pattern()
                if (metrics["hits"] != frozen["expected_hits"]
                        or metrics["misses"] != frozen["expected_misses"]
                        or metrics["evictions"] != frozen["expected_evictions"]):
                    raise RuntimeError("G101_FINAL_CACHE_COUNTER_DRIFT")
                if len(pairs) != PAIRS_PER_BACKEND or any(p["tensors"] != 24 for p in pairs):
                    raise RuntimeError("G101_FINAL_PAIR_COMPLETENESS")
                record = {
                    "attention_backend": actual, "pairs": pairs,
                    "generated_token_parity": True,
                    "model_calls": len(counter.calls),
                    "extra_prefix_forwards": metrics["extra_prefix_forwards"],
                    "max_resident_kv_bytes": metrics["max_resident_kv_bytes"],
                    "max_sampled_rss_bytes": metrics["max_rss"],
                    "cache_counters": {
                        key: metrics[key] for key in (
                            "hits", "misses", "admissions", "evictions", "capture_events")},
                    "output_sha256": hashlib.sha256(json.dumps(
                        candidate, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                }
                receipt["arms"][backend] = record
                print("G101_FINAL_BACKEND", backend, "exact_pairs",
                      sum(pair["exact"] for pair in pairs), "/10",
                      "max_ulp", max(pair["max_ulp"] for pair in pairs), flush=True)
                del model
            decision, feasible = final_verdict(receipt["arms"])
            receipt["decision"], receipt["feasible_backends"] = decision, feasible
            receipt["engineering"] = "PASS"
            print("G101_FINAL_MECHANISM_DECISION=" + decision, flush=True)
        finally:
            proc.cpu_affinity(previous)
    except BaseException as exc:
        receipt["engineering"] = "FAIL"
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
        receipt["traceback_tail"] = traceback.format_exc()[-3500:]
        raise
    finally:
        Path("cpu_g101_final_diagnostic.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
