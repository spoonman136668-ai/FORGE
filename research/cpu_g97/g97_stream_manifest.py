#!/usr/bin/env python3
"""G97 development-only frozen traffic manifest, independent of model inference.

The original G96 data rank selector supplies only development ranks 276..287.
The manifest contains prefix IDs and source-row identities, never expected outputs.
"""
import hashlib
import json
from pathlib import Path
from research.cpu_g96.g96_admission import build_traffic, traffic_digest

STRATA = ("round_robin", "bursty", "mixed", "overflow")
REPETITIONS = 4
RANK_START, RANK_STOP = 276, 288

def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def freeze(selected):
    if len(selected) != 12 or len({r["instruction_sha256"] for r in selected}) != 12:
        raise ValueError("G97_DEVELOPMENT_COHORT_DRIFT")
    streams = {}
    for stratum in STRATA:
        layout = build_traffic(stratum, cycles=1)
        stream = []
        for i, req in enumerate(layout):
            pid = req["prefix_id"]
            source = selected[(pid % 4) + 4 * ((i // 4) % 3)]
            stream.append({"prefix_id": pid, "source_row": source["source_row"],
                           "instruction_sha256": source["instruction_sha256"]})
        if len(stream) != 48:
            raise ValueError("G97_TRAFFIC_LENGTH_DRIFT")
        streams[stratum] = {"traffic_sha256": traffic_digest(layout), "requests": stream}
    payload = {"schema": "forge.cpu-g97.development-stream.v1", "phase": "DEVELOPMENT_ONLY",
               "rank_interval": [RANK_START, RANK_STOP], "repetitions": REPETITIONS,
               "strata": streams, "protected_heldout_used": False}
    return payload, hashlib.sha256(canonical_bytes(payload)).hexdigest()

def write_manifest(selected, destination):
    payload, digest = freeze(selected)
    path = Path(destination)
    path.write_bytes(canonical_bytes(payload))
    return digest
