#!/usr/bin/env python3
"""Independent, model-free G101 final numerical receipt verifier."""
import json
import math
import re
import sys
from pathlib import Path

from research.cpu_g97.g101_final_diagnostic import (
    BACKENDS, PAIRS_PER_BACKEND, TENSORS_PER_PAIR, final_verdict, SCHEMA)

def require(ok, why):
    if not ok:
        raise ValueError("G101_FINAL_RECEIPT_" + why)

def validate(receipt, frozen_sha):
    require(receipt.get("schema") == SCHEMA, "SCHEMA")
    require(re.fullmatch(r"[0-9a-f]{40}", frozen_sha) is not None
            and receipt.get("source_sha") == frozen_sha, "SOURCE")
    require(receipt.get("phase") == "DEVELOPMENT_ONLY"
            and receipt.get("heldout_executed") is False
            and receipt.get("promotion_allowed") is False
            and receipt.get("scientific_acceptance") == "NOT_GRANTED"
            and receipt.get("performance_verdict") == "NOT_EVALUATED", "GOVERNANCE")
    require(receipt.get("engineering") == "PASS", "ENGINEERING")
    require(receipt.get("development_ranks") == list(range(276,286))
            and len(receipt.get("question_hashes", [])) == 10, "DEVELOPMENT_SELECTION")
    arms = receipt.get("arms", {})
    require(set(arms) == set(BACKENDS), "BACKENDS")
    for backend in BACKENDS:
        arm = arms[backend]
        require(arm.get("attention_backend") == backend
                and len(arm.get("pairs", [])) == PAIRS_PER_BACKEND, "ATTENTION_OR_PAIRS")
        require(arm.get("generated_token_parity") is True, "TOKEN_PARITY")
        require(arm.get("model_calls") == 80 and arm.get("extra_prefix_forwards") == 0,
                "FORWARD_COUNT")
        ctr = arm.get("cache_counters", {})
        require(tuple(ctr.get(k) for k in ("hits","misses","admissions","evictions","capture_events"))
                == (3,7,7,3,7), "CACHE_COUNTERS")
        require(0 < arm.get("max_resident_kv_bytes", 0) <= 86114304,
                "MEMORY_CAP")
        require(re.fullmatch("[0-9a-f]{64}", arm.get("output_sha256", "")) is not None,
                "OUTPUT_DIGEST")
        require(len(arm["pairs"]) == 10, "PAIR_COUNT")
        for i, pair in enumerate(arm["pairs"]):
            require(pair.get("prefix_id") == i // 2
                    and pair.get("suffix_rank") == i // 2 + (0 if i % 2 == 0 else 5),
                    "PAIR_IDENTITY")
            require(pair.get("tensors") == TENSORS_PER_PAIR
                    and len(pair.get("layers", [])) == 12, "LAYER_COMPLETENESS")
            bit_mismatches, highest_abs, highest_ulp = 0, 0.0, 0
            for layer_index, layer in enumerate(pair["layers"]):
                require(layer.get("layer") == layer_index, "LAYER_ID")
                for kind in ("key", "value"):
                    t = layer.get(kind, {})
                    n, m = t.get("elements"), t.get("bit_mismatches")
                    require(type(n) is int and n > 0 and type(m) is int and 0 <= m <= n,
                            "ELEMENT_COUNT")
                    require(type(t.get("exact")) is bool and t["exact"] == (m == 0),
                            "TENSOR_EXACT")
                    for k in ("max_abs", "max_ulp"):
                        value = t.get(k)
                        require(type(value) in (int,float) and math.isfinite(value)
                                and value >= 0, "TENSOR_NUMERICAL")
                    if m == 0:
                        require(t["max_abs"] == 0 and t["max_ulp"] == 0, "ZERO_MISMATCH_VALUES")
                    bit_mismatches += m
                    highest_abs = max(highest_abs, t["max_abs"])
                    highest_ulp = max(highest_ulp, t["max_ulp"])
            require(pair.get("exact") is (bit_mismatches == 0), "PAIR_EXACT")
            require(pair.get("bit_mismatches") == bit_mismatches, "PAIR_BIT_SUM")
            require(math.isclose(pair.get("max_abs", -1), highest_abs, rel_tol=1e-10),
                    "PAIR_ABS_MAX")
            require(pair.get("max_ulp") == highest_ulp, "PAIR_ULP_MAX")
    decision, feasible = final_verdict(arms)
    require(receipt.get("decision") == decision
            and receipt.get("feasible_backends") == feasible, "FALSE_VERDICT")
    return decision

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: validator.py receipt.json frozen_sha")
    value = validate(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
    print("G101_FINAL_INDEPENDENT_RECEIPT=PASS", value)
