#!/usr/bin/env python3
"""Offline G99 development-only attribution of G97 paired request regressions.

Consumes the preserved G97/G98 artifact. Does not load models, network data,
protected cohorts or benchmark thresholds. Diagnostic, not performance admission.
"""
import argparse
import hashlib
import json
from pathlib import Path

STRATA = ("round_robin", "bursty", "mixed", "overflow")
PHASES = ("prefix_concatenation", "cache_request_inclusive", "kv_build",
          "kv_clone", "cached_decode", "fallback_decode")

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def classify(row):
    if row["hit"]:
        return "cache_hit"
    if row["bypass"]:
        return "fallback_bypass"
    if row["admitted"]:
        return "admitted_miss"
    raise ValueError("G99_UNCLASSIFIED_CACHE_DECISION")

def report(result, timing, stream_raw, *, artifact_sha256):
    if result["schema"] != "forge.cpu-g97.development.v1" or timing["schema"] != "forge.cpu-g98.original-development-timing.v1":
        raise ValueError("G99_UNEXPECTED_RECEIPT_SCHEMA")
    if result["phase"] != timing["phase"] or result["phase"] != "DEVELOPMENT_ONLY":
        raise ValueError("G99_PHASE_DRIFT")
    if result["heldout_executed"] or timing["heldout_executed"] or result["promotion_allowed"] or timing["promotion_allowed"]:
        raise ValueError("G99_PROTECTED_OR_PROMOTED_SOURCE")
    if result["source_sha"] != timing["source_sha"] or len(result["source_sha"]) != 40:
        raise ValueError("G99_SOURCE_IDENTITY_DRIFT")
    for key in ("model_revision", "weights_sha256", "development_stream_sha256"):
        if result[key] != timing[key]:
            raise ValueError("G99_" + key.upper() + "_DRIFT")
    if sha256(stream_raw) != result["development_stream_sha256"]:
        raise ValueError("G99_STREAM_DIGEST_DRIFT")
    if set(result["strata"]) != set(STRATA) or set(timing["strata"]) != set(STRATA):
        raise ValueError("G99_STRATA_DRIFT")
    if result["decision"] != "DEVELOPMENT_NO_GO" or not timing["diagnostic_only"]:
        raise ValueError("G99_EXPECTED_DIAGNOSTIC_NO_GO")
    out = {"schema": "forge.cpu-g99.development-attribution.v1", "phase": "DEVELOPMENT_ONLY",
           "source_sha": result["source_sha"], "model_revision": result["model_revision"],
           "weights_sha256": result["weights_sha256"],
           "development_stream_sha256": result["development_stream_sha256"],
           "original_artifact_sha256": artifact_sha256, "source_decision": result["decision"],
           "diagnostic_only": True, "heldout_executed": False, "promotion_allowed": False,
           "scientific_acceptance": "NOT_GRANTED", "strata": {}}
    for name in STRATA:
        info=result["strata"][name]
        diagnostic=timing["strata"][name]
        if not info["exact_parity"] or diagnostic["parity"] != "PASS" or not diagnostic["timing_accepted"]:
            raise ValueError("G99_PARITY_OR_TIMING_MISSING_" + name)
        if diagnostic["source_sha"] != result["source_sha"] or diagnostic["development_stream_sha256"] != result["development_stream_sha256"]:
            raise ValueError("G99_STRATUM_IDENTITY_DRIFT_" + name)
        reps=info["repetitions"]
        if len(reps) != 4:
            raise ValueError("G99_REPETITION_DRIFT_" + name)
        rows=[]
        for rep in reps:
            baseline=rep["arms"]["no_cache"]["rows"]
            candidate=rep["arms"]["g97_overflow_bypass"]["rows"]
            if len(baseline) != 48 or len(candidate) != 48:
                raise ValueError("G99_REQUEST_COUNT_DRIFT_" + name)
            for b,c in zip(baseline,candidate):
                for field in ("index", "prefix_id", "source_row", "output_sha256"):
                    if b[field] != c[field]:
                        raise ValueError("G99_PAIRED_IDENTITY_DRIFT_" + name)
                if b["request_wall_ns"] <= 0 or c["request_wall_ns"] <= 0:
                    raise ValueError("G99_INVALID_LATENCY")
                rows.append({"repetition": rep["rep"], "index": c["index"],
                             "prefix_id": c["prefix_id"], "source_row": c["source_row"],
                             "decision": classify(c), "baseline_wall_ns": b["request_wall_ns"],
                             "candidate_wall_ns": c["request_wall_ns"],
                             "paired_speedup": b["request_wall_ns"]/c["request_wall_ns"],
                             "candidate_clone_ns": c["clone_ns"],
                             "candidate_admitted": c["admitted"], "candidate_hit": c["hit"],
                             "candidate_bypass": c["bypass"]})
        worst=min(rows,key=lambda row:(row["paired_speedup"],row["repetition"],row["index"]))
        phase=diagnostic["timing"]["durations_ns"]
        if set(phase) != set(PHASES):
            raise ValueError("G99_TIMING_PHASE_DRIFT_" + name)
        out["strata"][name]={"paired_requests":len(rows),"worst_pair":worst,
                            "slowdown_count":sum(r["paired_speedup"]<1 for r in rows),
                            "failing_floor_count":sum(r["paired_speedup"]<.9 for r in rows),
                            "decision_counts":{category:sum(r["decision"]==category for r in rows)
                                               for category in ("admitted_miss","cache_hit","fallback_bypass")},
                            "worst_pairs_by_decision":{
                                category:min((r for r in rows if r["decision"]==category),
                                             key=lambda row:row["paired_speedup"],default=None)
                                for category in ("admitted_miss","cache_hit","fallback_bypass")},
                            "instrumented_phase_total_ns":{p:sum(phase[p]) for p in PHASES},
                            "timing_limit":"Phase totals come from a separate instrumented 48-request pass; they cannot be paired with individual uninstrumented requests, and nested timings overlap."}
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True,help="Directory containing extracted GitHub artifact")
    p.add_argument("--artifact-sha256",required=True,help="SHA256 of original GitHub artifact ZIP")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=json.loads((a.input/"cpu_g97_development_result.json").read_bytes())
    timing=json.loads((a.input/"cpu_g98_development_timing.json").read_bytes())
    stream=(a.input/"cpu_g97_development_stream.json").read_bytes()
    obj=report(result,timing,stream,artifact_sha256=a.artifact_sha256)
    a.output.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
    print("G99_OFFLINE_ATTRIBUTION=PASS",a.output)
if __name__=="__main__":main()
