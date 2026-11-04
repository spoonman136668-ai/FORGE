#!/usr/bin/env python3
"""G103 P1: frozen original GPT-2 structural sharing diagnostic, development only.

Three independent arms: identical prefix positive control, distinct one-token
related prefixes, and unrelated real original G95 prefix templates. Original
held-out and development questions are never loaded. This is storage-only,
not model deployment or inference acceleration.
"""
import hashlib
import json
import os
import platform
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
G96 = HERE.parent / "cpu_g96"
if str(G96) not in sys.path:
    sys.path.insert(0, str(G96))
from g96_original_adapter import _g95
from research.cpu_g97.g102_original_storage import (
    serialize_gpt2_kv, variant_tokens)
from research.cpu_g97.g103_block_sharing import pack, unpack, costs

SCHEMA = "forge.cpu-g103.original-block-reuse-p1.v1"
GROUPS = ("identical", "related", "unrelated")
MODES = ("fixed", "adaptive")
REPETITIONS = 2
RELATED_VARIANTS = 2
# Decision is frozen: 'related' alone must beat both standard zlib and
# conventional fixed-block dedup by >=10%; duplicate-only wins are excluded.
WIN_NUMERATOR, WIN_DENOMINATOR = 9, 10
MAX_RESIDENT_BYTES = 86114304


def evaluate(states):
    """Strict model-free resource and reconstruction check, with cold pool per arm."""
    if not isinstance(states, list) or len(states) < 2 or any(
            not isinstance(s, bytes) or not s or len(s) > MAX_RESIDENT_BYTES
            for s in states):
        raise RuntimeError("G103_STATE_CONTRACT")
    arms = {}
    for mode in MODES:
        t0, c0 = time.perf_counter_ns(), time.process_time_ns()
        bundle = pack(states, mode=mode)
        build_wall = time.perf_counter_ns() - t0
        build_cpu = time.process_time_ns() - c0
        t0, c0 = time.perf_counter_ns(), time.process_time_ns()
        accounting = costs(bundle, states)
        verify_wall = time.perf_counter_ns() - t0
        verify_cpu = time.process_time_ns() - c0
        decode_wall, decode_cpu = [], []
        for i, original in enumerate(states):
            t0, c0 = time.perf_counter_ns(), time.process_time_ns()
            restored = unpack(bundle, i)
            decode_wall.append(time.perf_counter_ns() - t0)
            decode_cpu.append(time.process_time_ns() - c0)
            if restored != original:
                raise RuntimeError("G103_BIT_EXACTNESS")
        accounting.update({
            "build_wall_ns": build_wall, "build_cpu_ns": build_cpu,
            "verify_wall_ns": verify_wall, "verify_cpu_ns": verify_cpu,
            "decode_wall_ns": decode_wall, "decode_cpu_ns": decode_cpu,
            "all_exact": True,
            "mode": mode,
        })
        arms[mode] = accounting
    for field in ("raw_bytes", "independent_zlib_bytes"):
        if arms["fixed"][field] != arms["adaptive"][field]:
            raise RuntimeError("G103_CONTROL_DRIFT")
    return arms


def decision(groups):
    if set(groups) != set(GROUPS) or any(
            set(groups[name].get("arms", {})) != set(MODES)
            for name in GROUPS):
        raise RuntimeError("G103_INCOMPLETE_GROUPS")
    same = groups["identical"]["identical_input"]
    related = groups["related"]["identical_input"]
    unrelated = groups["unrelated"]["identical_input"]
    if same is not True or related is not False or unrelated is not False:
        raise RuntimeError("G103_CONTROL_IDENTITIES_DRIFT")
    for group in GROUPS:
        for mode in MODES:
            if groups[group]["arms"][mode].get("all_exact") is not True:
                raise RuntimeError("G103_EXACTNESS_REQUIRED")
    target = groups["related"]["arms"]["adaptive"]
    fixed = groups["related"]["arms"]["fixed"]
    # Meaningful discovery requires a win beyond fixed hash block sharing
    # AND beyond independent compression, on distinct related KV states.
    best = min(fixed["shared_total_modeled_bytes"],
               target["independent_zlib_bytes"],
               target["raw_bytes"])
    if target["shared_total_modeled_bytes"] * WIN_DENOMINATOR <= best * WIN_NUMERATOR:
        return "STRUCTURAL_FEASIBLE_DIAGNOSTIC"
    return "STRUCTURAL_NO_GO_DIAGNOSTIC"


