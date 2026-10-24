#!/usr/bin/env python3
"""K5A: source-frozen zero-shot transfer to ORIGINAL MiniGrid SimpleCrossing.

Two unseen maze-topology regimes with intact Ygg R3, no-edge memory,
no-original-local-R2 ablation, static R2, equally informed conventional
online planning, full public-map conventional controls. Authentic action
consequences and per-policy costs. NO hidden grid supplied to native agent.
"""
import argparse
import copy
import hashlib
import json
import math
import resource
import subprocess
import sys
import time
import traceback
from pathlib import Path

import k4z_episodic_navigation as prior
from k4r_minigrid_source import public,act,sha,canon
from k4u_native_minigrid import public_grid

PROTOCOL=Path(__file__).with_name("k5a_frozen_crossing_ablation.json")
SCHEMA="mass.lcrm01.k5a.original-crossing-zero-shot-transfer.v1"
METHODS=("ygg_R3_intact","ygg_R3_no_episodic_edges","ygg_R3_no_R2_local",
 "ygg_R2_static","conventional_online_optimistic","conventional_fit_model_bfs",
 "public_bfs_upper","uniform_random")
TASKS=(("crossing_1",1),("crossing_3",3))
PHASES={"CHECK":tuple(range(20500,20504)),"DEV":tuple(range(21500,21508))}
SOURCE_BLOB="5348238f4ec2183bea29262659883391b5f429fd"

def frozen():
 p=json.loads(PROTOCOL.read_text())
 if (p.get("schema")!="mass.lcrm01.k5a.frozen-independent-topology-ablation.v1"
  or p["parents"]["K4Z_head"]!="51f83d97e982264f2cad905e80742eb790e40464"
  or p["source"]["crossing_blob"]!="f8c331e5e0e56b3b2a4a3b44dda8533bdabf4272"
  or p["unfamiliar_environment"]["DEV_seeds"]!=[21500,21507]
  or p["unfamiliar_environment"]["CHECK_seeds"]!=[20500,20503]
  or p["candidate_policies"]!=list(METHODS)):
  raise ValueError("K5A_FROZEN_SOURCE_OR_PRIMARY_HYPOTHESIS_DRIFT")
 return p

def make_world(kind):
 from minigrid.envs.crossing import CrossingEnv
 from minigrid.wrappers import FullyObsWrapper
 if kind not in dict(TASKS):
  raise ValueError("K5A_UNREGISTERED_SOURCE_TOPOLOGY")
 return FullyObsWrapper(CrossingEnv(size=9,num_crossings=dict(TASKS)[kind],
      obstacle_type="wall",max_steps=192))

def fit_authentic_models():
 # The unchanged K4Z training source FIT is public development previously
 # used to qualify R3: its original heldout worlds MUST NEVER enter training.
 events,starts,audit,source_wall,control=prior.fit_source()
 if (len(events)!=12000 or control is None or
     any(audit[f]["public_steps"]!=6000 for f in ("empty","fourrooms"))):
  raise ValueError("K5A_K4Z_PRIOR_FIT_OR_MODEL_UNQUALIFIED")
 r2,r3,info=prior.train(events)
 if not info["true_independent_OS_cold_restore"]:
  raise ValueError("K5A_NATIVE_COLD_RESTART_UNQUALIFIED")
 return events,starts,audit,source_wall,control,r2,r3,info

