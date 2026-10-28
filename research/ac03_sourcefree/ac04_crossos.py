"""AC-04 source-free cross-OS runner, CPU-first and isolated per variant.

Only local synthetic workload processes are spawned. No network, secrets, science
source, model mutation, controller or scientific authority. Python 3.11 stdlib.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys

import ac03_benchmark as prior

SOURCE_SHA256 = "b4295236b37b6b017841a863ab8fd551fee26cdafa8f5b02a4d80afdc78f2c5d"
REPEATS = 3
ALLOWED_CASES = tuple(prior.CASES)
SCHEMA = "forge.ac04.sourcefree.crossos.v1"

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def one(case, variant):
    command = [sys.executable, "-B", str(Path(prior.__file__).resolve()),
               "--child", case, variant]
    # Each sample executes in an independent Python process; measured child
    # process CPU excludes Python startup, so total runtime is undercounted.
    got = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, check=True, timeout=120,
                         cwd=str(Path(__file__).resolve().parent))
    result = json.loads(got.stdout)
    if result["case"] != case or result["variant"] != variant:
        raise ValueError("MISMATCHED_VARIANT")
    for key in ("cpu_ns", "wall_ns", "python_alloc_peak_bytes"):
        if not isinstance(result.get(key), int) or result[key] < 0:
            raise ValueError("INVALID_MEASUREMENT:"+key)
    return result

def run(output):
    source=Path(prior.__file__).resolve()
    if digest(source) != SOURCE_SHA256:
        raise RuntimeError("AC03_SOURCE_SHA256_DRIFT")
    if set(prior.CASES) != set(ALLOWED_CASES) or prior.REPEATS != REPEATS:
        raise RuntimeError("AC03_PROTOCOL_DRIFT")
    if os.environ.get("AC04_SOURCEFREE_ONLY") != "1":
        raise RuntimeError("AC04_SOURCEFREE_ONLY_GUARD_NOT_SET")
    rows=[]
    for case,(baseline,candidate) in prior.CASES.items():
        for replicate in range(REPEATS):
            order=(baseline,candidate) if replicate%2==0 else (candidate,baseline)
            pair={}
            for variant in order:
                result=one(case,variant)
                pair[variant]=result
                rows.append({
                    "case":case,"claim_ids":prior.IDS[case],"replicate":replicate,
                    "variant":variant,"role":"baseline" if variant==baseline else "candidate",
                    "cpu_ns":result["cpu_ns"],"wall_ns":result["wall_ns"],
                    "python_alloc_peak_bytes":result["python_alloc_peak_bytes"],
                    "process_peak_rss_bytes":result["process_peak_rss_bytes"],
                    "outcome_sha256":result["sha256"]
                })
            if case=="sketch":
                aa=pair[baseline]["outcome"]
                bb=pair[candidate]["outcome"]
                if len(aa)!=len(bb) or not any(b>a for a,b in zip(aa,bb)) or any(b<a for a,b in zip(aa,bb)):
                    raise AssertionError("COUNT_MIN_SKETCH_NEGATIVE_NOT_PRESERVED")
            elif pair[baseline]["sha256"] != pair[candidate]["sha256"]:
                raise AssertionError("PARITY_FAILED:"+case)
    summaries={}
    for case,(baseline,candidate) in prior.CASES.items():
        b=[s for s in rows if s["case"]==case and s["role"]=="baseline"]
        c=[s for s in rows if s["case"]==case and s["role"]=="candidate"]
        median=lambda seq,k:statistics.median(x[k] for x in seq)
        denom=median(b,"cpu_ns")
        summaries[case]={
            "claim_ids":prior.IDS[case],
            "cpu_ratio_candidate_over_baseline":median(c,"cpu_ns")/denom if denom>0 else None,
            "baseline_cpu_median_ns":median(b,"cpu_ns"),
            "candidate_cpu_median_ns":median(c,"cpu_ns"),
            "baseline_wall_median_ns":median(b,"wall_ns"),
            "candidate_wall_median_ns":median(c,"wall_ns"),
            "baseline_peak_rss_bytes_median":median(b,"process_peak_rss_bytes") if all(x["process_peak_rss_bytes"] is not None for x in b) else None,
            "candidate_peak_rss_bytes_median":median(c,"process_peak_rss_bytes") if all(x["process_peak_rss_bytes"] is not None for x in c) else None,
            "candidate_is_exact":case!="sketch",
        }
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    artifact={
        "schema":SCHEMA,"scope":"DEVELOPMENT_ONLY",
        "head_sha":os.environ.get("GITHUB_SHA") or "LOCAL_UNQUALIFIED",
        "ac03_source_sha256":SOURCE_SHA256,
        "ac04_runner_sha256":digest(__file__),
        "hardware":{"os":platform.platform(),"machine":platform.machine(),
                    "python":sys.version.split()[0],"cpu_count":os.cpu_count()},
        "timing_excludes_child_process_startup":True,
        "variant_isolation":"fresh child process per arm per repetition",
        "repetitions_per_variant":REPEATS,
        "measured_case_count":len(prior.CASES),
        "all_36_ideas_remain_in_portfolio":True,
        "science_admitted":False,
        "scientific_original_first_use":False,
        "new_controller":False,
        "accepted_model_updated":False,
        "source_results":rows,"summaries":summaries
    }
    output.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    # Check emitted evidence for byte-identical readback and no accidental mutation.
    if json.loads(output.read_text(encoding="utf-8")) != artifact:
        raise RuntimeError("AC04_EVIDENCE_ROUNDTRIP_FAILED")
    return artifact

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    d=run(args.output)
    print(json.dumps({"schema":d["schema"],"sha256":digest(args.output),
                      "cases":len(d["summaries"]),"samples":len(d["source_results"]),
                      "science_admitted":False,"first_use":False},sort_keys=True))
