#!/usr/bin/env python3
"""F5: original source native R6 observed edges vs unchanged R5 and sixfield fit."""
import argparse
import hashlib
import json
import math
import resource
import sys
import time
import traceback
from pathlib import Path

import k4y_native_affordance as k4y
import k4t_f4_original_r5_cost as f4
import k4t_f2_r3_original_public as f2
from k4r_minigrid_source import canon,sha

FROZEN=Path(__file__).with_name("k4t_f6_frozen_r7_physical.json")
SCHEMA="mass.lcrm01.k4t-f5.original-r6-observed-public-dev.v1"
FIT=tuple(range(81400,81424))
CHECK=tuple(range(82400,82404))
DEV=tuple(range(83400,83408))
FAMILIES=("empty","fourrooms")
OLD=k4y.METHODS
METHODS=OLD[:2]+f2.R3_METHODS+("wingless_r4_frontier","wingless_r5_cost_frontier","wingless_r6_observed_route","wingless_r7_physical_frontier","sixfield_fit_model_route")+OLD[2:]

def contract():
 p=json.loads(FROZEN.read_text())
 if(p["schema"]!="mass.lcrm01.k4t-f6.frozen-physical-cell-r7-v1"
    or p["priorExactF5Commit"]!="a1dc7bf282fdb9354941b1a7ad05f37941791cb3"
    or p["source"]["Wingless_R7_commit"]!="7980717a7b751844c154cdd35e795c21d9679464"
    or p["source"]["Wingless_R7_code"]!="4dcb8d83fe40be2f31faa90dac463ccf31485945"
    or p["cohorts"]["FIT"]!=[81400,81423]
    or p["cohorts"]["CHECK"]!=[82400,82403]
    or p["cohorts"]["DEV"]!=[83400,83407]
    or p["cohorts"]["methods"]!=list(METHODS)
    or p["governance"]["scientificFirstUse"] is not False
    or p["governance"]["scientificAccepted"] is not False):
  raise ValueError("F6_ORIGINAL_SOURCE_CONTRACT_DRIFT")
 return p

def evaluation(phase,method,subject):
 seeds=CHECK if phase=="CHECK" else DEV
 out=[]
 for family in FAMILIES:
  for seed in seeds:
   if method=="wingless_r3":
    raise ValueError("F5_R3_NEEDS_TWO_METHOD_EVALUATION")
   elif method=="sixfield_fit_model_route":
    row=f4.sixfield_episode(family,seed,subject)
   else:
    row=f4.r4_episode(family,seed,subject)
    row["method"]=method
   out.append(row)
 return out

