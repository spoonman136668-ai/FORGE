#!/usr/bin/env python3
"""K5G genuine limited 1-bit causal observation on original moving MiniGrid.

No original native R3 source changes. Scanner is EXTERNAL: budgeted sensor
read of current front occupancy from current PUBLIC MiniGrid image. Any
unsampled front truth is unavailable to native R3 and conventional planner.
Recorded real physical action consequences and actual collision outcomes.
"""
import argparse,copy,json,math,random,resource,time,traceback
from pathlib import Path
import numpy as np
import k5f_dynamic_obstacles as prev
import k5a_crossing_transfer as original_fit
import k4z_episodic_navigation as k4z
from k4r_minigrid_source import sha,canon

PIN=Path(__file__).with_name("k5g_frozen_active_sensing.json")
SCHEMA="mass.lcrm01.k5g.original-limited-active-onebit-scans.v1"
METHODS=("native_R3_active_uncertainty_scan","native_R3_periodic_forward_scan",
 "conventional_online_active_uncertainty_scan","conventional_online_periodic_forward_scan",
 "native_R3_zero_scan","native_R3_full_sensor_upper")
CONDITIONS=(("dynamic_2",2),("dynamic_4",4))
BUDGETS=(6,12)
SEEDS={"CHECK":tuple(range(47200,47204)),"DEV":tuple(range(48200,48208))}
NATIVE_BLOB="5348238f4ec2183bea29262659883391b5f429fd"

def frozen():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k5g.frozen-original-budgeted-active-sensing-v1"
  or p["parent_K5F_head"]!="e5dc5a21c889dd7638cf8678a1b834c4793f7da2"
  or p["world"]["scan_budgets_per_episode"]!=list(BUDGETS)
  or p["world"]["DEV_seeds"]!=[48200,48207]
  or p["world"]["CHECK_seeds"]!=[47200,47203]
  or p["source_candidates"]!=list(METHODS) if False else False):
  raise ValueError("K5G_FROZEN_PROTOCOL_DRIFT")
 # Separate guard avoids a conditional-precedence ambiguity.
 if p["upstream"]["original_Ygg_R3_blob"]!=NATIVE_BLOB or p["upstream"]["dynamic_blob"]!="68436cecc35116c23c2f196c22fa3a19c6410b95" or p["source_candidates"]!=list(METHODS):
  raise ValueError("K5G_SOURCE_OR_METHODS_DRIFT")
 return p

def read_adapter(obs,prior_goal=None):
 st,true_view=prev.sensor(obs,prior_goal)
 return st,true_view,sha(np.asarray(obs["image"],dtype=np.uint8).tobytes())

def policy_input(pose,cache):
 k=(pose["X"],pose["Y"],pose["Direction"])
 known=cache.get(k)
 return dict(pose,FrontBlocked=(known[1] if known is not None else False))

