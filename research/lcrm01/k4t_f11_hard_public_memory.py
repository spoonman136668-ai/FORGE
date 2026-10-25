#!/usr/bin/env python3
"""F11: prospective public difficult-state memory versus equal-source competitors.

All three alternative actions are genuinely executed on independently reset,
source-pinned MiniGrid environments. Model inputs have strictly public origin;
the common post-intervention BFS teacher is a more-informed evaluation policy.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import resource
import time
import traceback

import numpy as np
import k4r_minigrid_source as src
import k4t_f8_paired_actions as f8
import k4t_f9_randomized_value as f9

FROZEN=Path(__file__).with_name("k4t_f11_frozen_hard_public.json")
SCHEMA="mass.lcrm01.k4t-f11.original-difficult-public-route-history-v1"
FAMILY="fourrooms"
FIT=tuple(range(151400,151448))
DEV=tuple(range(161400,161416))
ACTIONS=(0,1,2)
CATEGORIES=("front_blocked","physical_revisit","forward_stall","goal_misaligned")
MAX_SCAN=110
MEMORY=12
PSEUDO=16
RIDGE=10.

def canon(x):
 return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def sha(x):
 return hashlib.sha256(canon(x).encode()).hexdigest()
def contract():
 p=json.loads(FROZEN.read_text())
 if (p["schema"]!="mass.lcrm01.k4t-f11.public-hard-state-memory-v1"
   or p["parentF10"]!="5eba1c8f103eb32c72b937b074259fc5cc7fc1b4"
   or p["originalSources"]["miniGridCommit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
   or p["originalWorld"]["FIT"]!=[151400,151447]
   or p["originalWorld"]["DEV"]!=[161400,161415]
   or p["originalWorld"]["scanLimitPerWorld"]!=MAX_SCAN
   or p["originalWorld"]["publicCategoriesInPriorityOrder"]!=list(CATEGORIES)
   or p["models"]["historyWindow"]!=MEMORY
   or p["models"]["regularizationPenalty"]!=RIDGE
   or p["models"]["historyEmpiricalPseudoCount"]!=PSEUDO
   or p["constraints"]["holdoutProtectedFirstUse"] is not False
   or p["constraints"]["scientificAccepted"] is not False):
  raise ValueError("F11_FROZEN_ORIGINAL_SOURCE_DRIFT")
 return p

def choose_exploration(t):
 mod=t%7
 return 1 if mod in (0,4) else (0 if mod in (2,5) else 2)

def category(public,t,history,departed):
 if t<contract()["originalWorld"]["minimumTick"]:
  return None
 if public["FrontBlocked"]:return "front_blocked"
 pos=(public["X"],public["Y"])
 if pos in departed:return "physical_revisit"
 recent=history[-8:]
 if sum(1 for e in recent if e["action"]==2 and not e["physically_moved"])>=2:
  return "forward_stall"
 direction=public["Direction"]
 dx,dy=src.EXPERT_MOVES[direction]
 gx=public["GoalX"]-public["X"];gy=public["GoalY"]-public["Y"]
 if gx*dx+gy*dy<=0:return "goal_misaligned"
 return None

def limited_history_features(row):
 past=row["witnessed_action_consequence_history"]
 if len(past)>MEMORY or type(past) is not list:
  raise ValueError("F11_TOO_MUCH_OR_INVALID_HISTORY")
 features=[]
 for e in [None]*(MEMORY-len(past))+past:
  if e is None:features.extend([0.,0.,0.,0.,0.,1.])
  else:
   action=e["action"];moved=e["physically_moved"];blocked=e["front_blocked_before"]
   if (action not in ACTIONS or type(moved) is not bool or
       type(blocked) is not bool or set(e)!={"action","physically_moved",
         "front_blocked_before","public_before","public_after"} or
       not f8.f7.valid(e["public_before"]) or not f8.f7.valid(e["public_after"])):
    raise ValueError("F11_PRIVILEGED_OR_UNOBSERVED_HISTORY")
   if moved!=((e["public_before"]["X"],e["public_before"]["Y"])!=
             (e["public_after"]["X"],e["public_after"]["Y"])):
    raise ValueError("F11_FALSE_PHYSICAL_ACTION_CONSEQUENCE")
   features.extend([float(action==a) for a in ACTIONS]+[float(moved),float(blocked),0.])
 summary=row["public_history_counts"]
 if set(summary)!={"unique_observed_cells","reentered_departed_cells",
                   "failed_forward_actions","ticks_since_last_physical_move"}:
  raise ValueError("F11_INVALID_SOURCE_HISTORY_SUMMARY")
 features.extend([min(summary["unique_observed_cells"],64)/64.,
    min(summary["reentered_departed_cells"],32)/32.,
    min(summary["failed_forward_actions"],64)/64.,
    min(summary["ticks_since_last_physical_move"],110)/110.])
 return features

def history_key(row,a):
 s=row["six_public_before"]
 if not f8.f7.valid(s):raise ValueError("F11_PRIVILEGED_CURRENT_OBSERVATION")
 h=tuple((e["action"],int(e["physically_moved"]),
          int(e["front_blocked_before"])) for e in row["witnessed_action_consequence_history"][-3:])
 return (a,s["Direction"],s["FrontBlocked"],
         f8.f7.clip(s["GoalX"]-s["X"]),
         f8.f7.clip(s["GoalY"]-s["Y"]),h)

def current_features(row,a):
 return f9.basis(FAMILY,row["six_public_before"],a)
def memory_features(row,a):
 return current_features(row,a)+limited_history_features(row)

def scan_original_world(seed):
 env=src.make_env(FAMILY)
 anchors=[]
 try:
  obs,_=env.reset(seed=seed)
  st=src.public(obs)
  initial=st["grid_sha256"];prefix=[];history=[]
  counters=dict.fromkeys(CATEGORIES,0)
  quota=contract()["originalWorld"]["maxPerSeedPerCategory"]
  observed={(st["x"],st["y"])}
  departed=set();returned=set()
  last_move_tick=0;failed_forward=0
  for tick in range(MAX_SCAN):
   s=f8.public_grid(st)
   if not f8.f7.valid(s):raise ValueError("F11_PUBLIC_SOURCE_FIELDS")
   cat=category(s,tick,history,departed)
   if(cat is not None and counters[cat]<quota[cat]
       and len(anchors)<contract()["originalWorld"]["maxTotalAnchorsPerSeed"]):
    row={"family":FAMILY,"seed":seed,"tick":tick,
      "initial_sha256":initial,"anchor_sha256":st["grid_sha256"],
      "public":s,"prefix":list(prefix),
      "witnessed_action_consequence_history":list(history[-MEMORY:]),
      "public_history_counts":{
       "unique_observed_cells":len(observed),
       "reentered_departed_cells":len(returned),
       "failed_forward_actions":failed_forward,
       "ticks_since_last_physical_move":tick-last_move_tick},
      "prospective_difficulty_label":cat}
    anchors.append(row);counters[cat]+=1
   action=choose_exploration(tick)
   b=s
   obs,reward,term,trunc,_=env.step(action)
   nxt=src.public(obs,st["goal"])
   n=f8.public_grid(nxt)
   moved=(n["X"],n["Y"])!=(b["X"],b["Y"])
   if moved:
    departed.add((b["X"],b["Y"]))
    if (n["X"],n["Y"]) in departed:returned.add((n["X"],n["Y"]))
    last_move_tick=tick+1
   observed.add((n["X"],n["Y"]))
   if action==2 and not moved:failed_forward+=1
   history.append({"action":action,"physically_moved":moved,
      "front_blocked_before":b["FrontBlocked"],
      "public_before":b,"public_after":n})
   prefix.append({"t":tick,"action":action,
     "before_sha":st["grid_sha256"],"after_sha":nxt["grid_sha256"],
     "reward":float(reward),"terminated":bool(term),"truncated":bool(trunc)})
   st=nxt
   if term or trunc:break
  return anchors,{"seed":seed,"anchors":len(anchors),
     "category_counts":counters,"actual_source_scan_steps":len(prefix),
     "physical_cells_observed":len(observed),"real_revisited_cells":len(returned)}
 finally:
  env.close()

def paired_original_source_rows(seeds,phase):
 out=[];audits=[]
 for seed in seeds:
  selected,audit=scan_original_world(seed)
  audits.append(audit)
  for anchor in selected:
   order=sorted(ACTIONS,key=lambda a:hashlib.sha256(
     f"F11:{phase}:{seed}:{anchor['tick']}:{a}".encode()).hexdigest())
   real={str(a):f8.execute_real_arm(anchor,a) for a in order}
   if set(real)!={"0","1","2"}:raise ValueError("F11_NOT_THREE_ACTUAL_SOURCE_ARMS")
   row={k:v for k,v in anchor.items() if k not in ("public","tick","anchor_sha256","initial_sha256","prefix")}
   row.update({"anchor_tick":anchor["tick"],"six_public_before":anchor["public"],
    "matched_anchor_public_sha256":anchor["anchor_sha256"],
    "initial_public_sha256":anchor["initial_sha256"],
    "actual_selected_action_prefix":anchor["prefix"],
    "randomized_arm_execution_order":order,
    "true_source_three_arm_interventions":real})
   out.append(row)
 return out,audits

class FullyTrained:
 def __init__(self,training):
  actions=defaultdict(lambda:[0.,0])
  empirical=defaultdict(lambda:[0.,0])
  current=[];memory=[];returns=[]
  for r in training:
   if not f8.f7.valid(r["six_public_before"]):
    raise ValueError("F11_TRAINING_INPUT_IS_NOT_PUBLIC")
   if set(r["true_source_three_arm_interventions"])!={"0","1","2"}:
    raise ValueError("F11_INCOMPLETE_TRAINING_COUNTERFACTUAL")
   for a in ACTIONS:
    trial=r["true_source_three_arm_interventions"][str(a)]
    if(trial["intervened_action"]!=a or
       trial["actual_public_action_consequence_trace"][0]["action"]!=a):
     raise ValueError("F11_UNPERFORMED_ACTION_USED_TO_FIT")
    y=trial["discounted_true_source_return"]
    if not math.isfinite(y):raise ValueError("F11_NONFINITE_SOURCE_RETURN")
    z=actions[a];z[0]+=y;z[1]+=1
    e=empirical[history_key(r,a)];e[0]+=y;e[1]+=1
    current.append(current_features(r,a))
    memory.append(memory_features(r,a))
    returns.append(y)
  if len(actions)!=3 or min(v[1] for v in actions.values())<100:
   raise ValueError("F11_CONVENTIONAL_NOT_TRAINED")
  self.action=dict(actions);self.empirical=dict(empirical)
  def fit(X):
   arr=np.asarray(X,dtype="float64")
   y=np.asarray(returns,dtype="float64")
   reg=np.eye(arr.shape[1],dtype="float64")*RIDGE
   reg[0,0]=0.
   return np.linalg.solve(arr.T@arr+reg,arr.T@y).tolist()
  self.current=fit(current);self.memory=fit(memory)
  self.n=len(returns)
  self.current_sha=sha(self.current);self.memory_sha=sha(self.memory)
 def score(self,row):
  ans=[]
  for a in ACTIONS:
   prior=self.action[a]
   mean=prior[0]/prior[1]
   c=self.empirical.get(history_key(row,a),(0.,0))
   empirical=(c[0]+PSEUDO*mean)/(c[1]+PSEUDO)
   curr=sum(w*x for w,x in zip(self.current,current_features(row,a)))
   mem=sum(w*x for w,x in zip(self.memory,memory_features(row,a)))
   ans.append({"action":a,"current_ridge":curr,"memory_ridge":mem,
     "history_empirical":empirical,"action_prior":mean,
     "historical_context_fit_events":c[1]})
  return ans

def choose(scores,name):
 return max(ACTIONS,key=lambda a:(scores[a][name],-a))

def evaluate():
 p=contract()
 train,train_audit=paired_original_source_rows(FIT,"FIT")
 model=FullyTrained(train)
 dev,dev_audit=paired_original_source_rows(DEV,"DEV")
 if not dev:raise ValueError("F11_NO_UNSEEN_REAL_PUBLIC_DECISIONS")
 for row in dev:
  scores=model.score(row)
  row["fully_FIT_trained_public_scores"]=scores
  for method in ("current_ridge","memory_ridge","history_empirical","action_prior"):
   row[method]=choose(scores,method)
 def measured(row,name,key="discounted_true_source_return"):
  return row["true_source_three_arm_interventions"][str(row[name])][key]
 n=len(dev)
 diff=sum(r["current_ridge"]!=r["memory_ridge"] for r in dev)
 gain_cur=sum(measured(r,"memory_ridge")-measured(r,"current_ridge") for r in dev)/n
 gain_emp=sum(measured(r,"memory_ridge")-measured(r,"history_empirical") for r in dev)/n
 methods=("current_ridge","memory_ridge","history_empirical","action_prior")
 results={m:{"mean_actual_discounted_source_reward":
          sum(measured(r,m) for r in dev)/n,
        "real_goal_completions":sum(measured(r,m,"goal_success") for r in dev),
        "mean_true_source_action_steps":
          sum(measured(r,m,"actual_steps_after_intervention") for r in dev)/n}
          for m in methods}
 label_counts={cat:sum(r["prospective_difficulty_label"]==cat for r in dev)
               for cat in CATEGORIES}
 g=p["decisionGates"]
 criteria={"fit_minimum":len(train)>=g["minimumTrueFITAnchors"],
   "prospective_minimum":n>=g["minimumTrueDEVAnchors"],
   "blocked_source_minimum":label_counts["front_blocked"]>=g["minimumBlockedDEVAnchors"],
   "physical_revisits_minimum":label_counts["physical_revisit"]>=g["minimumRevisitDEVAnchors"],
   "independent_decision_disagreement":diff>=g["minimumHistoryVCurrentDifferences"],
   "real_source_return_gain_over_current":gain_cur>=g["minimumMeanTrueReturnGainOverCurrent"],
   "same_history_empirical_control_not_better":gain_emp>=g["minimumMeanTrueReturnGainOverHistoryEmpirical"],
   "real_goal_nonregression":results["memory_ridge"]["real_goal_completions"]>=
                             results["current_ridge"]["real_goal_completions"]}
 verdict=g["positive"] if all(criteria.values()) else g["noGo"]
 return {"schema":SCHEMA,"gate":"LCRM01-K4T-F11","result":verdict,
   "criteria":criteria,"evaluation_difficulty_counts":label_counts,
   "metrics":{"FIT_actual_anchor_states":len(train),
     "DEV_actual_anchor_states":n,
     "FIT_real_source_action_branches":3*len(train),
     "DEV_real_source_action_branches":3*n,
     "history_vs_current_action_disagreements":diff,
     "mean_true_return_gain_history_vs_current":gain_cur,
     "mean_true_return_gain_history_vs_history_empirical":gain_emp,
     "original_source_results":results},
   "true_FIT_paired_action_training":train,
   "true_fresh_DEV_paired_action_evaluation":dev,
   "source_scan_FIT_audit":train_audit,
   "source_scan_DEV_audit":dev_audit,
   "fully_trained_current_model_sha256":model.current_sha,
   "fully_trained_public_memory_model_sha256":model.memory_sha,
   "equal_FIT_action_exposures_for_all_models":model.n,
   "original_Farama_commit":p["originalSources"]["miniGridCommit"],
   "frozen_protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
   "uses_more_informed_BFS_continuation":True,
   "native_R5_source_unchanged":True,"all_counterfactual_branches_actually_executed":True,
   "scientific_first_use":False,"scientific_accepted":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 a=parser.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("F11_EVIDENCE_MUST_BE_FRESH")
 start=time.perf_counter();cpu=time.process_time()
 try:result=evaluate()
 except Exception as e:
  result={"schema":SCHEMA,"gate":"LCRM01-K4T-F11",
    "result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
    "error_type":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-16:],
    "scientific_first_use":False,"scientific_accepted":False}
 result["resources"]={"python_cpu_seconds":time.process_time()-cpu,
   "whole_source_wall_seconds":time.perf_counter()-start,
   "python_peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
   "go_native_processes":0,"energy_measured":False}
 a.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F11_GENUINE_SOURCE_EXPERIMENT="+result["result"])
 if "metrics" in result:
  print("K4T_F11_REAL_SOURCE_METRICS="+canon(result["metrics"]))
  print("K4T_F11_FROZEN_CRITERIA="+canon(result["criteria"]))
 return int(result["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
