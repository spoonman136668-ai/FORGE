"""F124-BL paired fresh-Linux-process measurements, negative fixtures only.

The original AZ diagnostic is explicitly ineligible for scientific acceptance.
The earlier 192 TRAIN first-use cannot be replayed; immutable provider stdout
is independently identified as incomplete prior custody in all receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
ARMS=("learned","AZ_forced_diagnostic")
TAGS=("U","R")
REPEATS=3
TRAIN_RAW_CPU_NS=601013140
TRAIN_PEAK_RSS=20140032
PRIOR="5a00cd00"


def need(ok,reason):
    if not ok:
        raise RuntimeError("F124BL_RESOURCE_"+reason)


def child(arm,tag):
    need(sys.platform=="linux" and arm in ARMS and tag in TAGS,
         "PLATFORM_OR_PROTECTED_IDENTITY")
    import resource
    t0=time.process_time_ns()
    spec=importlib.util.spec_from_file_location("f124bl_native_child",
                                                 HERE/"f124bl_equal_native.py")
    model=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    result=model.evaluate(arm,tag)
    cpu=time.process_time_ns()-t0
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0, "REAL_OS_MEASUREMENT")
    witness=result["native_workload"]
    need(witness["native_graph_calls"]==1 and
         witness["native_work"]["max_active"]<=7 and
         witness["native_work"]["max_retained"]<=9 and
         result["original_192_TRAIN_replayed"] is False and
         result["protected_validation_or_U_R_used"] is False,
         "REAL_NATIVE_NO_FIRSTUSE")
    if arm=="AZ_forced_diagnostic":
        need(witness["original_AZ_policy_decision"]=="abstain"
             and witness["scientifically_admissible"] is False
             and witness["forced_native_work"] is True
             and witness["diagnostic_override_changes_AZ_policy"] is False,
             "FALSE_SCIENCE_CONTROL")
    return {
        "schema":"mass.f124bl.equivalent-native-workload-synthetic-measurement.v1",
        "arm":arm,"fixture":tag,
        "cpu_ns_including_source_import_fit_native_scorer":cpu,
        "whole_child_peak_RSS_bytes":rss,
        "native_execution":result,
        "python_runtime":sys.version,"platform":platform.platform(),
        "scientific_source_origin_witnessed":False,
        "protected_first_use":False,
        "resource_parity_scientifically_accepted":False,
    }


def combine(records):
    need(len(records)==12,"EXACT_REPETITIONS")
    pairs={}
    for tag in TAGS:
        arms={}
        for arm in ARMS:
            x=[v for v in records if v["arm"]==arm and v["fixture"]==tag]
            need(len(x)==REPEATS,"REPEAT_SET")
            pub={v["native_execution"]["same_public_48_sha256"] for v in x}
            graph={v["native_execution"]["same_native_graph_sha256"] for v in x}
            need(len(pub)==len(graph)==1,"SYNTHETIC_SOURCE_DRIFT")
            need(all(v["native_execution"]["native_workload"]["native_graph_calls"]
                     ==1 for v in x),"MISSING_NATIVE_EXECUTION")
            cpu=[v["cpu_ns_including_source_import_fit_native_scorer"] for v in x]
            rss=[v["whole_child_peak_RSS_bytes"] for v in x]
            arms[arm]={"public_48_sha256":next(iter(pub)),
                       "graph_sha256":next(iter(graph)),
                       "CPU_ns_samples":cpu,"peak_RSS_bytes_samples":rss,
                       "median_CPU_ns":int(statistics.median(cpu)),
                       "median_peak_RSS_bytes":int(statistics.median(rss)),
                       "work_counters":[v["native_execution"]["native_workload"][
                           "native_work"] for v in x]}
        need(arms["learned"]["graph_sha256"]==arms["AZ_forced_diagnostic"]["graph_sha256"]
             and arms["learned"]["public_48_sha256"]==
                 arms["AZ_forced_diagnostic"]["public_48_sha256"],
             "UNMATCHED_GRAPH")
        arms["learned"]["amortized_training_CPU_ns_ceiling_128"] = (
            (TRAIN_RAW_CPU_NS+127)//128)
        arms["learned"]["median_task_plus_observed_train_amortization_CPU_ns"] = (
            arms["learned"]["median_CPU_ns"]+(TRAIN_RAW_CPU_NS+127)//128)
        arms["learned"]["observed_original_train_and_task_RSS_envelope_bytes"] = max(
            TRAIN_PEAK_RSS,arms["learned"]["median_peak_RSS_bytes"])
        pairs[tag]=arms
    return {
        "schema":"mass.f124bl.ineligible-forced-AZ-equal-native-workload.v1",
        "same_native_graph_executed_both_arms":True,
        "real_os_CPU_and_RSS_on_synthetic_negative_fixtures":True,
        "samples":len(records),
        "paired":pairs,
        "original_192_train_once_consumed":True,
        "original_train_replayed":False,
        "original_train_cpu_ns_log_observed":TRAIN_RAW_CPU_NS,
        "original_train_peak_rss_log_observed":TRAIN_PEAK_RSS,
        "original_train_complete_firstuse_record_published":False,
        "AZ_original_scientific_abstention_preserved":True,
        "AZ_forced_diagnostic_is_eligible_baseline":False,
        "full_scientific_resource_parity":False,
        "independent_OOD_source_novelty":False,
        "protected_U_R_cases_generated":0,
        "scientific_acceptance":False,
        "optimizer_promotion":False,
        "disposition":"ENGINEERING_DIAGNOSTIC_ONLY_NO_FIRSTUSE",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--child",action="store_true")
    ap.add_argument("--arm",choices=ARMS)
    ap.add_argument("--tag",choices=TAGS)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    if a.child:
        need(a.arm is not None and a.tag is not None,"CHILD_ARGUMENTS")
        print(json.dumps(child(a.arm,a.tag),sort_keys=True))
        return
    need(a.output is not None and sys.platform=="linux","LINUX_ONLY")
    samples=[]
    for repeat in range(REPEATS):
        for tag in TAGS:
            order=ARMS if repeat%2==0 else tuple(reversed(ARMS))
            for arm in order:
                proc=subprocess.run(
                    [sys.executable,"-B",str(Path(__file__).resolve()),
                     "--child","--arm",arm,"--tag",tag],
                    cwd=ROOT,timeout=120,check=False,text=True,capture_output=True)
                need(proc.returncode==0,
                     "NATIVE_CHILD_"+tag+"_"+arm+":"+proc.stderr[-1800:])
                samples.append(json.loads(proc.stdout))
    data={"summary":combine(samples),"original_nonprotected_samples":samples}
    raw=json.dumps(data,sort_keys=True,indent=2)+"\n"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(raw,encoding="utf-8")
    print("F124BL_NATIVE_EQUAL_WORK_DIAGNOSTIC=PASS")
    print("F124BL_TRAIN_REPLAY=false")
    print("F124BL_ORIGINAL_AZ_SCIENCE_ABSTENTION=preserved")
    print("F124BL_SCIENTIFIC_RESOURCE_PARITY=false")
    print("F124BL_SHA256="+hashlib.sha256(raw.encode()).hexdigest())


if __name__=="__main__":
    main()
