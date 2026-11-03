#!/usr/bin/env python3
"""G101 P1 isolated original-model adapter: reuse ordinary full prefill KV.

No dataset selection, original-model staging, benchmark, held-out or promotion.
The caller owns exact original GPT-2 model identity, frozen development data,
and independent token-parity comparison. This adapter does not modify G96/G97.
"""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import g97_original_adapter as g97
from research.cpu_g96.g96_admission import AdmissionCache, BYTE_LIMIT
from research.cpu_g97.g101_prefix_capture import capture_prefix_from_full_prefill


class _FullPrefillCapture:
    """Transparent, one-shot model-call wrapper for a frozen baseline request."""
    def __init__(self, model, *, total_length, prefix_length, expected_bytes, proc):
        self.model = model
        self.total_length = total_length
        self.prefix_length = prefix_length
        self.expected_bytes = expected_bytes
        self.proc = proc
        self.seen = False
        self.prefix_past = None
        self.capture_ns = 0
        self.sampled_rss = 0

    def __call__(self, *args, **kwargs):
        if not self.seen:
            ids = kwargs.get("input_ids")
            if (args or ids is None or not hasattr(ids, "shape")
                    or int(ids.shape[1]) != self.total_length
                    or kwargs.get("use_cache") is not True
                    or kwargs.get("past_key_values") is not None):
                raise RuntimeError("G101_FIRST_FORWARD_MUST_BE_FULL_PREFILL")
            # Mark before calling the real model to forbid recursive/repeated capture.
            self.seen = True
            result = self.model(*args, **kwargs)
            if not hasattr(result, "past_key_values"):
                raise RuntimeError("G101_FULL_PREFILL_MISSING_KV")
            t0 = time.perf_counter_ns()
            self.prefix_past = capture_prefix_from_full_prefill(
                result.past_key_values, self.prefix_length,
                expected_bytes=self.expected_bytes)
            self.capture_ns = time.perf_counter_ns() - t0
            self.sampled_rss = self.proc.memory_info().rss
            return result
        return self.model(*args, **kwargs)


