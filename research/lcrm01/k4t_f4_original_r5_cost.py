#!/usr/bin/env python3
"""K4T-F4 fresh original source public-development R4 frontier versus R3 model.

Native R1/R2/R3 and Ygg source unchanged, one original 12k FIT experience.
R4 feedback during heldout episodes is non-training, session-local only.
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

import k4y_native_affordance as k4y
import k4t_f2_r3_original_public as f2
from k4t_f4_sixfield_conventional import fit as sixfit, SixFieldConventional
from k4r_minigrid_source import canon, sha
from k4u_native_minigrid import WingBridge, public_grid, wingless_wire_grid

FROZEN=Path(__file__).with_name("k4t_f4_frozen_r5_cost.json")
SCHEMA="mass.lcrm01.k4t-f3.original-r4-frontier-public-dev.v1"
FIT=tuple(range(61400,61424))
CHECK=tuple(range(62400,62404))
DEV=tuple(range(63400,63408))
FAMILIES=k4y.FAMILIES
ORIGINAL_METHODS=k4y.METHODS
METHODS=ORIGINAL_METHODS[:2]+f2.R3_METHODS+("wingless_r4_frontier","wingless_r5_cost_frontier","sixfield_fit_model_route")+ORIGINAL_METHODS[2:]

def contract():
 c=json.loads(FROZEN.read_text())
 if (c["schema"]!="mass.lcrm01.k4t-f4.r5-cost-aware-original-source-protocol-v1"
     or c["parent_F3_head"]!="b3fd22033fabfc03f9ffeca92ce061d3e4fff3fc"
     or c["original"]["Wingless_R5_head"]!="978825064dd6076058a1a38ae1a9a3d80e28d99e"
     or c["original"]["Wingless_R5_blob"]!="239a5f2ab6d122b10cd5c7cc9388d154929b9888"
     or c["cohorts"]["FIT"]!=[61400,61423]
     or c["cohorts"]["CHECK"]!=[62400,62403]
     or c["cohorts"]["DEV"]!=[63400,63407]
     or c["cohorts"]["methods"]!=list(METHODS)
     or c["protected_scientific_first_use"] is not False
     or c["scientific_accepted"] is not False):
  raise ValueError("K4T_F4_FROZEN_ORIGINAL_SOURCE_DRIFT")
 return c

def train_r4(stream,exe):
 started=time.perf_counter()
 w=WingBridge(exe)
 try:
  for x in stream:
   w.learn(x["before"],x["action"],x["after"],x["reward"],x["terminal"])
  full=w.snapshot()
  if w.request("snapshot").get("updates")!=len(stream):
   raise ValueError("K4T_F4_R4_SHARED_REAL_FIT_COUNT_DRIFT")
 finally:w.close()
 fresh=WingBridge(exe)
 try:
  fresh.restore(full)
  cold=fresh.snapshot()
  if full!=cold:raise ValueError("K4T_F4_R4_COLD_PROCESS_SNAPSHOT_DRIFT")
  base=fresh.request("snapshot_base")
  if base.get("updates")!=12000 or not base.get("state"):
   raise ValueError("K4T_F4_ORIGINAL_R3_BASE_SOURCE_NOT_RETAINED")
 except Exception:fresh.close();raise
 return fresh,{"R4_true_cold_OS_process":True,
    "R4_FIT_original_native_updates":len(stream),
    "R4_checkpoint_bytes":len(full),
    "R4_checkpoint_sha256":sha(full),
    "R4_core_original_R3_checkpoint_sha256":sha(__import__("base64").b64decode(base["state"])),
    "R4_fit_wall_seconds":time.perf_counter()-started,
    "native_CORE_snapshot_b64_before_holdout":base["state"]}

def r4_episode(family,seed,w):
 from k4r_minigrid_source import public
 e=k4y.make_env(family)
 rows=[];total=0.;cpu=time.process_time();wall=time.perf_counter()
 try:
  w.request("episode_start")
  obs,_=e.reset(seed=seed)
  st=public(obs)
  initial=st["grid_sha256"]
  for tick in range(k4y.STEPS[family]):
   b=public_grid(st)
   wire=wingless_wire_grid(b)
   action=w.request("choose",before=wire)["action"]
   if type(action) is not int or action not in (0,1,2):
    raise ValueError("K4T_F4_NATIVE_R4_ILLEGAL_REAL_ACTION")
   before=[st["x"],st["y"],st["dir"],st["goal"][0],st["goal"][1],int(b["FrontBlocked"])]
   nxtobs,reward,term,trunc,_=e.step(action)
   nxt=public(nxtobs,st["goal"])
   if not math.isfinite(float(reward)):raise ValueError("K4T_F4_NONFINITE_REAL_REWARD")
   after=[nxt["x"],nxt["y"],nxt["dir"],nxt["goal"][0],nxt["goal"][1],
          int(public_grid(nxt)["FrontBlocked"])]
   report=w.request("feedback",before=wire,action=action,
                    after=wingless_wire_grid(public_grid(nxt)))
   if report.get("steps")!=tick+1 or report.get("updates")!=12000:
    raise ValueError("K4T_F4_R4_HELDOUT_UPDATE_OR_EPISODE_DRIFT")
   rows.append({"t":tick,"a":action,"before":before,"after":after,
                "reward":float(reward),"terminated":bool(term),"truncated":bool(trunc)})
   total+=float(reward);st=nxt
   if term or trunc:break
  return {"family":family,"seed":seed,"method":"wingless_r4_frontier",
          "source_first_reset_sha256":initial,
          "success":bool(rows[-1]["terminated"] and total>0),
          "real_total_reward":total,"actual_public_step_trace":rows,
          "trace_sha256":sha(canon(rows).encode()),
          "episode_CPU_python_seconds":time.process_time()-cpu,
          "episode_wall_seconds":time.perf_counter()-wall}
 finally:e.close()

def r4_evaluation(part,w):
 seeds=CHECK if part=="CHECK" else DEV
 return [r4_episode(f,s,w) for f in FAMILIES for s in seeds]
def r5_evaluation(part,w):
 seeds=CHECK if part=="CHECK" else DEV
 rows=[r4_episode(f,s,w) for f in FAMILIES for s in seeds]
 for row in rows:row["method"]="wingless_r5_cost_frontier"
 return rows
def r3_evaluation(part,w):
 seeds=CHECK if part=="CHECK" else DEV
 return [f2.r3_episode(f,s,m,w) for f in FAMILIES for s in seeds for m in f2.R3_METHODS]
def sixfield_episode(family,seed,learned):
 policy=SixFieldConventional(learned)
 env=k4y.make_env(family)
 rows=[];total=0.;cpu=time.process_time();wall=time.perf_counter()
 try:
  obs,_=env.reset(seed=seed);st=k4y.public(obs)
  first=st["grid_sha256"]
  for tick in range(k4y.STEPS[family]):
   b=public_grid(st);a=policy.choose(b)
   if type(a) is not int or a not in (0,1,2):raise ValueError("K4T_F4_ILLEGAL_SIXFIELD_ACTION")
   before=[st["x"],st["y"],st["dir"],st["goal"][0],st["goal"][1],int(b["FrontBlocked"])]
   nextobs,reward,term,trunc,_=env.step(a)
   nxt=k4y.public(nextobs,st["goal"])
   policy.feedback(b,a,public_grid(nxt))
   if not math.isfinite(float(reward)):raise ValueError("K4T_F4_NONFINITE_SOURCE_REWARD")
   after=[nxt["x"],nxt["y"],nxt["dir"],nxt["goal"][0],nxt["goal"][1],int(public_grid(nxt)["FrontBlocked"])]
   rows.append({"t":tick,"a":a,"before":before,"after":after,"reward":float(reward),
                "terminated":bool(term),"truncated":bool(trunc)})
   total+=float(reward);st=nxt
   if term or trunc:break
  return {"family":family,"seed":seed,"method":"sixfield_fit_model_route",
          "source_first_reset_sha256":first,"success":bool(rows[-1]["terminated"] and total>0),
          "real_total_reward":total,"actual_public_step_trace":rows,
          "trace_sha256":sha(canon(rows).encode()),
          "episode_CPU_python_seconds":time.process_time()-cpu,
          "episode_wall_seconds":time.perf_counter()-wall}
 finally:env.close()
def sixfield_evaluation(part,learned):
 seeds=CHECK if part=="CHECK" else DEV
 return [sixfield_episode(f,s,learned) for f in FAMILIES for s in seeds]

def outcome(original,dev):
 result={f:dict(original["results"][f]) for f in FAMILIES}
 for f in FAMILIES:
  for method in ("wingless_r4_frontier","wingless_r5_cost_frontier","sixfield_fit_model_route"):
   episodes=[x for x in dev if x["family"]==f and x["method"]==method]
   if len(episodes)!=8:raise ValueError("K4T_F4_MISSING_ORIGINAL_DEV_METHOD")
   result[f][method]=f2.scores(episodes)
 rules=contract()["registered_decision"]
 c={}
 for f in FAMILIES:
  a=result[f]["wingless_r5_cost_frontier"]
  b=result[f]["wingless_r4_frontier"]
  full=result[f]["fit_dynamics_bfs"]
  c[f+"_source_goals"]=a["successes"] >= (rules["Empty_R5_min_goals"] if f=="empty" else rules["FourRooms_R5_min_goals"])
  c[f+"_fitted_control_source_eligible"]=full["successes"]>=rules["full_map_fitted_control_min_goals_each"]
  c[f+"_blocked_forward_not_worse_than_R4"]=a["blocked_forward_per_100_steps"]<=b["blocked_forward_per_100_steps"]
  if f=="fourrooms":
   c["fourrooms_extra_goals_over_R4"]=a["successes"]>=b["successes"]+rules["FourRooms_R5_min_extra_goals_over_R4"]
   c["fourrooms_reward_vs_full_map_planner"]=a["mean_real_reward"]>=full["mean_real_reward"]*rules["FourRooms_R5_reward_min_relative_to_FULL_MAP_fitted_dynamics_BFS"]
   c["fourrooms_not_worse_goals_than_sixfield_control"]=a["successes"]>=result[f]["sixfield_fit_model_route"]["successes"]
 return {"result":rules["development_GO"] if all(c.values()) else rules["NO_GO"],
         "criteria":c,"results":result,"scientific_first_use":False,"scientific_accepted":False,
         "conventional_sixfield_same_observations":True,"full_map_control_has_extra_information":True}

def experiment(r1,r2,r3,r4,r5):
 frozen=contract()
 k4y.SEEDS={"FIT":FIT,"CHECK":CHECK,"DEV":DEV}
 stream,starts,audit,wall,control=k4y.fit()
 base={"schema":SCHEMA,"gate":"LCRM01-K4T-F4",
       "source_minigrid_commit":frozen["original"]["minigrid_commit"],
       "Wingless_R5_source_blob":frozen["original"]["Wingless_R5_blob"],
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "FIT_public_experience_count":len(stream),"FIT_original_public_experiences":stream,
       "FIT_episodes":len(starts),"FIT_original_balance":audit,
       "shared_FIT_source_wall_seconds":wall,
       "CHECK_episodes":0,"DEV_episodes":0,
       "old_K4Y_F1_F2_F3_no_go_preserved":True,"scientific_first_use":False,"scientific_accepted":False}
 if control is None or len(stream)!=12000:
  base["result"]="FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED";return base
 learned,digest=sixfit(stream)
 base["sixfield_FIT_trained_model_sha256"]=digest
 base["FIT_fitted_control_sha256"]=sha(canon(control).encode())
 learners,y1,y2,native=k4y.train(stream,r1,r2)
 w3=w4=w5=None
 try:
  w3,info3=f2.train_r3(stream,r3)
  w4,info4=train_r4(stream,r4)
  w5,info5=train_r4(stream,r5)
  base4=info4.pop("native_CORE_snapshot_b64_before_holdout")
  base5=info5.pop("native_CORE_snapshot_b64_before_holdout")
  if base4!=base5:raise ValueError("K4T_F4_UNEQUAL_R3_FIT_MODELS")
  translated={("R5"+key[2:] if key.startswith("R4") else key):val for key,val in info5.items()}
  base["native_FIT_custody"]={**native,**info3,**info4,**translated}
  check=(k4y.evaluation("CHECK",learners,y1,y2,control)+r3_evaluation("CHECK",w3)+
    r4_evaluation("CHECK",w4)+r5_evaluation("CHECK",w5)+sixfield_evaluation("CHECK",learned))
  dev=(k4y.evaluation("DEV",learners,y1,y2,control)+r3_evaluation("DEV",w3)+
    r4_evaluation("DEV",w4)+r5_evaluation("DEV",w5)+sixfield_evaluation("DEV",learned))
  if len(check)!=112 or len(dev)!=224:raise ValueError("K4T_F4_METHODS_OR_FRESH_WORLDS_MISSING")
  if (w4.request("snapshot_base").get("state")!=base4 or
      w5.request("snapshot_base").get("state")!=base5):
   raise ValueError("K4T_F4_HELDOUT_WROTE_NATIVE_FIT_WEIGHTS")
  legacy=k4y.report([x for x in dev if x["method"] in ORIGINAL_METHODS])
  r3results=f2.judgment(legacy,[x for x in dev if x["method"] in f2.R3_METHODS])["results"]
  for f in FAMILIES:
   for name in f2.R3_METHODS:legacy["results"][f][name]=r3results[f][name]
  judge=outcome(legacy,dev)
  base.update({"result":"COMPLETE_R5_ORIGINAL_SOURCE_PUBLIC_DEVELOPMENT",
               "CHECK_episodes":len(check),"DEV_episodes":len(dev),
               "CHECK_original_public_traces":check,"DEV_original_public_traces":dev,
               "r5_preregistered_disposition":judge})
  return base
 finally:
  for w in (w3,w4,w5):
   if w is not None:w.close()
  learners["wingless_r1"].close();learners["wingless_r2"].close()

def main():
 p=argparse.ArgumentParser()
 for name in ("wingless_r1","wingless_r2","wingless_r3","wingless_r4","wingless_r5","yggdrasil_source"):
  p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("K4T_F4_NONFRESH_RESULT")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  sys.path.insert(0,str(a.yggdrasil_source.resolve()))
  v=experiment(a.wingless_r1,a.wingless_r2,a.wingless_r3,a.wingless_r4,a.wingless_r5)
 except Exception as e:
  v={"schema":SCHEMA,"gate":"LCRM01-K4T-F4",
     "result":"SOURCE_OR_INFRASTRUCTURE_BLOCKED","error":str(e),
     "error_type":type(e).__name__,
     "traceback_tail":traceback.format_exc().splitlines()[-18:],
     "scientific_first_use":False,"scientific_accepted":False}
 v["resources"]={"process_Python_CPU_excludes_Go":time.process_time()-cpu,
                 "wall_seconds":time.perf_counter()-wall,
                 "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
                 "full_subprocess_CPU_and_energy_unmeasured":True}
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F4_ORIGINAL_SOURCE_RESULT="+v["result"])
 if "r5_preregistered_disposition" in v:
  d=v["r5_preregistered_disposition"]
  print("K4T_F4_R5_DECISION="+d["result"])
  print("K4T_F4_GOALS="+canon({f:{m:d["results"][f][m]["successes"]
    for m in ("wingless_r3","wingless_r4_frontier","wingless_r5_cost_frontier","sixfield_fit_model_route","fit_dynamics_bfs")}
    for f in FAMILIES}))
  print("K4T_F4_CRITERIA="+canon(d["criteria"]))
 print("K4T_F4_FIT_PUBLIC_REAL_EVENTS="+str(v.get("FIT_public_experience_count",0)))
 return int(v["result"]=="SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
