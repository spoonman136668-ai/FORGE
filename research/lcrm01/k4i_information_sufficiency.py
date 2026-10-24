#!/usr/bin/env python3
"""K4I. FIT causal action-support before any new heldout exposure.

One prospectively frozen symmetric task grid, equal-information conventional
predictors. Original public simulator, no authority, no tuning from K4H DEV.
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

from k4h_varied_worlds import (
    load_protocol as old_protocol, collect, paired_violations, observe_public_context,
    evaluate_plan, canonical, checksum)

FROZEN=Path(__file__).with_name("k4i_frozen_information_sufficiency.json")
SCHEMA="mass.lcrm01.k4i.real-fit-information-source-and-context-controls.v1"
METHODS=("family_mean","raw_knn","scaled_knn","ridge","fixed_low")

def load():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4i.frozen-information-sufficiency-representation-v1":
        raise ValueError("FROZEN_SCHEMA_MISMATCH")
    allv=p["variants"]
    expected=[(dx,dy) for dx in (-.06,-.02,.02,.06) for dy in (-.04,0,.04)]
    expected += [(0,-.02),(0,.02),(-.045,-.025),(-.045,.025),(.045,-.025),(.045,.025)]
    if len(allv)!=18 or [(v["goal_dx"],v["goal_dy"]) for v in allv]!=expected:
        raise ValueError("WORLD_VARIANTS_UNFROZEN")
    if [(v["id"],v["phase"]) for v in allv] != [(i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(18)]:
        raise ValueError("SPLIT_ASSIGNMENT_DRIFT")
    if p["world"]["seed"]!=827 or p["hyperparameters"]!={"ridge_lambda":1,"nearest_neighbors":1,"std_floor":.05}:
        raise ValueError("FROZEN_NUMERICS_DRIFT")
    return p

def source_config(p):
    base=old_protocol() # K4H source-proven constructor, no edits to ancestor file.
    base["variants"]=p["variants"]
    base["world"]["seed"]=p["world"]["seed"]
    if base["world"]["steps"]!=p["world"]["episode_steps"] or base["world"]["families"]!=p["world"]["families"]:
        raise ValueError("K4H_SOURCE_SETTINGS_DRIFT")
    return base

def partition(p,phase):
    return [x for x in p["variants"] if x["phase"]==phase]

def information_support(rows,p):
    result={}
    for family in p["world"]["families"]:
        family_winners=[]
        profiles=[]
        distinct_public=set()
        for v in partition(p,"FIT"):
            examples=[r for r in rows if r["family"]==family and r["variant"]==v["id"]]
            if [r["arm"] for r in examples]!=[0,1,2,3]:
                raise ValueError("FIT_MISSING_ONE_OR_MORE_ACTUAL_ACTIONS")
            distinct_public.add(examples[0]["initial_observation_sha256"])
            winner=max(range(4),key=lambda a:(examples[a]["reward"],-a))
            family_winners.append({"variant":v["id"],"winner":winner,
                "rewards":[r["reward"] for r in examples],
                "spread":float(max(r["reward"] for r in examples)-min(r["reward"] for r in examples))})
            profiles.append([r["reward"] for r in examples])
        winner_arms=sorted({r["winner"] for r in family_winners})
        result[family]={"unique_public_FIT_contexts":len(distinct_public),
            "best_arm_ids":winner_arms,"action_ranking_diverse":len(winner_arms)>=2,
            "FIT_reward_profiles_unique":len({canonical(z) for z in profiles}),
            "per_context":family_winners}
    return result

def train(np,rows,p):
    if len(rows)!=96:
        raise ValueError("FIT_TOTAL_EPISODES_INCOMPLETE")
    m={"schema":"mass.k4i.conventional-trained-state.v1","by_family":{}}
    for family in p["world"]["families"]:
        ex=[r for r in rows if r["family"]==family]
        if len(ex)!=48 or any(sum(z["arm"]==i for z in ex)!=12 for i in range(4)):
            raise ValueError("EQUAL_FIT_INFORMATION_VIOLATION")
        x=np.asarray([r["features"] for r in ex if r["arm"]==0],dtype=np.float64)
        mean=np.mean(x,axis=0)
        scale=np.maximum(np.std(x,axis=0),p["hyperparameters"]["std_floor"])
        family_state={"mean":{}, "records":{}, "ridge":{},
            "feature_mean":mean.tolist(),"feature_scale":scale.tolist()}
        for arm in range(4):
            a=[r for r in ex if r["arm"]==arm]
            X=np.asarray([[1]+r["features"] for r in a],dtype=np.float64)
            Y=np.asarray([r["reward"] for r in a],dtype=np.float64)
            coef=X.T @ np.linalg.solve(X@X.T + np.eye(12)*p["hyperparameters"]["ridge_lambda"],Y)
            family_state["ridge"][str(arm)]=coef.tolist()
            family_state["mean"][str(arm)]=float(np.mean(Y))
            family_state["records"][str(arm)]=[
                {"x":r["features"],"y":r["reward"],"variant":r["variant"]} for r in a]
        m["by_family"][family]=family_state
    return m

def predict(np,state,family,feature,arm,method):
    if family not in state["by_family"] or method not in METHODS or arm not in range(4):
        raise ValueError("UNREGISTERED_METHOD")
    if method=="fixed_low":
        return 0.0 if arm==0 else -1e12
    s=state["by_family"][family]
    if method=="family_mean":return s["mean"][str(arm)]
    if method=="ridge":
        return float(np.asarray([1]+feature)@np.asarray(s["ridge"][str(arm)]))
    centers=s["records"][str(arm)]
    if method=="scaled_knn":
        center=np.asarray(s["feature_mean"])
        scale=np.asarray(s["feature_scale"])
        normalized=(np.asarray(feature)-center)/scale
        key=lambda r:(float(np.sum((normalized-(np.asarray(r["x"])-center)/scale)**2)),r["variant"])
    else:
        key=lambda r:(float(np.sum((np.asarray(feature)-np.asarray(r["x"]))**2)),r["variant"])
    return float(min(centers,key=key)["y"])

def choose(np,state,family,feature,method):
    values=[predict(np,state,family,feature,a,method) for a in range(4)]
    if not all(math.isfinite(x) for x in values):
        raise ValueError("NONFINITE_POLICY_SCORE")
    return max(range(4),key=lambda a:(values[a],-a))

def context_plan(np,state,p,contexts):
    out=[]
    for c in contexts:
        fam=c["family"];f=c["features"]
        out.append({"family":fam,"variant":c["variant"],
            "public_observation_sha256":c["initial_observation_sha256"],
            "choices":{method:choose(np,state,fam,f,method) for method in METHODS}})
    return out

def evaluate(rows,plan):
    return evaluate_plan(rows,plan)

def verdict(fit_info,fit,dev,dev_scored,source_errors,p):
    answer={}
    for family in p["world"]["families"]:
        contexts=[r for r in dev if r["family"]==family and r["arm"]==0]
        scored=[s for s in dev_scored if s["family"]==family]
        starts={z["initial_observation_sha256"] for z in contexts}
        previous={z["initial_observation_sha256"] for z in fit if z["family"]==family}
        means={m:sum(s["selected"][m]["reward"] for s in scored)/len(scored) for m in METHODS}
        acts={m:[s["selected"][m]["arm"] for s in scored] for m in METHODS}
        margin={m:means[m]-means["family_mean"] for m in ("raw_knn","scaled_knn","ridge")}
        support=fit_info[family]["action_ranking_diverse"]
        clean=(len(starts)==4 and not(starts&previous) and
               all(s["reward_spread"]>.05 for s in scored) and not source_errors)
        individual={m:bool(support and clean and margin[m]>=.01 and
                   len(set(acts[m]))>=2) for m in margin}
        answer[family]={"FIT_action_ranking_diverse":support,"DEV_new_contexts":len(starts),
            "DEV_disjoint_from_FIT":not bool(starts&previous),
            "DEV_action_spread_gt_0_05":sum(s["reward_spread"]>.05 for s in scored),
            "mean_real_reward":means,"selected_actions":acts,
            "incremental_reward_over_fitted_family_mean":margin,
            "predeclared_method_support":individual,
            "caution_any_method":"EXPLORATORY_MULTIPLE_COMPARISONS" if any(individual.values()) else "NO_GO"}
    return {"source_support":{k:z["action_ranking_diverse"] for k,z in fit_info.items()},
        "per_family":answer,"source_errors":source_errors,"first_use":False,
        "scientific_accepted":False}

def experiment(repo,p):
    from k4a_control_replay import verify_source
    if p["upstream"]["commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("ORIGINAL_SIMULATOR_DRIFT")
    root=repo.resolve();verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("NONPUBLIC_SOURCE_IMPORTED")
    start=time.perf_counter();cpu=time.process_time()
    config=source_config(p)
    fit=collect(np,CausalWorld,generate_task,config,partition(p,"FIT"))
    fit_errors=paired_violations(fit,partition(p,"FIT"),config)
    info=information_support(fit,p)
    if fit_errors:
        raise ValueError("FIT_PUBLIC_INITIAL_STATE_INCONSISTENT")
    if any(info[f]["unique_public_FIT_contexts"]!=12 for f in p["world"]["families"]):
        raise ValueError("FIT_WORLD_VARIATION_NOT_OBSERVABLE")
    gate=any(z["action_ranking_diverse"] for z in info.values())
    basis={"schema":SCHEMA,"gate":"LCRM01-K4I",
        "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
        "source_commit":p["upstream"]["commit"],
        "FIT_rows":fit,"FIT_information_support":info,
        "FIT_exposures":len(fit),
        "K4H_negative_preserved":True,"K4F_negative_preserved":True,
        "original_first_use":False,"scientific_accepted":False,"dispatch_authorized":False}
    if not gate:
        basis.update({"result":"INSUFFICIENT_FIT_ACTION_RANK_INFORMATION",
            "CHECK_exposures":0,"DEV_exposures":0,
            "unconsumed_phases":["CHECK","DEV"]})
        return basis
    state=train(np,fit,p)
    serialized=canonical(state)
    restored=json.loads(serialized)
    if any(predict(np,state,r["family"],r["features"],arm,method)!=
            predict(np,restored,r["family"],r["features"],arm,method)
            for r in fit for arm in range(4) for method in METHODS):
        raise ValueError("LEARNED_CHECKPOINT_MISMATCH")
    basis.update({"learned_checkpoint_sha256":hashlib.sha256(serialized.encode()).hexdigest(),
                  "checkpoint_bytes":len(serialized),"checkpoint_retention_pass":True})
    # Unlike post-hoc selection, decisions are frozen from public RESET probes
    # BEFORE any CHECK or DEV step/reward observations are collected.
    check_ctx=[observe_public_context(np,CausalWorld,generate_task,config,f,v)
              for f in p["world"]["families"] for v in partition(p,"CHECK")]
    check_plan=context_plan(np,restored,p,check_ctx)
    check=collect(np,CausalWorld,generate_task,config,partition(p,"CHECK"))
    check_errors=paired_violations(check,partition(p,"CHECK"),config)
    check_scored=evaluate(check,check_plan)
    dev_ctx=[observe_public_context(np,CausalWorld,generate_task,config,f,v)
             for f in p["world"]["families"] for v in partition(p,"DEV")]
    dev_plan=context_plan(np,restored,p,dev_ctx)
    dev=collect(np,CausalWorld,generate_task,config,partition(p,"DEV"))
    dev_errors=paired_violations(dev,partition(p,"DEV"),config)
    dev_scored=evaluate(dev,dev_plan)
    verify_source(root)
    basis.update({"result":"COMPLETE_PUBLIC_DEVELOPMENT",
        "CHECK_exposures":len(check),"DEV_exposures":len(dev),
        "CHECK_rows":check,"DEV_rows":dev,
        "CHECK_scored":check_scored,"DEV_scored":dev_scored,
        "CHECK_plan":check_plan,"DEV_plan":dev_plan,
        "comparison":verdict(info,fit,dev,dev_scored,check_errors+dev_errors,p),
        "resource":{"wall_seconds":time.perf_counter()-start,
                    "cpu_seconds":time.process_time()-cpu,
                    "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return basis

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--causalworld-repo",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("EXISTING_OUTPUT")
    try: result=experiment(args.causalworld_repo,load())
    except Exception as e:
        result={"schema":SCHEMA,"gate":"LCRM01-K4I",
            "result":"INFRASTRUCTURE_OR_SOURCE_FAILED","error_type":type(e).__name__,
            "error":str(e),"traceback_tail":traceback.format_exc().splitlines()[-12:],
            "K4H_negative_preserved":True,"original_first_use":False,"scientific_accepted":False}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("K4I_OUTCOME="+result["result"])
    if "FIT_information_support" in result:
        print("K4I_FIT_WINNERS="+canonical({k:v["best_arm_ids"] for k,v in result["FIT_information_support"].items()}))
    if "comparison" in result:
        print("K4I_FAMILY_COMPARISON="+canonical(result["comparison"]["per_family"]))
    return 1 if result["result"]=="INFRASTRUCTURE_OR_SOURCE_FAILED" else 0
if __name__=="__main__":
    sys.exit(main())