def run_world(kind,seed,method,r2trained,r3trained,control):
 from research.native.itd02.r2.affordance_cells import AffordanceColony,PublicGrid
 if method not in METHODS:raise ValueError("K5A_UNREGISTERED_POLICY")
 agent=copy.deepcopy(r3trained)
 if method=="ygg_R3_no_R2_local":
  agent.core=AffordanceColony()
 if method.startswith("ygg_R3"):
  agent.reset_episode(9,9)
 planner=prior.OnlinePlanner(control["dynamics"]["moves"])
 planner.reset(9,9)
 env=make_world(kind)
 actions=[];start=time.perf_counter();cpu=time.process_time()
 inference=0.;updating=0.;total=0.;success=False
 try:
  obs,info=env.reset(seed=seed)
  state=public(obs);origin=state["grid_sha256"]
  if tuple(state["shape"])!=(9,9):
   raise ValueError("K5A_SOURCE_TOPOLOGY_SIZE_CHANGED")
  for i in range(192):
   current=prior.into(state,PublicGrid)
   t=time.perf_counter()
   if method.startswith("ygg_R3"):a=agent.choose(current)
   elif method=="ygg_R2_static":a=r2trained.choose(current)
   elif method=="conventional_online_optimistic":a=planner.choose(current)
   elif method=="uniform_random":
    # K4R's deterministic original random-control formula, extended to the
    # two ORIGINAL crossing task names. Its old FAMILIES.index() only knows
    # Empty and FourRooms and cannot be called for unseen Crossing.
    import random
    family_index=list(dict(TASKS)).index(kind)
    a=random.Random(912000+seed*100+i+family_index*17000).randrange(3)
   else:
    baseline={"conventional_fit_model_bfs":"learned_model_bfs",
      "public_bfs_upper":"public_bfs_expert"}[method]
    a=act(kind,state,baseline,control,seed,i)
   inference+=time.perf_counter()-t
   if type(a)is not int or a not in (0,1,2):raise ValueError("K5A_ILLEGAL_ORIGINAL_NATIVE_ACTION")
   old=(state["x"],state["y"],state["dir"],bool(public_grid(state)["FrontBlocked"]))
   next_obs,reward,term,trunc,_=env.step(a)
   nxt=public(next_obs,state["goal"])
   new=(nxt["x"],nxt["y"],nxt["dir"],bool(public_grid(nxt)["FrontBlocked"]))
   if not math.isfinite(float(reward)):raise ValueError("K5A_PUBLIC_REAL_REWARD_NONFINITE")
   t=time.perf_counter()
   if method.startswith("ygg_R3"):
    agent.observe(current,a,prior.into(nxt,PublicGrid),float(reward),bool(term or trunc),False)
    if method=="ygg_R3_no_episodic_edges":
     # Original R3 source and trained native core stay unchanged;
     # only its acquired episode-local causal edges and visits are ablated.
     agent.blocked.clear();agent.open_edges.clear();agent.visits.clear()
   elif method=="conventional_online_optimistic":
    planner.observe(current,a,prior.into(nxt,PublicGrid))
   updating+=time.perf_counter()-t
   actions.append({"t":i,"a":a,"before":old,"after":new,"reward":float(reward),
     "terminated":bool(term),"truncated":bool(trunc)})
   state=nxt;total+=float(reward)
   if term or trunc:
    success=bool(term and total>0);break
  graphbytes=len(agent.snapshot()) if method.startswith("ygg_R3") else 0
  return {"kind":kind,"seed":seed,"policy":method,
    "original_public_reset_sha256":origin,
    "actual_goal_success":success,"real_reward":total,"steps":len(actions),
    "blocked_forward":sum(z["a"]==2 and z["before"][3] for z in actions),
    "actual_public_action_consequence_trace":actions,
    "trace_sha256":sha(canon(actions).encode()),
    "policy_inference_wall_seconds":inference,
    "policy_online_adaptation_wall_seconds":updating,
    "whole_python_episode_CPU_seconds":time.process_time()-cpu,
    "whole_episode_wall_seconds":time.perf_counter()-start,
    "learned_episode_graph_snapshot_bytes":graphbytes}
 finally:env.close()

def eval_phase(phase,r2,r3,model):
 return [run_world(k,seed,m,r2,r3,model) for k,_ in TASKS
   for seed in PHASES[phase] for m in METHODS]