def run_g101(model, stream, prefixes, keys, torch, proc):
    """G101 LRU variant; all full-prefill and cache-copy work is on request clock.

    Miss: perform the exact frozen full-prompt baseline decode once, intercept
    the first forward and clone its causal prefix KV for *later* requests.
    Hit: clone immutable resident prefix KV and use frozen cached decoding.
    No extra prefix-only model prefill is permitted on any request.
    """
    g95 = g97.frozen._g95()
    if not stream or len(prefixes) != len(keys) or len(set(keys)) != len(keys):
        raise ValueError("G101_INVALID_STREAM_OR_KEYS")
    cache = AdmissionCache("lru")
    outputs, rows = {}, []
    wall0, cpu0 = time.perf_counter_ns(), time.process_time_ns()
    with torch.inference_mode():
        for idx, request in enumerate(stream):
            t0, c0 = time.perf_counter_ns(), time.process_time_ns()
            pid = request["prefix_id"]
            if type(pid) is not int or not 0 <= pid < len(prefixes):
                raise ValueError("G101_INVALID_PREFIX_ID")
            prefix, suffix, key = prefixes[pid], request["suffix"], keys[pid]
            expected = request["prefix_kv_bytes"]
            if type(expected) is not int or expected <= 0 or expected > BYTE_LIMIT:
                raise RuntimeError("G101_KV_BUDGET_OR_SIZE_INVALID")
            full = torch.cat((prefix, suffix), dim=1)
            prefix_length, total = int(prefix.shape[1]), int(full.shape[1])
            if prefix_length <= 0 or total <= prefix_length:
                raise ValueError("G101_EMPTY_PREFIX_OR_SUFFIX")
            clone_ns, capture_ns = 0, 0
            sampled = proc.memory_info().rss
            if key in cache.entries:
                if cache.entries[key]["bytes"] != expected:
                    raise RuntimeError("G101_RESIDENT_SIZE_DRIFT")
                def unexpected_build():
                    raise RuntimeError("G101_HIT_ATTEMPTED_EXTRA_PREFILL")
                entry, hit, admitted = cache.request(key, expected, unexpected_build)
                if not hit or admitted or entry is None:
                    raise RuntimeError("G101_HIT_STATE_DRIFT")
                tcopy = time.perf_counter_ns()
                past = copy.deepcopy(entry["past"])
                clone_ns = time.perf_counter_ns() - tcopy
                sampled = max(sampled, proc.memory_info().rss)
                if g95.tensor_storage_ptrs(past) & g95.tensor_storage_ptrs(entry["past"]):
                    raise RuntimeError("G101_HIT_STORAGE_ALIAS")
                ids, _ = g95.request_decode(
                    model, full, suffix, past, prefix_length, g95.TOKENS, torch, proc)
                if g95.tensor_tree_digest(entry["past"]) != entry["snapshot"]:
                    raise RuntimeError("G101_RESIDENT_MUTATED")
                served_from_cache = True
            else:
                wrapper = _FullPrefillCapture(
                    model, total_length=total, prefix_length=prefix_length,
                    expected_bytes=expected, proc=proc)
                # The original G95 baseline performs all autoregressive steps.
                # The wrapper captures only its first ordinary full-prompt forward.
                ids, _ = g95.baseline_request(wrapper, full, g95.TOKENS, torch, proc)
                if not wrapper.seen or wrapper.prefix_past is None:
                    raise RuntimeError("G101_MISSING_FULL_PREFILL_CAPTURE")
                if g95.tensor_tree_bytes(wrapper.prefix_past) != expected:
                    raise RuntimeError("G101_CAPTURE_BYTES_DRIFT")
                snapshot = g95.tensor_tree_digest(wrapper.prefix_past)
                def commit_capture():
                    return {"past": wrapper.prefix_past, "snapshot": snapshot}
                entry, hit, admitted = cache.request(key, expected, commit_capture)
                if hit or not admitted or entry is None:
                    raise RuntimeError("G101_MISS_ADMISSION_DRIFT")
                capture_ns = wrapper.capture_ns
                sampled = max(sampled, wrapper.sampled_rss, proc.memory_info().rss)
                served_from_cache = False
            if len(cache.entries) > 4 or cache.resident_bytes() > BYTE_LIMIT:
                raise RuntimeError("G101_RESIDENT_BUDGET_EXCEEDED")
            outputs[idx] = ids
            rows.append({
                "index": idx, "prefix_id": pid, "source_row": request["source_row"],
                "hit": served_from_cache, "admitted": admitted, "bypass": False,
                "served_from_cache": served_from_cache,
                "used_full_prefill": not served_from_cache,
                "extra_prefix_forwards": 0,
                "prefix_capture_ns": capture_ns, "clone_ns": clone_ns,
                "request_wall_ns": time.perf_counter_ns() - t0,
                "request_cpu_ns": time.process_time_ns() - c0,
                "resident_kv_bytes": cache.resident_bytes(),
                "rss_bytes": max(sampled, proc.memory_info().rss),
                "output_sha256": hashlib.sha256(
                    json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
            })
    metrics = {
        "wall_ns": time.perf_counter_ns() - wall0,
        "cpu_ns": time.process_time_ns() - cpu0,
        "rows": rows, "hits": cache.hits, "misses": cache.misses,
        "admissions": cache.admissions, "evictions": cache.evictions,
        "bypasses": cache.bypasses,
        "max_resident_kv_bytes": max(r["resident_kv_bytes"] for r in rows),
        "max_rss": max(r["rss_bytes"] for r in rows),
        "capture_events": sum(r["used_full_prefill"] for r in rows),
        "extra_prefix_forwards": 0,
        "rss_caveat": "sampled CPU RSS, not complete transient allocation peak",
        "phase": "DEVELOPMENT_ONLY",
    }
    if metrics["hits"] + metrics["misses"] != len(stream):
        raise RuntimeError("G101_COUNTER_DRIFT")
    return outputs, metrics
