"""F124-BX NATURAL native work eligibility and full OS cost, no forced control.

Exact frozen BQ model, same source-neutral 40 FIT / 8 CHECK and paired
positive/hard graphs. AZ unmodified route is the ONLY admission authority.
A synthetic crossover may naturally admit both; if not, record and STOP.
Capture native input snapshots in a separate PREFLIGHT ONLY. OS budget
samples use no profiling instrumentation. Never replay scientific cases.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE=ROOT/"nativeevidence"
FIXTURE=HERE/"f124bx_nonregistered_native.py"
LEARNER=HERE/"f124bx_learned_flag.py"
VIEW=HERE/"f124br_native_view.py"
CASES=("BX-ENG-SWAP","BX-ENG-TWO-SHEAR")
ARMS=("AZ","learned")
REPS=5
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


def need(ok,reason):
    if not ok:raise RuntimeError("F124BX_NATURAL_"+reason)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"MODULE")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"))


def digest(obj):
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def bitvec(x):
    return [(x>>j)&1 for j in range(16)]


def run_child(case,arm,capture=False):
    need(sys.platform=="linux","ORIGINAL_LINUX_PROCESS")
    import resource
    need(case in CASES and arm in ARMS,"EXACT_TWO_SYNTHETIC_IDS")
    tic=time.process_time_ns()
    source=load("BU_nonregistered_source_crossover",FIXTURE)
    task,private_truth=source.make(case)
    need(private_truth["symbolic_positive_paths"]==1
         and private_truth["symbolic_hard_negative_paths"]==0,
         "SYNTHETIC_SOURCE_PRIVATE_TRUTH")
    public=task["FIT"]+task["CHECK"]
    graphs=(task["positive"],task["hard_negative"])
    source_hash=digest({"public":public,"positive":graphs[0],"negative":graphs[1]})
    unchanged=canon(graphs)
    demos=[{"input_bits":bitvec(x),"output_bits":bitvec(y)}
           for x,y in public] if arm=="AZ" else None
    sys.path.insert(0,str(NATIVE))
    import f124ag_transition_models as native
    records=[]
    native_code=native.ygg_transition.__code__
    def observe(frame,event,arg):
        if frame.f_code is native_code:
            if event=="call":
                records.append({"input":copy.deepcopy(frame.f_locals["g"])})
            elif event=="return":
                need(records and "output" not in records[-1],
                     "NATIVE_CAPTURE_STACK")
                need(type(arg) is tuple and len(arg)==4,"NATIVE_RETURN_SHAPE")
                records[-1]["output"]=arg
    if capture:
        sys.setprofile(observe)
    try:
        if arm=="AZ":
            import f124az_joint_public_inverse as az
            trained=az.train(demos,"BX_NONREGISTERED_SYNTHETIC_"+case,0)
            route=trained["choice"]
            need(route in ("abstain","affine","feistel"),"ORIGINAL_AZ_ROUTE")
            outcomes=[]
            for graph in graphs:
                val,work,diag=az.score(
                    graph,list(BASE),list(DELTA),trained,demos)
                outcomes.append({
                    "score":val,"work":work,
                    "abstained":diag.get("abstained",False)})
            genuine=sum(row["work"] is not None for row in outcomes)
            naturally_admitted=(route in ("affine","feistel")
                                and genuine==2
                                and not any(row["abstained"] for row in outcomes))
        else:
            model=load("BU_frozen_original_BQ_learned",LEARNER)
            original_parent=load("BX_immutable_original_BQ_parent",HERE/"f124bq_program_learner.py")
            learned,receipt,plausible=model.learn(task["FIT"],task["CHECK"],original_parent)
            route="BX_fit_selected_third_shear" if learned is not None else "abstain"
            naturally_admitted=bool(learned is not None and
                                    receipt["actual_packed_state_bits"]==32 and
                                    receipt["preselection_CHECK_used"] is False and
                                    receipt["confidence_CHECK_veto_only"])
            if naturally_admitted:
                choices=[model.causal_consensus(g,learned,plausible,original_parent)[0]
                         for g in graphs]
                view=load("BU_frozen_original_BT_native_view",VIEW)
                import types
                adapter=types.SimpleNamespace(
                    inverse=lambda y,p:model.inverse(y,p,original_parent))
                scored=view.score_exact_native_pair(
                    graphs,adapter,learned,native,BASE,DELTA)
                outcomes=[{"score":row["score"],"work":row["work"],
                           "raw":row["raw"],"ratio":row["ratio"]}
                          for row in scored]
                need(choices==[True,False],"CONFIDENT_POSITIVE_AND_HARD_DENIAL")
                expected_flag=1 if case=="BX-ENG-SWAP" else 0
                need(receipt["learned_structural_flag"]==expected_flag,
                     "FROZEN_FIT_ONLY_STRUCTURAL_FLAG_INCORRECT")
                genuine=len(scored)
            else:
                outcomes=[{"score":-1e9,"work":None}]*2
                genuine=0
        need(canon(graphs)==unchanged,"ORIGINAL_NATIVE_GRAPH_WAS_MUTATED")
    finally:
        if capture:
            sys.setprofile(None)
    need(genuine in (0,2),"PARTIAL_NATIVE_WORK_DISALLOWED")
    need(not capture or len(records)==genuine,
         "MEASURE_ACTUAL_NOT_FORCED_SCORER_CALLS")
    actual_work=[r["work"] for r in outcomes]
    cost_cpu=time.process_time_ns()-tic
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cost_cpu>0 and rss>0,"WHOLE_PROCESS_COST")
    result={
       "schema":"mass.f124bx.unchanged-policy-native-path-sample.v1",
       "case":case,"arm":arm,"route":route,
       "original_AZ_forced_routing":False,
       "public_pair_graph_sha256":source_hash,
       "native_calls":genuine,
       "natural_work_eligible":naturally_admitted,
       "native_work":actual_work,
       "native_score_and_work_sha256":digest([
           (x["score"],x["work"]) for x in outcomes]),
       "source_operator_passed_to_model":False,
       "CPU_process_ns":cost_cpu,
       "peak_OS_process_RSS_bytes":rss,
       "original_case_firstuse":False,
       "protected_case_firstuse":False,
       "scientific_acceptance":False,
       "allocator":(__import__("os").environ.get("PYTHONMALLOC") or "default")}
    if capture:
        result["native_input_graphs"]=[r["input"] for r in records]
        result["native_full_outputs"]=[r["output"] for r in records]
        result["native_call_input_hashes"]=[
            digest(r["input"]) for r in records]
        result["native_call_output_hashes"]=[
            digest(r["output"]) for r in records]
    return result


def preflight(rows):
    need(len(rows)==4,"TWO_CASES_TWO_FROZEN_ARMS")
    result={}
    for case in CASES:
        a=next(r for r in rows if r["case"]==case and r["arm"]=="AZ")
        b=next(r for r in rows if r["case"]==case and r["arm"]=="learned")
        need(a["public_pair_graph_sha256"]==b["public_pair_graph_sha256"],
             "EXACT_SAME_UNREGISTERED_TASK")
        route_ok=a["route"] in ("affine","feistel")
        admitted=bool(route_ok and a["native_calls"]==b["native_calls"]==2
                      and a["natural_work_eligible"] and b["natural_work_eligible"])
        matched=bool(admitted
                     and a["native_input_graphs"]==b["native_input_graphs"]
                     and a["native_full_outputs"]==b["native_full_outputs"]
                     and a["native_work"]==b["native_work"])
        result[case]={
            "AZ_original_natural_route":a["route"],
            "AZ_scored_original_two_graphs":a["native_calls"]==2,
            "learned_original_native_calls":b["native_calls"],
            "route_eligible_without_forcing":admitted,
            "identical_normalized_native_inputs_and_full_outputs":matched,
            "original_public_graph_sha256":a["public_pair_graph_sha256"],
            "AZ_native_call_input_hashes":a["native_call_input_hashes"],
            "BQ_native_call_input_hashes":b["native_call_input_hashes"],
            "AZ_native_call_output_hashes":a["native_call_output_hashes"],
            "BQ_native_call_output_hashes":b["native_call_output_hashes"]}
    return {
        "schema":"mass.f124bx.natural-native-match-preflight.v1",
        "registered_sources_created":0,
        "old_consumed_science_replayed":False,
        "original_AZ_routing_forced":False,
        "all_cases_naturally_eligible":all(
            x["route_eligible_without_forcing"] for x in result.values()),
        "all_cases_same_normalized_native_work":all(
            x["identical_normalized_native_inputs_and_full_outputs"]
            for x in result.values()),
        "source_neutral_only_not_scientific_admission":True,
        "cases":result,
    }


def measure(rows,prior):
    need(len(rows)==len(CASES)*len(ARMS)*REPS,"TWENTY_WHOLE_PROCESS_SAMPLES")
    reports={}
    for case in CASES:
        per={}
        for arm in ARMS:
            xs=[r for r in rows if r["case"]==case and r["arm"]==arm]
            need(len(xs)==REPS,"FIVE_INDEPENDENT_PROCESSES_PER_ARM")
            need(all(x["native_calls"]==2 and x["natural_work_eligible"]
                     and x["original_AZ_forced_routing"] is False
                     and x["public_pair_graph_sha256"]==
                        prior["cases"][case]["original_public_graph_sha256"]
                     and x["source_operator_passed_to_model"] is False
                     and x["original_case_firstuse"] is False
                     and x["protected_case_firstuse"] is False
                     for x in xs),
                 "AUTHENTIC_UNFORCED_NATIVE_EXECUTION_SAME_SOURCE")
            need(all(x["route"]==prior["cases"][case]["AZ_original_natural_route"]
                     for x in xs) if arm=="AZ" else
                 all(x["route"]=="BX_fit_selected_third_shear" for x in xs),
                 "NATURAL_ROUTE_CHANGED_AFTER_PREFLIGHT")
            need(len({x["native_score_and_work_sha256"] for x in xs})==1,
                 "NONDETERMINISTIC_FROZEN_NATIVE_RESULT")
            cpu=[x["CPU_process_ns"] for x in xs]
            rss=[x["peak_OS_process_RSS_bytes"] for x in xs]
            per[arm]={
                "CPU_samples_ns":cpu,"peak_RSS_samples_bytes":rss,
                "CPU_median_ns":statistics.median(cpu),
                "peak_RSS_median_bytes":statistics.median(rss),
                "peak_RSS_max_bytes":max(rss),
                "native_scoring_outcome_SHA256":xs[0]["native_score_and_work_sha256"],
                "allocator":xs[0]["allocator"]
            }
            need(all(x["allocator"]==("malloc" if arm=="learned" else "default")
                     for x in xs),"FROZEN_ENVIRONMENT_PER_ARM")
        need(per["AZ"]["native_scoring_outcome_SHA256"]==
             per["learned"]["native_scoring_outcome_SHA256"],
             "MATCHED_SAME_NATIVE_SCORE_AND_WORK")
        AZ=per["AZ"];BQ=per["learned"]
        per["same_work_full_OS_resource_noregression"]=bool(
            BQ["CPU_median_ns"]<=AZ["CPU_median_ns"]
            and BQ["peak_RSS_median_bytes"]<=AZ["peak_RSS_median_bytes"]
            and BQ["peak_RSS_max_bytes"]<=AZ["peak_RSS_max_bytes"])
        reports[case]=per
    return {
       "schema":"mass.f124bx.naturally-routed-matched-workload-process-cost.v1",
       "fresh_process_samples":len(rows),
       "natural_original_AZ_route":True,
       "never_forced_original_AZ_native_execution":True,
       "native_input_and_actual_native_work_matched":True,
       "whole_process_cost_per_case_nonregression":all(
           data["same_work_full_OS_resource_noregression"]
           for data in reports.values()),
       "nonregistered_synthetic_only":True,
       "BX_structural_sourceblind_branch_selection":True,
       "new_prospective_924xxx_925xxx_sources":False,
       "protected_cohorts_consumed":False,
       "real_scientific_generalization_accepted":False,
       "optimizer_policy_promoted":False,
       "case_results":reports
    }


def call_child(case,arm,original_capture):
    cmd=[sys.executable,"-B",str(Path(__file__).resolve()),
         "--child","--case",case,"--arm",arm]
    if original_capture:
        cmd.append("--capture")
    import os
    environ=(dict(os.environ,PYTHONMALLOC="malloc")
             if arm=="learned" else dict(os.environ))
    environ.pop("PYTHONMALLOC",None) if arm=="AZ" else None
    trial=subprocess.run(cmd,cwd=ROOT,env=environ,
                         text=True,capture_output=True,timeout=180)
    need(trial.returncode==0,
         "ORIGINAL_CHILD_FAILED_"+case+"_"+arm+":"+
         trial.stderr[-4000:])
    return json.loads(trial.stdout)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--case",choices=CASES)
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--capture",action="store_true")
    p.add_argument("--preflight",action="store_true")
    p.add_argument("--measure",action="store_true")
    p.add_argument("--eligibility",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.child:
        need(a.case is not None and a.arm is not None,"EXACT_CHILD")
        print(canon(run_child(a.case,a.arm,a.capture)))
        return
    need(a.out is not None and a.preflight!=a.measure,"ONE_MODE")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.preflight:
        attempts=[call_child(case,arm,True) for case in CASES for arm in ARMS]
        result=preflight(attempts)
    else:
        need(a.eligibility is not None and a.eligibility.is_file(),
             "REQUIRE_PRESERVED_ORIGINAL_PREFLIGHT")
        prior=json.loads(a.eligibility.read_text())
        need(prior["schema"]=="mass.f124bx.natural-native-match-preflight.v1"
             and prior["all_cases_naturally_eligible"] is True
             and prior["all_cases_same_normalized_native_work"] is True,
             "INELIGIBLE_STOP_BEFORE_RESOURCE")
        obs=[]
        for iteration in range(REPS):
            for case in CASES:
                arm_order=ARMS if iteration%2==0 else ARMS[::-1]
                for arm in arm_order:
                    obs.append(call_child(case,arm,False))
        result=measure(obs,prior)
        result["original_20_unreplayed_process_receipts"]=obs
    with a.out.open("x",encoding="utf8") as h:
        json.dump(result,h,sort_keys=True,indent=2)
        h.write("\n")
    if a.preflight:
        print("F124BX_REAL_UNFORCED_NATURAL_AZ_ROUTE="+
              str(result["all_cases_naturally_eligible"]))
        print("F124BX_NATIVE_INPUT_AND_WORK_EXACT="+
              str(result["all_cases_same_normalized_native_work"]))
    else:
        print("F124BX_REAL_WHOLE_PROCESS_MATCHED_WORK_NONREGRESSION="+
              str(result["whole_process_cost_per_case_nonregression"]))
        for case,detail in result["case_results"].items():
            for arm in ARMS:
                t=detail[arm]
                print("F124BX_"+case+"_"+arm+"_CPU_MEDIAN_NS="+
                      str(t["CPU_median_ns"]))
                print("F124BX_"+case+"_"+arm+"_RSS_MEDIAN="+
                      str(t["peak_RSS_median_bytes"]))
                print("F124BX_"+case+"_"+arm+"_RSS_MAX="+
                      str(t["peak_RSS_max_bytes"]))
    print("F124BX_REGISTERED_FIRSTUSE=false")
    print("F124BX_TRANSFER_SCIENCE_ACCEPTED=false")


if __name__=="__main__":
    main()
