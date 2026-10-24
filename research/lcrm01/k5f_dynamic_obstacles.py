#!/usr/bin/env python3
"""K5F source-original nonstationary moving obstacles vs fitted causal memories.

External MiniGrid DynamicObstaclesEnv: actual moving balls and collision
penalties. Native R3 and same-information conventional planner see ONLY pose,
goal and real current front-occupied sensor + OWN action consequences.
Privileged full-grid replanner is a declared upper bound, never a native input.
"""
import argparse,copy,hashlib,json,math,random,resource,time,traceback
from pathlib import Path
import numpy as np
import k5a_crossing_transfer as prior
import k4z_episodic_navigation as k4z
from k4r_minigrid_source import public,canon,sha,bfs

PIN=Path(__file__).with_name("k5f_frozen_dynamic_obstacles.json")
SCHEMA="mass.lcrm01.k5f.original-dynamic-obstacles-public-sensor.v1"
CONDS=(("dynamic_2",2),("dynamic_4",4))
SEEDS={"CHECK":tuple(range(45200,45204)),"DEV":tuple(range(46200,46208))}
METHODS=("native_R3_unchanged","native_R3_current_front_safety_veto",
         "conventional_online_optimistic_sensor_veto",
         "privileged_full_grid_dynamic_replanner","source_seeded_random")
R3_BLOB="5348238f4ec2183bea29262659883391b5f429fd"
MOVES=((1,0),(0,1),(-1,0),(0,-1))

def frozen():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k5f.frozen-dynamic-obstacles-information-limited-v1"
  or p["parent_K5E"]!="ee99cf0a2f91c032b57e86a896504a041f162cf0"
  or p["source"]["dynamic_blob"]!="68436cecc35116c23c2f196c22fa3a19c6410b95"
  or p["task"]["DEV_seeds"]!=[46200,46207]
  or [x["n_obstacles"] for x in p["task"]["conditions"]]!=[2,4]
  or p["task"]["candidates"]!=list(METHODS)):
  raise ValueError("K5F_FROZEN_REAL_SOURCE_OR_METHOD_DRIFT")
 return p

def original_env(n):
 from minigrid.envs.dynamicobstacles import DynamicObstaclesEnv
 from minigrid.wrappers import FullyObsWrapper
 if n not in (2,4):raise ValueError("K5F_UNQUALIFIED_PHYSICAL_OBSTACLE_COUNT")
 return FullyObsWrapper(DynamicObstaclesEnv(size=8,agent_start_pos=(1,1),
            agent_start_dir=0,n_obstacles=n,max_steps=192))

def sensor(obs,prior_goal=None):
 from minigrid.core.constants import OBJECT_TO_IDX
 image=np.asarray(obs["image"],dtype=np.uint8)
 st=public(obs,prior_goal)
 x,y,d=st["x"],st["y"],st["dir"]
 dx,dy=MOVES[d];front=(x+dx,y+dy)
 code=int(image[front[0],front[1],0])
 blocked=code not in (OBJECT_TO_IDX["empty"],OBJECT_TO_IDX["goal"])
 st["current_front_obstacle"]=bool(blocked)
 st["current_public_image_sha256"]=sha(image.tobytes())
 # No full scene, current wall positions or obstacle positions enter R3.
 public_view={"X":x,"Y":y,"GoalX":st["goal"][0],"GoalY":st["goal"][1],
      "Direction":d,"FrontBlocked":bool(blocked)}
 return st,public_view

