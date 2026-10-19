"""F124-CR complete real OS CPU/RSS native work accounting, no source birth.

A native route is eligible only if both trained arms naturally run both
identical PUBLIC graphs through same scorer with identical transition counts.
Never force abstentions, never call an ineligible resource case a PASS.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from collections import Counter

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROSTER=tuple(range(934000,934012))+tuple(range(935000,935012))
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
REPS=5

def need(ok,reason):
    if not ok:raise RuntimeError("F124CR_OS_"+reason)

def measure_case(path,arm,synthetic=False):
    need(sys.platform=="linux" and arm in ARMS,"LINUX_WHOLE_PROCESS_REQUIRED")
    import resource
    cmd=[sys.executable,"-B",str(HERE/"f124cr_blind_native.py"),
         "--public-case",str(path),"--arm",arm]
    if synthetic:cmd.append("--synthetic-engineering")
    env=dict(os.environ)
    env.pop("PYTHONPATH",None)
    for k in tuple(env):
        if k.startswith("F124CR_PRIVATE_") or k.startswith("F124CR_SOURCE_"):
            del env[k]
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"EXACT_OS_PID")
        p.returncode=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        content=stdout.read();error=stderr.read()
        need(p.returncode==0,"CHILD_FAILED_"+error[-1200:])
    row=json.loads(content)
    need(row["arm"]==arm and row["synthetic_engineering_only"] is synthetic,
         "SOURCE_NEUTRAL_CHILD_IDENTITY")
    row["complete_OS_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["complete_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["OS_measurement_includes_boot_import_fit_native_scoring"]=True
    need(row["complete_OS_CPU_ns"]>0 and row["complete_OS_peak_RSS_bytes"]>0,
         "VALID_WHOLE_PROCESS_COST")
    return row

def durable_append(path,observation):
    path=Path(path)
    need(path.parent.exists(),"APPEND_PARENT")
    fd=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
    try:
        output=(json.dumps({"schema":"mass.f124cr.original-append-only-os-receipt.v1",
                            "observation":observation},sort_keys=True)+"\n").encode()
        need(os.write(fd,output)==len(output),"COMPLETE_APPEND_WRITE")
        os.fsync(fd)
    finally:
        os.close(fd)

def summarize(preflights,samples):
    need(len(preflights)==72 and len(samples)==360,
         "ORIGINAL_72_PREFLIGHT_360_WHOLE_OS_SAMPLES")
    first={(x["case_id"],x["arm"]):x for x in preflights}
    need(len(first)==72 and all((case,arm) in first for case in ROSTER for arm in ARMS),
         "FULL_FROZEN_PREFLIGHT_ROSTER")
    cost={}
    for case in ROSTER:
        for arm in ARMS:
            head=first[case,arm]
            rows=[x for x in samples if x["case_id"]==case and x["arm"]==arm]
            need(len(rows)==REPS and all(
                 r["public_task_sha256"]==head["public_task_sha256"] and
                 r["native_public_input_sha256"]==head["native_public_input_sha256"] and
                 r["natural_model_admission"]==head["natural_model_admission"] and
                 r["native_graph_calls"]==head["native_graph_calls"] and
                 r["native_event_transition_calls"]==head["native_event_transition_calls"] and
                 r["positive_accepted"]==head["positive_accepted"] and
                 r["hard_false_positive"]==head["hard_false_positive"] and
                 r["OS_measurement_includes_boot_import_fit_native_scoring"] and
                 r["complete_OS_CPU_ns"]>0 and r["complete_OS_peak_RSS_bytes"]>0
                 for r in rows),"WHOLE_OS_REPETITIONS_NOT_COHERENT")
            cost[(case,arm)]={
              "median_CPU_ns":statistics.median(r["complete_OS_CPU_ns"] for r in rows),
              "median_peak_RSS_bytes":statistics.median(r["complete_OS_peak_RSS_bytes"] for r in rows),
              "max_peak_RSS_bytes":max(r["complete_OS_peak_RSS_bytes"] for r in rows)}
    cohorts={"J":list(range(934000,934012)),"K":list(range(935000,935012))}
    successes={}
    failures={"hard_false_positives":[],"lost_control_or_reference_positive":[],
              "unmatched_natural_native_work":[],"complete_CPU_RSS_regression":[],
              "natural_trained_abstentions":[]}
    full=[]
    for family,ids in cohorts.items():
        good=0;peer_good=0
        for case in ids:
            a,c,ref=[first[case,k] for k in ARMS]
            need(a["public_task_sha256"]==c["public_task_sha256"]==ref["public_task_sha256"] and
                 a["native_public_input_sha256"]==c["native_public_input_sha256"]==
                 ref["native_public_input_sha256"],"ACTUAL_IDENTICAL_PUBLIC_NATIVE_GRAPH")
            parity=bool(a["natural_model_admission"] and c["natural_model_admission"]
               and a["native_graph_calls"]==c["native_graph_calls"]==2
               and a["native_event_transition_calls"]==
                   c["native_event_transition_calls"]==
                   a["expected_complete_transition_calls"]==
                   c["expected_complete_transition_calls"])
            if not parity:failures["unmatched_natural_native_work"].append(case)
            if not a["natural_model_admission"] or not c["natural_model_admission"]:
                failures["natural_trained_abstentions"].append(case)
            if a["hard_false_positive"]:failures["hard_false_positives"].append(case)
            if (c["positive_accepted"] or ref["positive_accepted"]) and not a["positive_accepted"]:
                failures["lost_control_or_reference_positive"].append(case)
            ca,cb=cost[(case,"CANDIDATE")],cost[(case,"TRAINED_CONTROL")]
            budget=bool(parity and ca["median_CPU_ns"]<=cb["median_CPU_ns"] and
                        ca["median_peak_RSS_bytes"]<=cb["median_peak_RSS_bytes"] and
                        ca["max_peak_RSS_bytes"]<=cb["max_peak_RSS_bytes"])
            if parity and not budget:failures["complete_CPU_RSS_regression"].append(case)
            good+=int(a["correct_paired_causal_task"])
            peer_good+=int(c["correct_paired_causal_task"])
            full.append({"case_id":case,"native_parity_eligible":parity,
                         "complete_os_resource_nonregression_eligible_and_pass":budget,
                         "all_three_arms_complete_OS_cost":{arm:cost[(case,arm)] for arm in ARMS}})
        successes[family]={"candidate_pairs":good,"strongest_trained_pairs":peer_good,
                           "net_gain":good-peer_good}
    eligible=bool(all(s["net_gain"]>=2 for s in successes.values()) and
                  not any(failures.values()) and
                  all(row["complete_os_resource_nonregression_eligible_and_pass"] for row in full))
    return {"schema":"mass.f124cr.original-preliminary-scientific-observation.v1",
      "families":successes,"failures":failures,"all_24_case_costs":full,
      "all_original_native_preflights":72,"all_original_whole_OS_samples":360,
      "eligible_native_parity_cases":sum(q["native_parity_eligible"] for q in full),
      "candidate_development_criteria_met_before_independent_audit":eligible,
      "source_origin_internally_authored":True,
      "protected_opened":False,"independent_custody_verified":False,
      "resource_nonregression_claim_allowed_only_on_parity_eligible_cases":True,
      "science_accepted":False}

if __name__=="__main__":raise SystemExit("NO_ORIGINAL_AUTOMATIC_EVALUATION_OR_SOURCE_BIRTH")
