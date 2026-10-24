#!/usr/bin/env python3
"""K4H: novel, source-visible task configurations before decision-transfer claims.

Seven prospectively frozen distinct task constructor settings. Each action is
evaluated on a fresh public CausalWorld instance; all policy choices are fixed
from FIT before CHECK or DEV is evaluated. No native model/FSA admission.
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

FROZEN=Path(__file__).with_name("k4h_frozen_varied_worlds.json")
SCHEMA="mass.lcrm01.k4h.varied-public-worlds-development.v1"
METHODS=("untrained_fixed_low","FIT_trained_family_mean_action",
         "FIT_trained_nearest_observation_action","FIT_trained_regularized_action_ridge")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)

def checksum(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()

def load_protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    expected=[(0,0,0,"FIT"),(1,0.02,0,"FIT"),(2,-0.02,0,"FIT"),
              (3,0,0.02,"FIT"),(4,0,-0.02,"CHECK"),
              (5,0.03,0.01,"DEV"),(6,-0.03,-0.01,"DEV")]
    actual=[(x["id"],x["goal_dx"],x["goal_dy"],x["phase"]) for x in p["variants"]]
    if (p["schema"]!="mass.lcrm01.k4h.frozen-observable-varied-world-generalization.v1" or
        actual!=expected or p["study"]["fit_variants"]!=[0,1,2,3] or
        p["study"]["check_variants"]!=[4] or p["study"]["dev_variants"]!=[5,6] or
        p["world"]["families"]!=["reaching","pushing"] or p["world"]["seed"]!=811):
        raise ValueError("K4H_FROZEN_SOURCE_CONTRACT_DRIFT")
    return p

def source_task(np,generate_task,p,family,variant):
    if family not in ("reaching","pushing") or variant not in p["variants"]:
        raise ValueError("UNKNOWN_WORLD")
    dx=variant["goal_dx"];dy=variant["goal_dy"];w=p["world"]
    if family=="reaching":
        base=w["reaching_goal_xyz_base"]
        args={name:np.asarray((v[0]+dx,v[1]+dy,v[2]),dtype=np.float64)
              for name,v in zip(("default_goal_60","default_goal_120","default_goal_300"),base)}
    else:
        tool=w["pushing_tool_block_xyz_base"]
        goal=w["pushing_goal_block_xyz_base"]
        args={"tool_block_position":np.asarray((tool[0]-dx,tool[1],tool[2]),dtype=np.float64),
              "goal_block_position":np.asarray((goal[0]+dx,goal[1]+dy,goal[2]),dtype=np.float64)}
    return generate_task(task_generator_id=family,**args)

def action(np,space,index):
    if type(index)!=int or index not in range(4):
        raise ValueError("ACTION_NOT_FROZEN")
    lo=np.asarray(space.low,dtype=np.float64)
    hi=np.asarray(space.high,dtype=np.float64)
    if lo.shape!=(9,) or hi.shape!=(9,) or np.any(lo>=hi) or not np.all(np.isfinite(lo+hi)):
        raise ValueError("UNSAFE_JOINT_ACTION_SPACE")
    ratios=(np.zeros(9) if index==0 else np.full(9,0.5) if index==1 else
            np.ones(9) if index==2 else
            np.array([0.2 if j%2==0 else 0.8 for j in range(9)]))
    v=lo+(hi-lo)*ratios
    if np.any(v<lo) or np.any(v>hi):
        raise ValueError("ILLEGAL_ACTION")
    return v

def public_features(np,observation):
    v=np.asarray(observation,dtype=np.float64).ravel()
    if v.size<1 or v.size>128 or not np.all(np.isfinite(v)):
        raise ValueError("PUBLIC_OBSERVATION_NOT_SUPPORTED")
    x=np.zeros(128,dtype=np.float64)
    x[:v.size]=np.tanh(v/0.5)
    return x.tolist()

def rollout(np,CausalWorld,generate_task,p,family,variant,arm):
    w=p["world"]
    task=source_task(np,generate_task,p,family,variant)
    env=CausalWorld(task=task,enable_visualization=False,
        seed=w["seed"],skip_frame=w["skip_frame"],
        action_mode=w["action_mode"],observation_mode=w["observation_mode"],
        normalize_actions=w["normalize_actions"],
        normalize_observations=w["normalize_observations"],
        max_episode_length=w["max_episode_length"])
    try:
        initial=np.asarray(env.reset(),dtype=np.float64).ravel()
        feat=public_features(np,initial)
        initial_sha=hashlib.sha256(initial.tobytes()).hexdigest()
        selected=action(np,env.action_space,arm)
        result=0.0;steps=0
        for _ in range(w["steps"]):
            _obs,reward,done,_info=env.step(selected)
            num=float(reward)
            if not math.isfinite(num):
                raise ValueError("PUBLIC_REWARD_NONFINITE")
            result+=num
            steps+=1
            if done:
                break
        return {"family":family,"variant":variant["id"],"phase":variant["phase"],
                "arm":arm,"reward":float(result),"steps":steps,
                "initial_observation_sha256":initial_sha,
                "features":feat,"action_sha256":hashlib.sha256(selected.tobytes()).hexdigest()}
    finally:
        env.close()

def collect(np,CausalWorld,generate_task,p,variants):
    rows=[]
    for family in p["world"]["families"]:
        for variant in variants:
            for arm in range(4):
                rows.append(rollout(np,CausalWorld,generate_task,p,family,variant,arm))
    if len(rows)!=len(p["world"]["families"])*len(variants)*4:
        raise ValueError("ACTUAL_EPISODE_COUNT_MISMATCH")
    return rows

def paired_violations(rows,variants,p):
    failures=[]
    for family in p["world"]["families"]:
        for variant in variants:
            observed=[r for r in rows if r["family"]==family and r["variant"]==variant["id"]]
            if [r["arm"] for r in observed]!=[0,1,2,3]:
                raise ValueError("INCOMPLETE_FOUR_ARM_SOURCE")
            if len({r["initial_observation_sha256"] for r in observed})!=1:
                failures.append({"family":family,"variant":variant["id"],"reason":"RESET_OBSERVATION_DRIFT"})
            if len({r["action_sha256"] for r in observed})!=4:
                failures.append({"family":family,"variant":variant["id"],"reason":"DUPLICATE_ACTION"})
    return failures

def fit_models(np,fit_rows,p):
    if len(fit_rows)!=32:
        raise ValueError("FIT_DATA_NOT_FULL")
    models={}
    lam=p["study"]["ridge_lambda"]
    for family in p["world"]["families"]:
        data=[r for r in fit_rows if r["family"]==family]
        if len(data)!=16 or any(sum(r["arm"]==a for r in data)!=4 for a in range(4)):
            raise ValueError("CONVENTIONAL_FIT_INEQUITABLE")
        family_model={"mean":{},"records":{},"ridge":{}}
        for arm in range(4):
            ex=[r for r in data if r["arm"]==arm]
            family_model["mean"][str(arm)]=float(sum(r["reward"] for r in ex)/4)
            family_model["records"][str(arm)]=[
                {"variant":r["variant"],"x":r["features"],"reward":r["reward"]} for r in ex]
            # Ordinary fully fitted linear ridge (4 FIT task configurations).
            X=np.asarray([[1.0]+r["features"] for r in ex],dtype=np.float64)
            y=np.asarray([r["reward"] for r in ex],dtype=np.float64)
            beta=np.linalg.solve(X@X.T+np.eye(4)*lam,y)
            w=X.T@beta
            if not np.all(np.isfinite(w)):
                raise ValueError("RIDGE_FIT_NONFINITE")
            family_model["ridge"][str(arm)]=w.tolist()
        models[family]=family_model
    return {"state_format":"mass.k4h.fitted-equal-experience-controls.v1",
            "train_episode_count":len(fit_rows),"by_family":models}

def predict(np,state,family,features,arm,method):
    if method not in METHODS or arm not in range(4):
        raise ValueError("UNKNOWN_METHOD")
    if method==METHODS[0]:
        return 0.0 if arm==0 else -1.e15
    model=state["by_family"][family]
    if method==METHODS[1]:
        return model["mean"][str(arm)]
    if method==METHODS[2]:
        records=model["records"][str(arm)]
        best=min(records,key=lambda r:(sum((a-b)**2 for a,b in zip(features,r["x"])),r["variant"]))
        return best["reward"]
    w=np.asarray(model["ridge"][str(arm)],dtype=np.float64)
    return float(w@np.asarray([1.0]+features,dtype=np.float64))

def choose(np,state,family,features,method):
    preds=[predict(np,state,family,features,a,method) for a in range(4)]
    if not all(math.isfinite(x) for x in preds):
        raise ValueError("NONFINITE_PREDICTIONS")
    return max(range(4),key=lambda a:(preds[a],-a))

def make_frozen_plan(np,state,observed_rows,p):
    # Read PUBLIC initial observations, never held-out rewards.
    out=[]
    variants=sorted({(r["family"],r["variant"]) for r in observed_rows})
    for family,variant in variants:
        source=[r for r in observed_rows if r["family"]==family and r["variant"]==variant]
        if len(source)!=4 or len({r["initial_observation_sha256"] for r in source})!=1:
            raise ValueError("UNMATCHED_PUBLIC_RESET")
        x=source[0]["features"]
        out.append({"family":family,"variant":variant,
          "public_observation_sha256":source[0]["initial_observation_sha256"],
          "choices":{m:choose(np,state,family,x,m) for m in METHODS}})
    return out

def evaluate_plan(rows,plan):
    scored=[]
    for entry in plan:
        family,variant=entry["family"],entry["variant"]
        relevant=[r for r in rows if r["family"]==family and r["variant"]==variant]
        if len(relevant)!=4:
            raise ValueError("DEV_OR_CHECK_INCOMPLETE")
        rewards={r["arm"]:r["reward"] for r in relevant}
        scored.append({"family":family,"variant":variant,
            "reward_spread":max(rewards.values())-min(rewards.values()),
            "per_action_returns":{str(a):rewards[a] for a in range(4)},
            "selected":{m:{"arm":arm,"reward":rewards[arm]}
                        for m,arm in entry["choices"].items()}})
    return scored

def verdict(fit,dev,paired,p):
    quality={}
    for family in p["world"]["families"]:
        ft=[r for r in fit if r["family"]==family and r["arm"]==0]
        dv=[r for r in dev if r["family"]==family]
        unique_fit=len({r["initial_observation_sha256"] for r in ft})
        dev_hashes={r["initial_observation_sha256"] for r in p["_dev_raw"] if r["family"]==family}
        unique_dev=len(dev_hashes)
        disjoint=not (dev_hashes & {r["initial_observation_sha256"] for r in ft})
        reward_profiles=len({tuple(r["per_action_returns"][str(a)] for a in range(4)) for r in dv})
        action_sensitive=all(r["reward_spread"]>0.05 for r in dv)
        means={m:sum(r["selected"][m]["reward"] for r in dv)/len(dv) for m in METHODS}
        conventional_gain=max(means[m] for m in METHODS[1:])-means[METHODS[0]]
        learned_gain=max(means[m] for m in METHODS[2:])-means[METHODS[1]]
        context_methods_vary=any(len({r["selected"][m]["arm"] for r in dv})>1 for m in METHODS[2:])
        quality[family]={"FIT_unique_starts":unique_fit,"DEV_unique_starts":unique_dev,
         "DEV_disjoint_from_FIT":disjoint,"DEV_distinct_reward_profiles":reward_profiles,
         "DEV_each_action_sensitive":action_sensitive,
         "methods_mean_DEV_reward":means,
         "fitted_control_advantage_over_fixed":conventional_gain,
         "contextual_advantage_over_fitted_family_constant":learned_gain,
         "contextual_actions_vary_across_DEV":context_methods_vary}
    source_good=(not paired and all(x["FIT_unique_starts"]==4 and x["DEV_unique_starts"]==2
        and x["DEV_disjoint_from_FIT"] and x["DEV_distinct_reward_profiles"]==2
        and x["DEV_each_action_sensitive"] for x in quality.values()))
    conventional_good=(source_good and all(x["fitted_control_advantage_over_fixed"]>=0.01
        for x in quality.values()))
    context_good=(conventional_good and all(x["contextual_advantage_over_fitted_family_constant"]>=0.01
        for x in quality.values()) and any(x["contextual_actions_vary_across_DEV"]
        for x in quality.values()))
    return {"source_variation":"PASS" if source_good else "SOURCE_CONTEXT_NOT_QUALIFIED",
      "conventional_learnability":"PASS" if conventional_good else "CONVENTIONAL_IMPROVEMENT_NOT_ESTABLISHED",
      "contextual_generalization":"BOUNDED_DEV_POSITIVE" if context_good else "CONTEXTUAL_GENERALIZATION_NOT_ESTABLISHED",
      "per_family":quality,"paired_source_violations":paired,
      "scientific_accepted":False,"native_transfer_claim":False}

def experiment(repo,p):
    from k4a_control_replay import verify_source
    root=repo.resolve()
    if p["source"]["commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("UPSTREAM_SOURCE_PIN_DRIFT")
    verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("WRONG_PUBLIC_SIMULATOR_IMPORT")
    begin=time.perf_counter();cpu=time.process_time()
    by_id={v["id"]:v for v in p["variants"]}
    fit_variants=[by_id[i] for i in p["study"]["fit_variants"]]
    check_variants=[by_id[i] for i in p["study"]["check_variants"]]
    dev_variants=[by_id[i] for i in p["study"]["dev_variants"]]
    fit=collect(np,CausalWorld,generate_task,p,fit_variants)
    fit_errors=paired_violations(fit,fit_variants,p)
    state=fit_models(np,fit,p)
    stored=canonical(state);reloaded=json.loads(stored)
    if any(choose(np,state,fam,r["features"],method)!=choose(np,reloaded,fam,r["features"],method)
           for r in fit for fam in (r["family"],) for method in METHODS):
        raise ValueError("CHECKPOINT_RELOAD_PREDICTION_DRIFT")
    # No training or policy selection from CHECK/DEV rewards.
    check=collect(np,CausalWorld,generate_task,p,check_variants)
    check_errors=paired_violations(check,check_variants,p)
    check_plan=make_frozen_plan(np,reloaded,check,p)
    # CHECK: veto/diagnostic only; code does not refit.
    check_scores=evaluate_plan(check,check_plan)
    dev=collect(np,CausalWorld,generate_task,p,dev_variants)
    dev_errors=paired_violations(dev,dev_variants,p)
    dev_plan=make_frozen_plan(np,reloaded,dev,p)
    dev_scores=evaluate_plan(dev,dev_plan)
    verify_source(root)
    p["_dev_raw"]=dev
    v=verdict(fit,dev_scores,fit_errors+check_errors+dev_errors,p)
    del p["_dev_raw"]
    return {"schema":SCHEMA,"gate":"LCRM01-K4H",
      "result":"PUBLIC_DEVELOPMENT_COMPLETED","protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
      "source_commit":p["source"]["commit"],"FIT_exposures":len(fit),
      "CHECK_exposures":len(check),"DEV_exposures":len(dev),
      "FIT_rows":fit,"CHECK_rows":check,"DEV_rows":dev,
      "FIT_data_sha256":checksum(fit),"CHECK_data_sha256":checksum(check),"DEV_data_sha256":checksum(dev),
      "learned_checkpoint_sha256":hashlib.sha256(stored.encode()).hexdigest(),
      "checkpoint_bytes":len(stored),"checkpoint_predictions_retained":True,
      "check_plan":check_plan,"dev_plan":dev_plan,
      "check_scores":check_scores,"dev_scores":dev_scores,"calibration":v,
      "cost":{"wall_seconds":time.perf_counter()-begin,"cpu_seconds":time.process_time()-cpu,
              "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024},
      "K4F_original_negative_preserved":True,"K4G_context_limitation_preserved":True,
      "original_first_use":False,"scientific_accepted":False,"dispatch_authorized":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--causalworld-repo",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("EXISTING_RESULT_PATH")
    try:
        p=load_protocol();r=experiment(args.causalworld_repo,p)
    except Exception as e:
        r={"schema":SCHEMA,"gate":"LCRM01-K4H","result":"INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED",
           "exception_type":type(e).__name__,"exception":str(e),
           "traceback_tail":traceback.format_exc().splitlines()[-12:],
           "original_first_use":False,"scientific_accepted":False,
           "K4F_original_negative_preserved":True,"K4G_context_limitation_preserved":True}
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("K4H_RUN="+r["result"])
    if "calibration" in r:
        print("K4H_CALIBRATION="+canonical({k:v for k,v in r["calibration"].items() if k!="per_family"}))
        print("K4H_PER_FAMILY="+canonical(r["calibration"]["per_family"]))
    return 0 if r["result"]=="PUBLIC_DEVELOPMENT_COMPLETED" else 1

if __name__=="__main__":
    sys.exit(main())
