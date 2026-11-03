#!/usr/bin/env python3
"""Independent, model-free G100 development receipt verifier.

Checks provenance and recomputes the frozen scientific verdict from raw paired
rows. This is not independent scientific acceptance or protected first use.
"""
import hashlib
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

from research.cpu_g97.g100_stream_manifest import ARMS, RANK_INTERVAL, REPETITIONS, STRATA, canonical_bytes
from research.cpu_g96.g96_admission import BYTE_LIMIT

RATIO_LIMITS = {"throughput_speedup": 1.15, "minimum_paired_request_speedup": 0.90,
                "p95_latency_ratio": 1.10, "cpu_ratio": 1.10, "rss_ratio": 1.15}


def require(condition, message):
    if not condition:
        raise ValueError("G100_RECEIPT_" + message)


def number(x, *, positive=True):
    require(type(x) in (int, float) and math.isfinite(x) and
            (x > 0 if positive else x >= 0), "INVALID_MEASUREMENT")
    return x


def p95(values):
    return sorted(values)[math.ceil(.95 * len(values)) - 1]


def calculate(baseline, candidate, tokens):
    require(len(baseline) == len(candidate) == REPETITIONS, "REPETITION_COUNT")
    bt = [row["request_wall_ns"] for rep in baseline for row in rep["rows"]]
    ct = [row["request_wall_ns"] for rep in candidate for row in rep["rows"]]
    require(len(bt) == len(ct) == 48 * REPETITIONS, "PAIRED_REQUEST_COUNT")
    bps = statistics.median(48 * tokens / (r["wall_ns"] / 1e9) for r in baseline)
    cps = statistics.median(48 * tokens / (r["wall_ns"] / 1e9) for r in candidate)
    return {
        "throughput_speedup": cps / bps,
        "minimum_paired_request_speedup": min(b / c for b, c in zip(bt, ct)),
        "p95_latency_ratio": p95(ct) / p95(bt),
        "cpu_ratio": sum(r["cpu_ns"] for r in candidate) / sum(r["cpu_ns"] for r in baseline),
        "rss_ratio": max(r["max_rss"] for r in candidate) / max(r["max_rss"] for r in baseline),
        "max_resident_kv_bytes": max(r["max_resident_kv_bytes"] for r in candidate),
        "hits": sum(r["hits"] for r in candidate),
        "misses": sum(r["misses"] for r in candidate),
        "evictions": sum(r["evictions"] for r in candidate),
        "bypasses": sum(r["bypasses"] for r in candidate)}


