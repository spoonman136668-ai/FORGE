"""F124-CB complete original-OS-process trained-arm native parity evaluator.

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
SOURCE=HERE/"f124cb_frozen_engineering_source.py"
ARMS=("AZ","BQ","BX","BZ","CA","CB")
CASES=("CB-ENG-01","CB-ENG-02")
REPS=5
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


def need(ok,msg):
    if not ok:raise RuntimeError("F124CB_PROVIDER_ORIGINAL_"+msg)


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
            else:
                CB=load("CB_precode_learned_two_link",HERE/"f124cb_dual_link_learner.py")
                prog,r=CB.learn(task["FIT"],task["CHECK"])
                route="CB" if prog is not None else "abstain"
                adapter=CB
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
    if arm in ("BZ","CA","BX","CB"):
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
         "ALL_12_PREFLIGHT_AND_60_REAL_PROCESSES_REQUIRED")
    observed={}
    bypre={(r["case"],r["arm"]):r for r in pre}
    need(len(bypre)==12,"ALL_SIX_ARMS_PER_CASE")
    failures={"hard_false_positives":[],"lost_trained_control_positive":[],
              "ineligible_original_native_work":[],"resource_regression":[],
              "no_eligible_trained_comparator":[],"control_abstentions":[]}
    for case in CASES:
        prior={arm:bypre[case,arm] for arm in ARMS}
        need(len({p["source_task_sha256"] for p in prior.values()})==1,
             "SAME_ORIGINAL_SOURCE_PER_EVERY_ARM")
        cb=prior["CB"]
        need(cb["source_neutral_not_sci_admission"]
             and not cb["firstuse_924xxx_925xxx"]
             and not cb["protected_128_cohorts_opened"],
             "NO_FROZEN_SCIENCE_USE")
        full_native_equal=bool(
            prior["AZ"]["natural_route"] in ("affine","feistel")
            and all(prior[a]["actual_native_calls"]==2 for a in ARMS)
            and all(prior[a]["original_native_input_hashes"]==
                    cb["original_native_input_hashes"] and
                    prior[a]["original_native_full_output_hashes"]==
                    cb["original_native_full_output_hashes"] for a in ARMS))
        eligible_competitors=[
            arm for arm in ("BQ","BX","BZ","CA")
            if cb["actual_native_calls"]==prior[arm]["actual_native_calls"]==2
            and cb["original_native_input_hashes"]==
                prior[arm]["original_native_input_hashes"]
            and cb["original_native_full_output_hashes"]==
                prior[arm]["original_native_full_output_hashes"]]
        if cb["hard_false_positive"]:
            failures["hard_false_positives"].append(case)
        if any(prior[a]["positive_accepted"]
               and not cb["positive_accepted"]
               for a in ("AZ","BQ","BX","BZ","CA")):
            failures["lost_trained_control_positive"].append(case)
        if not full_native_equal:
            failures["ineligible_original_native_work"].append(case)
        if not eligible_competitors:
            failures["no_eligible_trained_comparator"].append(case)
        if any(prior[a]["natural_route"]=="abstain" for a in ARMS):
            failures["control_abstentions"].append(case)
        summary={}
        for arm in ARMS:
            rows=[x for x in samples if x["case"]==case and x["arm"]==arm]
            need(len(rows)==REPS,"ALL_FIVE_TRUE_CHILDREN_PER_ARM_CASE")
            p=prior[arm]
            need(all(
                 row["source_task_sha256"]==p["source_task_sha256"]
                 and row["natural_route"]==p["natural_route"]
                 and row["actual_native_calls"]==p["actual_native_calls"]
                 and row["positive_accepted"]==p["positive_accepted"]
                 and row["hard_false_positive"]==p["hard_false_positive"]
                 and row["complete_process_cpu_covers_boot_imports_training_and_native"]
                 for row in rows),"ALL_REPRODUCED_NATIVE_WORK_AND_OUTCOMES")
            cpu=[x["complete_process_cpu_ns"] for x in rows]
            rss=[x["complete_OS_peak_RSS_bytes"] for x in rows]
            summary[arm]={
                "original_cpu_samples_ns":cpu,"original_peak_RSS_bytes":rss,
                "median_cpu_ns":statistics.median(cpu),
                "median_peak_RSS_bytes":statistics.median(rss),
                "max_peak_RSS_bytes":max(rss),
                "allocator":rows[0]["allocator"],
                "native_calls":p["actual_native_calls"],
                "positive_accepted":p["positive_accepted"],
                "hard_false_positive":p["hard_false_positive"]}
            need(all(x["allocator"]==("malloc" if arm in
                     ("BZ","CA","BX","CB") else "default") for x in rows),
                 "FROZEN_PER_ARM_ALLOCATOR")
        candidate=summary["CB"]
        equal_trained_cost=bool(
            eligible_competitors
            and all(candidate["median_cpu_ns"]<=summary[arm]["median_cpu_ns"]
                    and candidate["median_peak_RSS_bytes"]<=
                        summary[arm]["median_peak_RSS_bytes"]
                    and candidate["max_peak_RSS_bytes"]<=
                        summary[arm]["max_peak_RSS_bytes"]
                    for arm in eligible_competitors))
        if eligible_competitors and not equal_trained_cost:
            failures["resource_regression"].append(case)
        observed[case]={
            "all_six_actual_native_inputs_outputs_identical":full_native_equal,
            "trained_same_native_competitors":eligible_competitors,
            "full_whole_process_cost_noregression_vs_every_eligible_trained_control":equal_trained_cost,
            "original_arm_receipts":{arm:{
                "route":prior[arm]["natural_route"],
                "positive":prior[arm]["positive_accepted"],
                "hard_false_positive":prior[arm]["hard_false_positive"],
                "native_calls":prior[arm]["actual_native_calls"],
                "native_input_sha256":prior[arm].get("original_native_input_hashes",[]),
                "native_return_sha256":prior[arm].get("original_native_full_output_hashes",[])}
                for arm in ARMS},
            "arm_metrics":summary}
    admission=all(
        v["all_six_actual_native_inputs_outputs_identical"]
        and v["full_whole_process_cost_noregression_vs_every_eligible_trained_control"]
        for v in observed.values()) and not any(failures.values())
    return {
        "schema":"mass.f124cb.12-preflight-60-real-process-source-neutral.v1",
        "original_twelve_arm_preflights":pre,
        "original_sixty_whole_OS_process_measurements":samples,
        "both_frozen_cases":observed,
        "retained_negatives_and_ineligibilities":failures,
        "all_six_arm_native_and_resource_science_gate":bool(admission),
        "new_external_independent_source_authenticated":False,
        "science_firstuse_924xxx_925xxx":False,
        "protected_128x2_opened":False,
        "scientific_transfer_accepted":False,
        "optimizer_promoted":False}

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
    for case,x in report["both_frozen_cases"].items():
        print("F124CB_CASE="+case)
        print("F124CB_ALL_SIX_NATIVE_MATCHED="+str(
            x["all_six_actual_native_inputs_outputs_identical"]))
        print("F124CB_ELIGIBLE_TRAINED_CONTROLS="+
              ",".join(x["trained_same_native_competitors"]))
        print("F124CB_COMPLETE_PARITY_ALL_TRAINED="+str(
            x["full_whole_process_cost_noregression_vs_every_eligible_trained_control"]))
        for arm in ARMS:
            v=x["arm_metrics"][arm]
            print("F124CB_"+case+"_"+arm+"_CPU_MEDIAN_NS="+str(v["median_cpu_ns"]))
            print("F124CB_"+case+"_"+arm+"_RSS_MEDIAN_BYTES="+str(v["median_peak_RSS_bytes"]))
            print("F124CB_"+case+"_"+arm+"_RSS_MAX_BYTES="+str(v["max_peak_RSS_bytes"]))
    for label,cases in report["retained_negatives_and_ineligibilities"].items():
        print("F124CB_"+label.upper()+"="+str(len(cases)))
    print("F124CB_REAL_WHOLE_OS_PROCESS_RECEIPTS=60")
    print("F124CB_COMPLETE_SCIENTIFIC_RESOURCE_ADMISSION="+str(
        report["all_six_arm_native_and_resource_science_gate"]))
    print("F124CB_EXTERNAL_SCIENTIFIC_SOURCE_FIRSTUSE=false")


if __name__=="__main__":
    main()
