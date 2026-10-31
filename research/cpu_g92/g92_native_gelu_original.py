#!/usr/bin/env python3
"""CPU G92 native fused GELU versus original GPT-2 NewGELU."""
from __future__ import annotations
import copy, hashlib, importlib.util, json, math, os, platform, statistics, time, traceback, urllib.request
from pathlib import Path

PREREG = "bdacb37f4614f4de646092089016a452acf06d9e"
MODEL_REV = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
WEIGHTS_SHA = "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"
DATA_REV = "3101c7d5072418e28b9008a6636bde82a006892c"
DATA_SHA = "3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
DATA_BYTES = 749738
SEED = b"G68-GPT2-HELDOUT-20261030:"
OFFSET, CASES, REPEATS, TOKENS, CPU_BUDGET = 228, 12, 4, 8, 3
ARMS = ("original_newgelu2", "native_gelu_tanh2")
THRESHOLDS = {"prefill_speedup_min": 1.15, "full_speedup_min": 1.10,
              "min_paired": 0.90, "p95_max": 1.10, "rss_max": 1.10, "cpu_max": 1.10}

def contract():
    assert (OFFSET, CASES, REPEATS, TOKENS, CPU_BUDGET) == (228, 12, 4, 8, 3)
    assert ARMS == ("original_newgelu2", "native_gelu_tanh2")
    assert THRESHOLDS == {"prefill_speedup_min": 1.15, "full_speedup_min": 1.10,
                          "min_paired": 0.90, "p95_max": 1.10, "rss_max": 1.10, "cpu_max": 1.10}

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def module(name, rel):
    p = Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def rank_original(records, n):
    pool = []
    for row, item in enumerate(records):
        q, cat = item.get("instruction", ""), item.get("category", "")
        if isinstance(q, str) and q.strip() and isinstance(cat, str) and cat.strip():
            pool.append((hashlib.sha256(SEED + q.encode()).hexdigest(), row, q, cat))
    pool.sort(key=lambda x: (x[0], x[1]))
    out, seen = [], set()
    for digest, row, q, cat in pool:
        if q in seen:
            continue
        seen.add(q)
        out.append({"source_row": row, "instruction": q, "category": cat,
                    "instruction_sha256": hashlib.sha256(q.encode()).hexdigest(), "rank_sha256": digest})
        if len(out) == n:
            break
    if len(out) != n:
        raise RuntimeError("G92_INSUFFICIENT_ORIGINAL_HELDOUT")
    return out

class NativeTanhGELU:
    def __new__(cls, torch):
        class _NativeGELU(torch.nn.Module):
            def forward(self, x):
                return torch.nn.functional.gelu(x, approximate="tanh")
        return _NativeGELU()

def replace_activations(model, torch):
    replacements = []
    for i, block in enumerate(model.transformer.h):
        old = block.mlp.act
        if old.__class__.__name__ != "NewGELUActivation":
            raise RuntimeError("G92_UNEXPECTED_ORIGINAL_ACTIVATION_" + str(i))
        block.mlp.act = NativeTanhGELU(torch)
        replacements.append({"layer": i, "old": old.__class__.__name__,
                              "new": block.mlp.act.__class__.__name__})
    return replacements

def percentile95(values):
    return sorted(values)[max(0, math.ceil(0.95 * len(values)) - 1)]

