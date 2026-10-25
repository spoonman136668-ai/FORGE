#!/usr/bin/env python3
"""F10: public action-consequence history sufficiency, genuine paired MiniGrid.

Data are actual source actions and physical consequences. Current-only and
history-aware controls train on exactly the same genuine three-arm outcomes.
The common future controller is a more-informed public BFS, never native R5.
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
import k4t_f8_paired_actions as f8
import k4t_f9_randomized_value as f9
import k4r_minigrid_source as src

FROZEN=Path(__file__).with_name("k4t_f10_frozen_history.json")
SCHEMA="mass.lcrm01.k4t-f10.genuine-paired-public-history-v1"
FAMILY="fourrooms"
FIT=tuple(range(131400,131436))
DEV=tuple(range(141400,141412))
ANCHORS=(4,8,12,16,20,24,28,32)
ACTIONS=(0,1,2)
HISTORY=3
ALPHA=16
RIDGE=10.

def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def frozen():
 p=json.loads(FROZEN.read_text())
 if(p["schema"]!="mass.lcrm01.k4t-f10.frozen-public-history-information-sufficiency-v1"
    or p["parentF9"]!="04ba6098b609c9417b982267cedd826a1ecd6349"
    or p["source"]["minigridCommit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
    or p["development"]["trainingSeeds"]!=[131400,131435]
    or p["development"]["evaluationSeeds"]!=[141400,141411]
    or p["development"]["teacherAnchorTicks"]!=list(ANCHORS)
    or p["development"]["historyLength"]!=HISTORY
    or p["comparison"]["linearRidgePenalty"]!=RIDGE
    or p["comparison"]["historyContextPriorPseudoCount"]!=ALPHA
    or p["governance"]["protectedFirstUse"] is not False):
  raise ValueError("F10_FROZEN_SOURCE_OR_EVALUATION_DRIFT")
 return p

def witnessed_history(anchor):
 """Re-execute the original source prefix and expose only selected public IO."""
 env=src.make_env(FAMILY)
 try:
  obs,_=env.reset(seed=anchor["seed"])
  st=src.public(obs)
  if st["grid_sha256"]!=anchor["initial_sha256"]:
   raise ValueError("F10_PREFIX_INITIAL_GRID_IDENTITY")
  events=[]
  for previous in anchor["prefix"]:
   if st["grid_sha256"]!=previous["before_sha"]:
    raise ValueError("F10_SOURCE_PREFIX_BEFORE_SHA")
   before=f8.public_grid(st)
   action=previous["action"]
   obs,reward,term,trunc,_=env.step(action)
   nxt=src.public(obs,st["goal"])
   after=f8.public_grid(nxt)
   if(nxt["grid_sha256"]!=previous["after_sha"]
      or reward!=previous["reward"]
      or bool(term)!=previous["terminated"]
      or bool(trunc)!=previous["truncated"]
      or (term or trunc)):
    raise ValueError("F10_SOURCE_PREFIX_AFTER_SHA")
   events.append({"action":action,
     "physically_moved":(before["X"],before["Y"])!=(after["X"],after["Y"]),
     "previous_front_blocked":before["FrontBlocked"],
     "before_public":before,"after_public":after,
     "before_sha256":st["grid_sha256"],"after_sha256":nxt["grid_sha256"]})
   st=nxt
  if st["grid_sha256"]!=anchor["anchor_sha256"] or f8.public_grid(st)!=anchor["public"]:
   raise ValueError("F10_PUBLIC_ANCHOR_IDENTITY_CHANGED")
  return events[-HISTORY:]
 finally:env.close()

def hvec(hist):
 if len(hist)>HISTORY or not isinstance(hist,list):
  raise ValueError("F10_IMPOSSIBLE_PUBLIC_HISTORY")
 v=[]
 padding=HISTORY-len(hist)
 for event in ([None]*padding+hist):
  if event is None:v.extend([0.,0.,0.,0.,0.,1.])
  else:
   a=event["action"]
   if a not in ACTIONS or type(event["physically_moved"]) is not bool or type(event["previous_front_blocked"]) is not bool:
    raise ValueError("F10_HISTORY_NOT_OBSERVED_ACTION_CONSEQUENCE")
   v.extend([float(a==i) for i in ACTIONS]+[float(event["physically_moved"]),
                float(event["previous_front_blocked"]),0.])
 return v

def history_key(row,action):
 state=row["six_public_before"]
 if not f8.f7.valid(state):raise ValueError("F10_PRIVILEGED_STATE")
 c=(state["Direction"],state["FrontBlocked"],
     f8.f7.clip(state["GoalX"]-state["X"]),
     f8.f7.clip(state["GoalY"]-state["Y"]),action)
 h=tuple((e["action"],int(e["physically_moved"]),int(e["previous_front_blocked"])) for e in row["recent_public_history"])
 return c+h

def current_features(row,action):
 return f9.basis(FAMILY,row["six_public_before"],action)

def extended_features(row,action):
 return current_features(row,action)+hvec(row["recent_public_history"])

def paired_anchors(seeds,phase):
 records=[]
 for seed in seeds:
  for tick in ANCHORS:
   anchor=f8.original_prefix(FAMILY,seed,tick)
   if anchor is None:continue
   history=witnessed_history(anchor)
   if len(history)!=min(HISTORY,tick):
    raise ValueError("F10_MISSING_ACTUALLY_OBSERVED_PREFIX")
   # Original-world trials, not model-generated synthetic next states.
   order=sorted(ACTIONS,key=lambda a:hashlib.sha256(
       f"F10:{phase}:{seed}:{tick}:{a}".encode()).hexdigest())
   real={str(a):f8.execute_real_arm(anchor,a) for a in order}
   if set(real)!={"0","1","2"}:raise ValueError("F10_NOT_ALL_GENUINE_ACTION_TRIALS")
   records.append({"family":FAMILY,"seed":seed,"anchor_tick":tick,
     "initial_public_sha256":anchor["initial_sha256"],
     "matched_anchor_public_sha256":anchor["anchor_sha256"],
     "six_public_before":anchor["public"],
     "recent_public_history":history,
     "original_public_prefix":anchor["prefix"],
     "randomized_action_execution_order":order,
     "true_original_interventions":real})
 return records

class Models:
 def __init__(self,training):
  currentX=[];historyX=[];rewards=[]
  actionPrior=defaultdict(lambda:[0.,0])
  context=defaultdict(lambda:[0.,0])
  for row in training:
   for a in ACTIONS:
    observed=row["true_original_interventions"][str(a)]
    if observed["intervened_action"]!=a or observed["actual_public_action_consequence_trace"][0]["action"]!=a:
     raise ValueError("F10_IMPUTED_ACTION_LABEL")
    y=observed["discounted_true_source_return"]
    if not math.isfinite(y):raise ValueError("F10_NONFINITE_REAL_SOURCE_RETURN")
    currentX.append(current_features(row,a))
    historyX.append(extended_features(row,a))
    rewards.append(y)
    prior=actionPrior[a];prior[0]+=y;prior[1]+=1
    c=context[history_key(row,a)];c[0]+=y;c[1]+=1
  if len(actionPrior)!=3 or min(s[1] for s in actionPrior.values())<100:
   raise ValueError("F10_INADEQUATELY_TRAINED_CONVENTIONAL")
  def fit(X):
   X=np.asarray(X,dtype="float64")
   y=np.asarray(rewards,dtype="float64")
   regularizer=np.eye(X.shape[1])*RIDGE
   regularizer[0,0]=0
   return np.linalg.solve(X.T@X+regularizer,X.T@y).tolist()
  self.now=fit(currentX)
  self.history=fit(historyX)
  self.prior=dict(actionPrior)
  self.context=dict(context)
  self.n=len(rewards)
  self.sha_current=digest(self.now)
  self.sha_history=digest(self.history)
 def scores(self,row):
  items=[]
  for a in ACTIONS:
   prior=self.prior[a]
   base=prior[0]/prior[1]
   ctx=self.context.get(history_key(row,a),(0.,0))
   hist=(ctx[0]+ALPHA*base)/(ctx[1]+ALPHA)
   now=sum(w*x for w,x in zip(self.now,current_features(row,a)))
   enriched=sum(w*x for w,x in zip(self.history,extended_features(row,a)))
   items.append({"action":a,"current_public_ridge":now,
      "history_public_ridge":enriched,"public_action_return_prior":base,
      "history_context_empirical":hist,"history_context_FIT_count":ctx[1]})
  return items

def argmax(scores,name):
 return max(ACTIONS,key=lambda a:(scores[a][name],-a))

def evaluate():
 p=frozen()
 training=paired_anchors(FIT,"FIT")
 if not training:raise ValueError("F10_NO_TRUE_FIT_INTERVENTIONS")
 model=Models(training)
 evaluation=paired_anchors(DEV,"DEV")
 summary={}
 for row in evaluation:
  scores=model.scores(row)
  row["FIT_only_model_scores"]=scores
  for name in ("current_public_ridge","history_public_ridge",
               "public_action_return_prior","history_context_empirical"):
   row[name]=argmax(scores,name)
 if not evaluation:raise ValueError("F10_NO_REAL_PROSPECTIVE_INTERVENTIONS")
 def actual(row,modelname,field="discounted_true_source_return"):
  return row["true_original_interventions"][str(row[modelname])][field]
 n=len(evaluation)
 delta_current=sum(actual(r,"history_public_ridge")-actual(r,"current_public_ridge") for r in evaluation)/n
 delta_empirical=sum(actual(r,"history_public_ridge")-actual(r,"history_context_empirical") for r in evaluation)/n
 different=sum(r["history_public_ridge"]!=r["current_public_ridge"] for r in evaluation)
 goals={name:sum(actual(r,name,"goal_success") for r in evaluation)
        for name in ("current_public_ridge","history_public_ridge",
                     "public_action_return_prior","history_context_empirical")}
 results={name:{"actual_goal_successes":goals[name],
    "mean_true_discounted_reward":sum(actual(r,name) for r in evaluation)/n,
    "mean_true_actions":sum(actual(r,name,"actual_steps_after_intervention") for r in evaluation)/n}
    for name in goals}
 metrics={"real_train_anchors":len(training),"real_dev_anchors":n,
  "three_arm_real_train_interventions":3*len(training),
  "three_arm_real_dev_interventions":3*n,
  "history_ridge_vs_current_ridge_choice_disagreements":different,
  "mean_actual_return_gain_history_vs_current":delta_current,
  "mean_actual_return_gain_history_vs_history_empirical":delta_empirical,
  "per_method_real_source_results":results}
 c=p["acceptance"]
 criteria={
  "minimum_actual_FIT_anchors":len(training)>=c["minimumFITAnchorStates"],
  "minimum_actual_DEV_anchors":n>=c["minimumDEVAnchorStates"],
  "minimum_history_vs_current_choice_disagreements":different>=c["minimumHistoryVCurrentActionDisagreements"],
  "minimum_actual_history_value_gain_vs_current":delta_current>=c["minimumHistoryRidgeActualReturnGainVsCurrentRidge"],
  "equal_information_history_empirical_not_stronger":delta_empirical>=c["minimumHistoryRidgeActualReturnGainVsHistoryEmpirical"],
  "actual_original_goal_nonregression":goals["history_public_ridge"]>=goals["current_public_ridge"]}
 verdict=c["positive"] if all(criteria.values()) else c["noGo"]
 return {"schema":SCHEMA,"gate":"LCRM01-K4T-F10","result":verdict,
  "criteria":criteria,"metrics":metrics,"true_randomized_FIT_episodes":training,
  "true_randomized_fresh_DEV_episodes":evaluation,
  "fitted_current_linear_SHA256":model.sha_current,
  "fitted_history_linear_SHA256":model.sha_history,
  "all_models_same_true_three_arm_source_FIT_count":model.n,
  "original_source_commit":p["source"]["minigridCommit"],
  "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
  "native_R5_untouched":True,"more_informed_original_BFS_continuation":True,
  "true_alternative_actions_actually_executed":True,
  "scientific_first_use":False,"scientific_accepted":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 args=parser.parse_args()
 if args.output.exists() or not args.output.parent.is_dir():raise ValueError("F10_NONFRESH_EVIDENCE_PATH")
 start=time.perf_counter();cpu=time.process_time()
 try:result=evaluate()
 except Exception as e:
  result={"schema":SCHEMA,"gate":"LCRM01-K4T-F10",
    "result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
    "error":str(e),"error_type":type(e).__name__,
    "traceback_tail":traceback.format_exc().splitlines()[-16:],
    "scientific_first_use":False,"scientific_accepted":False}
 result["resources"]={"Python_cpu_seconds":time.process_time()-cpu,
   "wall_seconds":time.perf_counter()-start,
   "peak_single_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
   "Go_subprocesses":0,"energy_measured":False}
 args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F10_SOURCE_HISTORY_RESULT="+result["result"])
 if "metrics" in result:
  print("K4T_F10_REAL_INTERVENTION_METRICS="+canon(result["metrics"]))
  print("K4T_F10_FROZEN_ACCEPTANCE_GATES="+canon(result["criteria"]))
 return int(result["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