def real_episode(kind,n,seed,method,r3trained,fitmodel):
 from research.native.itd02.r2.affordance_cells import PublicGrid
 if method not in METHODS:raise ValueError("K5F_UNREGISTERED_CONTROL")
 env=original_env(n)
 native=copy.deepcopy(r3trained)
 native.reset_episode(8,8)
 online=k4z.OnlinePlanner(fitmodel["dynamics"]["moves"])
 online.reset(8,8)
 trace=[];t=time.perf_counter();selection_cost=0.;adapt_cost=0.;success=False
 collision=False;source_ended=False;current=None
 try:
  obs,_=env.reset(seed=seed)
  start_hash=sha(np.asarray(obs["image"]).tobytes())
  st,sense=sensor(obs)
  for step in range(192):
   sensor_native=PublicGrid(**sense)
   selection_t=time.perf_counter()
   if method.startswith("native_R3"):
    candidate=native.choose(sensor_native)
    action=(0 if method=="native_R3_current_front_safety_veto"
         and candidate==2 and sense["FrontBlocked"] else candidate)
   elif method=="conventional_online_optimistic_sensor_veto":
    candidate=online.choose(sensor_native)
    action=0 if candidate==2 and sense["FrontBlocked"] else candidate
   elif method=="privileged_full_grid_dynamic_replanner":
    # Declare the upper control's current FULL global ball locations,
    # never made available to native or equally informed online model.
    from minigrid.core.constants import OBJECT_TO_IDX
    image=np.asarray(obs["image"],dtype=np.uint8)
    balls=frozenset(map(tuple,np.argwhere(image[:,:,0]==OBJECT_TO_IDX["ball"]).tolist()))
    full=dict(st);full["walls"]=st["walls"]|balls
    action=bfs(full,None)
   else:
    action=random.Random(850000+seed*77+step*13+n*1009).randrange(3)
   selection_cost+=time.perf_counter()-selection_t
   if type(action)is not int or action not in (0,1,2):
    raise ValueError("K5F_ACTION_NOT_LEGAL")
   before=[sense["X"],sense["Y"],sense["Direction"],int(sense["FrontBlocked"])]
   next_obs,reward,term,trunc,_=env.step(action)
   nxt,nsense=sensor(next_obs,st["goal"])
   after=[nsense["X"],nsense["Y"],nsense["Direction"],int(nsense["FrontBlocked"])]
   if not math.isfinite(float(reward)):raise ValueError("K5F_SOURCE_REWARD_INVALID")
   start=time.perf_counter()
   if method.startswith("native_R3"):
    native.observe(sensor_native,action,PublicGrid(**nsense),
           float(reward),bool(term or trunc),False)
   elif method=="conventional_online_optimistic_sensor_veto":
    online.observe(sensor_native,action,PublicGrid(**nsense))
   adapt_cost+=time.perf_counter()-start
   trace.append({"step":step,"action":action,"observed_previous_pose_front":before,
       "observed_next_pose_front":after,"real_reward":float(reward),
       "physical_terminated":bool(term),"physical_truncated":bool(trunc),
       "full_source_frame_sha256":nxt["current_public_image_sha256"]})
   obs=next_obs;st=nxt;sense=nsense
   if term or trunc:
    source_ended=True
    success=bool(term and float(reward)>0)
    collision=bool(term and float(reward)<0)
    break
  return {"kind":kind,"seed":seed,"method":method,"original_source_start_sha256":start_hash,
    "genuine_goal_success":success,"genuine_moving_obstacle_collision":collision,
    "episode_terminated":source_ended,
    "total_original_rewards":sum(z["real_reward"] for z in trace),
    "real_action_steps":len(trace),
    "physical_public_front_blocks":sum(z["action"]==2 and z["observed_previous_pose_front"][3] for z in trace),
    "full_original_action_consequence_trace":trace,
    "trace_sha256":sha(canon(trace).encode()),
    "policy_selection_wall_seconds":selection_cost,
    "policy_online_update_wall_seconds":adapt_cost,
    "episode_wall_seconds":time.perf_counter()-t}
 finally:env.close()

