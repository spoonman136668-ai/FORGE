"""F124-CC complete original-OS-process trained-arm native parity evaluator.

Only TWO predeclared, nonregistered mathematics fixtures. ALL FIVE trained
and original-policy arms observed without selecting favorable outcomes.
No protected first-use. Native input/score equality is read from actual
scorer calls under a PRE-FLIGHT ONLY profiler; per-process cost is obtained
from OS wait4 including interpreter, imports, full 40 FIT/8 CHECK training,
native scoring, and all process RSS. Never force an abstaining AZ route.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=HERE/"f124cc_new_source_neutral.py"
ARMS=("AZ","BQ","BX","BZ","CA","CB","CC")
CASES=("CC-ENG-01","CC-ENG-02")
REPS=5
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


def need(ok,msg):
    if not ok:raise RuntimeError("F124CC_PROVIDER_ORIGINAL_"+msg)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec is not None and spec.loader is not None,"MODULE_NOT_PRESENT")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def digest(value):
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()


def positive_decisions(graphs,word,decoder):
    decisions=[]
    for g in graphs:
        current=g["start"]
        carry=None
        matched=True
        for role in g["roles"]:
            edges=[e for e in g["edges"]
                   if e["from"]==current and e["role"]==role]
            if len(edges)!=1:
                matched=False
                break
            edge=edges[0]
            y=sum(bit<<i for i,bit in enumerate(edge["src_bits"]))
            x=decoder.inverse(y,word)
            if carry is not None and carry!=x:
                matched=False
                break
            carry=sum(bit<<i for i,bit in enumerate(edge["dst_bits"]))
            current=edge["to"]
        decisions.append(bool(matched and current==g["target"]))
    return decisions


def one(case,arm,capture):
    need(sys.platform=="linux" and case in CASES and arm in ARMS,
         "ONLY_EXACT_LINUX_NATIVE_SOURCE_NEUTRAL")
    src=load("CA_SNAPSHOT_ORIGIN",SOURCE)
    task,truth=src.make(case)
    need(truth["reserved_scientific_source_used"] is False
         and truth["protected_cohort_used"] is False,
         "PRIVATE_ORACLE_BOUNDARY")
    graphs=(task["positive"],task["hard_negative"])
    graph_sha=digest({"FIT":task["FIT"],"CHECK":task["CHECK"],"graphs":graphs})
    original=digest(graphs)
    sys.path.insert(0,str(ROOT/"nativeevidence"))
    import f124ag_transition_models as native
    observed=[]
    original_code=native.ygg_transition.__code__
    def trace(frame,event,arg):
        if frame.f_code is original_code:
            if event=="call":
                observed.append({"graph":copy.deepcopy(frame.f_locals["g"])})
            elif event=="return":
                need(observed and "result" not in observed[-1],
                     "NATIVE_ACTUAL_CALL_ORDER")
                observed[-1]["result"]=arg
    if capture:sys.setprofile(trace)
    route="abstain"
    calls=0
    decisions=[False,False]
    receipts={}
    try:
        if arm=="AZ":
            import f124az_joint_public_inverse as az
            demo=[{"input_bits":[(x>>i)&1 for i in range(16)],
                   "output_bits":[(y>>i)&1 for i in range(16)]}
                  for x,y in task["FIT"]+task["CHECK"]]
            trained=az.train(demo,"CA_NONREGISTERED",0)
            route=trained["choice"]
            outcomes=[az.score(g,list(BASE),list(DELTA),trained,demo)
                      for g in graphs]
            calls=sum(x[1] is not None for x in outcomes)
            decisions=[bool(x[0]>=0) for x in outcomes]
            receipts={"forced_AZ_native_route":False,
                      "actual_original_AZ_route":route}
        else:
            BQ=load("CA_original_BQ_frozen",HERE/"f124bq_program_learner.py")
            view=load("CA_original_native_view",HERE/"f124br_native_view.py")
            import types
            if arm=="BQ":
                prog,r,plausible=BQ.learn(task["FIT"],task["CHECK"])
                route="BQ" if prog is not None else "abstain"
                adapter=BQ
                if prog is not None:
                    decisions=[BQ.causal_consensus(g,prog,plausible)[0]
                               for g in graphs]
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="BX":
                BX=load("CA_frozen_BX",HERE/"f124bx_learned_flag.py")
                prog,r,plausible=BX.learn(task["FIT"],task["CHECK"],BQ)
                route="BX" if prog is not None else "abstain"
                adapter=types.SimpleNamespace(
                    inverse=lambda y,p:BX.inverse(y,p,BQ))
                if prog is not None:
                    decisions=[BX.causal_consensus(g,prog,plausible,BQ)[0]
                               for g in graphs]
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="BZ":
                BZ=load("CA_frozen_BZ",HERE/"f124bz_binding_candidate.py")
                prog,r=BZ.learn(task["FIT"],task["CHECK"])
                route="BZ" if prog is not None else "abstain"
                adapter=BZ
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="CA":
                CA=load("CB_frozen_trained_control",HERE/"f124ca_trained_symbol_control.py")
                prog,r=CA.train(task["FIT"],task["CHECK"])
                route="CA" if prog is not None else "abstain"
                adapter=CA
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="CB":
                CB=load("CC_unchanged_original_CB",HERE/"f124cb_dual_link_learner.py")
                prog,r=CB.learn(task["FIT"],task["CHECK"])
                route="CB" if prog is not None else "abstain"
                adapter=CB
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            else:
                CC=load("CC_independently_trained_two_link",HERE/"f124cc_trained_two_link_control.py")
                prog,r=CC.train(task["FIT"],task["CHECK"])
                route="CC" if prog is not None else "abstain"
                adapter=CC
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            if prog is not None:
                scored=view.score_exact_native_pair(
                    graphs,adapter,prog,native,BASE,DELTA)
                calls=len(scored)
        need(digest(graphs)==original,"SCIENTIFIC_GRAPH_INPUT_MUTATED")
    finally:
        if capture:sys.setprofile(None)
    if capture:need(calls==len(observed),"UNFORCED_NATIVE_PROFILER_ACCOUNTING")
    receipt={
        "schema":"mass.f124ca.original-sourceblind-native-v1",
        "case":case,"arm":arm,"source_task_sha256":graph_sha,
        "natural_route":route,"actual_native_calls":calls,
        "positive_accepted":bool(decisions[0]),
        "hard_false_positive":bool(decisions[1]),
        "source_family_label_used_by_learner":False,
        "private_oracle_passed_to_model":False,
        "source_neutral_not_sci_admission":True,
        "firstuse_924xxx_925xxx":False,
        "protected_128_cohorts_opened":False,
        "training":receipts
    }
    if capture:
        receipt["original_native_input_hashes"]=[
            digest(x["graph"]) for x in observed]
        receipt["original_native_full_output_hashes"]=[
            digest(x["result"]) for x in observed]
    return receipt


def measure_process(case,arm,capture=False):
    import resource
    args=[sys.executable,"-B",str(Path(__file__).resolve()),
          "--child","--case",case,"--arm",arm]
    if capture:args.append("--capture")
    env=dict(os.environ)
    if arm in ("BZ","CA","BX","CB","CC"):
        env["PYTHONMALLOC"]="malloc"
    else:
        env.pop("PYTHONMALLOC",None)
    # Temporary files prevent output buffering deadlock; wait4 captures
    # genuinely whole process (Python boot+imports+training+native scorer).
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        child=subprocess.Popen(args,cwd=ROOT,env=env,
                               stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(child.pid,0)
        need(pid==child.pid,"ORIGINAL_CHILD_PID")
        child.returncode=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        text=stdout.read();err=stderr.read()
        need(child.returncode==0,"REAL_PROCESS_"+case+"_"+arm+":"+err[-2200:])
    obj=json.loads(text)
    need(obj["case"]==case and obj["arm"]==arm
         and not obj["firstuse_924xxx_925xxx"]
         and not obj["protected_128_cohorts_opened"],
         "SOURCE_IDENTITY")
    obj["complete_process_cpu_ns"]=round(
        (usage.ru_utime+usage.ru_stime)*1e9)
    obj["complete_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    obj["complete_process_cpu_covers_boot_imports_training_and_native"]=True
    obj["allocator"]=env.get("PYTHONMALLOC","default")
    need(obj["complete_process_cpu_ns"]>0 and
         obj["complete_OS_peak_RSS_bytes"]>0,"VALID_FULL_PROCESS_COST")
    return obj


def overview(pre,samples):
    need(len(pre)==14 and len(samples)==70,
         "ALL_14_FIRST_NATIVE_PRELIGHT_AND_70_PROCESSES_REQUIRED")
    observed={}
    bypre={(row["case"],row["arm"]):row for row in pre}
    need(len(bypre)==14,"MISSING_OR_DUPLICATED_PREFLIGHT")
    negative={"hard_false_positives":[],"lost_control_positives":[],
              "no_equal_native_trained_control":[],
              "resource_regression":[],
              "all_seven_arm_natural_work_ineligible":[],
              "control_abstentions":[]}
    for case in CASES:
        orig={arm:bypre[case,arm] for arm in ARMS}
        need(len({r["source_task_sha256"] for r in orig.values()})==1,
             "MISMATCH_SAME_FROZEN_PUBLIC_SOURCE")
        cb=orig["CB"]
        cc=orig["CC"]
        strong_native=[
            arm for arm in ("BQ","BX","BZ","CA","CC")
            if cb["actual_native_calls"]==orig[arm]["actual_native_calls"]==2
            and cb.get("original_native_input_hashes")==
                orig[arm].get("original_native_input_hashes")
            and cb.get("original_native_full_output_hashes")==
                orig[arm].get("original_native_full_output_hashes")]
        all_seven_same=bool(
            orig["AZ"]["natural_route"] in ("affine","feistel")
            and cb["actual_native_calls"]==2
            and len(strong_native)==5)
        if cb["hard_false_positive"] or cc["hard_false_positive"]:
            negative["hard_false_positives"].append(case)
        if any(orig[arm]["positive_accepted"]
               and not cb["positive_accepted"]
               for arm in ("AZ","BQ","BX","BZ","CA","CC")):
            negative["lost_control_positives"].append(case)
        if not strong_native:
            negative["no_equal_native_trained_control"].append(case)
        if not all_seven_same:
            negative["all_seven_arm_natural_work_ineligible"].append(case)
        if any(x["natural_route"]=="abstain" for x in orig.values()):
            negative["control_abstentions"].append(case)
        stats={}
        for arm in ARMS:
            actual=[p for p in samples if p["case"]==case and p["arm"]==arm]
            need(len(actual)==REPS,
                 "EXACTLY_FIVE_WHOLE_CHILD_PROCESS_SAMPLES_PER_ARM")
            prior=orig[arm]
            expected_alloc="malloc" if arm in ("BZ","CA","BX","CB","CC") else "default"
            need(all(p["source_task_sha256"]==prior["source_task_sha256"]
                     and p["allocator"]==expected_alloc
                     and p["natural_route"]==prior["natural_route"]
                     and p["positive_accepted"]==prior["positive_accepted"]
                     and p["hard_false_positive"]==prior["hard_false_positive"]
                     and p["actual_native_calls"]==prior["actual_native_calls"]
                     for p in actual),"WHOLE_PROCESS_SOURCE_NATIVE_OR_DECISION_DRIFT")
            cpus=[p["complete_process_cpu_ns"] for p in actual]
            rss=[p["complete_OS_peak_RSS_bytes"] for p in actual]
            stats[arm]={
              "cpu_ns":cpus,"RSS_bytes":rss,
              "median_CPU_ns":statistics.median(cpus),
              "median_RSS_bytes":statistics.median(rss),
              "maximum_RSS_bytes":max(rss),
              "natural_route":prior["natural_route"],
              "positive_accepted":prior["positive_accepted"],
              "hard_false_positive":prior["hard_false_positive"],
              "actual_native_calls":prior["actual_native_calls"],
              "original_native_input_sha256":prior.get("original_native_input_hashes",[]),
              "original_native_full_output_sha256":prior.get("original_native_full_output_hashes",[])}
        target=stats["CB"]
        resource_ok=bool(strong_native and all(
            target["median_CPU_ns"]<=stats[arm]["median_CPU_ns"]
            and target["median_RSS_bytes"]<=stats[arm]["median_RSS_bytes"]
            and target["maximum_RSS_bytes"]<=stats[arm]["maximum_RSS_bytes"]
            for arm in strong_native))
        if strong_native and not resource_ok:
            negative["resource_regression"].append(case)
        observed[case]={
          "eligible_trained_same_native_controls":strong_native,
          "CC_same_real_native_work":("CC" in strong_native),
          "all_seven_original_native_work_matched":all_seven_same,
          "CB_resource_nonregression_vs_every_trained_same_native_control":resource_ok,
          "original_trained_arm_metrics":stats}
    full=bool(not any(negative.values())
              and all(v["CB_resource_nonregression_vs_every_trained_same_native_control"]
                      for v in observed.values()))
    return {
     "schema":"mass.f124cc.original-seven-trained-arms-70-complete-OS-process-v1",
     "preflight_original_14":pre,
     "whole_OS_process_original_70":samples,
     "cases":observed,
     "all_negative_and_native_ineligible_original_cases":negative,
     "full_seven_arm_scientific_resource_admission":full,
     "independent_external_source_authenticated":False,
     "scientific_firstuse_924xxx_925xxx":False,
     "both_128_protected_replication_cohorts_unopened":True,
     "science_accepted":False,"optimizer_promoted":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--child",action="store_true")
    ap.add_argument("--case",choices=CASES)
    ap.add_argument("--arm",choices=ARMS)
    ap.add_argument("--capture",action="store_true")
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.child:
        need(args.case is not None and args.arm is not None,"CHILD_ARGS")
        print(json.dumps(one(args.case,args.arm,args.capture),sort_keys=True))
        return
    need(args.out is not None,"RECEIPT_REQUIRED")
    pre=[measure_process(case,arm,True)
         for case in CASES for arm in ARMS]
    samples=[]
    for iteration in range(REPS):
        for case in CASES:
            for arm in (ARMS if iteration%2==0 else ARMS[::-1]):
                samples.append(measure_process(case,arm,False))
    report=overview(pre,samples)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf8") as out:
        json.dump(report,out,indent=2,sort_keys=True)
        out.write("\n")
    for case,d in report["cases"].items():
        print("F124CC_CASE="+case)
        print("F124CC_CC_SAME_ACTUAL_NATIVE_WORK="+str(d["CC_same_real_native_work"]))
        print("F124CC_ELIGIBLE_TRAINED_SAME_NATIVE_CONTROLS="+",".join(d["eligible_trained_same_native_controls"]))
        print("F124CC_ALL_SEVEN_NATIVE_MATCHED="+str(d["all_seven_original_native_work_matched"]))
        print("F124CC_CB_RESOURCE_NONREGRESSION="+str(d["CB_resource_nonregression_vs_every_trained_same_native_control"]))
        for arm,p in d["original_trained_arm_metrics"].items():
            print("F124CC_"+case+"_"+arm+"_CPU_MEDIAN_NS="+str(p["median_CPU_ns"]))
            print("F124CC_"+case+"_"+arm+"_RSS_MEDIAN_BYTES="+str(p["median_RSS_bytes"]))
            print("F124CC_"+case+"_"+arm+"_RSS_MAX_BYTES="+str(p["maximum_RSS_bytes"]))
    for key,v in report["all_negative_and_native_ineligible_original_cases"].items():
        print("F124CC_"+key.upper()+"="+str(len(v)))
    print("F124CC_RAW_WHOLE_PROCESS_COUNT=70")
    print("F124CC_SCIENTIFIC_RESOURCE_ADMISSION="+str(report["full_seven_arm_scientific_resource_admission"]))
    print("F124CC_PROTECTED_FIRSTUSE=FALSE")


if __name__=="__main__":
    main()
