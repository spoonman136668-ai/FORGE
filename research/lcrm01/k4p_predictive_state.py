#!/usr/bin/env python3
"""K4P: genuinely FIT-learned compact predictive state in original public physics.

Development only. Exact public experience parity. All heldout policies are
selected using reset-only observations before any heldout reward is generated.
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

FROZEN=Path(__file__).with_name("k4p_frozen_predictive_state.json")
SCHEMA="mass.lcrm01.k4p.original-public-predictive-state-study.v1"
METHODS=("predictive_state","predictive_state_terminal_shift",
         "ridge_latent","ridge_raw","rbf_kernel_ridge","raw_1nn",
         "fit_mean","fixed_low")
CONTROLS=("ridge_latent","ridge_raw","rbf_kernel_ridge","raw_1nn","fit_mean","fixed_low")
FIT_FAMILIES=("reaching","pushing")
ALL_FAMILIES=("reaching","pushing","picking")


def canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4p.frozen-compact-predictive-state-v1":
        raise ValueError("K4P_PROTOCOL_SCHEMA_DRIFT")
    v=p["cohort"]["variants"]
    expected=[(dx,dy) for dx in (-.087,-.037,.037,.087) for dy in (-.058,0,.058)]
    expected += [(0,-.062),(0,.062)]
    expected += [(dx,dy) for dx in (-.079,-.011,.011,.079) for dy in (-.048,.048)]
    if (len(v)!=22 or [(x["goal_dx"],x["goal_dy"]) for x in v]!=expected
        or [(x["id"],x["phase"]) for x in v]!=[
          (i,"FIT" if i<12 else "CHECK" if i<14 else "DEV") for i in range(22)]
        or p["cohort"]["sim_seed"]!=929
        or p["cohort"]["train_families"]!=list(FIT_FAMILIES)
        or p["cohort"]["unfamiliar_family"]!="picking"
        or p["evaluation"]["methods"]!=list(METHODS)
        or p["learning"]["rank_initial"]!=6
        or p["learning"]["rank_delta"]!=4
        or p["learning"]["lambda"]!=1
        or p["learning"]["kernel_sigma"]!=.25
        or p["cohort"]["FIT_episodes"]!=96
        or p["cohort"]["CHECK_episodes"]!=24
        or p["cohort"]["DEV_episodes"]!=96):
        raise ValueError("K4P_FROZEN_COHORT_OR_MECHANISM_DRIFT")
    # Fail closed on any earlier consumed public CausalWorld task offset.
    from k4i_information_sufficiency import load as k4i_load
    from k4j_replicate import frozen as k4j_load
    from k4k_compression import frozen as k4k_load
    from k4l_multicontext import protocol as k4l_load
    from k4n_decision_coreset import protocol as k4n_load
    old=(k4i_load()["variants"]+k4j_load()["design"]["variants"]+
         k4k_load()["cohort"]["world_variants"]+
         k4l_load()["cohort"]["variants"]+k4n_load()["cohort"]["variants"])
    seen={(r["goal_dx"],r["goal_dy"]) for r in old}
    if any((r["goal_dx"],r["goal_dy"]) in seen for r in v):
        raise ValueError("K4P_CONSUMED_SOURCE_COHORT_REUSED")
    return p


def subset(p,phase):
    return [x for x in p["cohort"]["variants"] if x["phase"]==phase]


def task(np,generate_task,family,v):
    dx,dy=v["goal_dx"],v["goal_dy"]
    if family=="reaching":
        params={"default_goal_60":np.array([dx,dy,.10]),
                "default_goal_120":np.array([dx,dy,.13]),
                "default_goal_300":np.array([dx,dy,.16])}
    elif family=="pushing":
        params={"tool_block_position":np.array([-dx,-.08,.0325]),
                "goal_block_position":np.array([dx,.08+dy,.0325])}
    elif family=="picking":
        params={"tool_block_position":np.array([dx,dy,.0325])}
    else:
        raise ValueError("UNKNOWN_FAMILY")
    return generate_task(task_generator_id=family,**params)


def public(np,obs):
    vals=np.asarray(obs,dtype=np.float64).ravel()
    if not 1<=vals.size<=128 or not np.all(np.isfinite(vals)):
        raise ValueError("NONFINITE_OR_UNEXPECTED_PUBLIC_OBSERVATION")
    out=np.zeros(128,dtype=np.float64)
    out[:vals.size]=np.tanh(vals/.5)
    return out


def action(np,space,arm):
    if type(arm)!=int or arm not in range(4):
        raise ValueError("OUTSIDE_FROZEN_ACTION_MENU")
    lo=np.asarray(space.low,dtype=np.float64)
    hi=np.asarray(space.high,dtype=np.float64)
    if (lo.shape!=(9,) or hi.shape!=(9,) or
        not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)) or np.any(lo>=hi)):
        raise ValueError("INVALID_PUBLIC_JOINT_BOUNDS")
    factors=([0.]*9 if arm==0 else [.5]*9 if arm==1 else [1.]*9 if arm==2 else
             [.2 if j%2==0 else .8 for j in range(9)])
    x=lo+(hi-lo)*np.asarray(factors)
    if np.any(x<lo-1e-12) or np.any(x>hi+1e-12):
        raise ValueError("ACTION_OUT_OF_LEGAL_BOUNDS")
    return np.minimum(np.maximum(x,lo),hi)


def new_world(CausalWorld,np,generate_task,p,family,v):
    c=p["cohort"]
    return CausalWorld(task=task(np,generate_task,family,v),
       enable_visualization=False,seed=c["sim_seed"],skip_frame=c["skip_frame"],
       action_mode="joint_positions",observation_mode="structured",
       normalize_actions=False,normalize_observations=False,
       max_episode_length=c["max_episode_length"])


def reset_only(np,CausalWorld,generate_task,p,family,v):
    e=new_world(CausalWorld,np,generate_task,p,family,v)
    try:
        z=np.asarray(e.reset(),dtype=np.float64).ravel()
        return {"family":family,"variant":v["id"],"x":public(np,z).tolist(),
                "initial_sha256":sha(z.tobytes())}
    finally:
        e.close()


def experience(np,CausalWorld,generate_task,p,family,v,arm):
    e=new_world(CausalWorld,np,generate_task,p,family,v)
    try:
        raw=np.asarray(e.reset(),dtype=np.float64).ravel()
        x=public(np,raw)
        start_digest=sha(raw.tobytes())
        a=action(np,e.action_space,arm)
        total=0.0; final_raw=raw; steps=0
        for _ in range(p["cohort"]["steps"]):
            obs,reward,done,info=e.step(a)
            final_raw=np.asarray(obs,dtype=np.float64).ravel()
            rv=float(reward)
            if not math.isfinite(rv):
                raise ValueError("NONFINITE_REAL_PUBLIC_REWARD")
            total+=rv;steps+=1
            if done:break
        return {"family":family,"variant":v["id"],"arm":arm,
                "reward":float(total),"x":x.tolist(),
                "delta":(public(np,final_raw)-x).tolist(),
                "start_sha256":start_digest,
                "end_sha256":sha(final_raw.tobytes()),
                "steps":steps,"action_sha256":sha(a.tobytes())}
    finally:
        e.close()


def collect(np,CausalWorld,generate_task,p,phase):
    families=FIT_FAMILIES if phase=="FIT" else ALL_FAMILIES
    rows=[experience(np,CausalWorld,generate_task,p,family,v,arm)
       for family in families for v in subset(p,phase) for arm in range(4)]
    expected=len(families)*len(subset(p,phase))*4
    if len(rows)!=expected:
        raise ValueError("MISSING_ACTUAL_PUBLIC_EPISODE")
    for family in families:
        for v in subset(p,phase):
            hits=[r for r in rows if r["family"]==family and r["variant"]==v["id"]]
            if [r["arm"] for r in hits]!=[0,1,2,3]:
                raise ValueError("ACTION_PARITY_SOURCE_INVALID")
            if len({r["start_sha256"] for r in hits})!=1:
                raise ValueError("PAIRED_PUBLIC_RESET_DRIFT")
            if len({r["action_sha256"] for r in hits})!=4:
                raise ValueError("REPEATED_OR_MISSING_ACTION")
    return rows


def ridge(np,X,Y,lam=1.):
    X=np.asarray(X,dtype=np.float64)
    Y=np.asarray(Y,dtype=np.float64)
    if len(X)!=len(Y) or len(X)==0:
        raise ValueError("UNPAIRED_FIT")
    return (X.T@np.linalg.solve(X@X.T+np.eye(len(X))*lam,Y)).tolist()


def fit_basis(np,data,n):
    D=np.asarray(data,dtype=np.float64)
    mean=D.mean(axis=0)
    vectors=np.linalg.svd(D-mean,full_matrices=False)[2][:n]
    if vectors.shape!=(n,128):
        raise ValueError("PUBLIC_PREDICTIVE_BASIS_RANK_MISSING")
    return mean.tolist(),vectors.tolist()


def design(np,vec,mean,basis):
    return (np.asarray(vec)-np.asarray(mean))@np.asarray(basis).T


def trained(np,fit):
    if len(fit)!=96:
        raise ValueError("FIT_INFORMATION_NOT_COMPLETE")
    models={}
    for family in FIT_FAMILIES:
        records=[r for r in fit if r["family"]==family]
        initial=[r["x"] for r in records if r["arm"]==0]
        deltas=[r["delta"] for r in records]
        mean_x,basis_x=fit_basis(np,initial,6)
        mean_d,basis_d=fit_basis(np,deltas,4)
        per_arm={}
        all_rewards=[r["reward"] for r in records]
        reward_mean=float(np.mean(all_rewards))
        reward_std=max(.01,float(np.std(all_rewards)))
        for arm in range(4):
            subset=[r for r in records if r["arm"]==arm]
            if len(subset)!=12 or [r["variant"] for r in subset]!=list(range(12)):
                raise ValueError("ORIGINAL_ARM_TRAIN_SOURCE_NOT_12")
            Q=np.asarray([design(np,r["x"],mean_x,basis_x) for r in subset])
            H=np.column_stack([np.ones(12),Q])
            target_delta=np.asarray([design(np,r["delta"],mean_d,basis_d) for r in subset])
            returns=np.asarray([r["reward"] for r in subset])
            t_weight=np.asarray(ridge(np,H,target_delta))
            predicted_train=np.asarray([np.asarray([1]+list(Q[i]))@np.asarray(
                ridge(np,H[[j for j in range(12) if j!=i]],
                          target_delta[[j for j in range(12) if j!=i]]))
                         for i in range(12)])
            head=np.column_stack([np.ones(12),Q,predicted_train])
            reward_head=ridge(np,head,returns)
            direct_latent=ridge(np,H,returns)
            raw_X=np.column_stack([np.ones(12),
                     np.asarray([r["x"] for r in subset])])
            direct_raw=ridge(np,raw_X,returns)
            x=np.asarray([r["x"] for r in subset])
            dist=((x[:,None,:]-x[None,:,:])**2).sum(axis=2)
            kernel=np.exp(-dist/(2*.25*.25))
            alpha=np.linalg.solve(kernel+np.eye(12),returns)
            shifted_delta=np.roll(target_delta,1,axis=0)
            shifted_transition=ridge(np,H,shifted_delta)
            per_arm[str(arm)]={"transition":t_weight.tolist(),
                "shifted_transition":shifted_transition,
                "head":reward_head,"direct_latent":direct_latent,
                "direct_raw":direct_raw,
                "kernel_alpha":alpha.tolist(),
                "records":[{"variant":r["variant"],"x":r["x"],"reward":r["reward"],
                       "latent_delta":list(target_delta[i])} for i,r in enumerate(subset)],
                "mean_reward":float(np.mean(returns)),
                "mean_latent_delta":list(np.mean(target_delta,axis=0))}
        models[family]={"mean_x":mean_x,"basis_x":basis_x,
              "mean_delta":mean_d,"basis_delta":basis_d,
              "fit_reward_mean":reward_mean,"fit_reward_std":reward_std,
              "by_arm":per_arm}
    return {"schema":"mass.k4p.learned-compact-transition-state.v1",
            "FIT_rows":96,"families":models}


def predict(np,model,family,x,arm,method):
    if method=="fixed_low":
        return 0.0 if arm==0 else -1e9
    m=model["families"][family]
    a=m["by_arm"][str(arm)]
    q=design(np,x,m["mean_x"],m["basis_x"])
    v=np.asarray([1]+list(q))
    if method=="fit_mean":return a["mean_reward"]
    if method=="ridge_latent":
        return float(v@np.asarray(a["direct_latent"]))
    if method=="ridge_raw":
        return float(np.asarray([1]+x)@np.asarray(a["direct_raw"]))
    if method=="raw_1nn":
        best=min(a["records"],key=lambda r:(float(
            np.sum((np.asarray(x)-np.asarray(r["x"]))**2)),r["variant"]))
        return best["reward"]
    if method=="rbf_kernel_ridge":
        xs=np.asarray([r["x"] for r in a["records"]])
        dif=np.asarray(x)-xs
        kval=np.exp(-np.sum(dif*dif,axis=1)/(2*.25*.25))
        return float(kval@np.asarray(a["kernel_alpha"]))
    if method in ("predictive_state","predictive_state_terminal_shift"):
        matrix=a["transition"] if method=="predictive_state" else a["shifted_transition"]
        nextstate=v@np.asarray(matrix)
        return float(np.concatenate([[1.],q,nextstate])@np.asarray(a["head"]))
    raise ValueError("UNFROZEN_POLICY_METHOD")


def choose(np,model,family,x,method):
    if method not in METHODS:
        raise ValueError("METHOD_NOT_REGISTERED")
    if family=="picking":
        # Never train on picking. Equal-weight normalized extrapolation from
        # reaching and pushing, identically for every frozen comparator.
        values=[sum((predict(np,model,family_fit,x,a,method)-
                   model["families"][family_fit]["fit_reward_mean"])/
                   model["families"][family_fit]["fit_reward_std"]
                   for family_fit in FIT_FAMILIES)/2 for a in range(4)]
    else:
        values=[predict(np,model,family,x,a,method) for a in range(4)]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("NONFINITE_POLICY_PREDICTION")
    return max(range(4),key=lambda a:(values[a],-a))


def freeze_plan(np,model,contexts):
    return [{"family":c["family"],"variant":c["variant"],
        "public_observation_sha256":c["initial_sha256"],
        "choices":{method:choose(np,model,c["family"],c["x"],method)
                   for method in METHODS}} for c in contexts]


def measure(np,model,contexts,plan):
    if len(contexts)!=30 or len(plan)!=30:
        raise ValueError("RESOURCE_CONTEXT_COHORT_DRIFT")
    out={}
    for method in METHODS:
        cpu=time.process_time_ns();wall=time.perf_counter_ns()
        for _ in range(200):
            for i,c in enumerate(contexts):
                if choose(np,model,c["family"],c["x"],method)!=plan[i]["choices"][method]:
                    raise ValueError("NONDETERMINISTIC_INFERENCE")
        out[method]={"cpu_ns":time.process_time_ns()-cpu,
                     "wall_ns":time.perf_counter_ns()-wall,
                     "decisions":6000}
    return out


def model_sizes(model):
    families=model["families"]
    pstate={f:{"mean_x":d["mean_x"],"basis_x":d["basis_x"],
      "mean_delta":d["mean_delta"],"basis_delta":d["basis_delta"],
      "by_arm":{a:{"transition":v["transition"],"head":v["head"]}
                for a,v in d["by_arm"].items()}} for f,d in families.items()}
    memories={f:{a:v["records"] for a,v in d["by_arm"].items()}
              for f,d in families.items()}
    return {"predictive_state":len(canon(pstate).encode()),
            "raw_1nn":len(canon(memories).encode()),
            "full_combined_fitted_state":len(canon(model).encode())}


def scoring(rows,plan):
    answer=[]
    for x in plan:
        records=[r for r in rows if r["family"]==x["family"] and r["variant"]==x["variant"]]
        if len(records)!=4 or [r["arm"] for r in records]!=[0,1,2,3]:
            raise ValueError("MISSING_REAL_ACTION_COMPARISON")
        if any(r["start_sha256"]!=x["public_observation_sha256"] for r in records):
            raise ValueError("HELDOUT_PUBLIC_CONTEXT_IDENTITIES_DRIFT")
        vals={r["arm"]:r["reward"] for r in records}
        answer.append({"family":x["family"],"variant":x["variant"],
          "action_reward":{str(a):vals[a] for a in range(4)},
          "offline_best_action":max(range(4),key=lambda a:(vals[a],-a)),
          "selected":{method:{"arm":a,"reward":vals[a]} for method,a in x["choices"].items()}})
    return answer


def dynamics(np,model,rows):
    results={}
    for family in FIT_FAMILIES:
        sub=[r for r in rows if r["family"]==family]
        predicted=[];ordinary=[]
        for r in sub:
            m=model["families"][family]
            a=m["by_arm"][str(r["arm"])]
            q=design(np,r["x"],m["mean_x"],m["basis_x"])
            actual=design(np,r["delta"],m["mean_delta"],m["basis_delta"])
            pred=np.asarray([1]+list(q))@np.asarray(a["transition"])
            predicted.append(float(np.sum((actual-pred)**2)))
            ordinary.append(float(np.sum((actual-np.asarray(a["mean_latent_delta"]))**2)))
        mean_pred=sum(predicted)/len(predicted)
        mean_fixed=sum(ordinary)/len(ordinary)
        results[family]={"predicted_latent_MSE":mean_pred,
            "armwise_mean_latent_MSE":mean_fixed,
            "fraction_MSE_reduction":(mean_fixed-mean_pred)/max(mean_fixed,1e-12)}
    return results


def decision(scores,model,dynamics_check,sizes,cost):
    summary={}
    for family in ALL_FAMILIES:
        cases=[s for s in scores if s["family"]==family]
        if len(cases)!=8:
            raise ValueError("MISSING_FAMILY_TRANSFER_CONTEXTS")
        means={method:sum(s["selected"][method]["reward"] for s in cases)/8
               for method in METHODS}
        hindsight_ids=sorted({s["offline_best_action"] for s in cases})
        selections={method:[s["selected"][method]["arm"] for s in cases]
                   for method in METHODS}
        best_control=max(CONTROLS,key=lambda m:(means[m],-CONTROLS.index(m)))
        better=sum(s["selected"]["predictive_state"]["reward"] >
             s["selected"][best_control]["reward"] for s in cases)
        summary[family]={"method_mean_reward":means,
              "strongest_conventional_control":best_control,
              "gain_vs_strongest_conventional":means["predictive_state"]-means[best_control],
              "strictly_improved_worlds":better,
              "offline_best_action_ids":hindsight_ids,"chosen_actions":selections}
    r=summary["reaching"]; push=summary["pushing"];pick=summary["picking"]
    ratio_mem=sizes["predictive_state"]/max(1,sizes["raw_1nn"])
    ratio_cpu=cost["predictive_state"]["cpu_ns"]/max(1,cost["raw_1nn"]["cpu_ns"])
    tests={
      "reaching_gain_gt_equal_0_01":r["gain_vs_strongest_conventional"]>=.01,
      "reaching_three_of_eight_strict_gains":r["strictly_improved_worlds"]>=3,
      "reaching_actions_context_dependent":len(set(r["chosen_actions"]["predictive_state"]))>=2,
      "pushing_not_worse_by_0_1":push["gain_vs_strongest_conventional"]>=-.1,
      "unfamiliar_picking_gain_ge_0_01":pick["gain_vs_strongest_conventional"]>=.01,
      "unfamiliar_picking_two_of_eight_strict_gains":pick["strictly_improved_worlds"]>=2,
      "unfamiliar_picking_reward_action_diversity":len(pick["offline_best_action_ids"])>=2,
      "unfamiliar_picking_choices_vary":len(set(pick["chosen_actions"]["predictive_state"]))>=2,
      "genuine_predictive_state_in_both_FIT_families":all(
           z["fraction_MSE_reduction"]>=.05 for z in dynamics_check.values()),
      "compact_state_size_le_half_raw_mem":ratio_mem<=.5,
      "inference_CPU_le_twice_raw_mem":ratio_cpu<=2.0}
    return {"result":"BOUNDED_PREDICTIVE_STATE_INTERACTIVE_TRANSFER_POSITIVE"
          if all(tests.values()) else "NO_QUALIFIED_PREDICTIVE_STATE_TRANSFER",
      "tests":tests,"per_family":summary,"CHECK_transition_prediction":dynamics_check,
      "model_size_ratio":ratio_mem,"inference_CPU_ratio":ratio_cpu,
      "scientific_accepted":False,"native_learning_architecture_proven":False}


def run(repo,p):
    from k4a_control_replay import verify_source
    if p["source"]["CausalWorld_commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("UPSTREAM_SOURCE_SHA_UNQUALIFIED")
    root=repo.resolve()
    verify_source(root);sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("UNAUTHORIZED_SIMULATOR_IMPORT")
    wall=time.perf_counter();cpu=time.process_time()
    fit=collect(np,CausalWorld,generate_task,p,"FIT")
    diversity={}
    for fam in FIT_FAMILIES:
        starting=[r for r in fit if r["family"]==fam and r["arm"]==0]
        if len({r["start_sha256"] for r in starting})!=12:
            raise ValueError("FIT_PUBLIC_STATES_NOT_DISTINCT")
        winners=[]
        for v in subset(p,"FIT"):
            items=[r for r in fit if r["family"]==fam and r["variant"]==v["id"]]
            winner=max(range(4),key=lambda a:(items[a]["reward"],-a))
            winners.append(winner)
        diversity[fam]=sorted(set(winners))
    basis={"schema":SCHEMA,"gate":"LCRM01-K4P",
        "protocol_sha256":sha(FROZEN.read_bytes()),
        "source_commit":p["source"]["CausalWorld_commit"],
        "FIT_rows":fit,"FIT_episodes":len(fit),
        "FIT_winning_actions":diversity,
        "CHECK_episodes":0,"DEV_episodes":0,
        "original_K4N_no_go_preserved":True,
        "original_K4O_diagnostic_preserved":True,
        "scientific_first_use":False,"scientific_accepted":False}
    if len(diversity["reaching"])<2:
        basis.update({"result":"FIT_ACTION_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
                      "resource":{"whole_cpu_seconds":time.process_time()-cpu,
                          "whole_wall_seconds":time.perf_counter()-wall,
                          "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
        return basis
    t0=time.process_time();w0=time.perf_counter()
    state=trained(np,fit)
    original=canon(state)
    restored=json.loads(original)
    if any(predict(np,state,r["family"],r["x"],arm,m)!=
           predict(np,restored,r["family"],r["x"],arm,m)
           for r in fit for arm in range(4) for m in METHODS):
        raise ValueError("FITTED_STATE_RESTART_PREDICTION_DRIFT")
    basis["checkpoint_sha256"]=sha(original.encode())
    basis["state_sizes"]=model_sizes(state)
    basis["shared_fit_cpu_seconds"]=time.process_time()-t0
    basis["shared_fit_wall_seconds"]=time.perf_counter()-w0
    # Zero reward-producing HELDOUT episodes have occurred at this point.
    contexts={phase:[reset_only(np,CausalWorld,generate_task,p,fam,v)
          for fam in ALL_FAMILIES for v in subset(p,phase)]
          for phase in ("CHECK","DEV")}
    planned={phase:freeze_plan(np,restored,contexts[phase])
             for phase in ("CHECK","DEV")}
    costs=measure(np,restored,contexts["CHECK"]+contexts["DEV"],
                  planned["CHECK"]+planned["DEV"])
    check=collect(np,CausalWorld,generate_task,p,"CHECK")
    dev=collect(np,CausalWorld,generate_task,p,"DEV")
    verify_source(root)
    check_dyn=dynamics(np,restored,check)
    score=scoring(dev,planned["DEV"])
    conclusion=decision(score,restored,check_dyn,basis["state_sizes"],costs)
    basis.update({"result":"COMPLETE_PUBLIC_PREDICTIVE_STATE_DEVELOPMENT",
       "CHECK_episodes":len(check),"DEV_episodes":len(dev),
       "CHECK_rows":check,"DEV_rows":dev,"CHECK_plan":planned["CHECK"],
       "DEV_plan":planned["DEV"],"DEV_scores":score,
       "CHECK_dynamics":check_dyn,"decision":conclusion,
       "per_method_inference_cpu":costs,
       "resource":{"whole_cpu_seconds":time.process_time()-cpu,
                   "whole_wall_seconds":time.perf_counter()-wall,
                   "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return basis


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--causalworld-repo",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("ORIGINAL_EVIDENCE_FILE_ALREADY_PRESENT")
    try:r=run(args.causalworld_repo,protocol())
    except Exception as e:
        r={"schema":SCHEMA,"gate":"LCRM01-K4P","result":"INFRASTRUCTURE_OR_SOURCE_BLOCKED",
           "error_type":type(e).__name__,"error":str(e),
           "traceback_tail":traceback.format_exc().splitlines()[-12:],
           "original_K4N_no_go_preserved":True,"scientific_first_use":False,
           "scientific_accepted":False}
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("K4P_ORIGINAL_RESULT="+r["result"])
    if "decision" in r:
        print("K4P_SCIENCE="+r["decision"]["result"])
        print("K4P_QUALIFICATION_TESTS="+canon(r["decision"]["tests"]))
        print("K4P_FAMILY_OUTCOMES="+canon(r["decision"]["per_family"]))
    if "FIT_winning_actions" in r:
        print("K4P_ORIGINAL_FIT_INFORMATION="+canon(r["FIT_winning_actions"]))
    return 1 if r["result"]=="INFRASTRUCTURE_OR_SOURCE_BLOCKED" else 0


if __name__=="__main__":
    sys.exit(main())
