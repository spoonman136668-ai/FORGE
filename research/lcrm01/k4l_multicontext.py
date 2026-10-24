#!/usr/bin/env python3
"""K4L: prospectively frozen decision-diverse public worlds and compressed memory.

Continue qualified K4I/K4K original FIT-only models, no threshold adjustment,
no first-use science, no unseen-data model selection.
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
    load as k4i_protocol, source_config, partition, information_support,
    train, predict, canonical)
from k4h_varied_worlds import (
    collect, paired_violations, observe_public_context, evaluate_plan)
from k4k_compression import make_models, checkpoints, make_plan, policy_choice, METHODS

FROZEN=Path(__file__).with_name("k4l_frozen_multicontext.json")
SCHEMA="mass.lcrm01.k4l.frozen-multicontext-actual-outcome-v1"

def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4l.frozen-multicontext-compression-and-coverage-v1":
        raise ValueError("K4L_UNFROZEN_SCHEMA")
    v=p["cohort"]["variants"]
    expected=[(dx,dy) for dx in (-.085,-.035,.035,.085) for dy in (-.05,0,.05)]
    expected += [(0,-.047),(0,.047)]
    expected += [(dx,dy) for dx in (-.072,-.012,.012,.072) for dy in (-.042,.042)]
    if (len(v)!=22 or [(x["goal_dx"],x["goal_dy"]) for x in v]!=expected or
        [(x["id"],x["phase"]) for x in v] != [
          (i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(22)]
        or p["cohort"]["seed"]!=877 or
        p["cohort"]["families"]!=["reaching","pushing"] or
        (p["cohort"]["FIT_episodes"],p["cohort"]["CHECK_episodes"],
         p["cohort"]["DEV_episodes"])!=(96,16,64) or
        p["methods"]!=list(METHODS)):
        raise ValueError("K4L_FROZEN_COHORT_OR_METHOD_DRIFT")
    # Do not reuse ANY prior FIT/CHECK/DEV source goal pair (even for new seeds).
    from k4j_replicate import frozen as k4j_frozen
    from k4k_compression import frozen as k4k_frozen
    old=k4i_protocol()["variants"]+k4j_frozen()["design"]["variants"]+k4k_frozen()["cohort"]["world_variants"]
    known={(x["goal_dx"],x["goal_dy"]) for x in old}
    if any((x["goal_dx"],x["goal_dy"]) in known for x in v):
        raise ValueError("K4L_PREVIOUS_SOURCE_COHORT_REUSED")
    return p

def environment(p):
    cfg=k4i_protocol()
    cfg["variants"]=p["cohort"]["variants"]
    cfg["world"]["seed"]=p["cohort"]["seed"]
    return cfg,source_config(cfg)

def resource_benchmark(np,models,full,contexts,plan):
    if len(contexts)!=20 or len(plan)!=20:
        raise ValueError("K4L_RESOURCE_COHORT_NOT_FROZEN")
    metrics={}
    for method in METHODS:
        cpu_start=time.process_time_ns()
        wall_start=time.perf_counter_ns()
        for repetition in range(200):
            for i,ctx in enumerate(contexts):
                predicted=policy_choice(np,models,full,ctx["family"],ctx["features"],method)
                if predicted!=plan[i]["choices"][method]:
                    raise ValueError("K4L_NONDETERMINISTIC_INFERENCE")
        metrics[method]={"CPU_ns":time.process_time_ns()-cpu_start,
             "wall_ns":time.perf_counter_ns()-wall_start,"calls":4000}
    return metrics

def decide(info,dev_scores,model_sizes,method_cost):
    pairs={}
    for family in ("reaching","pushing"):
        vals=[x for x in dev_scores if x["family"]==family]
        if len(vals)!=8:
            raise ValueError("K4L_INCOMPLETE_DEVELOPMENT_SOURCE")
        averages={m:float(sum(z["selected"][m]["reward"] for z in vals)/8)
                  for m in METHODS}
        selections={m:[z["selected"][m]["arm"] for z in vals] for m in METHODS}
        strict_counts={m:sum(z["selected"][m]["reward"] > z["selected"]["family_mean"]["reward"]
                    for z in vals) for m in METHODS}
        oracle=[max(range(4),key=lambda arm:(z["per_action_returns"][str(arm)],-arm))
                for z in vals]
        pairs[family]={
          "mean_public_reward":averages,
          "selected_action_by_context":selections,
          "strict_improved_vs_trained_constant":strict_counts,
          "offline_best_action_ids":oracle,
          "offline_best_action_diversity":len(set(oracle)),
          "FIT_best_action_diversity":len(info[family]["best_arm_ids"])}
    r=pairs["reaching"]
    means=r["mean_public_reward"]
    baseline=means["family_mean"]
    full_gain=means["full_12"]-baseline
    proposed=means["outcome_aware_4"]-baseline
    conventional=means["coverage_4"]
    sizes=model_sizes["outcome_aware_4"]/model_sizes["full_12"]
    cpu_ratio=method_cost["outcome_aware_4"]["CPU_ns"]/max(1,method_cost["full_12"]["CPU_ns"])
    tests={
      "FIT_has_multiple_best_actions":r["FIT_best_action_diversity"]>=2,
      "DEV_has_multiple_realized_best_actions":r["offline_best_action_diversity"]>=2,
      "full_reference_positive":full_gain>0,
      "compressed_gain_at_least_0_01":proposed>=.01,
      "preserves_90pct_full_positive_gain":full_gain>0 and proposed>=.90*full_gain,
      "strict_improvements_at_least_3_of_8":r["strict_improved_vs_trained_constant"]["outcome_aware_4"]>=3,
      "compressed_actions_vary":len(set(r["selected_action_by_context"]["outcome_aware_4"]))>=2,
      "beats_equal_capacity_coverage_by_0_01":means["outcome_aware_4"]-conventional>=.01,
      "checkpoint_ratio_le_0_50":sizes<=.50,
      "inference_CPU_ratio_le_0_65":cpu_ratio<=.65}
    return {
      "result":"K4L_BOUNDED_UNIQUE_CONTEXT_MEMORY_PARETO_POSITIVE" if all(tests.values())
          else "K4L_NOT_QUALIFIED_PRESERVE_FULL_NEGATIVE",
      "tests":tests,"reaching_baseline":baseline,"full_gain":full_gain,
      "compressed_gain":proposed,
      "outcome_aware_minus_coverage":means["outcome_aware_4"]-conventional,
      "checkpoint_byte_ratio":sizes,"inference_cpu_ratio":cpu_ratio,
      "per_family":pairs,"scientific_accepted":False,
      "first_use_authorized":False,"native_learning_claim":False}

def execute(repo,p):
    from k4a_control_replay import verify_source
    if p["source"]["CausalWorld_commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("K4L_UPSTREAM_SOURCE_DRIFT")
    root=repo.resolve();verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("K4L_UNPINNED_SOURCE_IMPORT")
    cfg,world=environment(p)
    start_wall=time.perf_counter();start_cpu=time.process_time()
    fit=collect(np,CausalWorld,generate_task,world,partition(cfg,"FIT"))
    fit_errors=paired_violations(fit,partition(cfg,"FIT"),world)
    info=information_support(fit,cfg)
    if fit_errors or info["reaching"]["unique_public_FIT_contexts"]!=12:
        raise ValueError("K4L_UNQUALIFIED_PUBLIC_FIT_STATE")
    output={"schema":SCHEMA,"gate":"LCRM01-K4L",
       "source_commit":p["source"]["CausalWorld_commit"],
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "FIT_exposures":len(fit),"FIT_rows":fit,"FIT_information_support":info,
       "CHECK_exposures":0,"DEV_exposures":0,
       "original_K4K_negative_preserved":True,
       "original_K4J_bounded_positive_preserved":True,
       "scientific_first_use":False,"scientific_accepted":False,"dispatch_authorized":False}
    if not info["reaching"]["action_ranking_diverse"]:
        output.update({"result":"FIT_ACTION_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
          "total_resource":{"cpu_seconds":time.process_time()-start_cpu,
           "wall_seconds":time.perf_counter()-start_wall,
           "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
        return output
    training_cpu=time.process_time();training_wall=time.perf_counter()
    fitted=train(np,fit,cfg)
    compressed=make_models(fitted)
    full=json.loads(canonical(fitted))
    if any(predict(np,fitted,r["family"],r["features"],arm,method)!=
           predict(np,full,r["family"],r["features"],arm,method)
           for r in fit for arm in range(4) for method in
             ("family_mean","raw_knn","ridge","fixed_low")):
        raise ValueError("MODEL_CHECKPOINT_RELOAD_NOT_REPRODUCIBLE")
    output.update({"shared_fitting_cpu_seconds":time.process_time()-training_cpu,
         "shared_fitting_wall_seconds":time.perf_counter()-training_wall,
         "model_checkpoint_sha256":hashlib.sha256(canonical(fitted).encode()).hexdigest(),
         "model_checkpoint_bytes":checkpoints(compressed,full),
         "checkpoint_retention_exact":True})
    # Frozen decisions from fresh read-only public reset probes, before outcome evaluation.
    check_contexts=[observe_public_context(np,CausalWorld,generate_task,world,f,v)
        for f in cfg["world"]["families"] for v in partition(cfg,"CHECK")]
    dev_contexts=[observe_public_context(np,CausalWorld,generate_task,world,f,v)
        for f in cfg["world"]["families"] for v in partition(cfg,"DEV")]
    all_contexts=check_contexts+dev_contexts
    check_plan=make_plan(np,compressed,full,check_contexts)
    dev_plan=make_plan(np,compressed,full,dev_contexts)
    cpu_cost=resource_benchmark(np,compressed,full,all_contexts,check_plan+dev_plan)
    check=collect(np,CausalWorld,generate_task,world,partition(cfg,"CHECK"))
    dev=collect(np,CausalWorld,generate_task,world,partition(cfg,"DEV"))
    if paired_violations(check,partition(cfg,"CHECK"),world) or paired_violations(
          dev,partition(cfg,"DEV"),world):
        raise ValueError("K4L_HOLDOUT_PUBLIC_START_DRIFT")
    check_scores=evaluate_plan(check,check_plan)
    dev_scores=evaluate_plan(dev,dev_plan)
    verify_source(root)
    result=decide(info,dev_scores,output["model_checkpoint_bytes"],cpu_cost)
    output.update({"result":"PUBLIC_DEVELOPMENT_COMPLETED",
       "CHECK_exposures":len(check),"DEV_exposures":len(dev),
       "CHECK_rows":check,"DEV_rows":dev,
       "CHECK_plan":check_plan,"DEV_plan":dev_plan,
       "CHECK_scores":check_scores,"DEV_scores":dev_scores,
       "method_inference_cpu_cost":cpu_cost,"quality_cost_decision":result,
       "total_resource":{"cpu_seconds":time.process_time()-start_cpu,
            "wall_seconds":time.perf_counter()-start_wall,
            "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return output

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--causalworld-repo",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    if x.output.exists() or not x.output.parent.is_dir():
        raise RuntimeError("OUTPUT_LOCATION_ALREADY_USED")
    try:result=execute(x.causalworld_repo,protocol())
    except Exception as e:
        result={"schema":SCHEMA,"gate":"LCRM01-K4L","result":"INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED",
            "error_type":type(e).__name__,"error":str(e),
            "traceback_tail":traceback.format_exc().splitlines()[-12:],
            "original_K4K_negative_preserved":True,
            "scientific_first_use":False,"scientific_accepted":False}
    x.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("K4L_RUN="+result["result"])
    if "quality_cost_decision" in result:
        q=result["quality_cost_decision"]
        print("K4L_SCIENTIFIC_DISPOSITION="+q["result"])
        print("K4L_REQUIREMENTS="+canonical(q["tests"]))
        print("K4L_FAMILY_EVIDENCE="+canonical(q["per_family"]))
        print("K4L_SAVING="+canonical({"model_ratio":q["checkpoint_byte_ratio"],
               "CPU_ratio":q["inference_cpu_ratio"]}))
    if "FIT_information_support" in result:
        print("K4L_FIT_WINNERS="+canonical({k:v["best_arm_ids"]
            for k,v in result["FIT_information_support"].items()}))
    return 1 if result["result"]=="INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED" else 0
if __name__=="__main__":
    sys.exit(main())
