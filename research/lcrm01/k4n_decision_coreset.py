#!/usr/bin/env python3
"""K4N: prospectively frozen FIT-only decision-fidelity memory selection.

Continue qualified K4I/K4K original FIT-only models, no threshold adjustment,
no first-use science, no unseen-data model selection.
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
    load as k4i_protocol, source_config, partition, information_support,
    train, predict, choose, canonical)
from k4h_varied_worlds import (
    collect, paired_violations, observe_public_context, evaluate_plan)
from k4k_compression import make_models, checkpoints as k4k_checkpoints, policy_choice as k4k_choice

FROZEN=Path(__file__).with_name("k4n_frozen_decision_coreset.json")
SCHEMA="mass.lcrm01.k4n.original-fit-decision-fidelity-development.v1"
METHODS=("fit_fidelity_4","coverage_4","outcome_aware_4","uniform_4",
         "full_12","family_mean","ridge","fixed_low")

def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4n.frozen-fit-decision-fidelity-coreset.v1":
        raise ValueError("K4N_UNFROZEN_SCHEMA")
    v=p["cohort"]["variants"]
    expected=[(dx,dy) for dx in (-.095,-.045,.045,.095) for dy in (-.060,0,.060)]
    expected += [(0,-.057),(0,.057)]
    expected += [(dx,dy) for dx in (-.088,-.018,.018,.088) for dy in (-.052,.052)]
    if (len(v)!=22 or [(x["goal_dx"],x["goal_dy"]) for x in v]!=expected or
        [(x["id"],x["phase"]) for x in v] != [
          (i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(22)]
        or p["cohort"]["seed"]!=907 or
        p["cohort"]["families"]!=["reaching","pushing"] or
        (p["cohort"]["FIT_episodes"],p["cohort"]["CHECK_episodes"],
         p["cohort"]["DEV_episodes"])!=(96,16,64) or
        p["methods"]!=list(METHODS)):
        raise ValueError("K4N_FROZEN_COHORT_OR_METHOD_DRIFT")
    # Do not reuse ANY prior FIT/CHECK/DEV source goal pair (even for new seeds).
    from k4j_replicate import frozen as k4j_frozen
    from k4k_compression import frozen as k4k_frozen
    from k4l_multicontext import protocol as k4l_protocol
    old=(k4i_protocol()["variants"]+k4j_frozen()["design"]["variants"]+
         k4k_frozen()["cohort"]["world_variants"]+k4l_protocol()["cohort"]["variants"])
    known={(x["goal_dx"],x["goal_dy"]) for x in old}
    if any((x["goal_dx"],x["goal_dy"]) in known for x in v):
        raise ValueError("K4N_PREVIOUS_SOURCE_COHORT_REUSED")
    return p

def environment(p):
    cfg=k4i_protocol()
    cfg["variants"]=p["cohort"]["variants"]
    cfg["world"]["seed"]=p["cohort"]["seed"]
    return cfg,source_config(cfg)


def _loss(np, full, candidate, family, contexts, scale):
    disagreements=0
    errors=0.0
    for x in contexts:
        full_values=[predict(np,full,family,x,arm,"raw_knn") for arm in range(4)]
        coreset_values=[predict(np,candidate,family,x,arm,"raw_knn") for arm in range(4)]
        full_arm=max(range(4),key=lambda a:(full_values[a],-a))
        small_arm=max(range(4),key=lambda a:(coreset_values[a],-a))
        disagreements+=int(full_arm!=small_arm)
        errors+=sum(abs(a-b)/scale for a,b in zip(full_values,coreset_values))
    return 1000*disagreements+errors

def fit_decision_fidelity(np,original,all_models,fit_rows,p):
    """Deterministic FIT-only one-for-one swaps, unchanged source reward lookup."""
    selected=copy.deepcopy(all_models["coverage_4"])
    audit={}
    if p["mechanism"]["capacity"]!=4:
        raise ValueError("K4N_UNFROZEN_CAPACITY")
    for family in ("reaching","pushing"):
        original_records=original["by_family"][family]["records"]
        contexts=[next(r for r in fit_rows if r["family"]==family and
               r["variant"]==i and r["arm"]==0)["features"] for i in range(12)]
        rewards=[r["reward"] for r in fit_rows if r["family"]==family]
        scale=max(1.0,max(rewards)-min(rewards))
        loss=_loss(np,original,selected,family,contexts,scale)
        starting=loss
        swaps=[]
        for iteration in range(8):
            best=loss
            choice_swap=None
            for arm in range(4):
                name=str(arm)
                active=selected["by_family"][family]["records"][name]
                present={r["variant"] for r in active}
                for slot,removed in enumerate(active):
                    for candidate in original_records[name]:
                        if candidate["variant"] in present:
                            continue
                        replacement=active[:slot]+[candidate]+active[slot+1:]
                        selected["by_family"][family]["records"][name]=sorted(
                            replacement,key=lambda r:r["variant"])
                        trial=_loss(np,original,selected,family,contexts,scale)
                        if trial<best-1e-12:
                            best=trial
                            choice_swap=(arm,removed["variant"],candidate["variant"],copy.deepcopy(
                                selected["by_family"][family]["records"][name]))
                    selected["by_family"][family]["records"][name]=active
            if choice_swap is None:
                break
            arm,removed,added,new_records=choice_swap
            selected["by_family"][family]["records"][str(arm)]=new_records
            swaps.append({"arm":arm,"removed_FIT":removed,"added_FIT":added,
                          "FIT_only_loss":best})
            loss=best
        audit[family]={"initial_FIT_loss":starting,"final_FIT_loss":loss,
              "strict_improving_swaps":swaps,
              "selected_FIT_variants_by_arm":{
                 str(a):[r["variant"] for r in selected["by_family"][family]["records"][str(a)]]
                 for a in range(4)}}
        if any(len(selected["by_family"][family]["records"][str(a)])!=4 for a in range(4)):
            raise ValueError("K4N_CORESET_SIZE_DRIFT")
    return selected,audit

def policy_choice(np,models,full,family,feature,method):
    if method=="fit_fidelity_4":
        return choose(np,models[method],family,feature,"raw_knn")
    return k4k_choice(np,models,full,family,feature,method)

def make_plan(np,models,full,contexts):
    return [{"family":ctx["family"],"variant":ctx["variant"],
       "public_observation_sha256":ctx["initial_observation_sha256"],
       "choices":{m:policy_choice(np,models,full,ctx["family"],ctx["features"],m)
                  for m in METHODS}}
          for ctx in contexts]

def checkpoints(models,full):
    result=k4k_checkpoints(models,full)
    state=models["fit_fidelity_4"]
    payload={family:detail["records"] for family,detail in state["by_family"].items()}
    result["fit_fidelity_4"]=len(canonical(payload).encode("utf-8"))
    return result

def resource_benchmark(np,models,full,contexts,plan):
    if len(contexts)!=20 or len(plan)!=20:
        raise ValueError("K4N_RESOURCE_COHORT_NOT_FROZEN")
    metrics={}
    for method in METHODS:
        cpu_start=time.process_time_ns()
        wall_start=time.perf_counter_ns()
        for repetition in range(200):
            for i,ctx in enumerate(contexts):
                predicted=policy_choice(np,models,full,ctx["family"],ctx["features"],method)
                if predicted!=plan[i]["choices"][method]:
                    raise ValueError("K4N_NONDETERMINISTIC_INFERENCE")
        metrics[method]={"CPU_ns":time.process_time_ns()-cpu_start,
             "wall_ns":time.perf_counter_ns()-wall_start,"calls":4000}
    return metrics

def decide(info,dev_scores,model_sizes,method_cost):
    by_family={}
    for family in ("reaching","pushing"):
        cases=[r for r in dev_scores if r["family"]==family]
        if len(cases)!=8:
            raise ValueError("K4N_UNQUALIFIED_DEV_COUPLING")
        means={m:sum(x["selected"][m]["reward"] for x in cases)/8 for m in METHODS}
        actions={m:[x["selected"][m]["arm"] for x in cases] for m in METHODS}
        improvements={m:sum(x["selected"][m]["reward"]>
             x["selected"]["family_mean"]["reward"] for x in cases) for m in METHODS}
        retrospective=[max(range(4),key=lambda a:
             (x["per_action_returns"][str(a)],-a)) for x in cases]
        by_family[family]={"mean_reward":means,"actions":actions,
             "strict_improvements_vs_constant":improvements,
             "offline_best_actions_only_for_diagnosis":retrospective,
             "FIT_best_action_ids":info[family]["best_arm_ids"]}
    reach=by_family["reaching"]
    y=reach["mean_reward"];base=y["family_mean"]
    full_gain=y["full_12"]-base
    main_gain=y["fit_fidelity_4"]-base
    size_ratio=model_sizes["fit_fidelity_4"]/model_sizes["full_12"]
    cpu_ratio=method_cost["fit_fidelity_4"]["CPU_ns"]/max(1,method_cost["full_12"]["CPU_ns"])
    checks={
      "FIT_action_winners_diverse":len(reach["FIT_best_action_ids"])>=2,
      "DEV_offline_best_actions_diverse":len(set(reach["offline_best_actions_only_for_diagnosis"]))>=2,
      "full_12_beats_fitted_constant":full_gain>0,
      "proposed_gain_at_least_0_01":main_gain>=.01,
      "retain_at_least_90pct_full_gain":full_gain>0 and main_gain>=.9*full_gain,
      "at_least_3_of_8_strict_better_cases":reach["strict_improvements_vs_constant"]["fit_fidelity_4"]>=3,
      "context_dependent_action_choice":len(set(reach["actions"]["fit_fidelity_4"]))>=2,
      "beat_coverage_equal_capacity_by_0_01":y["fit_fidelity_4"]-y["coverage_4"]>=.01,
      "beat_reward_aware_equal_capacity_by_0_01":y["fit_fidelity_4"]-y["outcome_aware_4"]>=.01,
      "serialized_records_at_most_50pct_full":size_ratio<=.50,
      "inference_CPU_at_most_65pct_full":cpu_ratio<=.65}
    return {"result":"K4N_BOUNDED_NEW_SOURCE_DECISION_CORESET_POSITIVE" if all(checks.values())
         else "K4N_NO_QUALIFIED_UNIQUE_MEMORY_ADVANCEMENT",
       "requirements":checks,"full_gain":full_gain,"proposed_gain":main_gain,
       "proposed_minus_coverage":y["fit_fidelity_4"]-y["coverage_4"],
       "proposed_minus_outcome_aware":y["fit_fidelity_4"]-y["outcome_aware_4"],
       "checkpoint_ratio":size_ratio,"inference_cpu_ratio":cpu_ratio,
       "per_family":by_family,"scientific_accepted":False,
       "scientific_first_use":False,"novel_cognition_claim":False}

def execute(repo,p):
    from k4a_control_replay import verify_source
    if p["source"]["CausalWorld_commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("K4N_UPSTREAM_SOURCE_DRIFT")
    root=repo.resolve();verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("K4N_UNPINNED_SOURCE_IMPORT")
    cfg,world=environment(p)
    start_wall=time.perf_counter();start_cpu=time.process_time()
    fit=collect(np,CausalWorld,generate_task,world,partition(cfg,"FIT"))
    fit_errors=paired_violations(fit,partition(cfg,"FIT"),world)
    info=information_support(fit,cfg)
    if fit_errors or info["reaching"]["unique_public_FIT_contexts"]!=12:
        raise ValueError("K4N_UNQUALIFIED_PUBLIC_FIT_STATE")
    output={"schema":SCHEMA,"gate":"LCRM01-K4N",
       "source_commit":p["source"]["CausalWorld_commit"],
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "FIT_exposures":len(fit),"FIT_rows":fit,"FIT_information_support":info,
       "CHECK_exposures":0,"DEV_exposures":0,
       "original_K4L_negative_preserved":True,
       "original_K4M_diagnostic_preserved":True,
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
    new_memory,selection_audit=fit_decision_fidelity(np,fitted,compressed,fit,p)
    compressed["fit_fidelity_4"]=new_memory
    output["FIT_only_selection_audit"]=selection_audit
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
        raise ValueError("K4N_HOLDOUT_PUBLIC_START_DRIFT")
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
        result={"schema":SCHEMA,"gate":"LCRM01-K4N","result":"INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED",
            "error_type":type(e).__name__,"error":str(e),
            "traceback_tail":traceback.format_exc().splitlines()[-12:],
            "original_K4K_negative_preserved":True,
            "scientific_first_use":False,"scientific_accepted":False}
    x.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("K4N_RUN="+result["result"])
    if "quality_cost_decision" in result:
        q=result["quality_cost_decision"]
        print("K4N_SCIENTIFIC_DISPOSITION="+q["result"])
        print("K4N_REQUIREMENTS="+canonical(q["tests"]))
        print("K4N_FAMILY_EVIDENCE="+canonical(q["per_family"]))
        print("K4N_SAVING="+canonical({"model_ratio":q["checkpoint_byte_ratio"],
               "CPU_ratio":q["inference_cpu_ratio"]}))
    if "FIT_information_support" in result:
        print("K4N_FIT_WINNERS="+canonical({k:v["best_arm_ids"]
            for k,v in result["FIT_information_support"].items()}))
    return 1 if result["result"]=="INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED" else 0
if __name__=="__main__":
    sys.exit(main())