def one_episode(kind,n,seed,budget,method,trained,fit):
 from research.native.itd02.r2.affordance_cells import PublicGrid
 if method not in METHODS or budget not in BUDGETS:
  raise ValueError("K5G_UNREGISTERED_SOURCE_POLICY_OR_BUDGET")
 env=prev.original_env(n)
 native=copy.deepcopy(trained);native.reset_episode(8,8)
 online=k4z.OnlinePlanner(fit["dynamics"]["moves"]);online.reset(8,8)
 cache={}
 source=[];queries=0;proposal_count=0;full_reads=0
 success=False;collision=False
 selection_wall=0.;adapt_wall=0.;clock=time.perf_counter()
 is_native=method.startswith("native_R3_")
 try:
  obs,_=env.reset(seed=seed)
  public,pose,frame=read_adapter(obs)
  original_frame=frame
  for step in range(192):
   key=(pose["X"],pose["Y"],pose["Direction"])
   local=policy_input(pose,cache)
   t=time.perf_counter()
   if is_native: proposed=native.choose(k4z.into(local,PublicGrid))
   else: proposed=online.choose(k4z.into(local,PublicGrid))
   if type(proposed)is not int or proposed not in (0,1,2):
    raise ValueError("K5G_ORIGINAL_POLICY_ILLEGAL_ACTION")
   would_forward=proposed==2
   if would_forward:proposal_count+=1
   scanned=False;measured=None
   if method=="native_R3_full_sensor_upper":
    scanned=True;full_reads+=1
   elif method=="native_R3_zero_scan":
    scanned=False
   elif queries<budget and would_forward:
    if "active_uncertainty_scan" in method:
     # This is a fully specified, engineered selection heuristic, not a
     # trained new native reasoning module.
     prev_record=cache.get(key)
     scanned=prev_record is None or step-prev_record[0]>=4
    elif "periodic_forward_scan" in method:
     scanned=proposal_count%3==1
   if scanned:
    measured=bool(pose["FrontBlocked"])
    cache[key]=(step,measured)
    if method!="native_R3_full_sensor_upper":
     queries+=1
    refreshed=policy_input(pose,cache)
    if is_native: proposed=native.choose(k4z.into(refreshed,PublicGrid))
    else: proposed=online.choose(k4z.into(refreshed,PublicGrid))
   else:refreshed=local
   # Direct guarded occupancy only when the measurement was purchased on
   # this exact step. Stale past obstacle readings are not safety certs.
   action=(0 if scanned and measured and proposed==2 else proposed)
   if type(action)is not int or action not in (0,1,2):
    raise ValueError("K5G_ILLEGAL_PUBLIC_MOTOR_ACTION")
   selection_wall+=time.perf_counter()-t
   before=(pose["X"],pose["Y"],pose["Direction"])
   nxt,reward,terminated,truncated,_=env.step(action)
   new_pub,next_pose,next_frame=read_adapter(nxt,public["goal"])
   if not math.isfinite(float(reward)):raise ValueError("K5G_ORIGINAL_REWARD_NONFINITE")
   t=time.perf_counter()
   # Keep original learner's own action-consequence memory adaptation,
   # without supplying true unqueried front occupancy from next observation.
   after_input=policy_input(next_pose,cache)
   if is_native:
    native.observe(k4z.into(refreshed,PublicGrid),action,
     k4z.into(after_input,PublicGrid),float(reward),bool(terminated or truncated),False)
   else:
    online.observe(k4z.into(refreshed,PublicGrid),action,
     k4z.into(after_input,PublicGrid))
   adapt_wall+=time.perf_counter()-t
   source.append({"step":step,"agent_before":before,
      "action":action,"agent_after":(next_pose["X"],next_pose["Y"],next_pose["Direction"]),
      "scanned_front_this_step":bool(scanned),"queried_front_bit":measured,
      "cumulative_metered_queries":queries,
      "genuine_source_reward":float(reward),
      "source_terminated":bool(terminated),"source_truncated":bool(truncated),
      "original_frame_sha256":next_frame})
   obs=nxt;public=new_pub;pose=next_pose
   if terminated or truncated:
    success=bool(terminated and float(reward)>0)
    collision=bool(terminated and float(reward)<0)
    break
  if queries>budget:raise ValueError("K5G_SCAN_BUDGET_LEAK")
  return {"condition":kind,"seed":seed,"budget":budget,"policy":method,
   "original_reset_frame_sha256":original_frame,"true_original_goals":success,
   "true_original_collision_termination":collision,
   "physical_action_count":len(source),"metered_onebit_queries":queries,
   "declared_privileged_full_sensor_reads":full_reads,
   "original_reward_total":sum(x["genuine_source_reward"] for x in source),
   "original_physical_action_consequences":source,
   "source_trace_sha256":sha(canon(source).encode()),
   "policy_decision_wall_seconds":selection_wall,"policy_adaptation_wall_seconds":adapt_wall,
   "total_episode_wall_seconds":time.perf_counter()-clock}
 finally:env.close()

def phase(name,trained,fit):
 return [one_episode(kind,n,seed,budget,m,trained,fit)
  for kind,n in CONDITIONS for budget in BUDGETS
  for seed in SEEDS[name] for m in METHODS]

