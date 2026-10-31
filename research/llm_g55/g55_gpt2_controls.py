#!/usr/bin/env python3
"""G55 research-only CPU study: prefix reuse versus two production-style cached baselines.

Predeclared: exact pinned GPT-2 identity, output parity, five AB/BA-like rotated
whole-workload repetitions; threshold 1.15x vs FASTEST matched baseline per trial.
No qualification for GPU, batching, compiled serving, energy, scientific first use.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import time

REPO = "openai-community/gpt2"
REV = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHT_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
FILES = ("config.json", "generation_config.json", "merges.txt", "model.safetensors",
         "tokenizer.json", "tokenizer_config.json", "vocab.json")
PREFIX = ("You are an assistant evaluating computational reuse. Answer precisely using the "
          "shared requirements, preserving correctness and avoiding unsupported claims. ") * 12
SUFFIXES = (" Question one: summarize the first requirement.",
            " Question two: identify the main constraint.",
            " Question three: explain the validation rule.")
TOKENS = 32
TRIALS = 5


def sha_file(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            d.update(chunk)
    return d.hexdigest()


def stage():
    """No unverified files: build fresh directory and compare exact source hashes."""
    from huggingface_hub import hf_hub_download
    root = Path("g55_frozen_model")
    root.mkdir(exist_ok=False)
    records = []
    for name in FILES:
        upstream = Path(hf_hub_download(repo_id=REPO, revision=REV, filename=name, token=False))
        dest = root / name
        with upstream.open("rb") as inp, dest.open("xb") as out:
            for chunk in iter(lambda: inp.read(1048576), b""):
                out.write(chunk)
        records.append({"path": name, "size": dest.stat().st_size, "sha256": sha_file(dest)})
    weights = next(rec for rec in records if rec["path"] == "model.safetensors")
    if weights["sha256"] != WEIGHT_SHA:
        raise RuntimeError("FROZEN_WEIGHT_MISMATCH")
    (root / "manifest.json").write_text(json.dumps({"revision": REV, "files": records},
                                                    sort_keys=True) + "\n")
    return root, records


def run():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(1)
    report = {"gate": "G55", "scope": "independent three-arm GPT-2 fixed-token CPU screen",
              "source_commit": os.getenv("GITHUB_SHA", "UNSET"), "revision": REV,
              "weight_sha256": WEIGHT_SHA, "torch": torch.__version__,
              "transformers": transformers.__version__, "platform": platform.platform(),
              "correctness": "UNVERIFIED", "acceleration": "UNVERIFIED",
              "scientific_acceptance": "NOT_GRANTED", "promotion_allowed": False}
    try:
        root, records = stage()
        report["artifacts"] = records
        report["model_manifest_sha256"] = sha_file(root / "manifest.json")
        tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True,
                                                   trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(str(root), local_files_only=True,
                         trust_remote_code=False, use_safetensors=True).eval()
        if model.config.model_type != "gpt2" or model.config.is_encoder_decoder:
            raise RuntimeError("MODEL_ARCHITECTURE_MISMATCH")
        def ids(s):
            return tokenizer(s, return_tensors="pt", add_special_tokens=False)["input_ids"]
        prefix = ids(PREFIX)
        suffixes = [ids(s) for s in SUFFIXES]
        full = [torch.cat((prefix, s), dim=1) for s in suffixes]
        if max(x.shape[1] for x in full) + TOKENS > model.config.n_positions:
            raise RuntimeError("CONTEXT_WINDOW_EXCEEDED")

        def manual_decode(first, past=None, prefix_len=0):
            consumed = prefix_len + first.shape[1]
            opts = {"input_ids": first, "use_cache": True}
            if past is not None:
                opts["past_key_values"] = copy.deepcopy(past)
                opts["attention_mask"] = torch.ones((1, consumed), dtype=torch.long)
            out = model(**opts)
            state, logits = out.past_key_values, out.logits[:, -1, :]
            output = []
            for i in range(TOKENS):
                token = logits.argmax(dim=-1, keepdim=True)
                output.append(token)
                if i < TOKENS - 1:
                    out = model(input_ids=token, past_key_values=state,
                                attention_mask=torch.ones((1, consumed + i + 1),
                                                          dtype=torch.long), use_cache=True)
                    state, logits = out.past_key_values, out.logits[:, -1, :]
            return torch.cat(output, dim=1)

        def arm_manual():
            return [manual_decode(x) for x in full]

        def arm_hf():
            return [model.generate(input_ids=x, do_sample=False, num_beams=1,
                                   max_new_tokens=TOKENS, min_new_tokens=TOKENS,
                                   use_cache=True, pad_token_id=tokenizer.eos_token_id)
                    [:, x.shape[1]:] for x in full]

        def arm_reuse():
            cached = model(input_ids=prefix, use_cache=True).past_key_values
            return [manual_decode(x, past=cached, prefix_len=prefix.shape[1])
                    for x in suffixes]

        def check(a, b, label):
            if len(a) != len(b) or any(not torch.equal(x, y) for x, y in zip(a, b)):
                raise RuntimeError("TOKEN_MISMATCH_" + label)

        def timed(fn):
            a = time.perf_counter()
            output = fn()
            return time.perf_counter() - a, output

        with torch.inference_mode():
            prefix_cache = model(input_ids=prefix, use_cache=True).past_key_values
            max_diff = 0.0
            for f, s in zip(full, suffixes):
                ordinary = model(input_ids=f, use_cache=True).logits[:, -1, :]
                reused = model(input_ids=s, past_key_values=copy.deepcopy(prefix_cache),
                          attention_mask=torch.ones((1, f.shape[1]), dtype=torch.long),
                          use_cache=True).logits[:, -1, :]
                max_diff = max(max_diff, (ordinary - reused).abs().max().item())
                if not torch.allclose(ordinary, reused, atol=1e-4, rtol=1e-4):
                    raise RuntimeError("NEXT_TOKEN_LOGIT_MISMATCH")
            funcs = {"manual": arm_manual, "hf_generate": arm_hf, "prefix_reuse": arm_reuse}
            reference = arm_manual()
            for label, fn in funcs.items():
                check(reference, fn(), label)
            for fn in funcs.values():
                fn()  # untimed warmup
            trials = []
            names = ("manual", "hf_generate", "prefix_reuse")
            for i in range(TRIALS):
                # Rotated and alternating direction avoids fixed-order advantage.
                order = list(names[i % 3:] + names[:i % 3])
                if i % 2:
                    order.reverse()
                times = {}
                for name in order:
                    seconds, ids_out = timed(funcs[name])
                    check(reference, ids_out, name + "_TRIAL_" + str(i))
                    times[name + "_s"] = seconds
                fastest = min(times["manual_s"], times["hf_generate_s"])
                times.update({"trial": i + 1, "order": order,
                              "speedup_vs_manual": times["manual_s"] / times["prefix_reuse_s"],
                              "speedup_vs_hf_generate": times["hf_generate_s"] / times["prefix_reuse_s"],
                              "speedup_vs_fastest_baseline": fastest / times["prefix_reuse_s"]})
                trials.append(times)
            median = statistics.median(t["speedup_vs_fastest_baseline"] for t in trials)
            report.update({
                "correctness": "PASS",
                "acceleration": "PASS_SCREEN" if median >= 1.15 else "FAIL_SCREEN",
                "median_vs_fastest_baseline": median,
                "median_vs_manual": statistics.median(t["speedup_vs_manual"] for t in trials),
                "median_vs_hf_generate": statistics.median(t["speedup_vs_hf_generate"] for t in trials),
                "trials": trials, "max_abs_next_logit_error": max_diff,
                "prefix_tokens": prefix.shape[1], "suffix_tokens": [x.shape[1] for x in suffixes],
                "tokens_per_request": TOKENS, "requests_per_arm": 3,
                "predeclared_screen_threshold": 1.15,
                "baselines": [
                    "manual efficient incremental past-key-value cached decoding",
                    "Transformers model.generate greedy with use_cache=True, fixed 32 tokens"],
                "nonclaims": [
                    "Single Ubuntu CPU host, 5 trials, one model and single prompt cohort",
                    "Hugging Face generate is a library baseline, not optimized production serving",
                    "No CUDA, batching, concurrency, throughput scaling, RSS or energy measurement",
                    "Not exact G51 execution and not native Wingless/Yggdrasil model proof"
                ]})
    except Exception as exc:
        report.update({"classification": "BLOCKED_OR_FAILED", "reason": type(exc).__name__ + ": " + str(exc)})
        raise
    finally:
        Path("g55_result.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({x: report.get(x) for x in ("gate", "correctness", "acceleration",
                          "median_vs_fastest_baseline", "reason")}, sort_keys=True))


if __name__ == "__main__":
    run()
