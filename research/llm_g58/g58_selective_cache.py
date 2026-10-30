#!/usr/bin/env python3
"""G58 preregistered authentic GPT-2 prefix admission/eviction screen.

Independent research only. Three frozen request streams; exact pinned weights.
Arms: no cache, eager LRU(2), second-seen LRU(2).
Five paired rotated trials, identical 16-token greedy outputs required.
Do NOT interpret this as server batching, peak OS RSS or scientific acceptance.
"""
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import time

MODEL_REV = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
MODEL_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
TRIALS = 5
OUTPUT_TOKENS = 16
CAPACITY = 2
STREAMS = {
    "high_locality_75pct": (0, 0, 0, 0, 1, 1, 1, 1),
    "unique_0pct": tuple(range(8)),
    "thrash_four_families": (0, 1, 2, 0, 1, 2, 3, 3),
}
ARMS = ("no_cache", "eager_lru2", "second_seen_lru2")


def import_g55():
    path = Path(__file__).resolve().parents[1] / "llm_g55" / "g55_gpt2_controls.py"
    spec = importlib.util.spec_from_file_location("g55_frozen_source", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tensor_nbytes(cache):
    import torch
    if isinstance(cache, torch.Tensor):
        return cache.numel() * cache.element_size()
    if hasattr(cache, "key_cache") and hasattr(cache, "value_cache"):
        return sum(tensor_nbytes(t) for t in cache.key_cache) + sum(tensor_nbytes(t) for t in cache.value_cache)
    if isinstance(cache, (tuple, list)):
        return sum(tensor_nbytes(v) for v in cache)
    raise TypeError("UNKNOWN_KV_CACHE_STRUCTURE_" + type(cache).__name__)


def sha_tokens(tokens):
    return hashlib.sha256(tokens.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    g55 = import_g55()
    if (g55.REV, g55.WEIGHT_SHA) != (MODEL_REV, MODEL_SHA):
        raise RuntimeError("FROZEN_G55_IDENTITY_MISMATCH")
    torch.set_num_threads(1)
    report = {
        "gate": "G58",
        "kind": "REAL_GPT2_SEQUENTIAL_PREFIX_POLICY_SCREEN_NOT_PRODUCTION_QUALIFICATION",
        "git_sha": os.getenv("GITHUB_SHA", "NOT_SET"),
        "model_revision": MODEL_REV, "weight_sha256": MODEL_SHA,
        "torch": torch.__version__, "transformers": transformers.__version__,
        "host": platform.platform(), "capacity_entries": CAPACITY,
        "trial_count": TRIALS, "tokens_per_request": OUTPUT_TOKENS,
        "arms": ARMS, "streams": STREAMS,
        "engineering": "UNVERIFIED", "scientific": "UNVERIFIED",
        "promotion_allowed": False,
        "nonclaims": ["No concurrent inference", "No dynamic batching",
                      "No end-to-end tokenization/model-startup within paired runs",
                      "RSS snapshots are not true OS peak RSS",
                      "No optimized production serving comparison",
                      "No original native Wingless/Yggdrasil model integration",
                      "No G51 source mutation or FORGE controller changes"],
    }
    try:
        model_load_start = time.perf_counter()
        root, files = g55.stage()
        report["weight_files"] = files
        report["file_manifest_sha256"] = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
        tokenizer = AutoTokenizer.from_pretrained(str(root), trust_remote_code=False, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(str(root), use_safetensors=True,
                trust_remote_code=False, local_files_only=True).eval()
        report["model_load_and_stage_wall_s"] = time.perf_counter() - model_load_start
        if model.config.model_type != "gpt2":
            raise RuntimeError("ARCHITECTURE_NOT_GPT2")
        def ids(s):
            return tokenizer(s, return_tensors="pt", add_special_tokens=False)["input_ids"]
        prefix = [
            ids(g55.PREFIX + f" Family {i} has a unique context marker.") for i in range(8)
        ]
        suffix = [
            ids(f" Request {i}: state the bounded validation requirement.") for i in range(8)
        ]
        if len({tuple(p[0].tolist()) for p in prefix}) != 8:
            raise RuntimeError("CACHE_KEY_COLLISION")
        if max(p.shape[1] for p in prefix) + max(s.shape[1] for s in suffix) + OUTPUT_TOKENS > model.config.n_positions:
            raise RuntimeError("CONTEXT_TOO_LONG")

        def decode(prompt, past=None, prefix_len=0):
            import copy
            n = prompt.shape[1] + prefix_len
            kw = {"input_ids": prompt, "use_cache": True}
            if past is not None:
                kw["past_key_values"] = copy.deepcopy(past)
                kw["attention_mask"] = torch.ones((1, n), dtype=torch.long)
            out = model(**kw)
            state, logits = out.past_key_values, out.logits[:, -1, :]
            made = []
            for i in range(OUTPUT_TOKENS):
                token = logits.argmax(-1, keepdim=True)
                made.append(token)
                if i < OUTPUT_TOKENS - 1:
                    out = model(input_ids=token, past_key_values=state,
                                attention_mask=torch.ones((1, n+i+1), dtype=torch.long),
                                use_cache=True)
                    state, logits = out.past_key_values, out.logits[:, -1, :]
            return torch.cat(made, dim=1)

        process = psutil.Process()
        def execute(pattern, policy):
            lru = collections.OrderedDict()
            seen = set()
            measurements = {"hits": 0, "misses": 0, "admissions": 0, "evictions": 0,
                            "max_cache_entries": 0, "max_cache_bytes": 0,
                            "end_cache_bytes": 0, "max_sampled_rss": 0,
                            "cache_bytes_by_request": []}
            outputs = []
            for i, family in enumerate(pattern):
                key = tuple(prefix[family][0].tolist())
                if key in lru:
                    if policy == "no_cache":
                        raise RuntimeError("BASELINE_CACHE_NOT_EMPTY")
                    cache = lru[key]
                    lru.move_to_end(key)
                    measurements["hits"] += 1
                    outputs.append(decode(suffix[i], cache, prefix[family].shape[1]))
                else:
                    measurements["misses"] += 1
                    admit = policy == "eager_lru2" or (policy == "second_seen_lru2" and key in seen)
                    if admit:
                        cache = model(input_ids=prefix[family], use_cache=True).past_key_values
                        lru[key] = cache
                        measurements["admissions"] += 1
                        if len(lru) > CAPACITY:
                            lru.popitem(last=False)
                            measurements["evictions"] += 1
                        outputs.append(decode(suffix[i], cache, prefix[family].shape[1]))
                    else:
                        outputs.append(decode(torch.cat((prefix[family], suffix[i]), dim=1)))
                seen.add(key)
                if len(lru) > CAPACITY:
                    raise RuntimeError("CAPACITY_VIOLATION")
                current_bytes = sum(tensor_nbytes(v) for v in lru.values())
                measurements["max_cache_entries"] = max(measurements["max_cache_entries"], len(lru))
                measurements["max_cache_bytes"] = max(measurements["max_cache_bytes"], current_bytes)
                measurements["end_cache_bytes"] = current_bytes
                measurements["max_sampled_rss"] = max(measurements["max_sampled_rss"], process.memory_info().rss)
                measurements["cache_bytes_by_request"].append(current_bytes)
            return outputs, measurements

        def timed(pattern, policy):
            wall0, cpu0 = time.perf_counter(), time.process_time()
            output, values = execute(pattern, policy)
            values["process_cpu_s"] = time.process_time() - cpu0
            values["wall_s"] = time.perf_counter() - wall0
            return output, values

        with torch.inference_mode():
            for scenario, pattern in STREAMS.items():
                baseline, _ = execute(pattern, "no_cache")
                for policy in ARMS[1:]:
                    other, detail = execute(pattern, policy)
                    if any(not torch.equal(a, b) for a,b in zip(baseline, other)):
                        raise RuntimeError("TOKEN_MISMATCH_" + scenario + "_" + policy)
                    if detail["hits"]+detail["misses"] != len(pattern):
                        raise RuntimeError("HIT_COUNT_MISMATCH")
                for policy in ARMS:
                    execute(pattern, policy)  # warmed after correctness
                trials = []
                for i in range(TRIALS):
                    order = list(ARMS[i % 3:] + ARMS[:i % 3])
                    if i % 2:
                        order.reverse()
                    results = {}
                    for policy in order:
                        output, details = timed(pattern, policy)
                        if any(not torch.equal(a,b) for a,b in zip(baseline,output)):
                            raise RuntimeError("TRIAL_TOKEN_PARITY_FAILURE")
                        if details["hits"]+details["misses"] != len(pattern):
                            raise RuntimeError("TRIAL_HIT_ACCOUNTING_FAILURE")
                        results[policy] = details
                    trials.append({"order": order, "results": results,
                          "eager_speedup": results["no_cache"]["wall_s"]/results["eager_lru2"]["wall_s"],
                          "selective_speedup": results["no_cache"]["wall_s"]/results["second_seen_lru2"]["wall_s"]})
                rows = {"paired_trials": trials,
                        "median_eager_speedup": statistics.median(t["eager_speedup"] for t in trials),
                        "median_selective_speedup": statistics.median(t["selective_speedup"] for t in trials),
                        "outputs_sha256": [sha_tokens(t) for t in baseline]}
                for policy in ARMS:
                    rows[policy] = {key: trials[0]["results"][policy][key] for key in
                         ("hits", "misses", "admissions", "evictions", "max_cache_entries",
                          "max_cache_bytes", "end_cache_bytes", "cache_bytes_by_request")}
                    if any(t["results"][policy]["max_cache_entries"] > CAPACITY for t in trials):
                        raise RuntimeError("POLICY_CAPACITY_EXCEEDED")
                if scenario == "unique_0pct":
                    if any(rows[p]["hits"] for p in ARMS):
                        raise RuntimeError("UNIQUE_WORKLOAD_FALSE_HIT")
                    if rows["second_seen_lru2"]["admissions"] != 0 or rows["second_seen_lru2"]["max_cache_bytes"] != 0:
                        raise RuntimeError("UNIQUE_SELECTIVE_CACHE_SHOULD_STAY_EMPTY")
                    if rows["eager_lru2"]["evictions"] != 6:
                        raise RuntimeError("UNIQUE_EAGER_EVICTION_COUNT_MISMATCH")
                report.setdefault("scenarios", {})[scenario] = rows

            high = report["scenarios"]["high_locality_75pct"]["median_selective_speedup"]
            unique = report["scenarios"]["unique_0pct"]["median_selective_speedup"]
            report["engineering"] = "PASS"
            report["policy_screen"] = ("PASS" if high >= 1.15 and unique >= 0.98 else "FAIL")
            report["screen_thresholds"] = {
                "high_locality_min_selective_speedup": 1.15,
                "unique_min_selective_speedup": 0.98,
                "all_tokens_exact": True, "max_entries": 2}
            report["scientific"] = "UNVERIFIED"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        Path("g58_result.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"gate":report["gate"], "engineering":report["engineering"],
                         "screen":report.get("policy_screen"),
                         "error":report.get("error")},sort_keys=True))
        for name,row in report.get("scenarios",{}).items():
            print(json.dumps({"scenario":name, "selective":row["median_selective_speedup"],
                  "eager":row["median_eager_speedup"],
                  "selective_cache_bytes":row["second_seen_lru2"]["max_cache_bytes"],
                  "eager_cache_bytes":row["eager_lru2"]["max_cache_bytes"],
                  "selective_evictions":row["second_seen_lru2"]["evictions"],
                  "eager_evictions":row["eager_lru2"]["evictions"]},sort_keys=True))


if __name__ == "__main__":
    main()