def decide(trials, dispatch):
    if len(trials) != CASES * REPEATS:
        raise RuntimeError("G92_INCOMPLETE_PAIRED_TRIALS")
    if dispatch["candidate_gelu_events"] <= 0 or dispatch["baseline_gelu_events"] != 0:
        raise RuntimeError("G92_NATIVE_GELU_DISPATCH_NOT_PROVEN")
    if dispatch["candidate_tanh_events"] >= dispatch["baseline_tanh_events"]:
        raise RuntimeError("G92_TANH_CHAIN_NOT_REDUCED")
    if dispatch["candidate_pow_events"] >= dispatch["baseline_pow_events"]:
        raise RuntimeError("G92_POW_CHAIN_NOT_REDUCED")
    summaries = {}
    for arm in ARMS:
        rows = [x[arm] for x in trials]
        summaries[arm] = {
            "median_prefill_ns": statistics.median(x["prefill_ns"] for x in rows),
            "median_full_ns": statistics.median(x["full_ns"] for x in rows),
            "p95_full_ns": percentile95([x["full_ns"] for x in rows]),
            "total_cpu_ns": sum(x["cpu_ns"] for x in rows),
            "max_sampled_rss_bytes": max(x["rss_bytes"] for x in rows)
        }
    base, cand = summaries[ARMS[0]], summaries[ARMS[1]]
    paired = [x[ARMS[0]]["full_ns"] / x[ARMS[1]]["full_ns"] for x in trials]
    metrics = {
        "median_prefill_speedup": base["median_prefill_ns"] / cand["median_prefill_ns"],
        "median_full_response_speedup": base["median_full_ns"] / cand["median_full_ns"],
        "minimum_individual_paired_full_speedup": min(paired),
        "p95_candidate_over_baseline": cand["p95_full_ns"] / base["p95_full_ns"],
        "sampled_rss_candidate_over_baseline": cand["max_sampled_rss_bytes"] / base["max_sampled_rss_bytes"],
        "total_cpu_candidate_over_baseline": cand["total_cpu_ns"] / base["total_cpu_ns"],
        "timed_authentic_responses": len(trials) * 2,
        "timed_authentic_generated_tokens": len(trials) * 2 * TOKENS
    }
    ok = (metrics["median_prefill_speedup"] >= THRESHOLDS["prefill_speedup_min"]
          and metrics["median_full_response_speedup"] >= THRESHOLDS["full_speedup_min"]
          and metrics["minimum_individual_paired_full_speedup"] >= THRESHOLDS["min_paired"]
          and metrics["p95_candidate_over_baseline"] <= THRESHOLDS["p95_max"]
          and metrics["sampled_rss_candidate_over_baseline"] <= THRESHOLDS["rss_max"]
          and metrics["total_cpu_candidate_over_baseline"] <= THRESHOLDS["cpu_max"])
    return summaries, metrics, "NATIVE_GELU_PASS" if ok else "NATIVE_GELU_NO_GO"