def outcome(base,dev):
 r={fam:dict(base["results"][fam]) for fam in FAMILIES}
 for fam in FAMILIES:
  for method in ("wingless_r4_frontier","wingless_r5_cost_frontier",
                 "wingless_r6_observed_route","wingless_r7_physical_frontier",
                 "sixfield_fit_model_route"):
   rows=[row for row in dev if row["family"]==fam and row["method"]==method]
   if len(rows)!=8:raise ValueError("F6_MISSING_AUTHENTIC_DEV_METHOD")
   r[fam][method]=f2.scores(rows)
 gates=contract()["predicates"]
 criteria={}
 for fam in FAMILIES:
  x=r[fam]["wingless_r7_physical_frontier"]
  y=r[fam]["wingless_r5_cost_frontier"]
  upper=r[fam]["fit_dynamics_bfs"]
  criteria[fam+"_R7_goal_minimum"]=x["successes"]>=(
    gates["EmptyR7MinGoals"] if fam=="empty" else gates["FourRoomsR7MinGoals"])
  criteria[fam+"_full_grid_control_eligible"]=upper["successes"]>=gates["FullMapPlannerMinGoalsEach"]
  criteria[fam+"_blocked_forward_not_worse_than_R5"]=x["blocked_forward_per_100_steps"]<=y["blocked_forward_per_100_steps"]
  if fam=="fourrooms":
   same=r[fam]["sixfield_fit_model_route"]
   criteria["fourrooms_R7_goals_at_least_R5"]=x["successes"]>=y["successes"]+gates["FourRoomsR7NotWorseGoalsThanR5"]
   criteria["fourrooms_R7_goals_at_least_sixfield"]=x["successes"]>=same["successes"]+gates["FourRoomsR7NotWorseGoalsThanSixfield"]
   criteria["fourrooms_R7_reward_at_least_R5"]=x["mean_real_reward"]>=gates["FourRoomsR7MeanRewardAtLeastR5"]*y["mean_real_reward"]
   criteria["fourrooms_R7_reward_at_least_sixfield"]=x["mean_real_reward"]>=gates["FourRoomsR7MeanRewardAtLeastSixfield"]*same["mean_real_reward"]
   criteria["fourrooms_R7_reward_75pct_full_grid"]=x["mean_real_reward"]>=gates["FourRoomsR7RewardAtLeastFullMapPlanner"]*upper["mean_real_reward"]
   criteria["fourrooms_R7_actions_at_most_R5"]=x["actual_total_steps"]<=gates["FourRoomsR7ActionsAtMostR5"]*y["actual_total_steps"]
 return {"result":gates["accept"] if all(criteria.values()) else gates["fail"],
         "criteria":criteria,"results":r,"scientific_first_use":False,"scientific_accepted":False,
         "matched_sixfield_independent_control":True,"full_map_fitted_BFS_is_more_informed":True}

def experiment(r1,r2,r3,r4,r5,r6):
 frozen=contract()
 k4y.SEEDS={"FIT":FIT,"CHECK":CHECK,"DEV":DEV}
 stream,starts,audit,source_wall,control=k4y.fit()
 base={"schema":SCHEMA,"gate":"LCRM01-K4T-F5",
       "source_minigrid_commit":frozen["sources"]["minigrid"],
       "original_Wingless_R6_blob":frozen["sources"]["r6_blob"],
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "FIT_public_experience_count":len(stream),"FIT_original_public_experiences":stream,
       "FIT_episodes":len(starts),"FIT_original_balance":audit,
       "shared_FIT_source_wall_seconds":source_wall,
       "CHECK_episodes":0,"DEV_episodes":0,
       "old_K4Y_F1_F2_F3_F4_no_go_immutable":True,
       "scientific_first_use":False,"scientific_accepted":False}
 if control is None or len(stream)!=12000:
  base["result"]="FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED"
  return base
 sixfield,fit_sha=f4.sixfit(stream)
 base["trained_sixfield_FIT_sha256"]=fit_sha
 base["full_grid_FIT_sha256"]=sha(canon(control).encode())
 legacy,y1,y2,native=k4y.train(stream,r1,r2)
 w3=w4=w5=w6=None
 try:
  w3,i3=f2.train_r3(stream,r3)
  w4,i4=f4.train_r4(stream,r4)
  w5,i5=f4.train_r4(stream,r5)
  w6,i6=f4.train_r4(stream,r6)
  base5=i5.pop("native_CORE_snapshot_b64_before_holdout")
  base6=i6.pop("native_CORE_snapshot_b64_before_holdout")
  i4.pop("native_CORE_snapshot_b64_before_holdout")
  if base5!=base6:raise ValueError("F5_NOT_SAME_ORIGINAL_FIT_MODEL")
  i5={("R5"+k[2:] if k.startswith("R4") else k):v for k,v in i5.items()}
  i6={("R6"+k[2:] if k.startswith("R4") else k):v for k,v in i6.items()}
  base["native_FIT_custody"]={**native,**i3,**i4,**i5,**i6}
  def phase(name):
   seeds=CHECK if name=="CHECK" else DEV
   original=k4y.evaluation(name,legacy,y1,y2,control)
   r3rows=[f2.r3_episode(f,s,m,w3) for f in FAMILIES for s in seeds for m in f2.R3_METHODS]
   return (original+r3rows+evaluation(name,"wingless_r4_frontier",w4)+
           evaluation(name,"wingless_r5_cost_frontier",w5)+
           evaluation(name,"wingless_r6_observed_route",w6)+
           evaluation(name,"sixfield_fit_model_route",sixfield))
  check=phase("CHECK")
  dev=phase("DEV")
  if len(check)!=120 or len(dev)!=240:
   raise ValueError("F5_REAL_SOURCE_METHOD_PARITY_INCOMPLETE")
  if (w5.request("snapshot_base").get("state")!=base5 or
      w6.request("snapshot_base").get("state")!=base6):
   raise ValueError("F5_UNAUTHORIZED_NATIVE_FIT_UPDATE_IN_HELDOUT")
  report=k4y.report([x for x in dev if x["method"] in OLD])
  r3part=f2.judgment(report,[x for x in dev if x["method"] in f2.R3_METHODS])["results"]
  for fam in FAMILIES:
   for method in f2.R3_METHODS:report["results"][fam][method]=r3part[fam][method]
  base.update({"result":"COMPLETE_R6_GENUINE_PUBLIC_DEVELOPMENT",
       "CHECK_episodes":len(check),"DEV_episodes":len(dev),
       "CHECK_original_public_traces":check,"DEV_original_public_traces":dev,
       "r6_preregistered_disposition":outcome(report,dev)})
  return base
 finally:
  for w in (w3,w4,w5,w6):
   if w is not None:w.close()
  legacy["wingless_r1"].close()
  legacy["wingless_r2"].close()

