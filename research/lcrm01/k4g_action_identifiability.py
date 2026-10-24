#!/usr/bin/env python3
"""K4G: prospectively frozen real-action sensitivity and fitted-control calibration.

No learner/transfer success can be claimed before identifying a discriminating
physical action/reward benchmark. All held-out action rewards are acquired
only after policies have already been frozen from FIT public observations.
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

FROZEN=Path(__file__).with_name("k4g_frozen_action_identifiability.json")
SCHEMA="mass.lcrm01.k4g.original-action-discrimination-dev.v1"
MODES=("fixed_low_action_0","FIT_trained_global_mean_best_action",
       "FIT_trained_task_family_mean_best_action")


def encode(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)

def sha(obj):
    return hashlib.sha256(encode(obj).encode("utf-8")).hexdigest()

def frozen():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    w=p["world"]
    if (p["schema"]!="mass.lcrm01.k4g.frozen-action-identifiability-public.v1" or
        w["families"]!=["reaching","pushing"] or
        w["new_fit_seeds"]!=[503,509,521,523] or
        w["new_check_seeds"]!=[601,607] or
        w["new_dev_seeds"]!=[701,709,719,727] or
        w["steps"]!=8 or
        w["arms"]!=["all_joint_low","all_joint_center","all_joint_high",
                     "alternating_20_80_percent"] or
        p["research_restrictions"]["original_FSA_first_use"] is not False):
        raise ValueError("K4G_FROZEN_PROTOCOL_DRIFT")
    if len(set(w["new_fit_seeds"]+w["new_check_seeds"]+w["new_dev_seeds"]))!=10:
        raise ValueError("K4G_SOURCE_COHORT_OVERLAP")
    return p

def action(np,space,arm):
    if type(arm)!=int or arm not in range(4):
        raise ValueError("NON_FROZEN_ACTION")
    low=np.asarray(space.low,dtype=np.float64)
    high=np.asarray(space.high,dtype=np.float64)
    if (low.shape!=(9,) or high.shape!=(9,) or not np.all(np.isfinite(low)) or
        not np.all(np.isfinite(high)) or np.any(low>=high)):
        raise ValueError("UNUSABLE_JOINT_SPACE")
    if arm==0:
        ratios=np.zeros(9)
    elif arm==1:
        ratios=np.full(9,0.5)
    elif arm==2:
        ratios=np.ones(9)
    else:
        ratios=np.array([0.2 if j%2==0 else 0.8 for j in range(9)])
    vec=low+(high-low)*ratios
    if np.any(vec<low-1.e-12) or np.any(vec>high+1.e-12):
        raise ValueError("OUT_OF_ACTION_BOUNDS")
    return np.minimum(np.maximum(vec,low),high)

def trial(np,CausalWorld,generate_task,p,family,seed,arm):
    if family not in p["world"]["families"] or type(seed)!=int:
        raise ValueError("NON_FROZEN_FAMILY")
    w=p["world"]
    env=CausalWorld(task=generate_task(task_generator_id=family),
        enable_visualization=False,seed=seed,skip_frame=w["skip_frame"],
        action_mode=w["action_mode"],observation_mode=w["observation_mode"],
        normalize_actions=w["normalize_actions"],
        normalize_observations=w["normalize_observations"],
        max_episode_length=w["max_episode_length"])
    try:
        initial=np.asarray(env.reset(),dtype=np.float64).ravel()
        if initial.size==0 or not np.all(np.isfinite(initial)):
            raise ValueError("PUBLIC_INITIAL_OBSERVATION_INVALID")
        act=action(np,env.action_space,arm)
        init_hash=hashlib.sha256(initial.tobytes()).hexdigest()
        act_hash=hashlib.sha256(act.tobytes()).hexdigest()
        total=0.0
        step_count=0
        for _ in range(w["steps"]):
            _observation,reward,done,_info=env.step(act)
            val=float(reward)
            if not math.isfinite(val):
                raise ValueError("NONFINITE_PUBLIC_REWARD")
            total+=val
            step_count+=1
            if done:
                break
        if step_count==0:
            raise ValueError("NO_PUBLIC_ACTIONS")
        return {"family":family,"seed":seed,"arm":arm,
                "actual_public_return":float(total),"step_count":step_count,
                "initial_observation_sha256":init_hash,
                "legal_action_sha256":act_hash}
    finally:
        env.close()

def observed_matrix(np,CausalWorld,generate_task,p,seeds):
    rows=[]
    for family in p["world"]["families"]:
        for seed in seeds:
            for arm in range(4):
                rows.append(trial(np,CausalWorld,generate_task,p,family,seed,arm))
    expected=len(p["world"]["families"])*len(seeds)*4
    if len(rows)!=expected:
        raise RuntimeError("INCOMPLETE_ACTUAL_SOURCE_EXPOSURE")
    return rows

def validate_paired_source(rows,seeds,p):
    errors=[]
    for family in p["world"]["families"]:
        for seed in seeds:
            subset=[x for x in rows if x["family"]==family and x["seed"]==seed]
            if len(subset)!=4 or [x["arm"] for x in subset]!=[0,1,2,3]:
                raise ValueError("MISSING_ACTUAL_ARM_EXPERIENCE")
            if len({x["initial_observation_sha256"] for x in subset})!=1:
                errors.append({"family":family,"seed":seed,"error":"PUBLIC_INITIAL_OBSERVATION_DRIFT"})
            if len({x["legal_action_sha256"] for x in subset})!=4:
                errors.append({"family":family,"seed":seed,"error":"ACTIONS_NOT_DISTINCT"})
    return errors

def trained_means(rows,p):
    families=p["world"]["families"]
    expect={(fam,arm):4 for fam in families for arm in range(4)}
    actual={(fam,arm):sum(x["family"]==fam and x["arm"]==arm for x in rows)
            for fam,arm in expect}
    if actual!=expect or len(rows)!=32:
        raise ValueError("FIT_EXPOSURES_NOT_EQUAL")
    global_means={str(arm):sum(x["actual_public_return"] for x in rows if x["arm"]==arm)/8.0
                  for arm in range(4)}
    family_means={fam:{str(arm):sum(x["actual_public_return"] for x in rows
                                   if x["family"]==fam and x["arm"]==arm)/4.0
                       for arm in range(4)} for fam in families}
    return {"state_format":"mass.k4g.fitted-control-state.v1",
            "FIT_rows":32,"global_action_mean":global_means,
            "family_action_mean":family_means}

def select_policy(state,family,method):
    if method==MODES[0]:
        return 0
    if method==MODES[1]:
        values=state["global_action_mean"]
    elif method==MODES[2]:
        values=state["family_action_mean"][family]
    else:
        raise ValueError("UNKNOWN_POLICY")
    return max(range(4),key=lambda arm:(values[str(arm)],-arm))

def freeze_plan(state,seeds,p):
    return [{"family":fam,"seed":seed,
             "selected":{method:select_policy(state,fam,method) for method in MODES}}
            for fam in p["world"]["families"] for seed in seeds]

def score_phase(rows,plan):
    score=[]
    for entry in plan:
        fam,seed=entry["family"],entry["seed"]
        subset=[r for r in rows if r["family"]==fam and r["seed"]==seed]
        vals={x["arm"]:x["actual_public_return"] for x in subset}
        if len(vals)!=4:
            raise ValueError("MISSING_PAIRED_ACTUAL_RETURN")
        spans=float(max(vals.values())-min(vals.values()))
        outcomes={method:{"action":arm,"actual_return":vals[arm]}
                  for method,arm in entry["selected"].items()}
        score.append({"family":fam,"seed":seed,"action_spread":spans,
            "actual_returns_by_arm":{str(a):vals[a] for a in range(4)},
            "policy_scores":outcomes})
    return score

def decision(check,dev,paired_errors,p):
    families=p["world"]["families"]
    d={}
    for fam in families:
        samples=[s for s in dev if s["family"]==fam]
        if len(samples)!=4:
            raise ValueError("DEV_SOURCE_COUNT_MISMATCH")
        spread_count=sum(s["action_spread"]>0.05 for s in samples)
        means={method:float(sum(s["policy_scores"][method]["actual_return"] for s in samples)/4)
               for method in MODES}
        fitted_adv=max(means[MODES[1]],means[MODES[2]])-means[MODES[0]]
        d[fam]={"action_spread_gt_0_05_count":spread_count,"policy_mean_returns":means,
                "best_fitted_advantage_over_fixed":fitted_adv,
                "family_action_identifiable":spread_count>=3,
                "fitted_policy_improves":fitted_adv>=0.01}
    ready=(len(paired_errors)==0 and all(z["family_action_identifiable"] and
           z["fitted_policy_improves"] for z in d.values()))
    return {"disposition":"CALIBRATED_PUBLIC_DEV_ONLY" if ready
            else "BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE",
            "per_family":d,"paired_source_errors":paired_errors,
            "diagnostic_check_score_rows":len(check),
            "no_new_cognitive_or_transfer_claim":True,"scientific_accepted":False}

def run(repo,p):
    from k4a_control_replay import verify_source
    if p["source"]["commit"]!="1045277101a92c506db42704da28f6e7227d401b":
        raise ValueError("PUBLIC_SIMULATOR_SOURCE_DRIFT")
    root=repo.resolve()
    verify_source(root)
    sys.path.insert(0,str(root))
    import numpy as np
    from causal_world.envs.causalworld import CausalWorld
    from causal_world.task_generators.task import generate_task
    if root not in Path(sys.modules[CausalWorld.__module__].__file__).resolve().parents:
        raise ValueError("PUBLIC_SIMULATOR_IMPORT_DRIFT")
    t=time.perf_counter();cpu=time.process_time()
    fit=observed_matrix(np,CausalWorld,generate_task,p,p["world"]["new_fit_seeds"])
    fit_errors=validate_paired_source(fit,p["world"]["new_fit_seeds"],p)
    # Training and policy selection end HERE. No CHECK or DEV exposures yet.
    state=trained_means(fit,p)
    state_bytes=encode(state).encode("utf-8")
    restored=json.loads(state_bytes)
    if restored!=state:
        raise RuntimeError("TRAINED_STATE_DID_NOT_RETAIN")
    check_plan=freeze_plan(restored,p["world"]["new_check_seeds"],p)
    dev_plan=freeze_plan(restored,p["world"]["new_dev_seeds"],p)
    source_plan_hash=sha({"check":check_plan,"dev":dev_plan})
    check_rows=observed_matrix(np,CausalWorld,generate_task,p,p["world"]["new_check_seeds"])
    check_errors=validate_paired_source(check_rows,p["world"]["new_check_seeds"],p)
    check_score=score_phase(check_rows,check_plan)
    # No model change or model selection after inspecting CHECK.
    dev_rows=observed_matrix(np,CausalWorld,generate_task,p,p["world"]["new_dev_seeds"])
    dev_errors=validate_paired_source(dev_rows,p["world"]["new_dev_seeds"],p)
    dev_score=score_phase(dev_rows,dev_plan)
    verify_source(root)
    measured={"wall_seconds":time.perf_counter()-t,
              "cpu_seconds":time.process_time()-cpu,
              "peak_rss_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
    return {"schema":SCHEMA,"gate":"LCRM01-K4G",
      "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
      "source_commit":p["source"]["commit"],
      "result":"COMPLETE_PUBLIC_DEVELOPMENT",
      "FIT_exposures":len(fit),"CHECK_exposures":len(check_rows),"DEV_exposures":len(dev_rows),
      "FIT_rows":fit,"CHECK_rows":check_rows,"DEV_rows":dev_rows,
      "FIT_source_sha256":sha(fit),"fitted_checkpoint_sha256":hashlib.sha256(state_bytes).hexdigest(),
      "checkpoint_bytes":len(state_bytes),"model_plan_sha256":source_plan_hash,
      "fixed_scoring_plans":{"check":check_plan,"dev":dev_plan},
      "check_scores":check_score,"dev_scores":dev_score,
      "calibration":decision(check_score,dev_score,fit_errors+check_errors+dev_errors,p),
      "source_reconciliation":{"fit_errors":fit_errors,"check_errors":check_errors,"dev_errors":dev_errors},
      "resources":measured,"learned_models_are_conventional_baselines":True,
      "first_use_authorized":False,"original_K4F_NO_GO_preserved":True,
      "scientific_accepted":False,"dispatch_authorized":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--causalworld-repo",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("EVIDENCE_DESTINATION_NOT_FRESH")
    try:
        result=run(args.causalworld_repo,frozen())
    except Exception as error:
        result={"schema":SCHEMA,"gate":"LCRM01-K4G",
          "result":"RUNTIME_INFRASTRUCTURE_BLOCKED",
          "error_type":type(error).__name__,"error":str(error),
          "traceback_tail":traceback.format_exc().splitlines()[-12:],
          "original_K4F_NO_GO_preserved":True,"first_use_authorized":False,
          "scientific_accepted":False,"dispatch_authorized":False}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print("K4G_RUN_RESULT="+result["result"])
    if "calibration" in result:
        print("K4G_CALIBRATION="+result["calibration"]["disposition"])
        print("K4G_PER_FAMILY="+encode(result["calibration"]["per_family"]))
    return 0 if result["result"]=="COMPLETE_PUBLIC_DEVELOPMENT" else 1

if __name__=="__main__":
    sys.exit(main())
