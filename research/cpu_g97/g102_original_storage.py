#!/usr/bin/env python3
"""G102 P1: pinned actual GPT-2 KV storage feasibility, development-only.

Tests exact target reconstruction and counts resident base storage and
uncompressed versus independently compressed controls. Not an inference
speedup test, no protected cohort, and no scientific promotion.
"""
import hashlib
import json
import os
import platform
import re
import sys
import time
import traceback
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
G96 = HERE.parent / "cpu_g96"
if str(G96) not in sys.path:
    sys.path.insert(0, str(G96))
from g96_original_adapter import _g95
from research.cpu_g97.g102_xor_state import (
    MAX_BYTES, accounting, decode, encode, digest)

SCHEMA = "forge.cpu-g102.original-kv-storage-p1.v1"
POSITIONS = (0, 1, 5, 11)
TOKEN_DELTAS = (1, 7, 101, 991)
NUM_VARIANTS = 4


def variant_tokens(base, vocab, offsets=POSITIONS, deltas=TOKEN_DELTAS):
    if len(offsets) != NUM_VARIANTS or len(deltas) != NUM_VARIANTS:
        raise RuntimeError("G102_VARIANT_PROTOCOL_DRIFT")
    if type(vocab) is not int or vocab < 1000:
        raise RuntimeError("G102_INVALID_VOCAB")
    if not base or len(base) <= max(offsets):
        raise RuntimeError("G102_SHORT_PREFIX")
    result = []
    for position, delta in zip(offsets, deltas):
        if position < 0 or position >= len(base) or delta <= 0:
            raise RuntimeError("G102_INVALID_VARIANT")
        mutated = list(base)
        mutated[position] = (mutated[position] + delta) % vocab
        if mutated == list(base):
            raise RuntimeError("G102_UNCHANGED_VARIANT")
        result.append(mutated)
    if len({tuple(x) for x in result}) != NUM_VARIANTS:
        raise RuntimeError("G102_COLLIDING_VARIANTS")
    return result


def serialize_gpt2_kv(past, torch):
    """Record all exact bits in fixed contiguous 12-layer K,V FP32 order."""
    if not isinstance(past, (tuple, list)) or len(past) != 12:
        raise RuntimeError("G102_LAYER_COUNT_DRIFT")
    chunks, shapes = [], []
    for layer in past:
        if not isinstance(layer, (tuple, list)) or len(layer) != 2:
            raise RuntimeError("G102_PAIR_LAYOUT_DRIFT")
        for tensor in layer:
            if tensor.dtype != torch.float32 or tensor.ndim != 4:
                raise RuntimeError("G102_KV_TYPE_OR_LAYOUT")
            if not bool(torch.isfinite(tensor).all()):
                raise RuntimeError("G102_NONFINITE_KV")
            t = tensor.detach().cpu().contiguous()
            shapes.append(list(t.shape))
            chunks.append(t.numpy().tobytes(order="C"))
    data = b"".join(chunks)
    if len(data) != sum(__import__("math").prod(shape) * 4 for shape in shapes):
        raise RuntimeError("G102_SERIALIZATION_BYTES")
    if len(data) > MAX_BYTES or not data:
        raise RuntimeError("G102_KV_EXCEEDS_BUDGET")
    return data, shapes


def assess(base, targets):
    if len(targets) != NUM_VARIANTS:
        raise RuntimeError("G102_VARIANT_COUNT")
    records, packets = [], []
    for target in targets:
        t0, c0 = time.perf_counter_ns(), time.process_time_ns()
        packet = encode(base, target)
        encode_wall, encode_cpu = time.perf_counter_ns()-t0, time.process_time_ns()-c0
        t0, c0 = time.perf_counter_ns(), time.process_time_ns()
        reconstructed = decode(base, packet)
        decode_wall, decode_cpu = time.perf_counter_ns()-t0, time.process_time_ns()-c0
        if reconstructed != target or digest(reconstructed) != digest(target):
            raise RuntimeError("G102_EXACT_KV_RECONSTRUCTION_FAIL")
        t0 = time.perf_counter_ns()
        standalone = zlib.compress(target, 6)
        standalone_encode_ns = time.perf_counter_ns()-t0
        t0 = time.perf_counter_ns()
        restored = zlib.decompress(standalone)
        standalone_decode_ns = time.perf_counter_ns()-t0
        if restored != target:
            raise RuntimeError("G102_STANDALONE_CONTROL_CORRUPT")
        t0 = time.perf_counter_ns()
        plain = bytes(bytearray(target))
        raw_copy_ns = time.perf_counter_ns()-t0
        if plain != target:
            raise RuntimeError("G102_PLAIN_CONTROL_CORRUPT")
        records.append({
            "target_sha256": digest(target),
            "raw_bytes": len(target), "independent_zlib_bytes": len(standalone),
            "xor_residual_bytes": len(packet["payload"]),
            "encode_wall_ns": encode_wall, "encode_cpu_ns": encode_cpu,
            "decode_wall_ns": decode_wall, "decode_cpu_ns": decode_cpu,
            "standalone_encode_ns": standalone_encode_ns,
            "standalone_decode_ns": standalone_decode_ns,
            "raw_copy_ns": raw_copy_ns, "exact": True
        })
        packets.append(packet)
    all_in = accounting(base, targets, packets)
    if all_in["raw_bytes"] != sum(x["raw_bytes"] for x in records):
        raise RuntimeError("G102_STORAGE_ACCOUNTING_DRIFT")
    if all_in["standalone_zlib_bytes"] != sum(x["independent_zlib_bytes"] for x in records):
        raise RuntimeError("G102_CONTROL_ACCOUNTING_DRIFT")
    if all_in["residual_with_base_bytes"] != len(base)+sum(x["xor_residual_bytes"] for x in records):
        raise RuntimeError("G102_REFERENCE_ACCOUNTING_DRIFT")
    # Fixed exploratory rule: require at least 10% less total storage than
    # both controls, with the whole base charged and exact reconstruction.
    qualifies = all_in["residual_with_base_bytes"] * 10 <= 9 * min(
        all_in["raw_bytes"], all_in["standalone_zlib_bytes"])
    return records, all_in, ("STORAGE_FEASIBLE_DIAGNOSTIC" if qualifies
                            else "STORAGE_NO_GO_DIAGNOSTIC")