def evaluate(dev):
 res={}
 for kind,_ in TASKS:
  rows=[r for r in dev if r["kind"]==kind]
  if len(rows)!=8*len(METHODS):raise ValueError("K5A_INCOMPLETE_REAL_CROSSING_EVALUATION")
  res[kind]={}
  for m in METHODS:
   x=[r for r in rows if r["policy"]==m]
   if sorted(r["seed"] for r in x)!=list(PHASES["DEV"]):
    raise ValueError("K5A_NONMATCHED_NEW_TOPOLOGY_SEEDS")
   res[kind][m]={"real_goals":sum(v["actual_goal_success"] for v in x),
    "mean_real_reward":sum(v["real_reward"] for v in x)/8,
    "real_total_steps":sum(v["steps"] for v in x),
    "real_blocked_forward":sum(v["blocked_forward"] for v in x),
    "total_policy_inference_seconds":sum(v["policy_inference_wall_seconds"] for v in x),
    "total_online_adaptation_seconds":sum(v["policy_online_adaptation_wall_seconds"] for v in x),
    "mean_episode_graph_bytes":sum(v["learned_episode_graph_snapshot_bytes"] for v in x)/8}
 intact=sum(res[k]["ygg_R3_intact"]["real_goals"] for k,_ in TASKS)
 noedges=sum(res[k]["ygg_R3_no_episodic_edges"]["real_goals"] for k,_ in TASKS)
 online=sum(res[k]["conventional_online_optimistic"]["real_goals"] for k,_ in TASKS)
 gates={
  "crossing1_at_least_4_of_8":res["crossing_1"]["ygg_R3_intact"]["real_goals"]>=4,
  "crossing3_at_least_4_of_8":res["crossing_3"]["ygg_R3_intact"]["real_goals"]>=4,
  "at_least_3_extra_goals_over_no_edge_ablation":intact-noedges>=3,
  "native_within_2_goals_of_equal_public_online_planner":intact>=online-2,
  "full_public_planner_qualified_both":all(res[k]["conventional_fit_model_bfs"]["real_goals"]>=6 for k,_ in TASKS)}
 native_gain=all(gates.values())
 better=intact-online>=3
 native_time=sum(res[k]["ygg_R3_intact"]["total_policy_inference_seconds"]+
                 res[k]["ygg_R3_intact"]["total_online_adaptation_seconds"] for k,_ in TASKS)
 online_time=sum(res[k]["conventional_online_optimistic"]["total_policy_inference_seconds"]+
                 res[k]["conventional_online_optimistic"]["total_online_adaptation_seconds"] for k,_ in TASKS)
 # This cannot substantiate energy/FLOP or full matched resource Pareto.
 novelty=better and native_time<=online_time
 return {"disposition":"BOUNDED_UNFAMILIAR_CROSSING_TOPOLOGY_TRANSFER" if native_gain
         else "NO_QUALIFIED_CROSSING_TOPOLOGY_TRANSFER",
  "per_topology":res,"frozen_primary_tests":gates,
  "native_unfamiliar_abstract_architecture_novelty_not_established":not novelty,
  "native_vs_online_real_goal_delta":intact-online,
  "native_vs_no_memory_real_goal_delta":intact-noedges,
  "native_vs_online_measured_policy_wall_seconds":[native_time,online_time],
  "native_scientific_first_use":False,"scientific_accepted":False}

def experiment():
 events,starts,audit,sourcewall,model,r2,r3,native=fit_authentic_models()
 out={"schema":SCHEMA,"gate":"LCRM01-K5A",
    "FIT_real_events":len(events),"FIT_source_episodes":len(starts),
    "FIT_source_sha256":sha(canon(events).encode()),
    "FIT_original_training_audit":audit,
    "FIT_shared_source_wall_seconds":sourcewall,
    "original_R3_native_source_blob":SOURCE_BLOB,
    "original_K4Z_negative_and_bounded_positive_preserved":True,
    "native_FIT_custody":native,"CHECK_real_episodes":0,"DEV_real_episodes":0,
    "scientific_first_use":False,"scientific_accepted":False}
 checks=eval_phase("CHECK",r2,r3,model)
 dev=eval_phase("DEV",r2,r3,model)
 out.update({"CHECK_real_episodes":len(checks),"DEV_real_episodes":len(dev),
  "CHECK_full_original_public_action_traces":checks,"DEV_full_original_public_action_traces":dev,
  "science":evaluate(dev),"result":"COMPLETE_NEW_TOPOLOGY_NATIVE_ABLATION_STUDY"})
 return out

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise RuntimeError("K5A_SOURCE_OUTPUT_NOT_FRESH")
 start=time.perf_counter();cpu=time.process_time()
 try:
  protocol=frozen()
  o=experiment()
  o["protocol_sha256"]=sha(PROTOCOL.read_bytes())
  o["original_crossing_blob"]=protocol["source"]["crossing_blob"]
 except Exception as e:
  o={"schema":SCHEMA,"gate":"LCRM01-K5A",
     "result":"ORIGINAL_SOURCE_OR_EXPERIMENT_BLOCKED",
     "error_type":type(e).__name__,"error":str(e),
     "traceback_tail":traceback.format_exc().splitlines()[-14:],
     "scientific_first_use":False,"scientific_accepted":False}
 o["resources"]={"whole_original_python_CPU_seconds":time.process_time()-cpu,
     "whole_original_wall_seconds":time.perf_counter()-start,
     "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 a.output.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("K5A_ORIGINAL_STUDY="+o["result"])
 if "science" in o:
  print("K5A_FROZEN_SCIENCE="+o["science"]["disposition"])
  print("K5A_NEW_TOPOLOGY_SUCCESS="+canon(o["science"]["per_topology"]))
 print("K5A_PRESERVED_FIT_EVENTS="+str(o.get("FIT_real_events",0)))
 return int(o["result"]=="ORIGINAL_SOURCE_OR_EXPERIMENT_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
