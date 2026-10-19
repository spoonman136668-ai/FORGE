"""F124-BY preserve ORIGINAL cost measurements for all 12 cases.

Even native-ineligible or structurally unrepresentable cases receive five
whole-process samples per arm, but may never count as matched parity.
Frozen original source neutral panel is downloaded from GitHub Actions;
model, source case, oracle and scientific resource thresholds unchanged.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARMS=("AZ","BX")
REPS=5


def need(ok,msg):
    if not ok:raise RuntimeError("F124BY_RESOURCE_"+msg)


def child(case,arm):
    tic=time.process_time_ns()
    mod=HERE/"f124by_classify.py"
    spec=importlib.util.spec_from_file_location("BY_cost_original",mod)
    obj=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=obj
    spec.loader.exec_module(obj)
    record=obj.classify_one(case,arm,False)
    cpu=time.process_time_ns()-tic
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0,"ACTUAL_OS_PROCESS_MEASUREMENT")
    return {
        "case":case,"arm":arm,"CPU_process_ns":cpu,
        "whole_peak_process_RSS_bytes":rss,
        "source_graph_SHA256":record["graph_source_sha256"],
        "route":record["route"],"native_calls":record["native_calls"],
        "positive_accepted":record["positive_accepted"],
        "hard_false_positive":record["hard_false_positive"],
        "allocator":(__import__("os").environ.get("PYTHONMALLOC") or "default"),
        "nonregistered_engineering_source_only":True,
        "protected_scientific_firstuse":False
    }


def summarize(samples,panel):
    cases=panel["cases"]
    need(len(cases)==12 and len(samples)==12*len(ARMS)*REPS,
         "ALL_120_RAW_PROCESS_SAMPLES_REQUIRED")
    summaries={}
    hard_fp=panel["counts"]["hard_false_positives"]
    lost=panel["counts"]["lost_BQ_baseline_positives"]
    gains=panel["counts"]["new_correct_pairs"]
    for case in cases:
        expected=cases[case]
        summaries[case]={}
        for arm in ARMS:
            obs=[p for p in samples if p["case"]==case and p["arm"]==arm]
            need(len(obs)==REPS,"FIVE_FRESH_SAMPLES_MANDATORY")
            need(all(p["source_graph_SHA256"]==
                     expected["same_public_input_sha256"]
                     and p["nonregistered_engineering_source_only"]
                     and p["protected_scientific_firstuse"] is False
                     and p["positive_accepted"]==expected[arm+"_positive"]
                     and p["hard_false_positive"]==expected[arm+"_hard_FP"]
                     and p["route"]==expected[arm+"_route"]
                     and p["allocator"]==
                         ("malloc" if arm=="BX" else "default")
                     for p in obs),
                 "EXACT_SOURCE_DECISION_UNFORCED_ROUTE_OR_ALLOCATOR_DRIFT")
            cpu=[p["CPU_process_ns"] for p in obs]
            rss=[p["whole_peak_process_RSS_bytes"] for p in obs]
            summaries[case][arm]={
                "CPU_process_ns":cpu,"RSS_process_bytes":rss,
                "CPU_median_ns":statistics.median(cpu),
                "RSS_median_bytes":statistics.median(rss),
                "RSS_max_bytes":max(rss),
                "native_calls":obs[0]["native_calls"]
            }
        matched=expected["same_actual_native_work_eligible"]
        az=summaries[case]["AZ"];bx=summaries[case]["BX"]
        passcost=bool(matched and
                      bx["CPU_median_ns"]<=az["CPU_median_ns"]
                      and bx["RSS_median_bytes"]<=az["RSS_median_bytes"]
                      and bx["RSS_max_bytes"]<=az["RSS_max_bytes"])
        summaries[case]["matched_natural_native_work"]=matched
        summaries[case]["resource_nonregression_admitted"]=passcost
        summaries[case]["disposition"]=(
           "MATCHED_SOURCE_NEUTRAL_CPU_RSS_PASS" if passcost
           else "MATCHED_SOURCE_NEUTRAL_CPU_RSS_FAIL" if matched
           else "NATURAL_NATIVE_WORK_INELIGIBLE_RETAIN_ALL_RAW_COSTS")
    fail=[k for k,v in summaries.items()
          if not v["resource_nonregression_admitted"]]
    return {
        "schema":"mass.f124by.all-12-compositions-complete-native-os-resources.v1",
        "all_120_raw_original_process_samples":samples,
        "all_12_cases_with_costs":summaries,
        "hard_false_positives":hard_fp,
        "lost_original_BQ_positive_cases":lost,
        "new_correct_pair_cases":gains,
        "original_all_12_source_arm_results_retained":True,
        "matched_native_resource_ineligible_or_failed_cases":fail,
        "joint_resource_gate":len(fail)==0,
        "joint_compositional_science_criteria":bool(
            len(hard_fp)==0 and len(lost)==0 and len(gains)>=3 and
            panel["distinct_new_correct_grammars"]>=2 and len(fail)==0),
        "independently_originated_new_scientific_sources":False,
        "protected_128x2_cohorts_used":False,
        "scientific_admission":False,
        "optimizer_policy_promotion":False,
        "no_post_outcome_seed_or_source_tuning":True
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--case")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.child:
        need(a.case and a.arm,"REQUIRED_CHILD")
        print(json.dumps(child(a.case,a.arm),sort_keys=True))
        return
    need(a.source is not None and a.out is not None,"PROVIDER_ORIGINAL_INPUTS")
    panel=json.loads(a.source.read_text())
    need(panel["schema"]=="mass.f124by.all-12-compositions-admission.v1"
         and len(panel["cases"])==12
         and len(panel["original_all_36_arm_results"])==36
         and panel["scientific_transfer_accepted"] is False,
         "ORIGINAL_ALL_36_PROVIDER_RESULTS")
    samples=[]
    for rep in range(REPS):
        for case in panel["cases"]:
            order=ARMS if rep%2==0 else ARMS[::-1]
            for arm in order:
                import os
                env=dict(os.environ)
                if arm=="BX":
                    env["PYTHONMALLOC"]="malloc"
                else:
                    env.pop("PYTHONMALLOC",None)
                run=subprocess.run(
                    [sys.executable,"-B",str(Path(__file__).resolve()),
                     "--child","--case",case,"--arm",arm],
                    cwd=ROOT,capture_output=True,text=True,
                    env=env,timeout=120)
                need(run.returncode==0,"ORIGINAL_FRESH_OS_PROCESS_"+case+arm+":"+run.stderr[-2000:])
                samples.append(json.loads(run.stdout))
    result=summarize(samples,panel)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    for case,v in result["all_12_cases_with_costs"].items():
        print("BY_RESOURCE_CASE="+case+
              " NATIVE_MATCH="+str(v["matched_natural_native_work"])+
              " RESOURCE_PASS="+str(v["resource_nonregression_admitted"]))
        for arm in ARMS:
            data=v[arm]
            print("BY_"+case+"_"+arm+"_CPU_MEDIAN_NS="+str(data["CPU_median_ns"]))
            print("BY_"+case+"_"+arm+"_RSS_MEDIAN_BYTES="+str(data["RSS_median_bytes"]))
            print("BY_"+case+"_"+arm+"_RSS_MAX_BYTES="+str(data["RSS_max_bytes"]))
    print("F124BY_ORIGINAL_FRESH_OS_PROCESS_SAMPLES="+str(len(samples)))
    print("F124BY_FULL_12_CASE_MATCHED_NATIVE_RESOURCE_ADMISSION="+str(result["joint_resource_gate"]))
    print("F124BY_SCIENTIFIC_INDEPENDENCE=false")


if __name__=="__main__":
    main()
