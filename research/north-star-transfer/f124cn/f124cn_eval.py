#!/usr/bin/env python3
"""F124CN public-development learning experiment, original E2 law not original first use.

The source-specific E2 oracle executes ONLY in this fixture parent. Each model
executes in a fresh OS process given public FIT/CHECK pairs and DEV INPUTS
without labels, source params, task family or source generator import.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import pathlib
import random
import subprocess
import sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ORIGINAL=ROOT/"research/north-star-transfer/f124cj_internal_source.py"
MODEL=HERE/"f124cn_model.py"
FROZEN=HERE/"FROZEN_PROTOCOL.json"
ORIGINAL_BLOB="4e7bbd8f93dab1c7242a9374c75731302b034f31"
ARMS=("stage","conventional_exact","nearest1","nearest5","constant")

def require(ok,why):
    if not ok:
        raise RuntimeError("F124CN_EXPERIMENT_DENIED_"+why)

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def source():
    out=subprocess.run(["git","hash-object",str(ORIGINAL.relative_to(ROOT))],
        cwd=ROOT,capture_output=True,text=True,check=True)
    require(out.stdout.strip()==ORIGINAL_BLOB,"ORIGINAL_SOURCE_GIT_DRIFT")
    spec=importlib.util.spec_from_file_location("F124CN_only_in_parent_source",ORIGINAL)
    require(spec is not None and spec.loader is not None,"SOURCE_MISSING")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def child(arm,public,restore=False):
    p=subprocess.run([sys.executable,"-B",str(MODEL),"--arm",arm]+(["--restore"] if restore else []),
       cwd=ROOT,input=json.dumps(public),capture_output=True,text=True,check=False)
    require(p.returncode==0,"CHILD_FAIL_"+arm+"_"+p.stderr[-1200:])
    return json.loads(p.stdout)

def run():
    frozen=json.loads(FROZEN.read_text())
    require(frozen["status"]=="FROZEN_BEFORE_IMPLEMENTATION_OR_NEW_FIXTURE_SOURCE_EXECUTION",
            "FROZEN_PROTOCOL_IDENTITY")
    orig=source()
    allrows=[]
    for i in range(16):
        rng=random.Random(10250000+i)
        xs=rng.sample(range(65536),112)
        par=[i,(5*i+1)%16,(9*i+2)%16,(7*i+3)%16]
        labels=[orig.E_forward(x,par)&15 for x in xs]
        fit=[[x,y] for x,y in zip(xs[:40],labels[:40])]
        check=[[x,y] for x,y in zip(xs[40:48],labels[40:48])]
        public={"FIT":fit,"CHECK":check,"dev":xs[48:]}
        true=labels[48:]
        rows={}
        for arm in ARMS:
            val=child(arm,public)
            preds=val["predictions"]
            require(len(preds)==64,"ALL_DEV_INPUTS_ACCOUNTED")
            if arm in ("stage","conventional_exact"):
                cold=child(arm,{"checkpoint":val["checkpoint_b64"],
                    "dev":xs[48:],"was_eligible":val["training"]["eligible"]},True)
                require(cold["predictions"]==preds and cold["cold_restarted"],
                    "SAME_ACTION_AFTER_INDEPENDENT_OS_RESTART")
            correct=sum(a==b for a,b in zip(preds,true))
            rows[arm]={"correct":correct,"total":64,"eligible":val["training"]["eligible"],
                       "train":val["training"],
                       "complete_child_cpu_ns":val["complete_child_cpu_ns"],
                       "peak_process_RSS_bytes":val["peak_process_RSS_bytes"],
                       "checkpoint_bytes":val["checkpoint_bytes"],
                       "cold_process_verified":arm in ("stage","conventional_exact")}
        allrows.append({"task_index":i,"arms":rows})
    totals={}
    for arm in ARMS:
        v=[t["arms"][arm] for t in allrows]
        totals[arm]={"total_correct":sum(z["correct"] for z in v),
                     "total":1024,
                     "train_ready_cases":sum(z["eligible"] for z in v),
                     "total_fit_examples":640,"total_check_veto_only":128,
                     "measured_process_cpu_ns_sum":sum(z["complete_child_cpu_ns"] for z in v),
                     "max_observed_process_RSS_bytes":max((z["peak_process_RSS_bytes"] or 0) for z in v),
                     "checkpoint_bytes_per_task":[z["checkpoint_bytes"] for z in v],
                     "cold_os_restart_qualified_cases":sum(z["cold_process_verified"] for z in v)}
    science={"classification":"DERIVED_ORIGINAL_SOURCE_LAW_TRAIN_ONLY_NOT_PROSPECTIVE_ORIGINAL_WORLD",
             "schema":"forge.itd02.f124cn.development_compositional_learning.v1",
             "source_original_git_blob":ORIGINAL_BLOB,
             "source_private_params_passed_to_learner":False,
             "original_born_E2F2_930_931_cases_or_replication_opened":False,
             "new_external_original_world_steps":0,
             "preregistered_task_count":16,
             "all_task_results":allrows,
             "complete_arm_totals_without_nondeterministic_resources":{
                 a:{"total_correct":totals[a]["total_correct"],
                    "total":totals[a]["total"],
                    "train_ready_cases":totals[a]["train_ready_cases"],
                    "cold_restart":totals[a]["cold_os_restart_qualified_cases"]}
                 for a in ARMS},
             "FSA_scientific_firstuse":False,
             "native_wingless_yggdrasil_scientific_superiority":"NOT_TESTED"}
    static_digest=hashlib.sha256(canonical({
       "task_arms":[{"task_index":t["task_index"],
                     "arms":{a:{"correct":t["arms"][a]["correct"],
                                 "eligible":t["arms"][a]["eligible"]}
                             for a in ARMS}} for t in allrows],
       "fixed_source_blob":ORIGINAL_BLOB
    })).hexdigest()
    return {"science":science,"totals":totals,"deterministic_science_sha256":static_digest,
            "resource_scope":"fresh Python child whole-process CPU, RSS on Linux (Windows RSS unavailable)",
            "optimizer_use":"original content-addressed reuse, prereg hypothesis discrimination, Pareto after frozen outcomes; all portfolio generator status unchanged",
            "learned_multistage_improved_native_science":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=pathlib.Path,required=True)
    args=p.parse_args()
    result=run()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("F124CN_SOURCE_LAW_ONLY_TRAINING=PASS")
    print("F124CN_EXACT_16_TASKS_5_ARMS_ALL_DEV=PASS")
    print("F124CN_SOURCE_PRIVATE_PARAMS_NOT_PASSED=PASS")
    print("F124CN_FSA_FIRSTUSE=DENIED")
    print("F124CN_DETERMINISTIC_SCIENCE_SHA256="+result["deterministic_science_sha256"])
    for arm in ARMS:
        z=result["totals"][arm]
        print("F124CN_"+arm+"_ACCURACY="+str(z["total_correct"])+"/1024")
        print("F124CN_"+arm+"_TRAIN_READY="+str(z["train_ready_cases"])+"/16")

if __name__=="__main__":
    main()