def main():
 parser=argparse.ArgumentParser()
 for name in ("wingless_r1","wingless_r2","wingless_r3","wingless_r4","wingless_r5","wingless_r6","yggdrasil_source"):
  parser.add_argument("--"+name.replace("_","-"),type=Path,required=True)
 parser.add_argument("--output",type=Path,required=True)
 a=parser.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F5_NONFRESH_EVIDENCE")
 cpu=time.process_time()
 wall=time.perf_counter()
 child=resource.getrusage(resource.RUSAGE_CHILDREN)
 try:
  sys.path.insert(0,str(a.yggdrasil_source.resolve()))
  q=experiment(a.wingless_r1,a.wingless_r2,a.wingless_r3,a.wingless_r4,a.wingless_r5,a.wingless_r6)
 except Exception as e:
  q={"schema":SCHEMA,"gate":"LCRM01-K4T-F5",
     "result":"SOURCE_OR_INFRASTRUCTURE_BLOCKED","error":str(e),
     "error_type":type(e).__name__,"traceback_tail":traceback.format_exc().splitlines()[-18:],
     "scientific_first_use":False,"scientific_accepted":False}
 after=resource.getrusage(resource.RUSAGE_CHILDREN)
 q["resources"]={"Python_process_CPU_seconds":time.process_time()-cpu,
    "wall_seconds":time.perf_counter()-wall,
    "Python_peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
    "native_child_user_CPU_seconds":after.ru_utime-child.ru_utime,
    "native_child_system_CPU_seconds":after.ru_stime-child.ru_stime,
    "native_max_single_child_RSS_bytes":int(after.ru_maxrss)*1024,
    "max_child_RSS_is_not_total_process_peak":True,"energy_not_measured":True}
 a.output.write_text(json.dumps(q,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F6_ORIGINAL_SOURCE_RESULT="+q["result"])
 if "r6_preregistered_disposition" in q:
  d=q["r6_preregistered_disposition"]
  print("K4T_F6_R6_DECISION="+d["result"])
  print("K4T_F6_REAL_GOALS="+canon({f:{m:d["results"][f][m]["successes"]
       for m in ("wingless_r5_cost_frontier","wingless_r6_observed_route","sixfield_fit_model_route","fit_dynamics_bfs")}
       for f in FAMILIES}))
  print("K4T_F6_CRITERIA="+canon(d["criteria"]))
 print("K4T_F6_REAL_TRAINING_STEPS="+str(q.get("FIT_public_experience_count",0)))
 return int(q["result"]=="SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
