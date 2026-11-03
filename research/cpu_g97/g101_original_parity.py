#!/usr/bin/env python3
"""G101 P2: original pinned GPT-2 *correctness-only* development diagnostic.

Uses already-consumed G100 development ranks 276-287, never protected ranks.
No timings, throughput verdict, production integration, or protected first-use.
"""
from __future__ import annotations
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
from research.cpu_g97.g101_original_adapter import run_g101

# Five exact keys exceed the frozen four-entry LRU capacity. Reuses existing
# development questions, with repeated prefixes and different suffixes.
PATTERN = (0, 1, 2, 3, 0, 4, 1, 4, 2, 2)
SUFFIX_RANKS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
SCHEMA = "forge.cpu-g101.original-parity-development.v1"


def check_pattern(pattern=PATTERN):
    if (not isinstance(pattern, tuple) or len(pattern) != 10
            or any(type(x) is not int or not 0 <= x < 5 for x in pattern)
            or set(pattern) != set(range(5)) or pattern != PATTERN):
        raise RuntimeError("G101_PARITY_PATTERN_DRIFT")
    # Frozen diagnostic needs both genuine hits and evictions.
    resident, hits, evictions = [], 0, 0
    for key in pattern:
        if key in resident:
            hits += 1
            resident.remove(key)
        elif len(resident) == 4:
            resident.pop(0)
            evictions += 1
        resident.append(key)
    if hits < 2 or evictions < 2:
        raise RuntimeError("G101_PARITY_COVERAGE_DRIFT")
    return {"requests": len(pattern), "expected_hits": hits,
            "expected_misses": len(pattern) - hits,
            "expected_evictions": evictions}


class ForwardCounter:
    """Observe model calls without adding an inference or changing the model."""
    def __init__(self, model):
        self.model = model
        self.calls = []
    def __call__(self, *args, **kwargs):
        ids = kwargs.get("input_ids")
        if args or ids is None or not hasattr(ids, "shape"):
            raise RuntimeError("G101_UNEXPECTED_MODEL_CALL")
        self.calls.append({"tokens": int(ids.shape[1]),
                           "has_past": kwargs.get("past_key_values") is not None})
        return self.model(*args, **kwargs)


def verify_forward_calls(calls, stream, prefixes, generated_tokens, hit_flags):
    if len(calls) != len(stream) * generated_tokens or len(hit_flags) != len(stream):
        raise RuntimeError("G101_EXTRA_MODEL_FORWARD_OR_COUNT_DRIFT")
    for i, (request, hit) in enumerate(zip(stream, hit_flags)):
        group = calls[i * generated_tokens:(i + 1) * generated_tokens]
        pid = request["prefix_id"]
        full = int(prefixes[pid].shape[1]) + int(request["suffix"].shape[1])
        first = group[0]
        expected = int(request["suffix"].shape[1]) if hit else full
        if first != {"tokens": expected, "has_past": hit}:
            raise RuntimeError("G101_WRONG_FIRST_FORWARD_" + str(i))
        if any(call != {"tokens": 1, "has_past": True} for call in group[1:]):
            raise RuntimeError("G101_EXTRA_PREFIX_FORWARD_" + str(i))
    return True


def kv_comparison(prefix_past, full_past, prefix_length, torch):
    if len(prefix_past) != len(full_past) or not prefix_past:
        raise RuntimeError("G101_KV_LAYER_COUNT_MISMATCH")
    exact, max_delta, entries = True, 0.0, 0
    for short_pair, full_pair in zip(prefix_past, full_past):
        if len(short_pair) != len(full_pair) or len(short_pair) != 2:
            raise RuntimeError("G101_KV_STRUCTURE_MISMATCH")
        for standalone, full in zip(short_pair, full_pair):
            view = full[..., :prefix_length, :]
            if standalone.shape != view.shape or standalone.dtype != view.dtype:
                raise RuntimeError("G101_KV_SHAPE_OR_DTYPE_MISMATCH")
            match = bool(torch.equal(standalone, view))
            exact &= match
            if not match:
                delta = float((standalone - view).abs().max().item())
                max_delta = max(max_delta, delta)
            entries += 1
    return {"exact": bool(exact), "max_abs_delta": max_delta, "tensors": entries}