def main():
    if os.environ.get("G103_DEVELOPMENT_ONLY") != "1":
        raise RuntimeError("G103_DEVELOPMENT_GUARD")
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise RuntimeError("G103_SOURCE_SHA_REQUIRED")
    receipt = {
        "schema": SCHEMA, "source_sha": sha, "phase": "DEVELOPMENT_ONLY",
        "heldout_executed": False, "promotion_allowed": False,
        "scientific_acceptance": "NOT_GRANTED",
        "performance_verdict": "NOT_EVALUATED",
        "decision": "UNVERIFIED", "groups": {},
    }
    try:
        import torch
        import transformers
        import psutil
        from transformers import AutoTokenizer, AutoModelForCausalLM
        g = _g95()
        if (platform.system() != "Linux"
                or platform.machine().lower() not in ("x86_64", "amd64")
                or torch.__version__ != "2.5.1+cpu"
                or transformers.__version__ != "4.48.3"
                or torch.version.cuda is not None):
            raise RuntimeError("G103_PINNED_RUNTIME_DRIFT")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        proc = psutil.Process()
        previous = proc.cpu_affinity()
        if len(previous) < 3:
            raise RuntimeError("G103_CPU_AFFINITY")
        proc.cpu_affinity(previous[:3])
        try:
            g55 = g.module("g103_g55", "llm_g55/g55_gpt2_controls.py")
            if (g55.REV, g55.WEIGHT_SHA) != (g.MODEL_REV, g.WEIGHTS_SHA):
                raise RuntimeError("G103_WEIGHT_IDENTITY")
            root, _manifest = g55.stage()
            model = AutoModelForCausalLM.from_pretrained(
                str(root), local_files_only=True, use_safetensors=True,
                trust_remote_code=False).eval()
            tok = AutoTokenizer.from_pretrained(
                str(root), local_files_only=True, trust_remote_code=False)
            def encode(text):
                return tok(text, add_special_tokens=False,
                           return_tensors="pt")["input_ids"][0].tolist()
            base = encode(g.PREFIX_TEXTS[0])
            related = variant_tokens(base, model.config.vocab_size)[:RELATED_VARIANTS]
            others = [encode(g.PREFIX_TEXTS[1]),encode(g.PREFIX_TEXTS[2])]
            # All prefix IDs are genuine original-model inputs; controls never
            # inject precomputed synthetic KV, protected questions, or oracle labels.
            sequences = {"identical": [base, list(base)],
                         "related": [base] + related,
                         "unrelated": [base] + others}
            if len({tuple(x) for x in sequences["related"]}) != 3:
                raise RuntimeError("G103_RELATED_IDENTITY_DRIFT")
            if len({tuple(x) for x in sequences["unrelated"]}) != 3:
                raise RuntimeError("G103_UNRELATED_IDENTITY_DRIFT")
            prefix_blobs, layouts = {}, {}
            with torch.inference_mode():
                for group in GROUPS:
                    states, shapes = [], []
                    for seq in sequences[group]:
                        if len(seq) + g.TOKENS > model.config.n_positions:
                            raise RuntimeError("G103_CONTEXT_LIMIT")
                        ids = torch.tensor([seq], dtype=torch.long)
                        past = model(input_ids=ids, use_cache=True).past_key_values
                        raw, shape = serialize_gpt2_kv(past, torch)
                        states.append(raw)
                        shapes.append(shape)
                        del past
                    prefix_blobs[group], layouts[group] = states, shapes
            # KV comparisons are only meaningful when the layout is equal.
            # The identical and related groups require same-shape states.
            # The unrelated original G95 templates naturally have different
            # token lengths; comparing their byte-level dedup is still valid.
            for group in ("identical", "related"):
                if any(shape != layouts[group][0] for shape in layouts[group]):
                    raise RuntimeError("G103_GROUP_LAYOUT_DRIFT")
            for group in GROUPS:
                states = prefix_blobs[group]
                identities = [hashlib.sha256(s).hexdigest() for s in states]
                same = len(set(identities)) == 1
                if same != (group == "identical"):
                    raise RuntimeError("G103_KV_CONTROL_DRIFT")
                arms = evaluate(states)
                receipt["groups"][group] = {
                    "arms": arms, "prefix_tokens": [len(x) for x in sequences[group]],
                    "state_hashes": identities,
                    "identical_input": group == "identical",
                    "state_bytes": [len(s) for s in states],
                }
                print("G103_GROUP",group,
                      "fixed",arms["fixed"]["shared_total_modeled_bytes"],
                      "adaptive",arms["adaptive"]["shared_total_modeled_bytes"],
                      "zlib",arms["fixed"]["independent_zlib_bytes"],flush=True)
            receipt["decision"] = decision(receipt["groups"])
            receipt.update({
                "model_revision": g.MODEL_REV, "weights_sha256": g.WEIGHTS_SHA,
                "manifest_sha256": g.sha_file(root / "manifest.json"),
                "original_forward_count": sum(len(s) for s in sequences.values()),
                "rss_sampled_bytes": proc.memory_info().rss,
                "rss_caveat": "sampled process RSS, not transient peak",
                "engineering": "PASS",
            })
            print("G103_STORAGE_DECISION="+receipt["decision"],flush=True)
        finally:
            proc.cpu_affinity(previous)
    except BaseException as exc:
        receipt["engineering"] = "FAIL"
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
        receipt["traceback_tail"] = traceback.format_exc()[-3500:]
        raise
    finally:
        Path("cpu_g103_original_block_result.json").write_text(
            json.dumps(receipt,sort_keys=True,indent=2)+"\n")


if __name__ == "__main__":
    main()