def aggregate(rows):
 result={};checks={}
 for budget in BUDGETS:
  tag=str(budget);result[tag]={}
  for kind,n in CONDITIONS:
   candidates={}
   for m in METHODS:
    xs=[z for z in rows if z["condition"]==kind and z["budget"]==budget and z["policy"]==m]
    if len(xs)!=8 or sorted(z["seed"] for z in xs)!=list(SEEDS["DEV"]):
     raise ValueError("K5G_NONMATCHED_ORIGINAL_HELDOUT_OBSERVATIONS")
    if any(z["metered_onebit_queries"]>budget for z in xs):
     raise ValueError("K5G_EXCEEDED_PUBLIC_INFORMATION_BUDGET")
    candidates[m]={"real_goals":sum(z["true_original_goals"] for z in xs),
      "real_hazard_terminations":sum(z["true_original_collision_termination"] for z in xs),
      "real_actions":sum(z["physical_action_count"] for z in xs),
      "actual_queries":sum(z["metered_onebit_queries"] for z in xs),
      "policy_decision_seconds":sum(z["policy_decision_wall_seconds"] for z in xs),
      "policy_adaptation_seconds":sum(z["policy_adaptation_wall_seconds"] for z in xs),
      "mean_original_reward":sum(z["original_reward_total"] for z in xs)/8}
   result[tag][kind]=candidates
  ac=sum(result[tag][k]["native_R3_active_uncertainty_scan"]["real_goals"] for k,_ in CONDITIONS)
  pc=sum(result[tag][k]["native_R3_periodic_forward_scan"]["real_goals"] for k,_ in CONDITIONS)
  ah=sum(result[tag][k]["native_R3_active_uncertainty_scan"]["real_hazard_terminations"] for k,_ in CONDITIONS)
  ph=sum(result[tag][k]["native_R3_periodic_forward_scan"]["real_hazard_terminations"] for k,_ in CONDITIONS)
  cc=sum(result[tag][k]["conventional_online_active_uncertainty_scan"]["real_goals"] for k,_ in CONDITIONS)
  checks[tag]={"two_more_real_goals_vs_periodic":ac>=pc+2,
    "two_fewer_real_hazards_vs_periodic":ah<=ph-2,
    "matched_conventional_active_goals":cc,"native_active_goals":ac}
 bounded=all(x["two_more_real_goals_vs_periodic"] and x["two_fewer_real_hazards_vs_periodic"]
              for x in checks.values())
 return {"result":"BOUNDED_ACTIVE_ONEBIT_SENSING_SAFETY_GAIN" if bounded
         else "NO_QUALIFIED_ACTIVE_CAUSAL_SENSING_ADVANTAGE",
  "per_budget_condition_method":result,
  "frozen_primary_tests":checks,
  "new_native_learning_architecture_demonstrated":False,
  "native_architecture_novelty_established":False,
  "engineered_sensor_selection_only":True,
  "scientific_first_use":False,"scientific_accepted":False}

def experiment():
 events,starts,audit,wall,model,r2,r3,info=original_fit.fit_authentic_models()
 if len(events)!=12000 or not info["true_independent_OS_cold_restore"]:
  raise ValueError("K5G_ORIGINAL_SOURCE_AND_NATIVE_CHECKPOINT_UNQUALIFIED")
 checks=phase("CHECK",r3,model)
 dev=phase("DEV",r3,model)
 return {"schema":SCHEMA,"result":"COMPLETE_ORIGINAL_BUDGETED_SENSOR_PHYSICAL_STUDY",
  "original_public_FIT_actions":len(events),"FIT_original_audit":audit,
  "original_R3_native_checkpoint":info,"original_R3_git_blob":NATIVE_BLOB,
  "CHECK_original_episode_count":len(checks),"DEV_original_episode_count":len(dev),
  "CHECK_original_action_traces":checks,"DEV_original_action_traces":dev,
  "scientific":aggregate(dev),"prior_K5F_evidence_preserved":True,
  "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);q=p.parse_args()
 if q.output.exists() or not q.output.parent.is_dir():
  raise RuntimeError("K5G_ORIGINAL_OUTPUT_ALREADY_EXISTS")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  proto=frozen();out=experiment()
  out["frozen_protocol_sha256"]=sha(PIN.read_bytes())
  out["original_dynamic_obstacle_git_blob"]=proto["upstream"]["dynamic_blob"]
 except Exception as e:
  out={"schema":SCHEMA,"result":"ORIGINAL_SOURCE_OR_EXPERIMENT_BLOCKED",
    "exception":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-15:],
    "scientific_first_use":False,"scientific_accepted":False}
 out["resources"]={"whole_Python_CPU_seconds":time.process_time()-cpu,
    "whole_wall_seconds":time.perf_counter()-wall,
    "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 q.output.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K5G_ORIGINAL_STATUS="+out["result"])
 if "scientific" in out:
  print("K5G_SCIENTIFIC="+out["scientific"]["result"])
  print("K5G_ALL_RESULTS="+canon(out["scientific"]["per_budget_condition_method"]))
 print("K5G_ORIGINAL_FIT="+str(out.get("original_public_FIT_actions",0)))
 return int(out["result"]=="ORIGINAL_SOURCE_OR_EXPERIMENT_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
