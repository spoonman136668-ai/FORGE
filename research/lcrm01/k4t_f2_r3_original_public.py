#!/usr/bin/env python3
"""K4T-F2: prospectively frozen authentic MiniGrid R3 action-model comparison.

This is PUBLIC DEVELOPMENT ONLY; reuses original K4Y R1/R2/Ygg/learned fitted
controls and gives original Wingless R3 the exact same real 12,000 FIT events.
Never mutates original K4Y modules, scientific results, or protected cohorts.
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
from k4r_minigrid_source import canon, sha
from k4u_native_minigrid import WingBridge, public_grid, wingless_wire_grid

FROZEN = Path(__file__).with_name("k4t_f2_frozen_r3_action_model.json")
SCHEMA = "mass.lcrm01.k4t-f2.original-source-r3-model-navigation-dev.v1"
FIT=tuple(range(41400,41424))
CHECK=tuple(range(42400,42404))
DEV=tuple(range(43400,43408))
R3_METHODS=("wingless_r3","wingless_r3_no_plan")
FAMILIES=("empty","fourrooms")
ORIGINAL_METHODS=k4y.METHODS
METHODS=ORIGINAL_METHODS+R3_METHODS

def contract():
 p=json.loads(FROZEN.read_text())
 sources=p["original_sources"]
 if(p["schema"]!="mass.lcrm01.k4t-f2.r3-original-source-action-model-frozen.v1"
    or p["frozen_parent"]["forge_head"]!="1f6157cb3fbe7d80e6d374adb0cff6ad566d42f8"
    or sources["original_Wingless_R3_commit"]!="3b11363b93e61311a8e96de2546b1a7f7f62d5db"
    or sources["original_Wingless_R3_blob"]!="3c8a60a5037e6c0f04648ae53175ed1187b5f8ac"
    or sources["minigrid_upstream"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
    or p["cohorts"]["FIT"]!={"start":41400,"end":41423,"steps_per_family":6000,"role":"TRAIN_ONLY"}
    or p["cohorts"]["CHECK"]!={"start":42400,"end":42403,"role":"NO_UPDATE"}
    or p["cohorts"]["DEV"]!={"start":43400,"end":43407,"role":"NO_UPDATE"}
    or p["cohorts"]["legal_actions"]!=[0,1,2]
    or p["cohorts"]["methods"]!=list(METHODS)
    or p["first_use"] is not False
    or p["scientific_accepted"] is not False
    or p["governance"]["no_protected_holdout"] is not True):
  raise ValueError("K4T_F2_FROZEN_FIRST_USE_SOURCE_OR_COHORT_DRIFT")
 return p

def train_r3(data,binary):
 start=time.perf_counter()
 w=WingBridge(binary)
 try:
  for x in data:
   w.learn(x["before"],x["action"],x["after"],x["reward"],x["terminal"])
  report=w.request("snapshot")
  raw=w.snapshot()
  if report.get("updates")!=len(data):
   raise ValueError("K4T_F2_NATIVE_R3_FIT_UPDATE_COUNT_DRIFT")
 finally:w.close()
 restored=WingBridge(binary)
 try:
  restored.restore(raw)
  report2=restored.request("snapshot")
  if report2.get("updates")!=len(data) or restored.snapshot()!=raw:
   raise ValueError("K4T_F2_NATIVE_R3_COLD_PROCESS_STATE_DRIFT")
  for x in data[:32]:
   v=x["before"]
   if (restored.choose(v) not in (0,1,2)
       or type(restored.request("choose_core",before=wingless_wire_grid(v)).get("action")) is not int):
    raise ValueError("K4T_F2_NATIVE_R3_COLD_PROCESS_ACTION_DRIFT")
 except Exception:restored.close();raise
 return restored,{"FIT_original_native_R3_completed_updates":len(data),
                  "R3_authentic_cold_OS_restore":True,
                  "R3_fit_wall_seconds":time.perf_counter()-start,
                  "R3_checkpoint_bytes":len(raw),
                  "R3_checkpoint_sha256":sha(raw)}

def r3_episode(family,seed,method,bridge):
 env=k4y.make_env(family)
 rows=[];total=0.;start=time.perf_counter();cpu=time.process_time()
 try:
  ob,_=env.reset(seed=seed)
  st=k4y.public(ob);original=st["grid_sha256"]
  for tick in range(k4y.STEPS[family]):
   wire=wingless_wire_grid(public_grid(st))
   if method=="wingless_r3":
    action=bridge.choose(public_grid(st))
   elif method=="wingless_r3_no_plan":
    action=bridge.request("choose_core",before=wire)["action"]
   else:raise ValueError("K4T_F2_UNKNOWN_R3_METHOD")
   if type(action) is not int or action not in (0,1,2):
    raise ValueError("K4T_F2_UNLAWFUL_NATIVE_ACTION")
   before=[st["x"],st["y"],st["dir"],st["goal"][0],st["goal"][1],
           int(public_grid(st)["FrontBlocked"])]
   newob,reward,term,trunc,_=env.step(action)
   nxt=k4y.public(newob,st["goal"])
   after=[nxt["x"],nxt["y"],nxt["dir"],nxt["goal"][0],nxt["goal"][1],
          int(public_grid(nxt)["FrontBlocked"])]
   if not math.isfinite(float(reward)):raise ValueError("K4T_F2_NONFINITE_REAL_REWARD")
   rows.append({"t":tick,"a":action,"before":before,"after":after,
                "reward":float(reward),"terminated":bool(term),"truncated":bool(trunc)})
   total+=float(reward);st=nxt
   if term or trunc:break
  return {"family":family,"seed":seed,"method":method,
          "source_first_reset_sha256":original,
          "success":bool(rows[-1]["terminated"] and total>0),
          "real_total_reward":total,"actual_public_step_trace":rows,
          "trace_sha256":sha(canon(rows).encode()),
          "episode_CPU_python_seconds":time.process_time()-cpu,
          "episode_wall_seconds":time.perf_counter()-start}
 finally:env.close()

def r3_evaluate(phase,model):
 seeds={"CHECK":CHECK,"DEV":DEV}[phase]
 return [r3_episode(f,seed,m,model)
         for f in FAMILIES for seed in seeds for m in R3_METHODS]

def scores(episodes):
 ticks=[step for ep in episodes for step in ep["actual_public_step_trace"]]
 return {"successes":sum(x["success"] for x in episodes),
         "mean_real_reward":sum(x["real_total_reward"] for x in episodes)/8,
         "actual_total_steps":len(ticks),
         "blocked_forward_steps":sum(t["a"]==2 and t["before"][5]==1 for t in ticks),
         "blocked_forward_per_100_steps":
           100*sum(t["a"]==2 and t["before"][5]==1 for t in ticks)/len(ticks),
         "first_actions":sorted({ep["actual_public_step_trace"][0]["a"] for ep in episodes})}

def judgment(original,r3dev):
 result={f:dict(original["results"][f]) for f in FAMILIES}
 for f in FAMILIES:
  for m in R3_METHODS:
   v=[ep for ep in r3dev if ep["family"]==f and ep["method"]==m]
   if len(v)!=8:raise ValueError("K4T_F2_INCOMPLETE_DEV_NATIVE_TRACES")
   result[f][m]=scores(v)
 criteria={}
 for f in FAMILIES:
  a=result[f]["wingless_r3"];b=result[f]["wingless_r2"]
  n=result[f]["wingless_r3_no_plan"];c=result[f]["fit_dynamics_bfs"]
  criteria[f+"_r3_four_goals"]=a["successes"]>=4
  criteria[f+"_r3_goal_better_than_no_plan"]=a["successes"]>=n["successes"]+1
  criteria[f+"_fitted_planner_six_goals"]=c["successes"]>=6
  criteria[f+"_r3_reward_75pct_planner"]=a["mean_real_reward"]>=.75*c["mean_real_reward"]
  criteria[f+"_no_more_blocked_forward_than_r2"]=(
      a["blocked_forward_per_100_steps"]<=b["blocked_forward_per_100_steps"])
 gain=sum(result[f]["wingless_r3"]["successes"]-result[f]["wingless_r2"]["successes"]
          for f in FAMILIES)
 criteria["two_real_additional_goals_over_r2"]=gain>=2
 success=all(criteria.values())
 return {"result":("BOUNDED_R3_ACTION_MODEL_GOAL_DEVELOPMENT_GAIN_NOT_NOVELTY"
                   if success else "NO_R3_MODEL_NAVIGATION_ADVANCEMENT"),
         "criteria":criteria,"R3_real_goal_delta_over_R2":gain,
         "results":result,
         "source_scope":"PUBLIC_DEVELOPMENT_NOT_PROTECTED_FIRST_USE",
         "scientific_accepted":False,"scientific_first_use":False,
         "not_proof_of_novel_native_causal_representation":True}

def experiment(r1,r2,r3):
 p=contract()
 k4y.SEEDS={"FIT":FIT,"CHECK":CHECK,"DEV":DEV}
 stream,starts,audit,source_wall,control=k4y.fit()
 base={"schema":SCHEMA,"gate":"LCRM01-K4T-F2",
       "FIT_original_public_experiences":stream,
       "FIT_public_experience_count":len(stream),
       "FIT_episodes":len(starts),"FIT_original_balance":audit,
       "shared_FIT_source_wall_seconds":source_wall,
       "CHECK_episodes":0,"DEV_episodes":0,
       "source_minigrid_commit":p["original_sources"]["minigrid_upstream"],
       "source_Wingless_R3_commit":p["original_sources"]["original_Wingless_R3_commit"],
       "source_Wingless_R3_blob":p["original_sources"]["original_Wingless_R3_blob"],
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "historical_K4T_F1_and_K4Y_negatives_unchanged":True,
       "scientific_first_use":False,"scientific_accepted":False}
 if control is None or len(stream)!=12000:
  base["result"]="FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED"
  return base
 base["FIT_conventional_sha256"]=sha(canon(control).encode())
 learners,y1,y2,info=k4y.train(stream,r1,r2)
 w3=None
 try:
  w3,info3=train_r3(stream,r3)
  base["native_FIT_custody"]={**info,**info3}
  check=k4y.evaluation("CHECK",learners,y1,y2,control)+r3_evaluate("CHECK",w3)
  dev=k4y.evaluation("DEV",learners,y1,y2,control)+r3_evaluate("DEV",w3)
  if(len(check)!=len(METHODS)*len(CHECK)*len(FAMILIES)
     or len(dev)!=len(METHODS)*len(DEV)*len(FAMILIES)):
   raise ValueError("K4T_F2_MATCHED_REAL_SOURCE_EVALUATION_MISSING")
  origin=k4y.report([x for x in dev if x["method"] in ORIGINAL_METHODS])
  base.update({"result":"COMPLETE_R3_ORIGINAL_SOURCE_PUBLIC_DEVELOPMENT",
               "CHECK_episodes":len(check),"DEV_episodes":len(dev),
               "CHECK_original_public_traces":check,
               "DEV_original_public_traces":dev,
               "original_R1_R2_Ygg_and_conventional_science":origin,
               "r3_preregistered_disposition":judgment(origin,r3_evaluation_subset(dev))})
  return base
 finally:
  if w3 is not None:w3.close()
  learners["wingless_r1"].close()
  learners["wingless_r2"].close()

def r3_evaluation_subset(dev):
 return [x for x in dev if x["method"] in R3_METHODS]

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--wingless-r1",type=Path,required=True)
 ap.add_argument("--wingless-r2",type=Path,required=True)
 ap.add_argument("--wingless-r3",type=Path,required=True)
 ap.add_argument("--yggdrasil-source",type=Path,required=True)
 ap.add_argument("--output",type=Path,required=True)
 a=ap.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("K4T_F2_NONFRESH_EVIDENCE")
 st=time.perf_counter();cpu=time.process_time()
 try:
  sys.path.insert(0,str(a.yggdrasil_source.resolve()))
  q=experiment(a.wingless_r1,a.wingless_r2,a.wingless_r3)
 except Exception as e:
  q={"schema":SCHEMA,"gate":"LCRM01-K4T-F2",
     "result":"SOURCE_OR_INFRASTRUCTURE_BLOCKED",
     "error_type":type(e).__name__,"error":str(e),
     "traceback_tail":traceback.format_exc().splitlines()[-18:],
     "scientific_first_use":False,"scientific_accepted":False}
 q["resources"]={"whole_python_process_CPU_seconds_excludes_Go":time.process_time()-cpu,
                 "whole_wall_seconds":time.perf_counter()-st,
                 "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
                 "Go_CPU_and_energy_not_measured":True}
 a.output.write_text(json.dumps(q,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F2_ORIGINAL_RESULT="+q["result"])
 if "r3_preregistered_disposition" in q:
  print("K4T_F2_R3_DISPOSITION="+q["r3_preregistered_disposition"]["result"])
  print("K4T_F2_REAL_DEV_COUNTS="+canon({f:{m:q["r3_preregistered_disposition"]["results"][f][m]["successes"]
                        for m in METHODS} for f in FAMILIES}))
 print("K4T_F2_FIT_REAL_EVENTS="+str(q.get("FIT_public_experience_count",0)))
 return int(q["result"]=="SOURCE_OR_INFRASTRUCTURE_BLOCKED")

if __name__=="__main__":
 raise SystemExit(main())
