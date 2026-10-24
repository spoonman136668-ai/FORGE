#!/usr/bin/env python3
"""K4K frozen prospective reward-aware compressed episodic memory.

Only fresh PUBLIC CausalWorld task-world configurations; no inference from
consumed K4J DEV records. Same unchanged K4I raw 1-NN predictor for all coresets.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
import traceback

from k4i_information_sufficiency import (
    load as k4i_load, source_config, partition, information_support, train,
    choose, predict, canonical)
from k4j_replicate import frozen as k4j_frozen
from k4h_varied_worlds import (
    collect, paired_violations, observe_public_context, evaluate_plan)

FROZEN=Path(__file__).with_name("k4k_frozen_compression.json")
SCHEMA="mass.lcrm01.k4k.original-cost-quality-development.v1"
METHODS=("outcome_aware_4","full_12","coverage_4","uniform_4",
         "family_mean","ridge","fixed_low")
MEMORY_METHODS=METHODS[:4]

def frozen():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4k.frozen-outcome-aware-compressed-episodic-memory-v1":
        raise ValueError("FROZEN_K4K_SCHEMA_DRIFT")
    cohorts=p["cohort"]
    expected=[(x,y) for x in (-.055,-.025,.025,.055) for y in (-.035,0,.035)]
    expected += [(0,-.045),(0,.045),(-.05,-.02),(-.05,.02),(.05,-.02),(.05,.02)]
    if ([(v["goal_dx"],v["goal_dy"]) for v in cohorts["world_variants"]]!=expected
        or [(v["id"],v["phase"]) for v in cohorts["world_variants"]]!=[
            (i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(18)]
        or cohorts["seed"]!=853 or
        (cohorts["fit_episode_count"],cohorts["check_episode_count"],
         cohorts["dev_episode_count"])!=(96,16,32) or
        p["models"]["capacity_per_action_per_family"]!=4):
        raise ValueError("K4K_FROZEN_COHORT_OR_MODEL_DRIFT")
    old=k4i_load()["variants"]+k4j_frozen()["design"]["variants"]
    seen={(v["goal_dx"],v["goal_dy"]) for v in old}
    if any((v["goal_dx"],v["goal_dy"]) in seen for v in cohorts["world_variants"]):
        raise ValueError("K4K_USED_PREVIOUSLY_CONSUMED_CONTEXT")
    return p

def source_settings(p):
    prior=k4i_load()
    prior["variants"]=p["cohort"]["world_variants"]
    prior["world"]["seed"]=p["cohort"]["seed"]
    return prior,source_config(prior)

def squared_distance(a,b):
    if len(a)!=128 or len(b)!=128:
        raise ValueError("PUBLIC_FEATURE_DIMENSION_DRIFT")
    return sum((x-y)*(x-y) for x,y in zip(a,b))

def select_four(records,mode):
    """Exactly four original FIT examples, no interpolation/synthetic rewards."""
    if len(records)!=12 or [r["variant"] for r in records]!=list(range(12)):
        raise ValueError("UNQUALIFIED_FIT_MEMORY_RECORDS")
    if mode=="uniform_4":
        positions=[0,3,6,9]
    elif mode=="coverage_4":
        positions=[0]
    elif mode=="outcome_aware_4":
        low=min(range(12),key=lambda i:(records[i]["y"],records[i]["variant"]))
        high=max(range(12),key=lambda i:(records[i]["y"],-records[i]["variant"]))
        positions=[low]
        if high!=low:
            positions.append(high)
    else:
        raise ValueError("UNFROZEN_MEMORY_COMPRESSOR")
    while len(positions)<4:
        options=[i for i in range(12) if i not in positions]
        if not options:raise ValueError("UNABLE_TO_COMPLETE_CORESET")
        chosen=max(options,key=lambda i:(min(squared_distance(
            records[i]["x"],records[j]["x"]) for j in positions),-records[i]["variant"]))
        positions.append(chosen)
    return [copy.deepcopy(records[i]) for i in sorted(positions)]

def make_models(original):
    if original.get("schema")!="mass.k4i.conventional-trained-state.v1":
        raise ValueError("FITTED_SOURCE_MODEL_WRONG")
    states={"full_12":original}
    for name in ("outcome_aware_4","coverage_4","uniform_4"):
        model=copy.deepcopy(original)
        for family in ("reaching","pushing"):
            for arm in range(4):
                model["by_family"][family]["records"][str(arm)]=select_four(
                  original["by_family"][family]["records"][str(arm)],name)
        states[name]=model
    # All retain the actual unchanged K4I armwise predictor.
    return states

def policy_choice(np,models,source,family,features,method):
    if method not in METHODS:
        raise ValueError("UNREGISTERED_COMPARISON_METHOD")
    if method in MEMORY_METHODS:
        return choose(np,models[method],family,features,"raw_knn")
    return choose(np,source,family,features,method)

def checkpoints(models,full):
    result={}
    for method in METHODS:
        if method in MEMORY_METHODS:
            payload={f:m["records"] for f,m in models[method]["by_family"].items()}
        elif method=="family_mean":
            payload={f:m["mean"] for f,m in full["by_family"].items()}
        elif method=="ridge":
            payload={f:m["ridge"] for f,m in full["by_family"].items()}
        else:
            payload={"method":"fixed_low"}
        result[method]=len(canonical(payload).encode("utf-8"))
    return result

def make_plan(np,models,full,contexts):
    output=[]
    for c in contexts:
        family=c["family"];feat=c["features"]
        decisions={method:policy_choice(np,models,full,family,feat,method)
                   for method in METHODS}
        output.append({"family":family,"variant":c["variant"],
            "public_observation_sha256":c["initial_observation_sha256"],
            "choices":decisions})
    return output

def inference_benchmark(np,models,full,contexts,plan,repetitions=200):
    if repetitions!=200 or len(contexts)!=12 or len(plan)!=12:
        raise ValueError("UNFROZEN_RESOURCE_BENCHMARK")
    elapsed={}
    for method in METHODS:
        started_cpu=time.process_time_ns()
        started_wall=time.perf_counter_ns()
        for _ in range(repetitions):
            for i,context in enumerate(contexts):
                act=policy_choice(np,models,full,context["family"],context["features"],method)
                if act!=plan[i]["choices"][method]:
                    raise ValueError("INFERENCE_CHECKPOINT_NOT_DETERMINISTIC")
        elapsed[method]={"CPU_ns":time.process_time_ns()-started_cpu,
                         "wall_ns":time.perf_counter_ns()-started_wall,
                         "decision_count":repetitions*len(contexts)}
    return elapsed

def evaluate_science(info,dev_score,model_sizes,inference,p):
    result={}
    for family in ("reaching","pushing"):
        rows=[r for r in dev_score if r["family"]==family]
        if len(rows)!=4:raise ValueError("INCOMPLETE_FROZEN_DEV_SCORE")
        means={m:sum(r["selected"][m]["reward"] for r in rows)/4 for m in METHODS}
        action_sequences={m:[r["selected"][m]["arm"] for r in rows] for m in METHODS}
        differences={m:means[m]-means["family_mean"] for m in MEMORY_METHODS}
        strict_counts={m:sum(r["selected"][m]["reward"]>
               r["selected"]["family_mean"]["reward"] for r in rows)
               for m in MEMORY_METHODS}
        result[family]={"method_mean_reward":means,"selected_actions":action_sequences,
            "gain_over_fit_mean":differences,"strict_case_gains":strict_counts,
            "FIT_winner_diversity":info[family]["action_ranking_diverse"]}
    reach=result["reaching"]
    full_gain=reach["gain_over_fit_mean"]["full_12"]
    compressed_gain=reach["gain_over_fit_mean"]["outcome_aware_4"]
    size_ratio=model_sizes["outcome_aware_4"]/model_sizes["full_12"]
    cpu_ratio=inference["outcome_aware_4"]["CPU_ns"]/max(1,inference["full_12"]["CPU_ns"])
    good=(reach["FIT_winner_diversity"] and full_gain>0 and
       compressed_gain>=.01 and compressed_gain>=.8*full_gain and
       reach["strict_case_gains"]["outcome_aware_4"]>=2 and
       len(set(reach["selected_actions"]["outcome_aware_4"]))>=2 and
       size_ratio<=.5 and cpu_ratio<=.65)
    return {"result":"BOUNDED_COMPRESSED_MEMORY_QUALITY_COST_POSITIVE" if good
        else "NO_QUALIFIED_COMPRESSION_PARETO_IMPROVEMENT",
        "primary_full_gain":full_gain,"primary_compressed_gain":compressed_gain,
        "primary_retained_fraction":compressed_gain/full_gain if full_gain>0 else None,
        "primary_checkpoint_byte_ratio":size_ratio,"primary_inference_cpu_ratio":cpu_ratio,
        "family_evidence":result,"native_architecture_claim":False,
        "scientific_accepted":False}

def execute(repo,p):
    from k4a_control_replay import verify_source
    if p["source"]["causalworld_commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("ORIGINAL_CW_SOURCE_DRIFT")
    root=repo.resolve();verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("WRONG_PUBLIC_SOURCE_IMPORT")
    prior,source=source_settings(p)
    first_wall=time.perf_counter();first_cpu=time.process_time()
    fit=collect(np,CausalWorld,generate_task,source,partition(prior,"FIT"))
    fit_errors=paired_violations(fit,partition(prior,"FIT"),source)
    info=information_support(fit,prior)
    if fit_errors or info["reaching"]["unique_public_FIT_contexts"]!=12:
        raise ValueError("FIT_PAIRED_SOURCE_NOT_QUALIFIED")
    basis={"schema":SCHEMA,"gate":"LCRM01-K4K",
         "result":"FIT_INFORMATION_CHECKED",
         "source_commit":p["source"]["causalworld_commit"],
         "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
         "FIT_exposures":len(fit),"FIT_rows":fit,"FIT_information_support":info,
         "CHECK_exposures":0,"DEV_exposures":0,
         "original_K4J_preserved":True,"scientific_first_use":False,
         "scientific_accepted":False,"dispatch_authorized":False}
    if not info["reaching"]["action_ranking_diverse"]:
        basis["result"]="FIT_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED"
        basis["total_shared_cost"]={"CPU_seconds":time.process_time()-first_cpu,
            "wall_seconds":time.perf_counter()-first_wall,
            "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
        return basis
    train_cpu=time.process_time();train_wall=time.perf_counter()
    trained=train(np,fit,prior)
    variants=make_models(trained)
    basis["shared_fit_cpu_seconds"]=time.process_time()-train_cpu
    basis["shared_fit_wall_seconds"]=time.perf_counter()-train_wall
    serialized=canonical(trained);full=json.loads(serialized)
    if any(predict(np,trained,r["family"],r["features"],arm,m)!=
           predict(np,full,r["family"],r["features"],arm,m)
           for r in fit for arm in range(4) for m in
              ("family_mean","raw_knn","ridge","fixed_low")):
        raise ValueError("SOURCE_FIT_RETENTION_MISMATCH")
    basis["original_full_checkpoint_sha256"]=hashlib.sha256(serialized.encode()).hexdigest()
    basis["checkpoint_bytes"]=checkpoints(variants,full)
    # Fresh heldout reset-only probes; all selections fixed before actual rewards.
    check_ctx=[observe_public_context(np,CausalWorld,generate_task,source,f,v)
          for f in prior["world"]["families"] for v in partition(prior,"CHECK")]
    dev_ctx=[observe_public_context(np,CausalWorld,generate_task,source,f,v)
          for f in prior["world"]["families"] for v in partition(prior,"DEV")]
    check_plan=make_plan(np,variants,full,check_ctx)
    dev_plan=make_plan(np,variants,full,dev_ctx)
    basis["per_method_inference_cost"]=inference_benchmark(np,variants,full,
        check_ctx+dev_ctx,check_plan+dev_plan)
    check=collect(np,CausalWorld,generate_task,source,partition(prior,"CHECK"))
    dev=collect(np,CausalWorld,generate_task,source,partition(prior,"DEV"))
    if paired_violations(check,partition(prior,"CHECK"),source) or paired_violations(
        dev,partition(prior,"DEV"),source):
        raise ValueError("HELDOUT_PAIRED_PUBLIC_RESET_IDENTITY_DRIFT")
    check_score=evaluate_plan(check,check_plan)
    dev_score=evaluate_plan(dev,dev_plan)
    verify_source(root)
    primary=evaluate_science(info,dev_score,basis["checkpoint_bytes"],
          basis["per_method_inference_cost"],p)
    basis.update({"result":"COMPLETE_PUBLIC_COMPRESSION_DEVELOPMENT",
       "CHECK_exposures":len(check),"DEV_exposures":len(dev),
       "CHECK_rows":check,"DEV_rows":dev,
       "CHECK_plan":check_plan,"DEV_plan":dev_plan,
       "CHECK_scores":check_score,"DEV_scores":dev_score,
       "science_quality_and_cost":primary,
       "total_shared_cost":{"CPU_seconds":time.process_time()-first_cpu,
          "wall_seconds":time.perf_counter()-first_wall,
          "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return basis

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--causalworld-repo",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("ORIGINAL_OUTPUT_MUST_BE_FRESH")
    try:r=execute(args.causalworld_repo,frozen())
    except Exception as exc:
        r={"schema":SCHEMA,"gate":"LCRM01-K4K","result":"RUNTIME_OR_SOURCE_BLOCKED",
            "type":type(exc).__name__,"error":str(exc),
            "traceback_tail":traceback.format_exc().splitlines()[-12:],
            "scientific_first_use":False,"scientific_accepted":False,
            "original_K4J_preserved":True}
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("K4K_STATUS="+r["result"])
    if "science_quality_and_cost" in r:
        q=r["science_quality_and_cost"]
        print("K4K_PRIMARY="+q["result"])
        print("K4K_QUALITY_AND_RESOURCE="+canonical({k:v for k,v in q.items() if k!="family_evidence"}))
        print("K4K_FAMILY_EVIDENCE="+canonical(q["family_evidence"]))
    if "FIT_information_support" in r:
        print("K4K_FIT_WINNERS="+canonical({k:x["best_arm_ids"] for k,x in r["FIT_information_support"].items()}))
    return 1 if r["result"]=="RUNTIME_OR_SOURCE_BLOCKED" else 0
if __name__=="__main__":
    sys.exit(main())
