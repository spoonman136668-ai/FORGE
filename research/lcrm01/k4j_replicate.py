#!/usr/bin/env python3
"""K4J: independent-Python-process replication of the unchanged K4I 1-NN.

Prospective public CausalWorld cohort; no protected science admission.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
import traceback

from k4i_information_sufficiency import (
    load as k4i_load, source_config, partition, information_support,
    train, predict, choose, context_plan, evaluate, verdict,
    METHODS, canonical)
from k4h_varied_worlds import collect, paired_violations, observe_public_context

FROZEN=Path(__file__).with_name("k4j_frozen_replication.json")
SCHEMA="mass.lcrm01.k4j.original-independent-process-public-replication.v1"

def frozen():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4j.frozen-independent-replication-v1":
        raise ValueError("K4J_FROZEN_SCHEMA_UNVERIFIED")
    v=p["design"]["variants"]
    required=[(x,y) for x in (-.07,-.03,.03,.07) for y in (-.03,0,.03)]
    required += [(0,-.035),(0,.035),(-.055,-.015),(-.055,.015),(.055,-.015),(.055,.015)]
    if [(r["goal_dx"],r["goal_dy"]) for r in v]!=required or len(v)!=18 or [
       (r["id"],r["phase"]) for r in v]!=[(i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(18)]:
        raise ValueError("K4J_FROZEN_COHORT_DRIFT")
    if p["design"]["source_seed"]!=839 or p["design"]["process_count"]!=2 or (
        p["design"]["fit_count"],p["design"]["check_count"],p["design"]["dev_count"])!=(96,16,32):
        raise ValueError("K4J_SOURCE_BOUNDARY_MISMATCH")
    old=k4i_load()
    old_pairs={(x["goal_dx"],x["goal_dy"]) for x in old["variants"]}
    if any((r["goal_dx"],r["goal_dy"]) in old_pairs for r in v):
        raise ValueError("K4J_REUSED_CONSUMED_K4I_COHORT")
    return p

def config_from_frozen(p):
    q=k4i_load()
    q["world"]["seed"]=p["design"]["source_seed"]
    q["variants"]=p["design"]["variants"]
    return q,source_config(q)

def action_diversity_gate(info):
    r=info["reaching"]
    return r["unique_public_FIT_contexts"]==12 and len(r["best_arm_ids"])>=2

def timed_methods(np,state,contexts,plan):
    # Per-method inference accounting; shared environment and model fitting
    # remain separate common costs and cannot be allocated fairly.
    times={}
    for method in METHODS:
        elapsed=0;cpu=0
        for ctx in contexts:
            start=time.perf_counter_ns();start_cpu=time.process_time_ns()
            selected=choose(np,state,ctx["family"],ctx["features"],method)
            cpu += time.process_time_ns()-start_cpu
            elapsed += time.perf_counter_ns()-start
            matched=next(r for r in plan if r["family"]==ctx["family"] and r["variant"]==ctx["variant"])
            if selected!=matched["choices"][method]:
                raise ValueError("TIMED_POLICY_DISAGREES_WITH_FROZEN_DECISION")
        times[method]={"inference_cpu_ns":cpu,"inference_wall_ns":elapsed,
            "actual_inferences":len(contexts)}
    return times

def model_bytes(state):
    result={}
    for method in METHODS:
        if method=="fixed_low":
            payload={"method":method}
        elif method=="family_mean":
            payload={fam:r["mean"] for fam,r in state["by_family"].items()}
        elif method=="ridge":
            payload={fam:r["ridge"] for fam,r in state["by_family"].items()}
        elif method=="raw_knn":
            payload={fam:r["records"] for fam,r in state["by_family"].items()}
        else:
            payload={fam:{"records":r["records"],"feature_mean":r["feature_mean"],
                  "feature_scale":r["feature_scale"]} for fam,r in state["by_family"].items()}
        result[method]=len(canonical(payload).encode("utf-8"))
    return result

def primary_decision(info,dev_scored,p):
    reaching=[r for r in dev_scored if r["family"]=="reaching"]
    if len(reaching)!=4:
        raise ValueError("PRIMARY_UNFAMILIAR_COHORT_INCOMPLETE")
    per_case=[]
    for r in reaching:
        primary=r["selected"]["raw_knn"]
        control=r["selected"]["family_mean"]
        per_case.append({"variant":r["variant"],"raw_action":primary["arm"],
           "constant_action":control["arm"],"raw_real_return":primary["reward"],
           "constant_real_return":control["reward"],
           "gain":float(primary["reward"]-control["reward"])})
    margin=float(sum(z["gain"] for z in per_case)/4)
    improved=sum(z["gain"]>0 for z in per_case)
    varied=len({z["raw_action"] for z in per_case})>=2
    qualified=info["reaching"]["action_ranking_diverse"] and varied and improved>=2 and margin>=.01
    return {"primary_method":"raw_knn","fixed_control":"family_mean",
       "reaching_mean_gain":margin,"reaching_strict_improvements":improved,
       "raw_actions_context_dependent":varied,"cases":per_case,
       "result":"REACHING_BOUNDED_POSITIVE_IN_THIS_PROCESS" if qualified else "NO_GO_OR_WEAK_REPLICATION",
       "protected_scientific_acceptance":False}

def execute(repo,p):
    from k4a_control_replay import verify_source
    if p["source"]["upstream_commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("UPSTREAM_CUSTODY_FAILED")
    root=repo.resolve();verify_source(root)
    sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("CAUSALWORLD_IMPORT_DRIFT")
    historical,source=config_from_frozen(p)
    t=time.perf_counter();cpu=time.process_time()
    original_fit=collect(np,CausalWorld,generate_task,source,partition(historical,"FIT"))
    fit_errors=paired_violations(original_fit,partition(historical,"FIT"),source)
    if fit_errors:
        raise ValueError("FIT_IDENTICAL_START_FAILURE")
    info=information_support(original_fit,historical)
    basis={"schema":SCHEMA,"gate":"LCRM01-K4J",
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "source_commit":p["source"]["upstream_commit"],
       "FIT_exposures":len(original_fit),"FIT_rows":original_fit,
       "FIT_information_support":info,"FIT_custody_errors":fit_errors,
       "CHECK_exposures":0,"DEV_exposures":0,
       "scientific_first_use":False,"scientific_accepted":False,
       "original_K4I_outcome_preserved":True,"original_K4F_negative_preserved":True,
       "K4I_model_unchanged":True}
    if not action_diversity_gate(info):
        basis["result"]="FIT_INFORMATION_NOT_QUALIFIED_HOLDOUT_UNCONSUMED"
        basis["whole_run_cost"]={"CPU_seconds":time.process_time()-cpu,
          "wall_seconds":time.perf_counter()-t,
          "peak_rss_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
        return basis
    fit_t=time.perf_counter();fit_cpu=time.process_time()
    trained=train(np,original_fit,historical)
    fit_time=time.perf_counter()-fit_t
    fit_cpu_sec=time.process_time()-fit_cpu
    original_checkpoint=canonical(trained)
    loaded=json.loads(original_checkpoint)
    if any(predict(np,trained,r["family"],r["features"],arm,method)!=
           predict(np,loaded,r["family"],r["features"],arm,method)
           for r in original_fit for arm in range(4) for method in METHODS):
        raise ValueError("FITTED_SOURCE_CHECKPOINT_NOT_RETAINED")
    basis.update({"checkpoint_sha256":hashlib.sha256(original_checkpoint.encode()).hexdigest(),
         "checkpoint_bytes":len(original_checkpoint),"method_checkpoint_bytes":model_bytes(trained),
         "common_fit_cpu_seconds":fit_cpu_sec,"common_fit_wall_seconds":fit_time,
         "retention_exact":True})
    # Freeze all heldout actions from RESET-ONLY public information
    # before any corresponding real CHECK/DEV action reward is generated.
    check_context=[observe_public_context(np,CausalWorld,generate_task,source,f,v)
          for f in source["world"]["families"] for v in partition(historical,"CHECK")]
    dev_context=[observe_public_context(np,CausalWorld,generate_task,source,f,v)
          for f in source["world"]["families"] for v in partition(historical,"DEV")]
    check_plan=context_plan(np,loaded,historical,check_context)
    dev_plan=context_plan(np,loaded,historical,dev_context)
    cpu_times=timed_methods(np,loaded,check_context+dev_context,check_plan+dev_plan)
    check=collect(np,CausalWorld,generate_task,source,partition(historical,"CHECK"))
    check_errors=paired_violations(check,partition(historical,"CHECK"),source)
    check_score=evaluate(check,check_plan)
    dev=collect(np,CausalWorld,generate_task,source,partition(historical,"DEV"))
    dev_errors=paired_violations(dev,partition(historical,"DEV"),source)
    dev_score=evaluate(dev,dev_plan)
    verify_source(root)
    if check_errors or dev_errors:
        raise ValueError("CHECK_DEV_PAIRED_SOURCE_IDENTITY_DRIFT")
    # K4I conventional comparator, frozen upstream, plus preregistered primary.
    analysis=verdict(info,original_fit,dev,dev_score,[],historical)
    primary=primary_decision(info,dev_score,p)
    basis.update({"result":"COMPLETE_ONE_PROCESS_PUBLIC_DEV",
       "CHECK_exposures":len(check),"DEV_exposures":len(dev),
       "CHECK_rows":check,"DEV_rows":dev,
       "CHECK_plan":check_plan,"DEV_plan":dev_plan,
       "CHECK_scores":check_score,"DEV_scores":dev_score,
       "secondary_conventional_evidence":analysis,
       "primary_reaching_replication":primary,
       "method_inference_cost":cpu_times,
       "whole_run_cost":{"CPU_seconds":time.process_time()-cpu,
          "wall_seconds":time.perf_counter()-t,
          "peak_rss_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return basis

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--causalworld-repo",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("K4J_ORIGINAL_FILE_ALREADY_EXISTS")
    try:
        out=execute(args.causalworld_repo,frozen())
    except Exception as e:
        out={"schema":SCHEMA,"gate":"LCRM01-K4J",
            "result":"INFRASTRUCTURE_OR_SOURCE_FAILED",
            "error_type":type(e).__name__,"error":str(e),
            "traceback_tail":traceback.format_exc().splitlines()[-12:],
            "scientific_first_use":False,"scientific_accepted":False,
            "original_K4I_outcome_preserved":True}
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("K4J_PROCESS_RESULT="+out["result"])
    if out.get("primary_reaching_replication"):
        print("K4J_PRIMARY="+canonical(out["primary_reaching_replication"]))
    if out.get("FIT_information_support"):
        print("K4J_FIT_ACTION_WINNERS="+canonical({k:v["best_arm_ids"] for k,v in out["FIT_information_support"].items()}))
    return 1 if out["result"]=="INFRASTRUCTURE_OR_SOURCE_FAILED" else 0

if __name__=="__main__":
    sys.exit(main())