def main():
    if os.getenv("G102_DEVELOPMENT_ONLY") != "1":
        raise RuntimeError("G102_DEVELOPMENT_GUARD")
    sha = os.getenv("GITHUB_SHA", "")
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise RuntimeError("G102_SOURCE_IDENTITY")
    receipt = {"schema": SCHEMA, "source_sha": sha,
               "phase": "DEVELOPMENT_ONLY", "heldout_executed": False,
               "promotion_allowed": False, "scientific_acceptance": "NOT_GRANTED",
               "performance_verdict": "NOT_EVALUATED", "decision": "UNVERIFIED"}
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
            raise RuntimeError("G102_RUNTIME_IDENTITY_DRIFT")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        proc = psutil.Process()
        old = proc.cpu_affinity()
        if len(old) < 3:
            raise RuntimeError("G102_AFFINITY_UNAVAILABLE")
        proc.cpu_affinity(old[:3])
        try:
            g55 = g.module("g102_g55", "llm_g55/g55_gpt2_controls.py")
            if (g55.REV, g55.WEIGHT_SHA) != (g.MODEL_REV, g.WEIGHTS_SHA):
                raise RuntimeError("G102_MODEL_IDENTITY_DRIFT")
            root, manifest = g55.stage()
            model = AutoModelForCausalLM.from_pretrained(
                str(root), local_files_only=True, use_safetensors=True,
                trust_remote_code=False).eval()
            tok = AutoTokenizer.from_pretrained(
                str(root), local_files_only=True, trust_remote_code=False)
            base_ids = tok(g.PREFIX_TEXTS[0], return_tensors="pt",
                           add_special_tokens=False)["input_ids"][0].tolist()
            variants = variant_tokens(base_ids, model.config.vocab_size)
            if len(base_ids)+g.TOKENS > model.config.n_positions:
                raise RuntimeError("G102_CONTEXT_OVERFLOW")
            sequences = [base_ids]+variants
            blobs, shapes, prefills = [], [], []
            with torch.inference_mode():
                for seq in sequences:
                    inp = torch.tensor([seq], dtype=torch.long)
                    t0 = time.perf_counter_ns()
                    output = model(input_ids=inp, use_cache=True).past_key_values
                    prefill_ns = time.perf_counter_ns()-t0
                    payload, layout = serialize_gpt2_kv(output, torch)
                    blobs.append(payload)
                    shapes.append(layout)
                    prefills.append(prefill_ns)
                    del output
            if any(layout != shapes[0] for layout in shapes):
                raise RuntimeError("G102_CROSS_STATE_LAYOUT_DRIFT")
            records, account, decision = assess(blobs[0], blobs[1:])
            receipt.update({
                "model_revision": g.MODEL_REV, "weights_sha256": g.WEIGHTS_SHA,
                "model_manifest_sha256": g.sha_file(root/"manifest.json"),
                "prefix_identity_sha256": hashlib.sha256(
                    json.dumps(base_ids,separators=(",",":")).encode()).hexdigest(),
                "variant_offsets": list(POSITIONS),
                "variant_token_deltas": list(TOKEN_DELTAS),
                "prefix_tokens": len(base_ids),
                "base_sha256": digest(blobs[0]), "base_bytes": len(blobs[0]),
                "layout_sha256": hashlib.sha256(json.dumps(
                    shapes[0],separators=(",",":")).encode()).hexdigest(),
                "original_forward_count": len(sequences),
                "model_prefill_wall_ns": prefills,
                "variants": records, "accounting": account,
                "rss_sampled_bytes": proc.memory_info().rss,
                "rss_caveat": "sampled process RSS, not transient peak",
                "decision": decision, "engineering": "PASS"
            })
            print("G102_REAL_KV_STORAGE_DECISION="+decision,flush=True)
        finally:
            proc.cpu_affinity(old)
    except BaseException as exc:
        receipt["engineering"]="FAIL"
        receipt["error"]=type(exc).__name__+": "+str(exc)
        receipt["traceback_tail"]=traceback.format_exc()[-3500:]
        raise
    finally:
        Path("cpu_g102_kv_storage_result.json").write_text(
            json.dumps(receipt,sort_keys=True,indent=2)+"\n")


if __name__ == "__main__":
    main()