def score(heldout):
 report={}
 for kind,n in CONDS:
  by={}
  for method in METHODS:
   r=[x for x in heldout if x["kind"]==kind and x["method"]==method]
   if len(r)!=8 or sorted(x["seed"] for x in r)!=list(SEEDS["DEV"]):
    raise ValueError("K5F_UNMATCHED_REAL_HELDOUT_SOURCE")
   by[method]={"actual_goals":sum(x["genuine_goal_success"] for x in r),
      "actual_collision_terminations":sum(x["genuine_moving_obstacle_collision"] for x in r),
      "actual_physical_steps":sum(x["real_action_steps"] for x in r),
      "mean_original_real_reward":sum(x["total_original_rewards"] for x in r)/8,
      "total_policy_selection_seconds":sum(x["policy_selection_wall_seconds"] for x in r),
      "total_policy_update_seconds":sum(x["policy_online_update_wall_seconds"] for x in r)}
  report[kind]=by
 old=sum(report[k]["native_R3_unchanged"]["actual_collision_terminations"] for k,_ in CONDS)
 new=sum(report[k]["native_R3_current_front_safety_veto"]["actual_collision_terminations"] for k,_ in CONDS)
 before=sum(report[k]["native_R3_unchanged"]["actual_goals"] for k,_ in CONDS)
 after=sum(report[k]["native_R3_current_front_safety_veto"]["actual_goals"] for k,_ in CONDS)
 gates={"at_least_three_genuine_collisions_prevented":old-new>=3,
    "at_least_two_additional_original_goal_successes":after-before>=2,
    "source_conventional_control_present":all("conventional_online_optimistic_sensor_veto" in report[k]
                                       for k,_ in CONDS),
    "source_privileged_upper_control_present":all("privileged_full_grid_dynamic_replanner" in report[k]
                                       for k,_ in CONDS)}
 return {"result":"BOUNDED_EXTERNAL_SENSOR_SAFETY_MITIGATION" if all(gates.values())
  else "NO_QUALIFIED_NONSTATIONARY_R3_SAFETY_ADVANCEMENT",
  "original_true_experience_results":report,"frozen_gates":gates,
  "native_architecture_superiority_established":False,
  "source_native_algorithm_changed":False,"scientific_first_use":False,"scientific_accepted":False}

def experiment():
 events,starts,audit,fitwall,fitcontrol,r2,r3,checkpoint=prior.fit_authentic_models()
 if len(events)!=12000 or not checkpoint["true_independent_OS_cold_restore"]:
  raise ValueError("K5F_ORIGINAL_R3_SOURCE_NOT_AUTHENTIC")
 check=[real_episode(k,n,seed,m,r3,fitcontrol) for k,n in CONDS
        for seed in SEEDS["CHECK"] for m in METHODS]
 dev=[real_episode(k,n,seed,m,r3,fitcontrol) for k,n in CONDS
        for seed in SEEDS["DEV"] for m in METHODS]
 return {"schema":SCHEMA,"result":"COMPLETE_ORIGINAL_DYNAMIC_OBSTACLES_STUDY",
    "original_FIT_true_actions":len(events),
    "original_FIT_source_audit":audit,
    "source_native_FIT_checkpoint":checkpoint,
    "original_R3_source_blob":R3_BLOB,
    "CHECK_real_episodes":len(check),"DEV_real_episodes":len(dev),
    "CHECK_full_original_traces":check,"DEV_full_original_traces":dev,
    "scientific":score(dev),"source_original_K5E_nonlinear_findings_preserved":True,
    "scientific_first_use":False,"scientific_accepted":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 args=parser.parse_args()
 if args.output.exists() or not args.output.parent.is_dir():
  raise RuntimeError("K5F_NONFRESH_ORIGINAL_REPORT")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  p=frozen()
  out=experiment()
  out["protocol_sha256"]=sha(PIN.read_bytes())
  out["upstream_original_dynamic_obstacles_blob"]=p["source"]["dynamic_blob"]
 except Exception as err:
  out={"schema":SCHEMA,"result":"K5F_SOURCE_OR_EXPERIMENT_BLOCKED",
       "error":str(err),"exception":type(err).__name__,
       "traceback_tail":traceback.format_exc().splitlines()[-14:],
       "scientific_first_use":False,"scientific_accepted":False}
 out["resources"]={"whole_Python_CPU_seconds":time.process_time()-cpu,
    "whole_wall_seconds":time.perf_counter()-wall,
    "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 args.output.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K5F_ORIGINAL_RESULT="+out["result"])
 if "scientific" in out:
  print("K5F_SCIENCE="+out["scientific"]["result"])
  print("K5F_REAL_DEV="+canon(out["scientific"]["original_true_experience_results"]))
 print("K5F_R3_FIT_REAL_PUBLIC="+str(out.get("original_FIT_true_actions",0)))
 return int(out["result"]=="K5F_SOURCE_OR_EXPERIMENT_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
