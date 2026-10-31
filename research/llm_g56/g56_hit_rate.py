#!/usr/bin/env python3
"""G56: preregistered GPT-2 cache-hit sensitivity (0% and 75% reuse).

Research-only. Same pinned checkpoint, 32-token greedy cached decode,
four-request batch, five paired alternating-order runs, exact token parity.
No concurrency, server-side batching, scientific promotion or production claims.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import time


def load_g55():
    path = Path(__file__).resolve().parents[1] / "llm_g55" / "g55_gpt2_controls.py"
    spec = importlib.util.spec_from_file_location("g55_original", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    import psutil
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    g55 = load_g55()
    torch.set_num_threads(1)
    report = {
        "gate": "G56",
        "type": "AUTHENTIC_HIT_RATE_SENSITIVITY_NOT_G51_REPLAY",
        "git_commit": os.getenv("GITHUB_SHA", "UNSET"),
        "model_revision": g55.REV,
        "weight_sha256": g55.WEIGHT_SHA,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "platform": platform.platform(),
        "correctness": "UNVERIFIED",
        "screen": "UNVERIFIED",
        "scientific_acceptance": "NOT_GRANTED",
        "promotion_allowed": False,
        "measurements_not_included": ["GPU", "energy", "peak_RSS", "batched_attention",
                                      "concurrent_serving", "tokenizer_runtime",
                                      "model_startup", "G51_frozen_archive_execution"],
    }
    try:
        root, records = g55.stage()
        report["file_sha256"] = records
        tok = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(str(root), local_files_only=True,
                                                     trust_remote_code=False, use_safetensors=True).eval()
        if model.config.model_type != "gpt2":
            raise RuntimeError("PINNED_MODEL_ARCHITECTURE_FAILURE")

        def ids(s):
            return tok(s, return_tensors="pt", add_special_tokens=False)["input_ids"]

        # Four prefixes deliberately differ in token IDs; no cache aliasing allowed.
        prefixes = [ids(g55.PREFIX + " Family " + c + " context.") for c in "ABCD"]
        suffixes = [ids(s) for s in (*g55.SUFFIXES,
                    " Question four: state the validation requirement.")]
        if len(set(tuple(p[0].tolist()) for p in prefixes)) != 4:
            raise RuntimeError("UNIQUE_PREFIX_COLLISION")
        patterns = {
            "zero_hit": [0, 1, 2, 3],
            "seventyfive_hit": [0, 0, 0, 0],
        }

        def decode(first, past=None, prefix_len=0):
            n = first.shape[1] + prefix_len
            kw = {"input_ids": first, "use_cache": True}
            if past is not None:
                kw["past_key_values"] = copy.deepcopy(past)
                kw["attention_mask"] = torch.ones((1, n), dtype=torch.long)
            out = model(**kw)
            logits, cache = out.logits[:, -1, :], out.past_key_values
            generated = []
            for i in range(32):
                token = logits.argmax(-1, keepdim=True)
                generated.append(token)
                if i < 31:
                    out = model(input_ids=token, past_key_values=cache, use_cache=True,
                                attention_mask=torch.ones((1, n+i+1), dtype=torch.long))
                    cache, logits = out.past_key_values, out.logits[:, -1, :]
            return torch.cat(generated, dim=1)

        def run_arm(pattern, reuse):
            memo = {}
            outputs = []
            hits = 0
            for i, pi in enumerate(pattern):
                prefix = prefixes[pi]
                suffix = suffixes[i]
                if not reuse:
                    outputs.append(decode(torch.cat((prefix, suffix), dim=1)))
                else:
                    key = tuple(prefix[0].tolist())
                    cached = memo.get(key)
                    if cached is None:
                        cached = model(input_ids=prefix, use_cache=True).past_key_values
                        memo[key] = cached
                    else:
                        hits += 1
                    outputs.append(decode(suffix, cached, prefix.shape[1]))
            return outputs, hits

        def assert_equal(a, b, scenario):
            if len(a) != 4 or any(not torch.equal(x, y) for x, y in zip(a, b)):
                raise RuntimeError("EXACT_TOKEN_PARITY_FAILURE_" + scenario)

        proc = psutil.Process()
        def measured(pattern, reuse):
            rss_before = proc.memory_info().rss
            cpu_start = time.process_time()
            wall_start = time.perf_counter()
            output, hits = run_arm(pattern, reuse)
            wall = time.perf_counter() - wall_start
            cpu = time.process_time() - cpu_start
            return {"wall_s": wall, "process_cpu_s": cpu,
                    "rss_before_bytes": rss_before,
                    "rss_after_bytes": proc.memory_info().rss,
                    "hits": hits}, output

        with torch.inference_mode():
            for scenario, pattern in patterns.items():
                if max(prefixes[j].shape[1] + suffixes[i].shape[1]
                       for i, j in enumerate(pattern)) + 32 > model.config.n_positions:
                    raise RuntimeError("CONTEXT_EXCEEDED")
                ground, _ = run_arm(pattern, reuse=False)
                reused, observed_hits = run_arm(pattern, reuse=True)
                assert_equal(ground, reused, scenario)
                expected_hits = len(pattern) - len(set(pattern))
                if observed_hits != expected_hits:
                    raise RuntimeError("CACHE_HIT_COUNT_INVALID")
                run_arm(pattern, reuse=False)
                run_arm(pattern, reuse=True)
                trials = []
                for idx in range(5):
                    if idx % 2:
                        candidate, r = measured(pattern, True)
                        baseline, b = measured(pattern, False)
                    else:
                        baseline, b = measured(pattern, False)
                        candidate, r = measured(pattern, True)
                    assert_equal(b, r, scenario)
                    if candidate["hits"] != expected_hits or baseline["hits"] != 0:
                        raise RuntimeError("HIT_ACCOUNTING_INVALID")
                    trials.append({
                        "trial": idx+1,
                        "order": "reuse_first" if idx % 2 else "baseline_first",
                        "baseline": baseline, "reuse": candidate,
                        "wall_speedup": baseline["wall_s"]/candidate["wall_s"],
                        "cpu_speedup": baseline["process_cpu_s"]/candidate["process_cpu_s"],
                    })
                median_wall = statistics.median(x["wall_speedup"] for x in trials)
                median_cpu = statistics.median(x["cpu_speedup"] for x in trials)
                report.setdefault("scenarios", {})[scenario] = {
                    "hits": expected_hits,
                    "requests": 4,
                    "hit_rate": expected_hits / 4,
                    "median_paired_wall_speedup": median_wall,
                    "median_paired_process_cpu_speedup": median_cpu,
                    "trials": trials,
                    "outputs_sha256": [
                        hashlib.sha256(x.numpy().tobytes()).hexdigest() for x in ground
                    ],
                }
            report["correctness"] = "PASS"
            report["screen"] = ("PASS_HIGH_REUSE_SCREEN" if
                report["scenarios"]["seventyfive_hit"]["median_paired_wall_speedup"] >= 1.15
                else "FAIL_HIGH_REUSE_SCREEN")
            report["single_host_only"] = True
    except Exception as e:
        report["reason"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        Path("g56_result.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
        print(json.dumps({x: report.get(x) for x in
                          ("gate", "correctness", "screen", "reason")}, sort_keys=True))
        for name, row in report.get("scenarios", {}).items():
            print(json.dumps({"scenario": name, "wall_speedup": row["median_paired_wall_speedup"],
                              "cpu_speedup": row["median_paired_process_cpu_speedup"],
                              "hits": row["hits"]}, sort_keys=True))


if __name__ == "__main__":
    main()