def main():
    if os.environ.get("G101_DEVELOPMENT_ONLY") != "1":
        raise RuntimeError("G101_PARITY_DEVELOPMENT_GUARD")
    source = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise RuntimeError("G101_SOURCE_IDENTITY_MISSING")
    receipt = {"schema": SCHEMA, "phase": "DEVELOPMENT_ONLY",
               "source_sha": source, "heldout_executed": False,
               "promotion_allowed": False, "performance_verdict": "NOT_EVALUATED",
               "scientific_acceptance": "NOT_GRANTED",
               "parity": "UNVERIFIED", "kv_exact": "UNVERIFIED"}
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
            raise RuntimeError("G101_PINNED_RUNTIME_DRIFT")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        proc = psutil.Process()
        old = proc.cpu_affinity()
        if len(old) < 3:
            raise RuntimeError("G101_THREE_CPUS_REQUIRED")
        proc.cpu_affinity(old[:3])
        try:
            receipt.update({"model_revision": g.MODEL_REV, "weights_sha256": g.WEIGHTS_SHA,
                            "data_revision": g.DATA_REV, "data_sha256": g.DATA_SHA,
                            "affinity": proc.cpu_affinity(),
                            "pattern": list(PATTERN), "coverage": check_pattern()})
            req = urllib.request.Request(
                "https://raw.githubusercontent.com/openai/grade-school-math/"
                + g.DATA_REV + "/grade_school_math/data/test.jsonl",
                headers={"User-Agent": "FORGE-G101-PARITY-DEVELOPMENT/1"})
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read(800001)
            if len(data) != g.DATA_BYTES or hashlib.sha256(data).hexdigest() != g.DATA_SHA:
                raise RuntimeError("G101_DATASET_IDENTITY_DRIFT")
            records = [{"instruction": x["question"], "category": "math_word_problem"}
                       for x in (json.loads(line) for line in data.decode().splitlines()
                                 if line.strip())]
            selected = select_cohort(records, "development")
            # Explicitly test the same *already-consumed* G100 development subset.
            receipt["development_ranks"] = [276 + i for i in SUFFIX_RANKS]
            receipt["question_hashes"] = [selected[i]["instruction_sha256"] for i in SUFFIX_RANKS]
            g55 = g.module("g101_g55", "llm_g55/g55_gpt2_controls.py")
            if (g55.REV, g55.WEIGHT_SHA) != (g.MODEL_REV, g.WEIGHTS_SHA):
                raise RuntimeError("G101_MODEL_IDENTITY_DRIFT")
            root, manifest = g55.stage()
            receipt["model_manifest_sha256"] = g.sha_file(root / "manifest.json")
            tok = AutoTokenizer.from_pretrained(
                str(root), local_files_only=True, trust_remote_code=False)
            model = AutoModelForCausalLM.from_pretrained(
                str(root), local_files_only=True, use_safetensors=True,
                trust_remote_code=False).eval()
            def encode(text):
                return tok(text, return_tensors="pt", add_special_tokens=False)["input_ids"]
            prefixes = [encode(text) for text in g.PREFIX_TEXTS]
            prefixes += [encode(g.PREFIX_TEXTS[0] + " [G96_OVERFLOW_00]")]
            fp = hashlib.sha256("".join(part["sha256"] for part in manifest).encode()).hexdigest()
            keys = [g.key_for(prefix, fp) for prefix in prefixes]
            if len(set(keys)) != 5:
                raise RuntimeError("G101_PREFIX_KEY_COLLISION")
            suffixes = [encode(selected[i]["instruction"]) for i in SUFFIX_RANKS]
            reference_past, expected_bytes, checks = [], [], []
            with torch.inference_mode():
                for pid, prefix in enumerate(prefixes):
                    oracle = model(input_ids=prefix, use_cache=True).past_key_values
                    expected_bytes.append(g.tensor_tree_bytes(oracle))
                    if expected_bytes[-1] > 86114304:
                        raise RuntimeError("G101_PREFIX_EXCEEDS_FROZEN_BUDGET")
                    reference_past.append(oracle)
                    # Two distinct suffixes for the same causal prefix.
                    for suffix in (suffixes[pid], suffixes[(pid + 5) % len(suffixes)]):
                        full = torch.cat((prefix, suffix), dim=1)
                        if int(full.shape[1]) + g.TOKENS > model.config.n_positions:
                            raise RuntimeError("G101_CONTEXT_OVERFLOW")
                        full_kv = model(input_ids=full, use_cache=True).past_key_values
                        result = kv_comparison(oracle, full_kv, int(prefix.shape[1]), torch)
                        checks.append({"prefix_id": pid,
                                       "suffix_tokens": int(suffix.shape[1]), **result})
                stream = []
                for i, pid in enumerate(PATTERN):
                    stream.append({"prefix_id": pid, "suffix": suffixes[i],
                                   "source_row": selected[i]["source_row"],
                                   "prefix_kv_bytes": expected_bytes[pid]})
                baseline = {}
                for i, request in enumerate(stream):
                    full = torch.cat((prefixes[request["prefix_id"]], request["suffix"]), dim=1)
                    baseline[i], _ = g.baseline_request(model, full, g.TOKENS, torch, proc)
                counter = ForwardCounter(model)
                outputs, metrics = run_g101(counter, stream, prefixes, keys, torch, proc)
            assert_parity(baseline, outputs)
            flags = [row["hit"] for row in metrics["rows"]]
            verify_forward_calls(counter.calls, stream, prefixes, g.TOKENS, flags)
            if (metrics["hits"] != receipt["coverage"]["expected_hits"]
                    or metrics["misses"] != receipt["coverage"]["expected_misses"]
                    or metrics["evictions"] != receipt["coverage"]["expected_evictions"]
                    or metrics["extra_prefix_forwards"] != 0):
                raise RuntimeError("G101_CACHE_EVENT_DRIFT")
            if metrics["max_resident_kv_bytes"] > 86114304:
                raise RuntimeError("G101_RESIDENT_MEMORY_DRIFT")
            receipt["kv_checks"] = checks
            receipt["cache_counters"] = {
                k: metrics[k] for k in ("hits", "misses", "admissions",
                                        "evictions", "max_resident_kv_bytes", "capture_events")}
            receipt["model_calls"] = len(counter.calls)
            receipt["output_sha256"] = hashlib.sha256(
                json.dumps(outputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            receipt["parity"] = "PASS"
            receipt["kv_exact"] = "PASS" if all(x["exact"] for x in checks) else "FAIL"
            if receipt["kv_exact"] != "PASS":
                raise RuntimeError("G101_PREFIX_KV_NOT_BIT_EXACT")
            print("G101_ORIGINAL_MODEL_PARITY=PASS")
            print("G101_PREFIX_KV_BIT_EXACT=PASS")
        finally:
            proc.cpu_affinity(old)
    except BaseException as exc:
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
        receipt["traceback_tail"] = traceback.format_exc()[-2500:]
        raise
    finally:
        Path("cpu_g101_original_parity.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
