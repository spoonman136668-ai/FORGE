#!/usr/bin/env python3
"""G100 deterministic independent DEVELOPMENT-ONLY stream preregistration.

No original model, held-out rows, oracle outputs, or runtime timing data.
The G96 prefix traffic shape is retained; only development-source assignment
is independently keyed and frozen before measurement.
"""
import hashlib
import json
from research.cpu_g96.g96_admission import build_traffic, traffic_digest
from research.cpu_g97.g97_stream_manifest import STRATA, REPETITIONS

_SEED = b"FORGE-CPU-G100-FROZEN-DEVELOPMENT-SOURCES-20261103"
ARMS = ("no_cache", "lru", "g97_overflow_bypass", "g100_deferred_first_use")
RANK_INTERVAL = (276, 288)


def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def freeze(selected):
    if len(selected) != 12:
        raise ValueError("G100_DEVELOPMENT_COHORT_LENGTH")
    identities = []
    for item in selected:
        if not isinstance(item, dict) or not isinstance(item.get("source_row"), int):
            raise ValueError("G100_MISSING_ROW_ID")
        h = item.get("instruction_sha256")
        if not isinstance(h, str) or len(h) != 64:
            raise ValueError("G100_INVALID_INSTRUCTION_HASH")
        try:
            if h.lower() != h or bytes.fromhex(h).hex() != h:
                raise ValueError("G100_NONCANONICAL_HASH")
        except ValueError as exc:
            raise ValueError("G100_INVALID_INSTRUCTION_HASH") from exc
        identities.append((item["source_row"], h))
    if len(set(identities)) != 12 or len({r for r, _ in identities}) != 12 or len({h for _, h in identities}) != 12:
        raise ValueError("G100_DUPLICATE_DEVELOPMENT_SOURCE")
    # Assign source questions in a new deterministic order, independent of G97
    # and of the model's generated tokens or timings.
    order = sorted(range(12), key=lambda i: hashlib.sha256(
        _SEED + selected[i]["instruction_sha256"].encode("ascii")).digest())
    streams = {}
    for stratum in STRATA:
        layout = build_traffic(stratum, cycles=1)
        requests = []
        for i, request in enumerate(layout):
            pid = request["prefix_id"]
            source_idx = order[(pid % 4) + 4 * ((i // 4) % 3)]
            source = selected[source_idx]
            requests.append({"prefix_id": pid, "source_row": source["source_row"],
                             "instruction_sha256": source["instruction_sha256"]})
        if len(requests) != 48:
            raise ValueError("G100_TRAFFIC_LENGTH_DRIFT")
        streams[stratum] = {"traffic_sha256": traffic_digest(layout), "requests": requests}
    payload = {"schema": "forge.cpu-g100.development-stream.v1",
               "phase": "DEVELOPMENT_ONLY", "rank_interval": list(RANK_INTERVAL),
               "repetitions": REPETITIONS, "arms": list(ARMS),
               "protected_heldout_used": False, "strata": streams,
               "source_assignment_seed_sha256": hashlib.sha256(_SEED).hexdigest()}
    return payload, hashlib.sha256(canonical_bytes(payload)).hexdigest()
