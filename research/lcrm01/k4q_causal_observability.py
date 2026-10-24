#!/usr/bin/env python3
"""K4Q public physical causal-observability source gate, not a native learner.

Freeze FIT and holdout before any physics execution. Intervene through original
public CausalWorld set_starting_state, never private ground truth. Train only
conventional source-prediction controls if real state-action information exists.
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

from k4p_predictive_state import (
    task, public, action, canon, FIT_FAMILIES as UNUSED)

FROZEN=Path(__file__).with_name("k4q_frozen_causal_observability.json")
SCHEMA="mass.lcrm01.k4q.original-public-causal-observability-v1"
FAMILIES=("reaching","pushing","picking")
METHODS=("mean_delta","one_nn_delta","ridge_delta")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frozen():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4q.frozen-public-causal-observability-qualification-v1":
        raise ValueError("K4Q_FROZEN_SCHEMA_DRIFT")
    v=p["source_design"]["variants"]
    expected=[(dx,dy) for dx in (-.105,-.057,.057,.105) for dy in (-.065,0,.065)]
    expected += [(-.085,-.025),(.085,.025)]
    expected += [(-.095,.04),(-.015,-.04),(.015,.04),(.095,-.04)]
    if (len(v)!=18 or [(z["goal_dx"],z["goal_dy"]) for z in v]!=expected or
        [(z["id"],z["phase"]) for z in v]!=[(i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(18)] or
        p["source_design"]["seed"]!=947 or
        p["source_design"]["tasks"]!=list(FAMILIES) or
        p["source_design"]["phases"]!={"FIT":144,"CHECK":24,"DEV":48} or
        p["source_design"]["processes"]!=2):
        raise ValueError("K4Q_COHORT_DRIFT")
    from k4i_information_sufficiency import load as k4i_load
    from k4j_replicate import frozen as k4j_load
    from k4k_compression import frozen as k4k_load
    from k4l_multicontext import protocol as k4l_load
    from k4n_decision_coreset import protocol as k4n_load
    from k4p_predictive_state import protocol as k4p_load
    prior=(k4i_load()["variants"]+k4j_load()["design"]["variants"]+
       k4k_load()["cohort"]["world_variants"]+k4l_load()["cohort"]["variants"]+
       k4n_load()["cohort"]["variants"]+k4p_load()["cohort"]["variants"])
    previous={(z["goal_dx"],z["goal_dy"]) for z in prior}
    if any((z["goal_dx"],z["goal_dy"]) in previous for z in v):
        raise ValueError("K4Q_PRIOR_CONSUMED_COHORT_REUSED")
    return p


def cohort(p,phase):
    return [z for z in p["source_design"]["variants"] if z["phase"]==phase]


def initial_joint_positions(np,v):
    dx,dy=v["goal_dx"],v["goal_dy"]
    q=[]
    for j in range(9):
        base=[0.,math.pi/4.,-math.pi/4.][j%3]
        delta=.70*dx*(1. if j%3==0 else -.5)+.80*dy*(1. if j%3==1 else -.4)+.02*dx*((j//3)-1)
        q.append(base+delta)
    arr=np.asarray(q,dtype=np.float64)
    if arr.shape!=(9,) or not np.all(np.isfinite(arr)):
        raise ValueError("INVALID_INTERVENTION_VECTOR")
    return arr


def world(np,CausalWorld,generate_task,p,family,v):
    c=p["source_design"]
    return CausalWorld(task=task(np,generate_task,family,v),
        enable_visualization=False,seed=c["seed"],skip_frame=c["skip_frame"],
        action_mode=c["action_mode"],observation_mode=c["observation_mode"],
        normalize_actions=c["normalize_actions"],
        normalize_observations=c["normalize_observations"],
        max_episode_length=c["max_episode_length"])


def observe(np,e,v):
    set_result=e.set_starting_state({"joint_positions":initial_joint_positions(np,v)},
                                      check_bounds=True)
    if not isinstance(set_result,tuple) or len(set_result)!=2 or set_result[0] is not True:
        raise ValueError("PUBLIC_STARTING_STATE_INTERVENTION_FAILED")
    raw=np.asarray(set_result[1],dtype=np.float64).ravel()
    if not raw.size or not np.all(np.isfinite(raw)):
        raise ValueError("INVALID_PUBLIC_RESET")
    return raw


def reset_probe(np,CausalWorld,generate_task,p,family,v):
    e=world(np,CausalWorld,generate_task,p,family,v)
    try:
        z=observe(np,e,v)
        return {"family":family,"variant":v["id"],
                "reset_sha256":sha(z.tobytes()),
                "x":public(np,z).tolist()}
    finally:
        e.close()


def trial(np,CausalWorld,generate_task,p,family,v,arm):
    e=world(np,CausalWorld,generate_task,p,family,v)
    try:
        raw=observe(np,e,v)
        start=public(np,raw)
        a=action(np,e.action_space,arm)
        reward=0.; end=raw;steps=0
        for _ in range(p["source_design"]["episode_steps"]):
            obs,r,done,info=e.step(a)
            end=np.asarray(obs,dtype=np.float64).ravel()
            value=float(r)
            if not math.isfinite(value):
                raise ValueError("NONFINITE_ACTION_REWARD")
            reward+=value;steps+=1
            if done:break
        final=public(np,end)
        delta=final-start
        return {"family":family,"variant":v["id"],"arm":arm,
                "x":start.tolist(),"delta":delta.tolist(),
                "reset_sha256":sha(raw.tobytes()),
                "terminal_sha256":sha(end.tobytes()),
                "delta_sha256":sha(delta.tobytes()),
                "reward":float(reward),"steps":steps,
                "action_sha256":sha(a.tobytes())}
    finally:
        e.close()


def collect(np,CausalWorld,generate_task,p,phase):
    rows=[trial(np,CausalWorld,generate_task,p,fam,v,arm)
          for fam in FAMILIES for v in cohort(p,phase) for arm in range(4)]
    if len(rows)!=p["source_design"]["phases"][phase]:
        raise ValueError("INCOMPLETE_PUBLIC_INTERACTION_COHORT")
    errors=[]
    for fam in FAMILIES:
        for v in cohort(p,phase):
            group=[r for r in rows if r["family"]==fam and r["variant"]==v["id"]]
            if [r["arm"] for r in group]!=[0,1,2,3]:
                errors.append((fam,v["id"],"MISSING_ARM"))
            if len({r["reset_sha256"] for r in group})!=1:
                errors.append((fam,v["id"],"RESET_IDENTITY_DRIFT"))
            if len({r["action_sha256"] for r in group})!=4:
                errors.append((fam,v["id"],"DUPLICATE_ACTION"))
            if any(not 1<=r["steps"]<=p["source_design"]["episode_steps"] for r in group):
                errors.append((fam,v["id"],"STEP_COUNT"))
    if errors:
        raise ValueError("REAL_ACTION_SOURCE_UNQUALIFIED:"+canon(errors))
    return rows


def check_fit(np,rows,p):
    info={}
    for fam in FAMILIES:
        starts=[r for r in rows if r["family"]==fam and r["arm"]==0]
        if len(starts)!=12:
            raise ValueError("BAD_FIT_VARIANTS")
        winning=[]
        reward_cases=0
        action_sensitive=0
        deltas={}
        for v in cohort(p,"FIT"):
            group=[r for r in rows if r["family"]==fam and r["variant"]==v["id"]]
            reward=[r["reward"] for r in group]
            winning.append(max(range(4),key=lambda a:(reward[a],-a)))
            reward_cases+=int(max(reward)-min(reward)>.01)
            D=np.asarray([r["delta"] for r in group])
            action_sensitive+=int(float(np.max(np.sum((D-D[0])**2,axis=1)))>1e-4)
        for a in range(4):
            vectors=np.asarray([r["delta"] for r in rows if r["family"]==fam and r["arm"]==a])
            deltas[str(a)]={"unique_sha":len({r["delta_sha256"] for r in rows if
                 r["family"]==fam and r["arm"]==a}),
                 "max_squared_delta_distance":float(np.max(np.sum((vectors-vectors[0])**2,axis=1)))}
        info[fam]={"unique_FIT_reset_sha":len({r["reset_sha256"] for r in starts}),
            "FIT_best_action_ids":sorted(set(winning)),
            "FIT_reward_sensitive_cases":reward_cases,
            "FIT_action_sensitive_cases":action_sensitive,
            "delta_by_arm":deltas,
            "state_transitions_variable":all(v["unique_sha"]>=2 and
                   v["max_squared_delta_distance"]>=1e-4 for v in deltas.values())}
    source_ok=all(z["unique_FIT_reset_sha"]==12 and
          z["FIT_action_sensitive_cases"]==12 and
          z["FIT_reward_sensitive_cases"]>=6 for z in info.values())
    enough=(source_ok and len(info["reaching"]["FIT_best_action_ids"])>=2
            and sum(z["state_transitions_variable"] for z in info.values())>=2)
    return info,enough


def learn(np,rows):
    # Strong source-only conventional next-state regressors, FIT outcomes only.
    source={}
    for fam in FAMILIES:
        arms={}
        for arm in range(4):
            examples=[r for r in rows if r["family"]==fam and r["arm"]==arm]
            if len(examples)!=12 or [r["variant"] for r in examples]!=list(range(12)):
                raise ValueError("UNEQUAL_SOURCE_INFORMATION")
            X=np.asarray([r["x"] for r in examples],dtype=np.float64)
            D=np.asarray([r["delta"] for r in examples],dtype=np.float64)
            Z=np.column_stack([np.ones(12),X])
            coef=Z.T@np.linalg.solve(Z@Z.T+np.eye(12),D)
            arms[str(arm)]={"mean_delta":np.mean(D,axis=0).tolist(),
                "ridge":coef.tolist(),
                "records":[{"variant":r["variant"],"x":r["x"],"delta":r["delta"]}
                          for r in examples]}
        source[fam]=arms
    return {"schema":"mass.lcrm01.k4q.fit-only-public-forward-baselines.v1",
            "by_family":source,"original_FIT_experiences":144}


def predictor(np,state,family,arm,x,method):
    if method not in METHODS:raise ValueError("UNREGISTERED_FORWARD_PREDICTOR")
    arm_state=state["by_family"][family][str(arm)]
    if method=="mean_delta":return np.asarray(arm_state["mean_delta"])
    if method=="ridge_delta":
        return np.asarray([1]+x)@np.asarray(arm_state["ridge"])
    records=arm_state["records"]
    nearest=min(records,key=lambda r:(float(np.sum(
                (np.asarray(r["x"])-np.asarray(x))**2)),r["variant"]))
    return np.asarray(nearest["delta"])


def plan(np,state,contexts):
    out=[]
    for c in contexts:
        predictions={m:{str(arm):predictor(np,state,c["family"],arm,c["x"],m).tolist()
                      for arm in range(4)} for m in METHODS}
        out.append({"family":c["family"],"variant":c["variant"],
                    "reset_sha256":c["reset_sha256"],"predictions":predictions})
    return out


def score(np,actual,planrows):
    rows=[]
    for p in planrows:
        group=[r for r in actual if r["family"]==p["family"] and r["variant"]==p["variant"]]
        if len(group)!=4 or [r["arm"] for r in group]!=[0,1,2,3] or any(
            r["reset_sha256"]!=p["reset_sha256"] for r in group):
            raise ValueError("HELDOUT_SOURCE_HIDDEN_LEAK_OR_DRIFT")
        for r in group:
            errors={m:float(np.mean((np.asarray(r["delta"])-
                np.asarray(p["predictions"][m][str(r["arm"])]))**2))
                     for m in METHODS}
            rows.append({"family":r["family"],"variant":r["variant"],"arm":r["arm"],
                "reward":r["reward"],"errors":errors,
                "reset_sha256":r["reset_sha256"]})
    return rows


def summarize(rows):
    answer={}
    for fam in FAMILIES:
        sub=[r for r in rows if r["family"]==fam]
        if not sub:raise ValueError("HOLDOUT_FAMILY_EMPTY")
        errors={m:sum(r["errors"][m] for r in sub)/len(sub) for m in METHODS}
        winners={}
        for v in sorted({r["variant"] for r in sub}):
            rr=[r for r in sub if r["variant"]==v]
            winners[str(v)]=max(range(4),key=lambda a:(rr[a]["reward"],-a))
        best=min(("one_nn_delta","ridge_delta"),key=lambda m:(errors[m],m))
        base=errors["mean_delta"]
        answer[fam]={"MSE":errors,"best_fitted_model":best,
            "best_fitted_MSE_reduction":(base-errors[best])/max(base,1e-12),
            "hindsight_best_arm_by_variant":winners,
            "distinct_hindsight_best_arms":len(set(winners.values()))}
    return answer


def verdict(check,dev):
    tests={}
    for fam in FAMILIES:
        tests[fam+"_CHECK_5pct_forward_uplift"]=check[fam]["best_fitted_MSE_reduction"]>=.05
        tests[fam+"_DEV_5pct_forward_uplift"]=dev[fam]["best_fitted_MSE_reduction"]>=.05
    trained=sum(tests[f+"_CHECK_5pct_forward_uplift"] and
                tests[f+"_DEV_5pct_forward_uplift"] for f in FAMILIES)
    outcome_diverse=sum(z["distinct_hindsight_best_arms"]>=2 for z in dev.values())
    qualified=trained>=2 and outcome_diverse>=2
    return {"result":"SOURCE_OBSERVABILITY_AND_BASELINE_LEARNABILITY_QUALIFIED" if qualified
         else "SOURCE_INFORMATION_OR_BASELINE_LEARNABILITY_NOT_QUALIFIED",
       "forward_qualified_task_families":trained,"hindsight_action_diverse_families":outcome_diverse,
       "tests":tests,"science_accepted":False,"native_cognition_claim":False}


def execute(root,p):
    from k4a_control_replay import verify_source
    if p["upstream"]["git_commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("PINNED_ORIGINAL_SOURCE_DRIFT")
    root=root.resolve()
    verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("NONPINNED_SIMULATOR_IMPORTED")
    wall=time.perf_counter();cpu=time.process_time()
    fit=collect(np,CausalWorld,generate_task,p,"FIT")
    fit_report,eligible=check_fit(np,fit,p)
    base={"schema":SCHEMA,"gate":"LCRM01-K4Q",
        "protocol_sha256":sha(FROZEN.read_bytes()),
        "source_commit":p["upstream"]["git_commit"],
        "FIT_rows":fit,"FIT_exposures":len(fit),"FIT_source_calibration":fit_report,
        "CHECK_exposures":0,"DEV_exposures":0,
        "K4P_original_NO_GO_preserved":True,
        "scientific_first_use":False,"scientific_accepted":False}
    if not eligible:
        base.update({"result":"FIT_PHYSICAL_CAUSAL_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
          "resource":{"cpu_seconds":time.process_time()-cpu,
             "wall_seconds":time.perf_counter()-wall,
             "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
        return base
    start_train_cpu=time.process_time()
    fitted=learn(np,fit)
    state=json.loads(canon(fitted))
    original_hash=sha(canon(state).encode())
    for example in fit:
        for method in METHODS:
            if not np.array_equal(predictor(np,fitted,example["family"],example["arm"],example["x"],method),
                    predictor(np,state,example["family"],example["arm"],example["x"],method)):
                raise ValueError("FITTED_CONVENTIONAL_PREDICTOR_RELOAD_DRIFT")
    train_cpu=time.process_time()-start_train_cpu
    # CHECK and DEV action predictions are frozen from public reset-only probes BEFORE
    # the FIRST heldout physics reward or transition is produced.
    contexts={phase:[reset_probe(np,CausalWorld,generate_task,p,fam,v)
             for fam in FAMILIES for v in cohort(p,phase)]
             for phase in ("CHECK","DEV")}
    plans={phase:plan(np,state,contexts[phase]) for phase in ("CHECK","DEV")}
    check=collect(np,CausalWorld,generate_task,p,"CHECK")
    dev=collect(np,CausalWorld,generate_task,p,"DEV")
    verify_source(root)
    check_scored=score(np,check,plans["CHECK"])
    dev_scored=score(np,dev,plans["DEV"])
    check_info=summarize(check_scored);dev_info=summarize(dev_scored)
    result=verdict(check_info,dev_info)
    base.update({"result":"PUBLIC_SOURCE_QUALIFICATION_COMPLETE",
        "fit_model_sha256":original_hash,"fit_model_bytes":len(canon(state).encode()),
        "FIT_baseline_train_cpu_seconds":train_cpu,
        "CHECK_rows":check,"DEV_rows":dev,
        "CHECK_exposures":len(check),"DEV_exposures":len(dev),
        "CHECK_plan":plans["CHECK"],"DEV_plan":plans["DEV"],
        "CHECK_scored":check_scored,"DEV_scored":dev_scored,
        "CHECK_information":check_info,"DEV_information":dev_info,
        "source_qualification":result,
        "resource":{"cpu_seconds":time.process_time()-cpu,
           "wall_seconds":time.perf_counter()-wall,
           "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return base


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--causalworld-repo",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("K4Q_ORIGINAL_OUTPUT_ALREADY_EXISTS")
    try:r=execute(args.causalworld_repo,frozen())
    except Exception as e:
        r={"schema":SCHEMA,"gate":"LCRM01-K4Q","result":"INFRASTRUCTURE_OR_SOURCE_BLOCKED",
           "error_type":type(e).__name__,"error":str(e),
           "traceback_tail":traceback.format_exc().splitlines()[-12:],
           "K4P_original_NO_GO_preserved":True,
           "scientific_first_use":False,"scientific_accepted":False}
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("K4Q_ORIGINAL_RESULT="+r["result"])
    if "FIT_source_calibration" in r:
        print("K4Q_FIT_INFO="+canon({k:{"best_actions":v["FIT_best_action_ids"],
            "sensitive_actions":v["FIT_action_sensitive_cases"],
            "variable_public_deltas":v["state_transitions_variable"]}
            for k,v in r["FIT_source_calibration"].items()}))
    if "source_qualification" in r:
        print("K4Q_SCIENTIFIC_SOURCE_GATE="+r["source_qualification"]["result"])
        print("K4Q_FORWARD_AND_CAUSAL_DETAIL="+canon({"check":r["CHECK_information"],
              "dev":r["DEV_information"]}))
    return 1 if r["result"]=="INFRASTRUCTURE_OR_SOURCE_BLOCKED" else 0


if __name__=="__main__":
    sys.exit(main())
