#!/usr/bin/env python3
"""F12: prospective public difficult-state memory versus equal-source competitors.

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

FROZEN=Path(__file__).with_name("k4t_f12_frozen_physical_return.json")
SCHEMA="mass.lcrm01.k4t-f12.true-physical-revisit-causal-map-v1"
FAMILY="fourrooms"
FIT=tuple(range(171400,171448))
DEV=tuple(range(181400,181416))
ACTIONS=(0,1,2)
CATEGORIES=("actual_physical_reentry","public_front_blocked","failed_actual_forward","novel_physical_edge")
MAX_SCAN=90
MEMORY=12
PSEUDO=16
RIDGE=10.

def canon(x):
 return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def sha(x):
 return hashlib.sha256(canon(x).encode()).hexdigest()
def contract():
 p=json.loads(FROZEN.read_text())
 if(p["schema"]!="mass.lcrm01.k4t-f12.physical-return-causal-map-frozen-v1"
   or p["parentF11Commit"]!="7364e2af3677b91956136cda675f39e4ffe2a290"
   or p["sources"]["originalMiniGridCommit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
   or p["worlds"]["FIT"]!=[171400,171447]
   or p["worlds"]["DEV"]!=[181400,181415]
   or p["worlds"]["sourceScanHorizon"]!=MAX_SCAN
   or p["publicExploration"]["categoryPriority"]!=list(CATEGORIES)
   or p["models"]["regularization"]!=RIDGE
   or p["models"]["actionPriorPseudoCount"]!=PSEUDO
   or p["models"]["newGraph"] is None
   or p["governance"]["protectedScientificFirstUse"] is not False
   or p["governance"]["scientificAccepted"] is not False):
  raise ValueError("F12_FROZEN_SOURCE_HYPOTHESIS_DRIFT")
 return p

def limited_history_features(row):
 past=row["witnessed_action_consequence_history"]
 if len(past)>MEMORY or type(past) is not list:
  raise ValueError("F12_TOO_MUCH_OR_INVALID_HISTORY")
 features=[]
 for e in [None]*(MEMORY-len(past))+past:
  if e is None:features.extend([0.,0.,0.,0.,0.,1.])
  else:
   action=e["action"];moved=e["physically_moved"];blocked=e["front_blocked_before"]
   if (action not in ACTIONS or type(moved) is not bool or
       type(blocked) is not bool or set(e)!={"action","physically_moved",
         "front_blocked_before","public_before","public_after"} or
       not f8.f7.valid(e["public_before"]) or not f8.f7.valid(e["public_after"])):
    raise ValueError("F12_PRIVILEGED_OR_UNOBSERVED_HISTORY")
   if moved!=((e["public_before"]["X"],e["public_before"]["Y"])!=
             (e["public_after"]["X"],e["public_after"]["Y"])):
    raise ValueError("F12_FALSE_PHYSICAL_ACTION_CONSEQUENCE")
   features.extend([float(action==a) for a in ACTIONS]+[float(moved),float(blocked),0.])
 summary=row["public_history_counts"]
 if set(summary)!={"unique_observed_cells","reentered_departed_cells",
                   "failed_forward_actions","ticks_since_last_physical_move"}:
  raise ValueError("F12_INVALID_SOURCE_HISTORY_SUMMARY")
 features.extend([min(summary["unique_observed_cells"],64)/64.,
    min(summary["reentered_departed_cells"],32)/32.,
    min(summary["failed_forward_actions"],64)/64.,
    min(summary["ticks_since_last_physical_move"],110)/110.])
 return features

def history_key(row,a):
 s=row["six_public_before"]
 if not f8.f7.valid(s):raise ValueError("F12_PRIVILEGED_CURRENT_OBSERVATION")
 h=tuple((e["action"],int(e["physically_moved"]),
          int(e["front_blocked_before"])) for e in row["witnessed_action_consequence_history"][-3:])
 return (a,s["Direction"],s["FrontBlocked"],
         f8.f7.clip(s["GoalX"]-s["X"]),
         f8.f7.clip(s["GoalY"]-s["Y"]),h)

def current_features(row,a):
 return f9.basis(FAMILY,row["six_public_before"],a)
def memory_features(row,a):
 return current_features(row,a)+limited_history_features(row)

def category(public,t,history,reentered_now,used_anchor_cells):
 if t<contract()["worlds"]["minimumSourceTick"]:return None
 if reentered_now:return "actual_physical_reentry"
 if public["FrontBlocked"]:return "public_front_blocked"
 if sum(1 for e in history[-2:] if e["action"]==2 and not e["physically_moved"])>=2:
  return "failed_actual_forward"
 if (public["X"],public["Y"]) not in used_anchor_cells:
  return "novel_physical_edge"
 return None

def scan_original_world(seed):
 env=src.make_env(FAMILY)
 anchors=[]
 try:
  obs,_=env.reset(seed=seed)
  st=src.public(obs)
  initial=st["grid_sha256"]
  history=[];prefix=[];departed=set();returns=set();known=set()
  seen={(st["x"],st["y"])};edge={}
  counts=dict.fromkeys(CATEGORIES,0)
  anchored_cells=set();queued=[];free_attempts=0
  last_move=0;failed=0;returned_now=False
  quota=contract()["publicExploration"]["perSeedCategoryQuota"]
  for tick in range(MAX_SCAN):
   state=f8.public_grid(st)
   if not f8.f7.valid(state):raise ValueError("F12_NONPUBLIC_SOURCE_STATE")
   which=category(state,tick,history,returned_now,anchored_cells)
   if(which is not None and counts[which]<quota[which]
       and len(anchors)<contract()["publicExploration"]["maxAnchorsPerSeed"]):
    local={k:list(v) for k,v in edge.items()
           if k.startswith(str(state["X"])+","+str(state["Y"])+",")}
    anchors.append({"family":FAMILY,"seed":seed,"tick":tick,
      "initial_sha256":initial,"anchor_sha256":st["grid_sha256"],
      "public":state,"prefix":list(prefix),
      "witnessed_action_consequence_history":list(history[-MEMORY:]),
      "local_forward_edge_counts":local,
      "public_history_counts":{"unique_observed_cells":len(seen),
       "reentered_departed_cells":len(returns),
       "failed_forward_actions":failed,"ticks_since_last_physical_move":tick-last_move},
      "prospective_difficulty_label":which})
    counts[which]+=1
    anchored_cells.add((state["X"],state["Y"]))
   if queued:
    action=queued.pop(0);start_probe=False;commit=False
   elif state["FrontBlocked"]:
    action=1;start_probe=False;commit=False
   else:
    action=2
    start_probe=(free_attempts%3)!=2
    commit=not start_probe
    free_attempts+=1
   b=state
   obs,reward,term,trunc,_=env.step(action)
   nxt=src.public(obs,st["goal"])
   n=f8.public_grid(nxt)
   moved=(b["X"],b["Y"])!=(n["X"],n["Y"])
   returned_now=False
   if moved:
    departed.add((b["X"],b["Y"]))
    if (n["X"],n["Y"]) in departed:
     returned_now=True
     returns.add((n["X"],n["Y"]))
    last_move=tick+1
   seen.add((n["X"],n["Y"]))
   if action==2:
    key=str(b["X"])+","+str(b["Y"])+","+str(b["Direction"])
    z=edge.setdefault(key,[0,0])
    z[0 if moved else 1]+=1
    if not moved:failed+=1
   history.append({"action":action,"physically_moved":moved,
     "front_blocked_before":b["FrontBlocked"],
     "public_before":b,"public_after":n})
   prefix.append({"t":tick,"action":action,"before_sha":st["grid_sha256"],
     "after_sha":nxt["grid_sha256"],"reward":float(reward),
     "terminated":bool(term),"truncated":bool(trunc)})
   if start_probe:
    # A real move establishes a reversible selected-action path. Turns
    # and the return are still physically executed and verified later.
    queued=[0,0,2,0,0,1] if moved else [1]
   elif commit:
    queued=[1]
   st=nxt
   if term or trunc:break
  return anchors,{"seed":seed,"anchors":len(anchors),
    "category_counts":counts,"actual_source_scan_steps":len(prefix),
    "physical_cells_observed":len(seen),"real_revisited_cells":len(returns)}
 finally:env.close()

def graph_features(row):
 s=row["six_public_before"]
 if not f8.f7.valid(s):raise ValueError("F12_PRIVILEGED_MAP_FEATURE")
 prefix=str(s["X"])+","+str(s["Y"])+","
 local=row["local_forward_edge_counts"]
 if not isinstance(local,dict) or any(not k.startswith(prefix) for k in local):
  raise ValueError("F12_GRAPH_NEIGHBOR_IS_UNOBSERVED")
 v=[]
 for direction in range(4):
  x=local.get(prefix+str(direction),[0,0])
  if(len(x)!=2 or any(type(n) is not int or n<0 for n in x)):
   raise ValueError("F12_GRAPH_IS_NOT_WITNESSED_ACTION")
  v.extend([min(x[0],8)/8.,min(x[1],8)/8.])
 c=row["public_history_counts"]
 if set(c)!={"unique_observed_cells","reentered_departed_cells",
            "failed_forward_actions","ticks_since_last_physical_move"}:
  raise ValueError("F12_PRIVATE_GRAPH_METADATA")
 v.extend([min(c["reentered_departed_cells"],16)/16.,
   min(c["unique_observed_cells"],64)/64.,
   min(c["failed_forward_actions"],64)/64.,
   min(c["ticks_since_last_physical_move"],90)/90.])
 return v

def graph_key(row,a):
 s=row["six_public_before"]
 local=graph_features(row)
 return history_key(row,a)+tuple(round(v,3) for v in local)

def map_features(row,a):
 return extended_features(row,a)+graph_features(row)

def paired_original_source_rows(seeds,phase):
 out=[];audits=[]
 for seed in seeds:
  selected,audit=scan_original_world(seed)
  audits.append(audit)
  for anchor in selected:
   order=sorted(ACTIONS,key=lambda a:hashlib.sha256(
     f"F11:{phase}:{seed}:{anchor['tick']}:{a}".encode()).hexdigest())
   real={str(a):f8.execute_real_arm(anchor,a) for a in order}
   if set(real)!={"0","1","2"}:raise ValueError("F12_NOT_THREE_ACTUAL_SOURCE_ARMS")
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
  nowX=[];histX=[];mapX=[];rewards=[]
  priors=defaultdict(lambda:[0.,0])
  empirical=defaultdict(lambda:[0.,0])
  for row in training:
   if set(row["true_source_three_arm_interventions"])!={"0","1","2"}:
    raise ValueError("F12_INCOMPLETE_REAL_THREE_ARM_FIT")
   for a in ACTIONS:
    trial=row["true_source_three_arm_interventions"][str(a)]
    if(trial["intervened_action"]!=a or
       not trial["actual_public_action_consequence_trace"] or
       trial["actual_public_action_consequence_trace"][0]["action"]!=a):
     raise ValueError("F12_IMPUTED_NOT_EXECUTED_ACTION")
    y=trial["discounted_true_source_return"]
    if not math.isfinite(y):raise ValueError("F12_NONFINITE_ORIGINAL_REWARD")
    pr=priors[a];pr[0]+=y;pr[1]+=1
    z=empirical[graph_key(row,a)];z[0]+=y;z[1]+=1
    nowX.append(current_features(row,a))
    histX.append(extended_features(row,a))
    mapX.append(map_features(row,a))
    rewards.append(y)
  if len(priors)!=3 or min(v[1] for v in priors.values())<100:
   raise ValueError("F12_UNDERTRAINED_EQUAL_ACTION_PRIOR")
  def fit(X):
   arr=np.asarray(X,dtype="float64")
   y=np.asarray(rewards,dtype="float64")
   reg=np.eye(arr.shape[1])*RIDGE
   reg[0,0]=0.
   return np.linalg.solve(arr.T@arr+reg,arr.T@y).tolist()
  self.current=fit(nowX);self.history=fit(histX);self.graph=fit(mapX)
  self.priors=dict(priors);self.empirical=dict(empirical)
  self.n=len(rewards)
  self.current_sha=sha(self.current)
  self.history_sha=sha(self.history)
  self.graph_sha=sha(self.graph)
 def score(self,row):
  ans=[]
  for a in ACTIONS:
   prior=self.priors[a][0]/self.priors[a][1]
   c=self.empirical.get(graph_key(row,a),(0.,0))
   emp=(c[0]+PSEUDO*prior)/(c[1]+PSEUDO)
   now=sum(w*x for w,x in zip(self.current,current_features(row,a)))
   hist=sum(w*x for w,x in zip(self.history,extended_features(row,a)))
   graph=sum(w*x for w,x in zip(self.graph,map_features(row,a)))
   ans.append({"action":a,"current_ridge":now,"history12_ridge":hist,
      "physical_graph_ridge":graph,"graph_empirical":emp,
      "source_action_prior":prior,"FIT_source_local_graph_count":c[1]})
  return ans

def choose(scores,name):
 return max(ACTIONS,key=lambda a:(scores[a][name],-a))

def evaluate():
 p=contract()
 train,audfit=paired_original_source_rows(FIT,"FIT")
 if not train:raise ValueError("F12_NO_REAL_FIT")
 models=FullyTrained(train)
 dev,auddev=paired_original_source_rows(DEV,"DEV")
 if not dev:raise ValueError("F12_NO_REAL_DEV")
 methods=("current_ridge","history12_ridge","physical_graph_ridge",
          "graph_empirical","source_action_prior")
 for row in dev:
  vals=models.score(row)
  row["all_identical_FIT_source_scoring"]=vals
  for method in methods:row[method]=choose(vals,method)
 def observed(r,m,key="discounted_true_source_return"):
  return r["true_source_three_arm_interventions"][str(r[m])][key]
 n=len(dev)
 outcomes={m:{"mean_real_discounted_return":sum(observed(r,m) for r in dev)/n,
    "real_source_goal_completions":sum(observed(r,m,"goal_success") for r in dev),
    "mean_actual_post_action_steps":sum(observed(r,m,"actual_steps_after_intervention") for r in dev)/n}
    for m in methods}
 def gain(rhs):
  return sum(observed(r,"physical_graph_ridge")-observed(r,rhs) for r in dev)/n
 diff=sum(r["physical_graph_ridge"]!=r["current_ridge"] for r in dev)
 cats={cat:sum(r["prospective_difficulty_label"]==cat for r in dev)
       for cat in CATEGORIES}
 c=p["acceptance"]
 criteria={"real_FIT_coverage":len(train)>=c["minFITTrueAnchorStates"],
   "real_prospective_DEV_coverage":n>=c["minDEVTrueAnchorStates"],
   "genuine_physical_return_coverage":cats["actual_physical_reentry"]>=c["minDEVActualReentries"],
   "front_blocked_coverage":cats["public_front_blocked"]>=c["minDEVFrontBlocked"],
   "different_public_action_choices":diff>=c["minMapVsCurrentDifferentActions"],
   "graph_better_than_current":gain("current_ridge")>=c["mapVsCurrentMeanActualDiscountedGain"],
   "graph_better_than_short_history":gain("history12_ridge")>=c["mapVsHistory12MeanActualDiscountedGain"],
   "graph_at_least_fully_FIT_graph_empirical":gain("graph_empirical")>=c["mapVsGraphEmpiricalMeanActualDiscountedGain"],
   "source_goal_nonregression":outcomes["physical_graph_ridge"]["real_source_goal_completions"]>=outcomes["current_ridge"]["real_source_goal_completions"]}
 verdict=c["positive"] if all(criteria.values()) else c["failure"]
 return {"schema":SCHEMA,"gate":"LCRM01-K4T-F12","result":verdict,
   "criteria":criteria,"fresh_DEV_category_counts":cats,
   "metrics":{"true_FIT_anchor_count":len(train),"true_DEV_anchor_count":n,
    "true_FIT_action_interventions":3*len(train),
    "true_DEV_action_interventions":3*n,
    "graph_vs_current_actual_choice_differences":diff,
    "graph_vs_current_mean_true_return_gain":gain("current_ridge"),
    "graph_vs_history_mean_true_return_gain":gain("history12_ridge"),
    "graph_vs_graph_empirical_mean_true_return_gain":gain("graph_empirical"),
    "genuine_real_source_results":outcomes},
   "FIT_true_original_source_matched_actions":train,
   "DEV_true_original_source_matched_actions":dev,
   "original_FIT_source_scanner_audit":audfit,
   "original_DEV_source_scanner_audit":auddev,
   "fitted_current_source_sha256":models.current_sha,
   "fitted_history_source_sha256":models.history_sha,
   "fitted_graph_source_sha256":models.graph_sha,
   "all_models_exact_same_actual_source_FIT_exposure":models.n,
   "original_MiniGrid_source_commit":p["sources"]["originalMiniGridCommit"],
   "frozen_protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
   "better_informed_common_BFS_follower":True,
   "native_R5_unchanged":True,"real_all_three_source_action_trials":True,
   "scientific_first_use":False,"scientific_accepted":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 a=parser.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("F12_EVIDENCE_MUST_BE_FRESH")
 start=time.perf_counter();cpu=time.process_time()
 try:result=evaluate()
 except Exception as e:
  result={"schema":SCHEMA,"gate":"LCRM01-K4T-F12",
    "result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
    "error_type":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-16:],
    "scientific_first_use":False,"scientific_accepted":False}
 result["resources"]={"python_cpu_seconds":time.process_time()-cpu,
   "whole_source_wall_seconds":time.perf_counter()-start,
   "python_peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
   "go_native_processes":0,"energy_measured":False}
 a.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F12_GENUINE_SOURCE_EXPERIMENT="+result["result"])
 if "metrics" in result:
  print("K4T_F12_REAL_SOURCE_METRICS="+canon(result["metrics"]))
  print("K4T_F12_FROZEN_CRITERIA="+canon(result["criteria"]))
 return int(result["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
