"""F124-CU authentic whole-Python-process source-blind sequence-cost ledger.

Each real process starts Python, imports NumPy, trains its full BPTT model on
identical source-born FIT/CHECK, and scores both public graphs. Five independent
processes per arm/case, no replay or source generation by observer.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASES=tuple(range(936000,936012))+tuple(range(937000,937012))
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
REPS=5

def need(ok,msg):
    if not ok:raise RuntimeError("F124CU_OS_"+msg)

def observe(file,arm,synthetic=False):
    need(sys.platform=="linux" and arm in ARMS,"COMPLETE_LINUX_WAIT4_ONLY")
    import resource
    cmd=[sys.executable,"-B",str(HERE/"f124cu_blind_sequence_eval.py"),
         "--public-case",str(file),"--arm",arm]
    if synthetic:cmd.append("--synthetic-engineering")
    env=dict(os.environ)
    env["OPENBLAS_NUM_THREADS"]="1";env["OMP_NUM_THREADS"]="1"
    env.pop("PYTHONPATH",None)
    for k in tuple(env):
        if k.startswith("F124CU_PRIVATE_") or k.startswith("F124CU_SOURCE_"):
            del env[k]
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"WAIT4_ORIGINAL_PROCESS_PID")
        p.returncode=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        output=stdout.read();error=stderr.read()
        need(p.returncode==0,"ORIGINAL_CHILD_FAILED_"+error[-1800:])
    row=json.loads(output)
    need(row["arm"]==arm and row["synthetic_engineering_only"] is synthetic,
         "ORIGINAL_SOURCE_FREE_PROCESSED_IDENTITY")
    row["full_OS_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    row["full_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    row["OS_measurement_includes_Python_start_NumPy_import_full_BPTT_and_scoring"]=True
    need(row["full_OS_CPU_ns"]>0 and row["full_OS_peak_RSS_bytes"]>0,
         "NONZERO_ORIGINAL_OS_MEASUREMENT")
    return row

def append(path,receipt):
    path=Path(path)
    need(path.parent.exists(),"EXISTING_RECEIPT_DIRECTORY")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    try:
        b=(json.dumps({"schema":"mass.f124cu.original-appended-whole-OS-process.v1",
                       "observation":receipt},sort_keys=True)+"\n").encode()
        need(os.write(fd,b)==len(b),"WHOLE_ATOMIC_LINE_APPEND")
        os.fsync(fd)
    finally:os.close(fd)

def review(preflights,samples):
    need(len(preflights)==72 and len(samples)==360,"EXACT_432_ORIGINAL_OBSERVATIONS")
    first={(x["case_id"],x["arm"]):x for x in preflights}
    need(len(first)==72 and all((case,arm) in first
               for case in CASES for arm in ARMS),"ALL_CASE_ARM_PREFLIGHTS")
    costs={}
    for case in CASES:
        for arm in ARMS:
            h=first[case,arm]
            rows=[x for x in samples if x["case_id"]==case and x["arm"]==arm]
            need(len(rows)==REPS and all(
              x["public_case_sha256"]==h["public_case_sha256"] and
              x["identical_native_public_graph_hashes"]==
                 h["identical_native_public_graph_hashes"] and
              x["identical_train_FIT_sha256"]==h["identical_train_FIT_sha256"] and
              x["identical_veto_CHECK_sha256"]==h["identical_veto_CHECK_sha256"] and
              x["natural_trained_admission"]==h["natural_trained_admission"] and
              x["native_complete_graph_calls"]==h["native_complete_graph_calls"] and
              x["native_event_count"]==h["native_event_count"] and
              x["correct_positive_and_hard_negative"]==
                 h["correct_positive_and_hard_negative"] and
              x["OS_measurement_includes_Python_start_NumPy_import_full_BPTT_and_scoring"] and
              x["full_OS_CPU_ns"]>0 and x["full_OS_peak_RSS_bytes"]>0
              for x in rows),"EACH_FIVE_ORIGINAL_COMPLETE_OS_PROCESSES")
            costs[(case,arm)]={
              "median_complete_CPU_ns":statistics.median(x["full_OS_CPU_ns"] for x in rows),
              "median_complete_peak_RSS_bytes":statistics.median(x["full_OS_peak_RSS_bytes"] for x in rows),
              "maximum_complete_peak_RSS_bytes":max(x["full_OS_peak_RSS_bytes"] for x in rows)}
    outcomes={}
    errors={"hard_false_positive":[],"lost_trained_or_reference_positive":[],
            "ineligible_natural_work":[],"naturally_abstained":[],"complete_OS_CPU_RSS_regression":[]}
    per_case=[]
    for family,ids in (("L",range(936000,936012)),("M",range(937000,937012))):
        cand=0;peer=0
        for case in ids:
            a,c,r=(first[case,k] for k in ARMS)
            need(a["public_case_sha256"]==c["public_case_sha256"]==
                 r["public_case_sha256"] and
                 a["identical_native_public_graph_hashes"]==
                 c["identical_native_public_graph_hashes"]==
                 r["identical_native_public_graph_hashes"] and
                 a["identical_train_FIT_sha256"]==c["identical_train_FIT_sha256"] and
                 a["identical_veto_CHECK_sha256"]==c["identical_veto_CHECK_sha256"],
                 "SAME_BORN_FULL_CAUSAL_EPISODES_FOR_EVERY_MODEL")
            equal=bool(a["natural_trained_admission"] and
                       c["natural_trained_admission"] and
                       a["native_complete_graph_calls"]==
                       c["native_complete_graph_calls"]==2 and
                       a["native_event_count"]==c["native_event_count"]==16)
            if not equal:errors["ineligible_natural_work"].append(case)
            if not a["natural_trained_admission"] or not c["natural_trained_admission"]:
                errors["naturally_abstained"].append(case)
            if a["hard_false_positive"]:errors["hard_false_positive"].append(case)
            if (c["positive_accepted"] or r["positive_accepted"]) and not a["positive_accepted"]:
                errors["lost_trained_or_reference_positive"].append(case)
            ca=costs[case,"CANDIDATE"];cb=costs[case,"TRAINED_CONTROL"]
            within=bool(equal and all(ca[key]<=cb[key] for key in
              ("median_complete_CPU_ns","median_complete_peak_RSS_bytes",
               "maximum_complete_peak_RSS_bytes")))
            if equal and not within:errors["complete_OS_CPU_RSS_regression"].append(case)
            cand+=int(a["correct_positive_and_hard_negative"])
            peer+=int(c["correct_positive_and_hard_negative"])
            per_case.append({"case_id":case,"natural_equal_native_work":equal,
                      "eligible_complete_cost_nonregression":within,
                      "all_arm_real_CPU_RSS":{arm:costs[case,arm] for arm in ARMS}})
        outcomes[family]={"candidate_correct_pairs":cand,
                          "fully_trained_control_correct_pairs":peer,
                          "net_gain":cand-peer}
    admitted=bool(all(x["net_gain"]>=2 for x in outcomes.values())
                  and not any(errors.values())
                  and all(q["eligible_complete_cost_nonregression"] for q in per_case))
    return {"schema":"mass.f124cu.original-readonly-preliminary-science.v1",
       "family_outcomes":outcomes,"failure_categories":errors,
       "natural_equal_native_work_cases":sum(x["natural_equal_native_work"] for x in per_case),
       "per_case_real_OS_cost":per_case,
       "preliminary_scientific_gate_met_before_independent_custody":admitted,
       "independent_original_source_custody_verified":False,
       "protected_firstuse":False,"scientific_acceptance":False}

if __name__=="__main__":
    raise SystemExit("INERT_OS_OBSERVER_NO_SOURCE_BIRTH_OR_RETRY")