def main():
    import torch, transformers, psutil
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from torch.profiler import profile, ProfilerActivity
    contract()
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise RuntimeError("G92_NOT_NATIVE_X86_64_LINUX")
    if torch.version.cuda is not None:
        raise RuntimeError("G92_NON_CPU_PYTORCH")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    proc = psutil.Process()
    old_aff = None
    receipt = {
        "schema": "forge.cpu-llm-g92.authentic-native-gelu.v1", "gate": "CPU_G92",
        "preregistration_commit": PREREG, "source_sha": os.getenv("GITHUB_SHA", "UNSET"),
        "model_revision": MODEL_REV, "model_weights_sha256": WEIGHTS_SHA,
        "dataset_revision": DATA_REV, "dataset_sha256": DATA_SHA,
        "engineering": "UNVERIFIED", "correctness": "UNVERIFIED", "decision": "UNVERIFIED",
        "scientific_acceptance": "NOT_GRANTED", "promotion_allowed": False,
        "runtime": {"torch": torch.__version__, "torch_cuda": torch.version.cuda,
                    "transformers": transformers.__version__, "python": platform.python_version(),
                    "platform": platform.platform(), "machine": platform.machine(),
                    "processor": platform.processor(), "logical_cpus": os.cpu_count()},
        "limitations": ["Pinned original GPT-2 FP32 CPU execution only",
                        "GSM8K source cohort is disjoint by rank but not proven unseen during pretraining",
                        "One Linux x86_64 host, three-core affinity; sampled RSS, no energy metric",
                        "No model weight changes, production acceptance, native intelligence claim or promotion"]
    }
    try:
        raw = Path("cpu_g92_original_gsm8k.jsonl")
        req = urllib.request.Request(
            "https://raw.githubusercontent.com/openai/grade-school-math/" + DATA_REV + "/grade_school_math/data/test.jsonl",
            headers={"User-Agent": "FORGE-CPU-G92-Native-GELU/1"})
        with urllib.request.urlopen(req, timeout=45) as inp, raw.open("xb") as out:
            count = 0
            while True:
                b = inp.read(1 << 20)
                if not b:
                    break
                count += len(b)
                if count > 800000:
                    raise RuntimeError("G92_DATA_SIZE_CAP")
                out.write(b)
        if raw.stat().st_size != DATA_BYTES or sha_file(raw) != DATA_SHA:
            raise RuntimeError("G92_DATA_IDENTITY_DRIFT")
        with raw.open(encoding="utf-8") as f:
            records = [{"instruction": x["question"], "category": "math_word_problem"}
                       for x in (json.loads(line) for line in f if line.strip())]
        ranked = rank_original(records, OFFSET + CASES)
        g68 = module("g92_g68", "llm_g68/g68_gsm8k_http.py")
        g70 = module("g92_g70", "llm_g70/g70_gsm8k_locality.py")
        if ranked[:12] != g68.select_heldout(records) or ranked[12:24] != g70.select_heldout(records):
            raise RuntimeError("G92_RANK_CONTRACT_DRIFT")
        selected = ranked[OFFSET:OFFSET + CASES]
        receipt["selected"] = [{k: v for k, v in x.items() if k != "instruction"} for x in selected]
        receipt["selected_ranks"] = [OFFSET, OFFSET + CASES - 1]
        g55 = module("g92_g55", "llm_g55/g55_gpt2_controls.py")
        if (g55.REV, g55.WEIGHT_SHA) != (MODEL_REV, WEIGHTS_SHA):
            raise RuntimeError("G92_G55_MODEL_IDENTITY_DRIFT")
        root, manifest = g55.stage()
        receipt["model_manifest_sha256"] = sha_file(root / "manifest.json")
        receipt["model_files"] = manifest
        tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False)
        baseline = AutoModelForCausalLM.from_pretrained(str(root), local_files_only=True,
                     use_safetensors=True, trust_remote_code=False).eval()
        candidate = AutoModelForCausalLM.from_pretrained(str(root), local_files_only=True,
                      use_safetensors=True, trust_remote_code=False).eval()
        bp, cp = list(baseline.parameters()), list(candidate.parameters())
        if len(bp) != len(cp) or any(not torch.equal(a, b) for a, b in zip(bp, cp)):
            raise RuntimeError("G92_ORIGINAL_WEIGHT_PARITY_FAILURE")
        if not hasattr(proc, "cpu_affinity"):
            raise RuntimeError("G92_CPU_AFFINITY_UNAVAILABLE")
        old_aff = proc.cpu_affinity()
        if len(old_aff) < CPU_BUDGET:
            raise RuntimeError("G92_THREE_CPU_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old_aff[:CPU_BUDGET])
        receipt["fixed_affinity"] = proc.cpu_affinity()
        receipt["fixed_torch_interop"] = torch.get_num_interop_threads()
        replacements = replace_activations(candidate, torch)
        if len(replacements) != 12:
            raise RuntimeError("G92_EXPECTED_TWELVE_ACTIVATION_REPLACEMENTS")
        if any(not torch.equal(a, b) for a, b in zip(baseline.parameters(), candidate.parameters())):
            raise RuntimeError("G92_WEIGHT_MUTATION_DETECTED")
        if baseline.config.to_dict() != candidate.config.to_dict():
            raise RuntimeError("G92_CONFIG_MUTATION_DETECTED")
        receipt["activation_replacements"] = replacements
        receipt["parameter_count"] = sum(p.numel() for p in baseline.parameters())
        def token_ids(s):
            return tokenizer(s, return_tensors="pt", add_special_tokens=False)["input_ids"]
        inputs = []
        for item in selected:
            full = torch.cat((token_ids(g55.PREFIX), token_ids(item["instruction"])[:, :64]), dim=1)
            if full.shape[1] + TOKENS > baseline.config.n_positions:
                raise RuntimeError("G92_CONTEXT_OVERFLOW")
            inputs.append((item["source_row"], full))
        # Capture true original MLP pre-activation tensors for activation error diagnostics.
        captured = []
        handle = baseline.transformer.h[0].mlp.c_fc.register_forward_hook(
            lambda module, args, output: captured.append(output.detach().clone()))
        with torch.inference_mode():
            baseline(input_ids=inputs[0][1], use_cache=True)
        handle.remove()
        x = captured[0]
        native = torch.nn.functional.gelu(x, approximate="tanh")
        original = 0.5 * x * (1.0 + torch.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * torch.pow(x, 3.0))))
        diff = (native - original).abs()
        receipt["activation_error"] = {"max_abs": float(diff.max()), "median_abs": float(diff.median()),
            "max_relative": float((diff / original.abs().clamp(min=1e-12)).max()),
            "elements": int(diff.numel())}
        def decode(model, full):
            t0 = time.perf_counter_ns()
            c0 = time.process_time_ns()
            torch.set_num_threads(2)
            with torch.inference_mode():
                p0 = time.perf_counter_ns()
                out = model(input_ids=full, use_cache=True)
                p1 = time.perf_counter_ns()
                past, logits = out.past_key_values, out.logits[:, -1, :]
                generated = []
                selection_ns = 0
                cached_ns = 0
                for step in range(TOKENS):
                    ts = time.perf_counter_ns()
                    nxt = logits.argmax(-1, keepdim=True)
                    selection_ns += time.perf_counter_ns() - ts
                    generated.append(nxt)
                    if step + 1 < TOKENS:
                        mask = torch.ones((1, int(full.shape[1]) + step + 1), dtype=torch.long)
                        ts = time.perf_counter_ns()
                        out = model(input_ids=nxt, past_key_values=past, attention_mask=mask, use_cache=True)
                        cached_ns += time.perf_counter_ns() - ts
                        past, logits = out.past_key_values, out.logits[:, -1, :]
            t1 = time.perf_counter_ns()
            cpu = time.process_time_ns() - c0
            result = torch.cat(generated, dim=1).flatten().tolist()
            return result, {"prefill_ns": p1-p0, "cached_forward_ns": cached_ns,
                "token_selection_ns": selection_ns, "full_ns": t1-t0,
                "cpu_ns": cpu, "rss_bytes": proc.memory_info().rss,
                "output_sha256": hashlib.sha256(json.dumps(result, separators=(",", ":")).encode()).hexdigest()}
        # Separate, unmeasured native-operator profiling verifies candidate dispatch.
        dispatch = {}
        for name, model in (("baseline", baseline), ("candidate", candidate)):
            with profile(activities=[ProfilerActivity.CPU]) as prof:
                with torch.inference_mode():
                    model(input_ids=inputs[0][1], use_cache=True)
            counts = {key: sum(e.count for e in prof.key_averages() if e.key == key)
                      for key in ("aten::gelu", "aten::tanh", "aten::pow")}
            dispatch[name] = counts
        receipt["dispatch_evidence"] = {
            "baseline_gelu_events": dispatch["baseline"]["aten::gelu"],
            "baseline_tanh_events": dispatch["baseline"]["aten::tanh"],
            "baseline_pow_events": dispatch["baseline"]["aten::pow"],
            "candidate_gelu_events": dispatch["candidate"]["aten::gelu"],
            "candidate_tanh_events": dispatch["candidate"]["aten::tanh"],
            "candidate_pow_events": dispatch["candidate"]["aten::pow"]}
        if receipt["dispatch_evidence"]["candidate_gelu_events"] <= 0:
            raise RuntimeError("G92_NATIVE_GELU_DISPATCH_MISSING")
        if receipt["dispatch_evidence"]["baseline_gelu_events"] != 0:
            raise RuntimeError("G92_BASELINE_UNEXPECTED_NATIVE_GELU")
        trials = []
        references = {}
        for i, (row, full) in enumerate(inputs):
            for model, arm in ((baseline, ARMS[0]), (candidate, ARMS[1])):
                for _ in range(2):
                    out, _ = decode(model, full)
                    if len(out) != TOKENS:
                        raise RuntimeError("G92_WARMUP_TOKEN_COUNT")
                    if arm == ARMS[0]:
                        references[i] = out
                    elif out != references[i]:
                        raise RuntimeError("G92_WARMUP_TOKEN_MISMATCH")
        for i, (row, full) in enumerate(inputs):
            for rep in range(REPEATS):
                order = ARMS if (i + rep) % 2 == 0 else tuple(reversed(ARMS))
                measurement = {}
                for arm in order:
                    model = baseline if arm == ARMS[0] else candidate
                    out, timing = decode(model, full)
                    if out != references[i]:
                        raise RuntimeError("G92_EXACT_TOKEN_MISMATCH_" + arm + "_" + str(i))
                    measurement[arm] = timing
                trials.append(measurement)
        summaries, metrics, decision = decide(trials, receipt["dispatch_evidence"])
        receipt["paired_trials"] = trials
        receipt["arm_summaries"] = summaries
        receipt["metrics"] = metrics
        receipt["decision"] = decision
        receipt["engineering"] = "PASS"
        receipt["correctness"] = "PASS"
    except BaseException as exc:
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
        receipt["traceback_tail"] = traceback.format_exc()[-3000:]
        raise
    finally:
        if old_aff is not None:
            receipt["cpu_affinity_at_end"] = proc.cpu_affinity()
            proc.cpu_affinity(old_aff)
        Path("cpu_g92_original_result.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps({k: receipt.get(k) for k in
            ("gate", "engineering", "correctness", "decision", "dispatch_evidence", "metrics", "error")},
            sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
