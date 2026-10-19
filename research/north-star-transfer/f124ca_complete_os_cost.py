"""F124-CA complete original-OS-process trained-arm native parity evaluator.

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
SOURCE=HERE/"f124ca_nonregistered_binding.py"
ARMS=("AZ","BQ","BX","BZ","CA")
CASES=("CA-ENG-01","CA-ENG-02")
REPS=5
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


def need(ok,msg):
    if not ok:raise RuntimeError("F124CA_PROVIDER_ORIGINAL_"+msg)


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
    need(truth["private_oracle_never_model_input"] is True,
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
            else:
                CA=load("CA_trained_competitor",HERE/"f124ca_trained_symbol_control.py")
                prog,r=CA.train(task["FIT"],task["CHECK"])
                route="CA" if prog is not None else "abstain"
                adapter=CA
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
    if arm in ("BZ","CA","BX"):
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
    need(len(pre)==len(CASES)*len(ARMS)
         and len(samples)==len(CASES)*len(ARMS)*REPS,
         "ALL_10_PREFLIGHT_AND_50_GENUINE_PROCESS_OBSERVATIONS_REQUIRED")
    observed={}
    bypre={(r["case"],r["arm"]):r for r in pre}
    need(len(bypre)==10,"ONE_FIRSTUSE_PER_ARM_CASE")
    failures={"hard_false_positives":[],"lost_trained_control_positive":[],
              "ineligible_original_native_work":[],"resource_regression":[],
              "control_abstentions":[]}
    for case in CASES:
        prior={arm:bypre[case,arm] for arm in ARMS}
        need(len({p["source_task_sha256"] for p in prior.values()})==1,
             "SAME_TASK_FOR_ALL_FIVE_ARMS")
        az=prior["AZ"]
        ca=prior["CA"]
        bz=prior["BZ"]
        native_match=bool(az["natural_route"] in ("affine","feistel")
                          and all(prior[a]["actual_native_calls"]==2 for a in ARMS)
                          and all(prior[a]["original_native_input_hashes"]==
                                  az["original_native_input_hashes"] and
                                  prior[a]["original_native_full_output_hashes"]==
                                  az["original_native_full_output_hashes"]
                                  for a in ARMS))
        same_binding=bool(ca["actual_native_calls"]==bz["actual_native_calls"]==2
                          and ca["original_native_input_hashes"]==
                              bz["original_native_input_hashes"]
                          and ca["original_native_full_output_hashes"]==
                              bz["original_native_full_output_hashes"])
        if any(x["hard_false_positive"] for x in (ca,bz)):
            failures["hard_false_positives"].append(case)
        if ca["positive_accepted"] and not bz["positive_accepted"]:
            failures["lost_trained_control_positive"].append(case)
        if not native_match:
            failures["ineligible_original_native_work"].append(case)
        if any(x["natural_route"]=="abstain" for x in prior.values()):
            failures["control_abstentions"].append(case)
        summary={}
        for arm in ARMS:
            observed_arm=[r for r in samples if
                          r["arm"]==arm and r["case"]==case]
            need(len(observed_arm)==REPS,"FIVE_PER_ARM_CASE")
            p=prior[arm]
            need(all(r["source_task_sha256"]==p["source_task_sha256"]
                     and r["natural_route"]==p["natural_route"]
                     and r["positive_accepted"]==p["positive_accepted"]
                     and r["hard_false_positive"]==p["hard_false_positive"]
                     and r["actual_native_calls"]==p["actual_native_calls"]
                     for r in observed_arm),
                 "REPRODUCIBLE_SOURCE_TRAINING_NATIVE_DECISION")
            cpu=[r["complete_process_cpu_ns"] for r in observed_arm]
            rss=[r["complete_OS_peak_RSS_bytes"] for r in observed_arm]
            summary[arm]={
                "cpu_samples_ns":cpu,"peak_RSS_samples_bytes":rss,
                "median_cpu_ns":statistics.median(cpu),
                "median_peak_RSS_bytes":statistics.median(rss),
                "maximum_peak_RSS_bytes":max(rss),
                "naturally_trained":p["natural_route"]!="abstain",
                "genuine_native_calls":p["actual_native_calls"],
                "positive":p["positive_accepted"],
                "hard_FP":p["hard_false_positive"],
                "allocator":observed_arm[0]["allocator"]}
        competitor=summary["CA"];candidate=summary["BZ"]
        parity=bool(native_match
             and candidate["median_cpu_ns"]<=competitor["median_cpu_ns"]
             and candidate["median_peak_RSS_bytes"]<=competitor["median_peak_RSS_bytes"]
             and candidate["maximum_peak_RSS_bytes"]<=competitor["maximum_peak_RSS_bytes"])
        if not parity and native_match:
            failures["resource_regression"].append(case)
        observed[case]={
            "source_task_sha256":az["source_task_sha256"],
            "actual_native_work_all_5_same":native_match,
            "actual_native_work_BZ_CA_same":same_binding,
            "BZ_full_cost_nonregression_vs_CA":parity,
            "arm_metrics":summary}
    all_pass=bool(not any(failures.values()) and
                  all(v["BZ_full_cost_nonregression_vs_CA"] for v in observed.values()))
    return {
       "schema":"mass.f124ca.complete-original-five-trained-arms.v1",
       "preflight_raw_original_10":pre,
       "full_OS_process_original_50":samples,
       "cases":observed,
       "negative_or_ineligible_cases":failures,
       "all_source_neutral_equal_training_resource_eligible":all_pass,
       "newly_independent_original_sources_authenticated":False,
       "reserved_development_FIT_firstuse":False,
       "protected_cohorts_consumed":False,
       "science_accepted":False,"optimizer_promoted":False
    }


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
    for case,x in report["cases"].items():
        print("F124CA_CASE="+case)
        print("F124CA_ALL_NATIVE_WORK_MATCHED="+str(x["actual_native_work_all_5_same"]))
        print("F124CA_BZ_CA_NATIVE_WORK_MATCHED="+str(x["actual_native_work_BZ_CA_same"]))
        for arm in ARMS:
            a=x["arm_metrics"][arm]
            print("CA_"+case+"_"+arm+"_CPU_MEDIAN_NS="+str(a["median_cpu_ns"]))
            print("CA_"+case+"_"+arm+"_RSS_MEDIAN_BYTES="+str(a["median_peak_RSS_bytes"]))
            print("CA_"+case+"_"+arm+"_RSS_MAX_BYTES="+str(a["maximum_peak_RSS_bytes"]))
        print("F124CA_"+case+"_RESOURCE_NONREGRESSION="+str(
            x["BZ_full_cost_nonregression_vs_CA"]))
    print("F124CA_RAW_OS_PROCESS_SAMPLES="+str(len(samples)))
    print("F124CA_COMPLETE_SCIENTIFIC_COST_QUALIFIED="+str(
        report["all_source_neutral_equal_training_resource_eligible"]))
    print("F124CA_NEW_UNSEEN_SCIENTIFIC_FIRSTUSE=false")


if __name__=="__main__":
    main()