def validate(receipt, manifest, manifest_raw, source_sha, *, tokens):
    require(re.fullmatch(r"[0-9a-f]{40}", source_sha) is not None, "SOURCE_SHA")
    require(receipt.get("schema") == "forge.cpu-g100.development.v1", "RECEIPT_SCHEMA")
    require(manifest.get("schema") == "forge.cpu-g100.development-stream.v1", "MANIFEST_SCHEMA")
    require(manifest_raw == canonical_bytes(manifest), "MANIFEST_NOT_CANONICAL")
    digest = hashlib.sha256(manifest_raw).hexdigest()
    require(receipt.get("development_stream_sha256") == digest, "STREAM_HASH_DRIFT")
    require(receipt.get("source_sha") == source_sha, "SOURCE_MISMATCH")
    require(receipt.get("phase") == manifest.get("phase") == "DEVELOPMENT_ONLY", "PHASE")
    require(receipt.get("heldout_executed") is False and receipt.get("promotion_allowed") is False
            and manifest.get("protected_heldout_used") is False, "PROTECTED_OR_PROMOTION")
    require(manifest.get("rank_interval") == list(RANK_INTERVAL)
            and manifest.get("repetitions") == REPETITIONS
            and manifest.get("arms") == list(ARMS), "FROZEN_PROTOCOL_DRIFT")
    require(receipt.get("engineering") == "PASS" and receipt.get("correctness") == "PASS"
            and receipt.get("scientific_acceptance") == "NOT_GRANTED", "ENGINEERING_UNVERIFIED")
    require(set(receipt.get("strata", {})) == set(STRATA)
            and set(manifest.get("strata", {})) == set(STRATA), "STRATA_DRIFT")
    require(type(tokens) is int and tokens > 0, "GENERATED_TOKEN_COUNT")
    selected = receipt.get("selected_question_hashes")
    require(isinstance(selected, list) and len(selected) == 12 and len(set(selected)) == 12
            and all(isinstance(h, str) and re.fullmatch(r"[0-9a-f]{64}", h) for h in selected),
            "SELECTED_SOURCE_IDENTITIES")

    all_qualified = True
    overflow_better = False
    for stratum in STRATA:
        record = receipt["strata"][stratum]
        stream = manifest["strata"][stratum]
        requests = stream["requests"]
        require(record.get("traffic_sha256") == stream.get("traffic_sha256")
                and len(requests) == 48, "TRAFFIC_DRIFT")
        require(all(r["instruction_sha256"] in selected for r in requests), "UNKNOWN_SOURCE")
        require(record.get("exact_parity") is True, "PARITY")
        reps = record.get("repetitions")
        require(isinstance(reps, list) and len(reps) == REPETITIONS, "REPETITION_COUNT")
        by_arm = {arm: [] for arm in ARMS}
        baseline_output_hashes = None
        for i, rep in enumerate(reps):
            expected_order = list(ARMS) if i % 2 == 0 else list(reversed(ARMS))
            require(rep.get("rep") == i + 1 and rep.get("order") == expected_order
                    and set(rep.get("arms", {})) == set(ARMS), "PAIRED_ORDER")
            for arm in ARMS:
                sample = rep["arms"][arm]
                rows = sample.get("rows")
                require(isinstance(rows, list) and len(rows) == 48, "ROW_COUNT")
                for field in ("wall_ns", "cpu_ns", "max_rss"):
                    number(sample.get(field))
                for field in ("hits", "misses", "admissions", "evictions", "bypasses", "max_resident_kv_bytes"):
                    require(type(sample.get(field)) is int and sample[field] >= 0, "COUNTER")
                require(sample["hits"] + sample["misses"] == 48, "CACHE_EVENT_TOTAL")
                require(sample["max_resident_kv_bytes"] <= BYTE_LIMIT, "RESIDENT_KV_BUDGET")
                require(sample["admissions"] <= sample["misses"]
                        and sample["evictions"] <= sample["admissions"], "CACHE_EVENT_BOUNDS")
                hashes = []
                for idx, row in enumerate(rows):
                    request = requests[idx]
                    require(row.get("index") == idx and row.get("prefix_id") == request["prefix_id"]
                            and row.get("source_row") == request["source_row"], "REQUEST_IDENTITY")
                    for name in ("request_wall_ns", "rss_bytes"):
                        number(row.get(name))
                    for name in ("request_cpu_ns", "clone_ns", "resident_kv_bytes"):
                        number(row.get(name), positive=False)
                    require(row["resident_kv_bytes"] <= BYTE_LIMIT, "RESIDENT_KV_BUDGET")
                    require(type(row.get("hit")) is bool and type(row.get("admitted")) is bool
                            and type(row.get("bypass")) is bool, "EVENT_FLAGS")
                    require(isinstance(row.get("output_sha256"), str) and
                            re.fullmatch(r"[0-9a-f]{64}", row["output_sha256"]), "OUTPUT_DIGEST")
                    hashes.append(row["output_sha256"])
                require(sample["hits"] == sum(r["hit"] for r in rows)
                        and sample["admissions"] == sum(r["admitted"] for r in rows)
                        and sample["bypasses"] == sum(r["bypass"] for r in rows), "COUNTER_ROW_DRIFT")
                require(sample["max_resident_kv_bytes"] == max(r["resident_kv_bytes"] for r in rows)
                        and sample["max_rss"] == max(r["rss_bytes"] for r in rows), "PEAK_ROW_DRIFT")
                if baseline_output_hashes is None:
                    baseline_output_hashes = hashes
                else:
                    require(hashes == baseline_output_hashes, "OUTPUT_PARITY")
                by_arm[arm].append(sample)
        metrics = record.get("metrics", {})
        require(set(metrics) == set(ARMS[1:]), "METRIC_ARMS")
        baseline = by_arm["no_cache"]
        for arm in ARMS[1:]:
            calculated = calculate(baseline, by_arm[arm], tokens)
            declared = metrics[arm]
            for name, value in calculated.items():
                observed = declared.get(name)
                if type(value) in (int,):
                    require(type(observed) is int and observed == value, "METRIC_" + name)
                else:
                    number(observed)
                    require(math.isclose(observed, value, rel_tol=1e-10, abs_tol=1e-12),
                            "METRIC_" + name)
            qualifies = (calculated["throughput_speedup"] >= RATIO_LIMITS["throughput_speedup"]
                         and calculated["minimum_paired_request_speedup"] >= RATIO_LIMITS["minimum_paired_request_speedup"]
                         and calculated["p95_latency_ratio"] <= RATIO_LIMITS["p95_latency_ratio"]
                         and calculated["cpu_ratio"] <= RATIO_LIMITS["cpu_ratio"]
                         and calculated["rss_ratio"] <= RATIO_LIMITS["rss_ratio"]
                         and calculated["max_resident_kv_bytes"] <= BYTE_LIMIT)
            require(declared.get("qualifies") is qualifies, "FALSE_QUALIFICATION")
            if arm == "g100_deferred_first_use":
                all_qualified &= qualifies
        if stratum == "overflow":
            current = sum(x["wall_ns"] for x in by_arm["g100_deferred_first_use"])
            control = sum(x["wall_ns"] for x in by_arm["g97_overflow_bypass"])
            overflow_better = current < control
            require(metrics["g100_deferred_first_use"].get("improves_overflow_g97") is overflow_better,
                    "OVERFLOW_COMPARISON")
    verdict = "DEVELOPMENT_CANDIDATE" if all_qualified and overflow_better else "DEVELOPMENT_NO_GO"
    require(receipt.get("decision") == verdict, "FALSE_VERDICT")
    return verdict


def main():
    require(len(sys.argv) == 4, "USAGE")
    result_path, manifest_path, source_sha = map(str, sys.argv[1:])
    manifest_raw = Path(manifest_path).read_bytes()
    manifest = json.loads(manifest_raw)
    receipt = json.loads(Path(result_path).read_bytes())
    from research.cpu_g96.g96_development_original import _g95
    model_spec = _g95()
    print("G100_INDEPENDENT_RECEIPT_VALIDATION=PASS",
          validate(receipt, manifest, manifest_raw, source_sha, tokens=model_spec.TOKENS))


if __name__ == "__main__":
    main()
