"""F124-CN complete real OS process cost and source-neutral native parity.

Never constructs sources or imports hidden laws. A future, independently
authorized original evaluator may consume ONLY immutable public case files
born in a prior source-only job. Ineligible/abstained cases are retained.
Successful engineering observations do not constitute scientific acceptance.
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
ARMS=("CANDIDATE","TRAINED_CONTROL","PERSISTENCE_REFERENCE")
IDS=tuple(range(932000,932012))+tuple(range(933000,933012))
REPS=5

def need(ok,reason):
    if not ok:raise ValueError("F124CN_RESOURCE_"+reason)

def run_original_public_process(public_file,arm,synthetic=False):
    """Exactly one real Python process: startup + imports + FIT + scoring."""
    need(sys.platform=="linux" and arm in ARMS,"REQUIRES_LINUX_OS_PROCESS")
    import resource
    cmd=[sys.executable,"-B",str(HERE/"f124cn_blind_trajectory_eval.py"),
         "--public-file",str(public_file),"--arm",arm]
    if synthetic:cmd.append("--synthetic-engineering")
    env=dict(os.environ)
    env.pop("PYTHONPATH",None)
    for key in tuple(env):
        if key.startswith("F124CN_PRIVATE_") or key.startswith("F124CN_SOURCE_"):
            del env[key]
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(p.pid,0)
        need(pid==p.pid,"ORIGINAL_WAIT4_PID")
        p.returncode=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        output=stdout.read();error=stderr.read()
        need(p.returncode==0,"CHILD_FAIL_"+error[-2000:])
    data=json.loads(output)
    need(data["arm"]==arm and data["synthetic_engineering_only"] is synthetic,
         "NO_CHILD_SOURCE_OR_IDENTITY_DRIFT")
    data["whole_OS_process_CPU_ns"]=round((usage.ru_utime+usage.ru_stime)*1e9)
    data["whole_OS_process_peak_RSS_bytes"]=usage.ru_maxrss*1024
    data["whole_OS_boot_import_train_score_included"]=True
    need(data["whole_OS_process_CPU_ns"]>0 and data["whole_OS_process_peak_RSS_bytes"]>0,
         "REAL_OS_RESOURCE_OBSERVATION")
    return data

def append_journal(path,observation):
    path=Path(path)
    need(path.parent.exists(),"JOURNAL_PARENT_MUST_EXIST")
    flags=os.O_WRONLY|os.O_CREAT|os.O_APPEND
    fd=os.open(path,flags,0o600)
    try:
        payload=(json.dumps({"schema":"mass.f124cn.append-only-original-OS-measurement.v1",
                             "observation":observation},sort_keys=True)+"\n").encode()
        os.write(fd,payload)
        os.fsync(fd)
    finally:
        os.close(fd)

def review(preflights,samples):
    """Read-only aggregate; independent reviewer must verify original custody."""
    need(len(preflights)==len(IDS)*len(ARMS) and
         len(samples)==len(IDS)*len(ARMS)*REPS,"COMPLETE_ORIGINAL_ROSTER")
    pre={(r["case_id"],r["arm"]):r for r in preflights}
    need(len(pre)==len(preflights),"NO_DUPLICATE_PREFLIGHT")
    counted={(case,arm):[] for case in IDS for arm in ARMS}
    for s in samples:
        key=(s["case_id"],s["arm"])
        need(key in counted and s["whole_OS_boot_import_train_score_included"] 
             and s["whole_OS_process_CPU_ns"]>0
             and s["whole_OS_process_peak_RSS_bytes"]>0,
             "MEASURE_ONLY_FROZEN_REAL_OS_WORK")
        counted[key].append(s)
    need(all(len(v)==REPS for v in counted.values()),"FIVE_EACH")
    totals={"G":{"candidate_correct":0,"control_correct":0},
            "H":{"candidate_correct":0,"control_correct":0}}
    failures={"hard_false_positives":[],"lost_peer_or_reference_positive":[],
              "no_equal_native_work":[],"complete_CPU_RSS_regression":[],
              "natural_abstentions":[]}
    case_results=[]
    for case in IDS:
        a=pre[case,"CANDIDATE"];control=pre[case,"TRAINED_CONTROL"]
        reference=pre[case,"PERSISTENCE_REFERENCE"]
        need(len({x["public_task_sha256"] for x in (a,control,reference)})==1,
             "ALL_ARMS_SAME_PUBLIC_TASK")
        need(a["graph_sha256"]==control["graph_sha256"]==reference["graph_sha256"],
             "PUBLIC_NATIVE_GRAPH_IDENTITY")
        expected=a["expected_event_transition_calls_if_admitted"]
        native_equal=bool(a["natural_admission"] and control["natural_admission"]
                          and a["native_graph_score_calls"]==2
                          and control["native_graph_score_calls"]==2
                          and a["native_event_transition_calls"]==expected
                          and control["native_event_transition_calls"]==expected)
        if not native_equal:failures["no_equal_native_work"].append(case)
        if not a["natural_admission"] or not control["natural_admission"]:
            failures["natural_abstentions"].append(case)
        if a["hard_false_positive"]:failures["hard_false_positives"].append(case)
        if (control["positive_accepted"] or reference["positive_accepted"]) and not a["positive_accepted"]:
            failures["lost_peer_or_reference_positive"].append(case)
        fam="G" if case<933000 else "H"
        totals[fam]["candidate_correct"]+=int(a["correct_pair"])
        totals[fam]["control_correct"]+=int(control["correct_pair"])
        cost={}
        for arm in ARMS:
            rows=counted[case,arm];start=pre[case,arm]
            need(all(s["public_task_sha256"]==start["public_task_sha256"]
                     and s["graph_sha256"]==start["graph_sha256"]
                     and s["natural_admission"]==start["natural_admission"]
                     and s["native_graph_score_calls"]==start["native_graph_score_calls"]
                     and s["native_event_transition_calls"]==start["native_event_transition_calls"]
                     and s["correct_pair"]==start["correct_pair"] for s in rows),
                 "ORIGINAL_PROCESS_OUTCOME_DRIFT")
            cost[arm]={"median_cpu_ns":statistics.median(s["whole_OS_process_CPU_ns"] for s in rows),
                       "median_peak_RSS_bytes":statistics.median(s["whole_OS_process_peak_RSS_bytes"] for s in rows),
                       "max_peak_RSS_bytes":max(s["whole_OS_process_peak_RSS_bytes"] for s in rows)}
        ca=cost["CANDIDATE"];cc=cost["TRAINED_CONTROL"]
        budget=bool(native_equal and ca["median_cpu_ns"]<=cc["median_cpu_ns"]
                    and ca["median_peak_RSS_bytes"]<=cc["median_peak_RSS_bytes"]
                    and ca["max_peak_RSS_bytes"]<=cc["max_peak_RSS_bytes"])
        if native_equal and not budget:failures["complete_CPU_RSS_regression"].append(case)
        case_results.append({"case_id":case,"equal_native_work":native_equal,
                             "candidate_complete_resource_nonregression":budget,
                             "actual_OS_cost":cost})
    gains={name:x["candidate_correct"]-x["control_correct"] for name,x in totals.items()}
    eligible=bool(all(gain>=2 for gain in gains.values())
                 and not any(failures.values())
                 and all(r["candidate_complete_resource_nonregression"] for r in case_results))
    return {"schema":"mass.f124cn.preliminary-original-complete-review.v1",
            "family":totals,"gain_over_trained":gains,
            "failures":failures,"all_case_resources":case_results,
            "original_negative_retained":True,
            "whole_process_resource_observed":True,
            "scientific_criteria_met_in_preliminary_metrics":eligible,
            "independent_original_firstuse_custody_verified":False,
            "protected_replication_allowed":False,
            "science_accepted":False}

if __name__=="__main__":
    raise SystemExit("NO_AUTO_SOURCE_ORIGINAL_REPLAY_OR_MEASUREMENT")
