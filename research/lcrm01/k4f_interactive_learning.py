#!/usr/bin/env python3
"""K4F public interactive learning/retention/unfamiliar-task experiment.

Frozen prospective protocol: 2 FIT families, 4 FIT seeds, 4 discrete legal
actions, CHECK veto only, once-only unfamiliar picking DEV. No FSA first use,
native Wingless/Yggdrasil claim, hidden state, or hindsight tuning.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import traceback

FROZEN=Path(__file__).with_name("k4f_frozen_interactive_learning.json")
SCHEMA="mass.lcrm01.k4f.fitted-interaction-transfer-development.v1"
METHODS=("selective_memory","ridge","knn","mean","fixed")
TRAINABLE=METHODS[:-1]

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()

def read_protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p["schema"]!="mass.lcrm01.k4f.frozen-actual-online-learning-and-unfamiliar-transfer.v1":
        raise ValueError("FROZEN_SCHEMA_DRIFT")
    if p["cohorts"]["fit_seeds"]!=[101,103,107,109] or p["cohorts"]["check_seeds"]!=[201,203]:
        raise ValueError("FROZEN_TRAIN_CHECK_DRIFT")
    if p["cohorts"]["unfamiliar_dev_seeds"]!=[301,307,311,313] or p["cohorts"]["same_family_dev_seeds"]!=[401,407]:
        raise ValueError("FROZEN_DEV_SEED_DRIFT")
    if p["world"]["task_fit"]!=["reaching","pushing"] or p["world"]["task_unfamiliar"]!=["picking"]:
        raise ValueError("FROZEN_FAMILY_DRIFT")
    if [(x["id"],x["delta_joint0"],x["delta_joint2"]) for x in p["world"]["action_menu"]] != [
        (0,0,0),(1,0.04,0),(2,0,0.03),(3,0.04,0.03)]:
        raise ValueError("ACTION_MENU_DRIFT")
    return p

def features(np, observation):
    """Only real structured PUBLIC reset observation; no task name or future."""
    a=np.asarray(observation,dtype=np.float64).ravel()
    if a.size==0 or a.size>2048 or not np.all(np.isfinite(a)):
        raise ValueError("PUBLIC_OBSERVATION_INVALID")
    core=np.zeros(12,dtype=np.float64)
    core[:min(12,a.size)]=np.tanh(np.clip(a[:12],-5,5))
    extra=np.array([min(a.size,256)/256.0,
        math.tanh(float(np.mean(a))),math.tanh(float(np.std(a)))])
    return [float(v) for v in np.concatenate((core,extra))]

def action_for(np,space,choice,p):
    options=p["world"]["action_menu"]
    if type(choice)!=int or choice<0 or choice>=len(options):
        raise ValueError("NON_FROZEN_ACTION")
    lo=np.asarray(space.low,dtype=np.float64)
    hi=np.asarray(space.high,dtype=np.float64)
    if lo.shape!=(9,) or hi.shape!=(9,) or not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)):
        raise ValueError("ACTION_SPACE_INVALID")
    a=np.array(lo,copy=True)
    a[0]+=options[choice]["delta_joint0"]
    a[2]+=options[choice]["delta_joint2"]
    if np.any(a<lo) or np.any(a>hi):
        raise ValueError("ACTION_OUT_OF_BOUNDS")
    return a

def simulate(np,CausalWorld,generate_task,p,task,seed,chooser):
    if task not in ("reaching","pushing","picking") or type(seed)!=int:
        raise ValueError("TASK_SEED_INVALID")
    w=p["world"]
    env=CausalWorld(task=generate_task(task_generator_id=task),
        enable_visualization=False,seed=seed,
        skip_frame=w["skip_frame"],action_mode=w["action_mode"],
        observation_mode=w["observation_mode"],
        normalize_actions=w["normalize_actions"],
        normalize_observations=w["normalize_observations"],
        max_episode_length=w["max_episode_length"])
    try:
        x=features(np,env.reset())
        choice=int(chooser(x))
        a=action_for(np,env.action_space,choice,p)
        rewards=[]
        for _ in range(w["episode_steps"]):
            _obs,reward,done,_info=env.step(a)
            v=float(reward)
            if not math.isfinite(v):
                raise ValueError("NONFINITE_PUBLIC_REWARD")
            rewards.append(v)
            if done:
                break
        if len(rewards)==0:
            raise ValueError("NO_PUBLIC_INTERACTION")
        return {"x":x,"choice":choice,"total_return":float(sum(rewards)),
                "reward_steps":len(rewards)}
    finally:
        env.close()

def kernel_pred(memory,x,arm,temp):
    candidates=[r for r in memory if r["choice"]==arm]
    if not candidates:
        return None
    weights=[math.exp(-sum((a-b)**2 for a,b in zip(x,r["x"]))/temp)
             for r in candidates]
    total=sum(weights)
    if total<=0:
        return float(sum(r["total_return"] for r in candidates)/len(candidates))
    return float(sum(w*r["total_return"] for w,r in zip(weights,candidates))/total)

def fit_models(np,samples,p):
    if len(samples)!=32 or set(r["choice"] for r in samples)!={0,1,2,3}:
        raise ValueError("MATCHED_FIT_EXPERIENCES_MISSING")
    controls=p["models"]
    limit=controls["episodic_memory_capacity"]
    threshold=controls["novelty_threshold"]
    fast=[]
    counts=[0,0,0,0]
    totals=[0.,0.,0.,0.]
    # Updates are chronological and based only on observed FIT rewards.
    for row in samples:
        arm=row["choice"]
        current=totals[arm]/counts[arm] if counts[arm] else 0.0
        surprise=abs(row["total_return"]-current)
        if counts[arm]==0 or surprise>=threshold:
            fast.append(row)
            if len(fast)>limit:
                fast.pop(0)
        counts[arm]+=1
        totals[arm]+=row["total_return"]
    if min(counts)!=8:
        raise ValueError("FIT_ARM_EXPOSURE_MISMATCH")
    means=[float(t/c) for t,c in zip(totals,counts)]
    # Fully fitted conventional ridge uses exactly the same 32 public records.
    dim=16*4
    matrix=np.zeros((len(samples),dim),dtype=np.float64)
    target=np.array([r["total_return"] for r in samples],dtype=np.float64)
    for i,r in enumerate(samples):
        start=r["choice"]*16
        matrix[i,start:start+16]=np.array([1.0]+r["x"])
    ridge=np.linalg.solve(matrix.T@matrix+
          np.eye(dim)*controls["ridge_lambda"],matrix.T@target)
    if not np.all(np.isfinite(ridge)):
        raise ValueError("RIDGE_NUMERIC_FAILURE")
    return {"format":"mass.k4f.learned-state.v1","samples":samples,"fast":fast,
            "counts":counts,"means":means,"ridge":ridge.tolist(),
            "training_experiences":len(samples),"novelty_threshold":threshold}

def predict(np,state,x,arm,p,method):
    if arm not in range(4) or method not in METHODS:
        raise ValueError("UNKNOWN_METHOD_ARM")
    if method=="fixed":
        return 0.0 if arm==0 else -1.0e12
    if method=="mean":
        return state["means"][arm]
    if method=="ridge":
        w=np.asarray(state["ridge"][arm*16:(arm+1)*16],dtype=np.float64)
        return float(w@np.asarray([1.0]+x,dtype=np.float64))
    if method=="knn":
        rows=[(sum((a-b)**2 for a,b in zip(x,r["x"])),i,r)
              for i,r in enumerate(state["samples"]) if r["choice"]==arm]
        rows.sort(key=lambda y:(y[0],y[1]))
        k=p["models"]["knn_neighbors"]
        if not rows:
            raise ValueError("NO_TRAINED_KNN_ACTION")
        return float(sum(r["total_return"] for _,_,r in rows[:k])/min(k,len(rows)))
    local=kernel_pred(state["fast"],x,arm,p["models"]["kernel_temperature"])
    return float(state["means"][arm] if local is None else
                 0.5*state["means"][arm]+0.5*local)

def choose(np,state,x,p,method):
    values=[predict(np,state,x,a,p,method) for a in range(4)]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("NONFINITE_PREDICTION")
    return int(max(range(4),key=lambda a:(values[a],-a)))

def evaluate(np,CausalWorld,generate_task,p,phase,state):
    c=p["cohorts"]
    if phase=="check":
        pairs=[(task,seed) for task in p["world"]["task_fit"] for seed in c["check_seeds"]]
    elif phase=="dev_unfamiliar":
        pairs=[("picking",seed) for seed in c["unfamiliar_dev_seeds"]]
    elif phase=="dev_familiar":
        pairs=[(task,seed) for task in p["world"]["task_fit"] for seed in c["same_family_dev_seeds"]]
    else:
        raise ValueError("UNKNOWN_SCORING_PHASE")
    rows=[]
    for task,seed in pairs:
        for method in METHODS:
            trial=simulate(np,CausalWorld,generate_task,p,task,seed,
                lambda x,m=method:choose(np,state,x,p,m))
            rows.append({"task":task,"seed":seed,"method":method,
                         "action":trial["choice"],"total_return":trial["total_return"],
                         "reward_steps":trial["reward_steps"]})
    return rows

def means(rows):
    return {m:float(sum(r["total_return"] for r in rows if r["method"]==m)/
              sum(r["method"]==m for r in rows)) for m in METHODS}

def decision(check,unfamiliar,familiar,p):
    cm=means(check);um=means(unfamiliar);fm=means(familiar)
    best_u=max((um[m],m) for m in ("ridge","knn","mean"))
    best_c=max(cm[m] for m in ("ridge","knn","mean"))
    best_f=max(fm[m] for m in ("ridge","knn","mean"))
    margin=um["selective_memory"]-best_u[0]
    eligible=(margin>=0.01 and
              cm["selective_memory"]>=best_c-0.1 and
              fm["selective_memory"]>=best_f-0.1)
    return {"decision":"BOUNDED_DEV_TRANSFER_CANDIDATE" if eligible else
            "NO_EVIDENCE_OF_SUPERIOR_UNFAMILIAR_TRANSFER",
            "unfamiliar_mean_advantage_vs_best_fitted_control":margin,
            "best_unfamiliar_fitted_control":best_u[1],
            "check_mean":cm,"unfamiliar_mean":um,"familiar_dev_mean":fm,
            "scientific_acceptance":False,"native_transfer_claim":False}

def experiment(repo,p):
    from k4a_control_replay import verify_source
    if p["world"]["commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("FROZEN_ORIGINAL_COMMIT_DRIFT")
    root=repo.resolve(); verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("PUBLIC_CW_IMPORT_MISMATCH")
    t0=time.perf_counter();cpu0=time.process_time()
    samples=[]
    for task in p["world"]["task_fit"]:
        for seed in p["cohorts"]["fit_seeds"]:
            for arm in range(4):
                r=simulate(np,CausalWorld,generate_task,p,task,seed,lambda x,i=arm:i)
                samples.append({"x":r["x"],"choice":arm,"total_return":r["total_return"]})
    fitted=fit_models(np,samples,p)
    payload=canon(fitted)
    restored=json.loads(payload)
    probe=[samples[0]["x"],samples[-1]["x"],[0.0]*15]
    retention=all(
        predict(np,fitted,x,arm,p,method)==predict(np,restored,x,arm,p,method)
        for x in probe for arm in range(4) for method in METHODS)
    if not retention:
        raise ValueError("CHECKPOINT_RETENTION_FAILED")
    check=evaluate(np,CausalWorld,generate_task,p,"check",restored)
    # CHECK is a frozen veto, not a tuning loop. No model changes after CHECK.
    uncommon=evaluate(np,CausalWorld,generate_task,p,"dev_unfamiliar",restored)
    familiar=evaluate(np,CausalWorld,generate_task,p,"dev_familiar",restored)
    verify_source(root)
    cpu=time.process_time()-cpu0;wall=time.perf_counter()-t0
    mem=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
    return {"schema":SCHEMA,"protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
            "source_commit":p["world"]["commit"],"result":"COMPLETE_PUBLIC_DEVELOPMENT",
            "fit_trials":len(samples),"check_trials":len(check),
            "unfamiliar_dev_trials":len(uncommon),"familiar_dev_trials":len(familiar),
            "fit_digest":digest(samples),"learned_checkpoint_sha256":hashlib.sha256(payload.encode()).hexdigest(),
            "learned_checkpoint_bytes":len(payload),"learned_state_retained":retention,
            "learned_state_changed":any(abs(v)>1.e-12 for v in fitted["means"]),
            "decision":decision(check,uncommon,familiar,p),
            "check_records":check,"unfamiliar_dev_records":uncommon,
            "familiar_dev_records":familiar,
            "resource":{"whole_run_cpu_seconds":cpu,"whole_run_wall_seconds":wall,
                        "peak_rss_bytes":mem},
            "no_hidden_outcomes_for_learners":True,"no_dev_training":True,
            "negative_history_preserved":True,"scientific_first_use":False,
            "native_cognition_qualified":False,"scientific_accepted":False,
            "dispatch_authorized":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--causalworld-repo",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("OUTPUT_PATH_NOT_FRESH")
    try:
        p=read_protocol();out=experiment(args.causalworld_repo,p)
    except Exception as e:
        out={"schema":SCHEMA,"result":"INFRASTRUCTURE_OR_RESEARCH_RUNTIME_FAILURE",
            "error_type":type(e).__name__,"error":str(e),
            "traceback_tail":traceback.format_exc().splitlines()[-12:],
            "scientific_first_use":False,"scientific_accepted":False,
            "negative_history_preserved":True}
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print("K4F_RESULT="+out["result"])
    if out.get("decision"):
        print("K4F_UNFAMILIAR_TRANSFER="+out["decision"]["decision"])
        print("K4F_UNFAMILIAR_ADVANTAGE="+str(out["decision"]["unfamiliar_mean_advantage_vs_best_fitted_control"]))
    print("K4F_EVIDENCE="+str(args.output))
    return 0 if out["result"]=="COMPLETE_PUBLIC_DEVELOPMENT" else 1

if __name__=="__main__":
    sys.exit(main())
