"""F124-BK synthetic only: actual native 7+9 full-task CPU and OS RSS.

Matched 48 public observations; 3 repeated fresh Linux processes per arm per
fixture. Original 192 consumed TRAIN task never reruns. Original TRAIN resource
figures from archived stdout are a separate INCOMPLETE custody observation.
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
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TRAIN_CPU_NS=601013140
TRAIN_PEAK_RSS_BYTES=20140032
TRAIN_EVALS=500736
TRAIN_FIRSTUSE="26d3fa51f629584ad01fc1dfa7be8ffae524e938"
TRAIN_RECEIPT_SHA256="aa16e07d04a8702fd840395df52017b508cc3bf7f920e8bea261077b22f6cd3c"
ARMS=("learned","AZ")
TAGS=("U","R")
REPEATS=3


def need(ok,code):
    if not ok:
        raise RuntimeError("F124BK_RESOURCE_"+code)


def child(arm,tag):
    need(sys.platform=="linux" and arm in ARMS and tag in TAGS,
         "LINUX_NEGATIVE_ONLY")
    import resource
    t0=time.process_time_ns()
    from importlib.util import spec_from_file_location,module_from_spec
    path=HERE/"f124bk_native_graph.py"
    spec=spec_from_file_location("f124bk_native_child",path)
    adapter=module_from_spec(spec)
    spec.loader.exec_module(adapter)
    native=adapter.evaluate(arm,tag)
    cpu=time.process_time_ns()-t0
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and peak>0,"POSITIVE_PROCESS_ACCOUNTING")
    evidence=native["native_path_evidence"]
    if arm=="learned":
        need(evidence["original_native_scorer_invoked"] is True
             and evidence["edge_inverse_calls"]==12
             and evidence["graph_work"]["max_active"]<=7
             and evidence["graph_work"]["max_retained"]<=9,
             "NATIVE_LEARNED_REAL_CALL")
    return {"schema":"mass.f124bk.same-public-native-graph-fresh-process.v1",
            "arm":arm,"tag":tag,"native_execution":native,
            "task_CPU_ns_including_source_import_fit_and_graph_score":cpu,
            "whole_process_peak_RSS_bytes":peak,
            "runtime_identity":{"python":sys.version,"os":platform.platform()},
            "train_executed_in_child":False,
            "native_scoring_on_unseen_U_R":False,
            "complete_scientific_resource_parity":False}


def aggregate(samples):
    need(len(samples)==2*2*REPEATS,"SAMPLE_COUNT")
    results={}
    for tag in TAGS:
        arms={}
        for arm in ARMS:
            obs=[x for x in samples if x["tag"]==tag and x["arm"]==arm]
            need(len(obs)==REPEATS,"REPETITION_COUNT")
            cpu=[x["task_CPU_ns_including_source_import_fit_and_graph_score"]
                 for x in obs]
            rss=[x["whole_process_peak_RSS_bytes"] for x in obs]
            pub={x["native_execution"]["same_public_48_sha256"] for x in obs}
            graph={x["native_execution"]["same_public_graph_sha256"] for x in obs}
            need(len(pub)==len(graph)==1,"NONDETERMINISTIC_PUBLIC")
            arms[arm]={"cpu_ns_samples":cpu,"rss_bytes_samples":rss,
                       "median_CPU_ns":int(statistics.median(cpu)),
                       "median_peak_RSS_bytes":int(statistics.median(rss)),
                       "same_public_sha256":next(iter(pub)),
                       "same_graph_sha256":next(iter(graph)),
                       "native_invoked_each":[x["native_execution"][
                           "native_path_evidence"]["original_native_scorer_invoked"]
                           for x in obs],
                       "native_work":[x["native_execution"][
                           "native_path_evidence"].get("graph_work") for x in obs]}
        need(arms["AZ"]["same_public_sha256"]==
             arms["learned"]["same_public_sha256"] and
             arms["AZ"]["same_graph_sha256"]==
             arms["learned"]["same_graph_sha256"],
             "DIFFERENT_TASK_OR_GRAPH")
        results[tag]=arms
    for tag in TAGS:
        results[tag]["learned"]["median_cpu_plus_original_192_TRAIN_over_128_ns"] = (
            results[tag]["learned"]["median_CPU_ns"] +
            (TRAIN_CPU_NS+127)//128)
        results[tag]["learned"]["observed_train_and_task_peak_RSS_envelope_bytes"] = max(
            TRAIN_PEAK_RSS_BYTES,results[tag]["learned"]["median_peak_RSS_bytes"])
    return {"schema":"mass.f124bk.same-public-synthetic-native-resource.v1",
            "measured_task_types":"nonprotected_negative_engineering_only",
            "samples":len(samples),
            "repeats_per_arm_per_fixture":REPEATS,
            "separate_original_TRAIN_observation":{
                "provider_firstuse_head":TRAIN_FIRSTUSE,
                "CPU_ns":TRAIN_CPU_NS,
                "max_RSS_bytes":TRAIN_PEAK_RSS_BYTES,
                "forward_evaluations":TRAIN_EVALS,
                "original_receipt_digest_from_stdout":TRAIN_RECEIPT_SHA256,
                "complete_original_raw_firstuse_receipt_archived":False,
                "original_TRAIN_replayed":False,
                "amortized_CPU_ns_per_128_ceiling":(TRAIN_CPU_NS+127)//128},
            "arms":results,
            "platform_identity_comparable_with_original_TRAIN":"NOT_PROVEN",
            "U_R_authentic_graphs_executed":False,
            "resource_parity_authority":False,
            "two_novel_families_science_tested":False,
            "external_source_novelty_accepted":False,
            "positive_retention_tested":False,
            "hard_false_positive_acceptance_tested":False,
            "scientific_admission":False,
            "optimizer_promotion":False,
            "next_required":["resolve original TRAIN incomplete custody without replay",
                             "genuine source novelty independent scientific witness",
                             "freeze native graph evaluation source to match U/R",
                             "fully matched end-to-end scientific task including protected evaluation after admission"]
            }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--tag",choices=TAGS)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.child:
        need(a.arm is not None and a.tag is not None,"CHILD_ARGS")
        print(json.dumps(child(a.arm,a.tag),sort_keys=True))
        return
    need(a.output is not None and sys.platform=="linux","LINUX_OUTPUT")
    samples=[]
    for repeat in range(REPEATS):
        for tag in TAGS:
            arms=ARMS if repeat%2==0 else tuple(reversed(ARMS))
            for arm in arms:
                proc=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                                     "--child","--arm",arm,"--tag",tag],
                                     cwd=ROOT,capture_output=True,text=True,timeout=180)
                need(proc.returncode==0,"NATIVE_CHILD_"+arm+"_"+tag+
                     "_"+proc.stderr[-2000:].replace("\n","/"))
                data=json.loads(proc.stdout)
                need(not data["train_executed_in_child"],"TRAIN_REPLAY")
                samples.append(data)
    report={"summary":aggregate(samples),"raw_samples":samples}
    raw=json.dumps(report,sort_keys=True,indent=2)+"\n"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(raw,encoding="utf-8")
    print("F124BK_ORIGINAL_NATIVE_YGG_7_9_EXECUTION=PASS")
    print("F124BK_MATCHED_FULL_SYNTHETIC_TASK_RESOURCE_SAMPLES="+str(len(samples)))
    print("F124BK_TRAIN_REPLAY=false")
    print("F124BK_SCIENCE_RESOURCE_PARITY=false")
    print("F124BK_NATIVE_RESOURCE_SHA256="+hashlib.sha256(raw.encode()).hexdigest())


if __name__=="__main__":
    main()
