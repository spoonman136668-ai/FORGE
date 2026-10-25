#!/usr/bin/env python3
"""K4T-F3 fresh original source public-development R4 frontier versus R3 model.

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
from k4r_minigrid_source import canon, sha
from k4u_native_minigrid import WingBridge, public_grid, wingless_wire_grid

FROZEN=Path(__file__).with_name("k4t_f3_frozen_r4_frontier.json")
SCHEMA="mass.lcrm01.k4t-f3.original-r4-frontier-public-dev.v1"
FIT=tuple(range(51400,51424))
CHECK=tuple(range(52400,52404))
DEV=tuple(range(53400,53408))
FAMILIES=k4y.FAMILIES
ORIGINAL_METHODS=k4y.METHODS
METHODS=ORIGINAL_METHODS[:2]+f2.R3_METHODS+("wingless_r4_frontier",)+ORIGINAL_METHODS[2:]

def contract():
 c=json.loads(FROZEN.read_text())
 if(c["schema"]!="mass.lcrm01.k4t-f3.frozen-r4-source-local-frontier-v1"
    or c["parent"]["forge_F2_head"]!="d8394de63d0715d622ae96bdac3a1d1bf5e14230"
    or c["original_sources"]["wingless_r4_commit"]!="1b1bea442027132df5acdf67b8353e9a5a3046f4"
    or c["original_sources"]["wingless_r4_blob"]!="61678ff1c95966151f1b1731fef62b804504cdf8"
    or c["cohorts"]["FIT"]!=[51400,51423]
    or c["cohorts"]["CHECK"]!=[52400,52403]
    or c["cohorts"]["DEV"]!=[53400,53407]
    or c["cohorts"]["method_names"]!=list(METHODS)
    or c["scientific_first_use"] is not False
    or c["scientific_accepted"] is not False
    or c["governance"]["no_protected_merge"] is not True):
  raise ValueError("K4T_F3_FROZEN_NATIVE_OR_COHORT_DRIFT")
 return c

def train_r4(stream,exe):
 started=time.perf_counter()
 w=WingBridge(exe)
 try:
  for x in stream:
   w.learn(x["before"],x["action"],x["after"],x["reward"],x["terminal"])
  full=w.snapshot()
  if w.request("snapshot").get("updates")!=len(stream):
   raise ValueError("K4T_F3_R4_SHARED_REAL_FIT_COUNT_DRIFT")
 finally:w.close()
 fresh=WingBridge(exe)
 try:
  fresh.restore(full)
  cold=fresh.snapshot()
  if full!=cold:raise ValueError("K4T_F3_R4_COLD_PROCESS_SNAPSHOT_DRIFT")
  base=fresh.request("snapshot_base")
  if base.get("updates")!=12000 or not base.get("state"):
   raise ValueError("K4T_F3_ORIGINAL_R3_BASE_SOURCE_NOT_RETAINED")
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
    raise ValueError("K4T_F3_NATIVE_R4_ILLEGAL_REAL_ACTION")
   before=[st["x"],st["y"],st["dir"],st["goal"][0],st["goal"][1],int(b["FrontBlocked"])]
   nxtobs,reward,term,trunc,_=e.step(action)
   nxt=public(nxtobs,st["goal"])
   if not math.isfinite(float(reward)):raise ValueError("K4T_F3_NONFINITE_REAL_REWARD")
   after=[nxt["x"],nxt["y"],nxt["dir"],nxt["goal"][0],nxt["goal"][1],
          int(public_grid(nxt)["FrontBlocked"])]
   report=w.request("feedback",before=wire,action=action,
                    after=wingless_wire_grid(public_grid(nxt)))
   if report.get("steps")!=tick+1 or report.get("updates")!=12000:
    raise ValueError("K4T_F3_R4_HELDOUT_UPDATE_OR_EPISODE_DRIFT")
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

def r4_evaluation(part,bridge):
 return [r4_episode(f,seed,bridge)
         for f in FAMILIES for seed in (CHECK if part=="CHECK" else DEV)]

def r3_evaluation(part,bridge):
 return [f2.r3_episode(f,seed,method,bridge)
         for f in FAMILIES for seed in (CHECK if part=="CHECK" else DEV)
         for method in f2.R3_METHODS]

def outcome(original,real):
 results={f:dict(original["results"][f]) for f in FAMILIES}
 for f in FAMILIES:
  selected=[row for row in real if row["family"]==f]
  if len(selected)!=8:raise ValueError("K4T_F3_R4_DEV_INCOMPLETE")
  results[f]["wingless_r4_frontier"]=f2.scores(selected)
 rules=contract()["decision_thresholds"]
 c={}
 for f in FAMILIES:
  r=results[f]["wingless_r4_frontier"]
  b=results[f]["wingless_r3"]
  planner=results[f]["fit_dynamics_bfs"]
  c[f+"_fitted_trained_planner_six"]=planner["successes"]>=rules["learned_fitted_planner_min_goals_each_family"]
  c[f+"_goal_preserve"]=r["successes"]>=(
   rules["R4_min_Empty_goals"] if f=="empty" else rules["R4_min_FourRooms_goals"])
  c[f+"_blocked_forward_not_worse"]=(
   r["blocked_forward_per_100_steps"]<=b["blocked_forward_per_100_steps"]+
       rules["R4_max_blocked_forward_per100_relative_to_R3"])
  if f=="fourrooms":
   c["fourrooms_two_extra_goals_over_r3"]=(
    r["successes"]>=b["successes"]+rules["R4_extra_FourRooms_goals_over_R3"])
   c["fourrooms_reward_75pct_strong_fitted_control"]=(
    r["mean_real_reward"]>=planner["mean_real_reward"]*
         rules["R4_min_mean_FourRooms_reward_fraction_of_fitted_planner"])
 gain=sum(results[f]["wingless_r4_frontier"]["successes"]-
          results[f]["wingless_r3"]["successes"] for f in FAMILIES)
 c["two_actual_extra_goals_total"]=gain>=rules["R4_extra_total_goals_over_R3"]
 ok=all(c.values())
 return {"result":(rules["accepted_result_label"] if ok else rules["failed_result_label"]),
         "criteria":c,"r4_real_goal_gain_over_r3":gain,"results":results,
         "scientific_first_use":False,"scientific_accepted":False,
         "information_parity_with_full_grid_planner":False}

def experiment(bin_r1,bin_r2,bin_r3,bin_r4):
 c=contract()
 k4y.SEEDS={"FIT":FIT,"CHECK":CHECK,"DEV":DEV}
 stream,starts,audit,wall,control=k4y.fit()
 base={"schema":SCHEMA,"gate":"LCRM01-K4T-F3",
       "source_minigrid_commit":c["original_sources"]["minigrid_commit"],
       "Wingless_R4_source_blob":c["original_sources"]["wingless_r4_blob"],
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "FIT_public_experience_count":len(stream),"FIT_original_public_experiences":stream,
       "FIT_episodes":len(starts),"FIT_original_balance":audit,
       "shared_FIT_source_wall_seconds":wall,
       "CHECK_episodes":0,"DEV_episodes":0,
       "original_K4Y_F1_F2_no_go_immutable":True,
       "scientific_first_use":False,"scientific_accepted":False}
 if control is None or len(stream)!=12000:
  base["result"]="FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED";return base
 base["FIT_fitted_control_sha256"]=sha(canon(control).encode())
 learners,y1,y2,native=k4y.train(stream,bin_r1,bin_r2)
 w3=None;w4=None
 try:
  w3,info3=f2.train_r3(stream,bin_r3)
  w4,info4=train_r4(stream,bin_r4)
  saved=info4.pop("native_CORE_snapshot_b64_before_holdout")
  base["native_FIT_custody"]={**native,**info3,**info4}
  check=(k4y.evaluation("CHECK",learners,y1,y2,control)+
         r3_evaluation("CHECK",w3)+r4_evaluation("CHECK",w4))
  dev=(k4y.evaluation("DEV",learners,y1,y2,control)+
       r3_evaluation("DEV",w3)+r4_evaluation("DEV",w4))
  if w4.request("snapshot_base").get("state")!=saved:
   raise ValueError("K4T_F3_R4_FIT_WEIGHTS_CONTAMINATED_BY_CHECK_DEV")
  if len(check)!=96 or len(dev)!=192:
   raise ValueError("K4T_F3_REAL_COMPARATOR_COHORT_INCOMPLETE")
  original=k4y.report([x for x in dev if x["method"] in ORIGINAL_METHODS])
  r3rows=[x for x in dev if x["method"] in f2.R3_METHODS]
  fusion=f2.judgment(original,r3rows)["results"]
  for f in FAMILIES:original["results"][f].update({name:fusion[f][name] for name in f2.R3_METHODS})
  r4rows=[x for x in dev if x["method"]=="wingless_r4_frontier"]
  base.update({"result":"COMPLETE_R4_GENUINE_PUBLIC_DEVELOPMENT",
               "CHECK_episodes":len(check),"DEV_episodes":len(dev),
               "CHECK_original_public_traces":check,"DEV_original_public_traces":dev,
               "r4_preregistered_disposition":outcome(original,r4rows)})
  return base
 finally:
  if w3 is not None:w3.close()
  if w4 is not None:w4.close()
  learners["wingless_r1"].close();learners["wingless_r2"].close()

def main():
 p=argparse.ArgumentParser()
 for name in ("wingless_r1","wingless_r2","wingless_r3","wingless_r4","yggdrasil_source"):
  p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("K4T_F3_NONFRESH_RESULT")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  sys.path.insert(0,str(a.yggdrasil_source.resolve()))
  v=experiment(a.wingless_r1,a.wingless_r2,a.wingless_r3,a.wingless_r4)
 except Exception as e:
  v={"schema":SCHEMA,"gate":"LCRM01-K4T-F3",
     "result":"SOURCE_OR_INFRASTRUCTURE_BLOCKED","error":str(e),
     "error_type":type(e).__name__,
     "traceback_tail":traceback.format_exc().splitlines()[-18:],
     "scientific_first_use":False,"scientific_accepted":False}
 v["resources"]={"process_Python_CPU_excludes_Go":time.process_time()-cpu,
                 "wall_seconds":time.perf_counter()-wall,
                 "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
                 "full_subprocess_CPU_and_energy_unmeasured":True}
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F3_ORIGINAL_SOURCE_RESULT="+v["result"])
 if "r4_preregistered_disposition" in v:
  d=v["r4_preregistered_disposition"]
  print("K4T_F3_R4_DECISION="+d["result"])
  print("K4T_F3_GOALS="+canon({f:{m:d["results"][f][m]["successes"]
    for m in ("wingless_r2","wingless_r3","wingless_r4_frontier","fit_dynamics_bfs")}
    for f in FAMILIES}))
  print("K4T_F3_CRITERIA="+canon(d["criteria"]))
 print("K4T_F3_FIT_PUBLIC_REAL_EVENTS="+str(v.get("FIT_public_experience_count",0)))
 return int(v["result"]=="SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
