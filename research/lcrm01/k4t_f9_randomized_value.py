#!/usr/bin/env python3
"""F9 fully executed randomized-action intervention training, prospective evaluation.

Every observed action-return label comes from an actual, separately restarted
original MiniGrid environment. All three actions are executed at every anchor.
Only public six-field observations are supplied to trained estimators.
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

import k4t_f8_paired_actions as f8

FROZEN=Path(__file__).with_name("k4t_f9_frozen_randomized_value.json")
SCHEMA="mass.lcrm01.k4t-f9.prospective-causal-three-arm-value-v1"
FIT=tuple(range(111400,111424))
DEV=tuple(range(121400,121412))
FAMILIES=("empty","fourrooms")
ANCHORS=(0,1,2,3)
ACTIONS=(0,1,2)
ALPHA=16
RIDGE=10.

def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def frozen():
 p=json.loads(FROZEN.read_text())
 if(p["schema"]!="mass.lcrm01.k4t-f9.randomized-true-action-value-v1"
    or p["parentF8Head"]!="1ca269d19f81c295f196068c5d354dd5991c1a8e"
    or p["source"]["originalMiniGridCommit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
    or p["source"]["F8PairedEngineBlob"]!="31302c29f3dab743e85b94666683d604092bce2c"
    or p["design"]["trainingSeeds"]!=[111400,111423]
    or p["design"]["neverSeenEvaluationSeeds"]!=[121400,121411]
    or p["design"]["precommittedAnchors"]!=list(ANCHORS)
    or p["models"]["causalValueTable"]["shrinkagePriorCount"]!=ALPHA
    or p["models"]["fullyTrainedConventionalLinearRidge"]["ridgePenalty"]!=RIDGE
    or p["governance"]["protectedFirstUse"] is not False
    or p["governance"]["scientificAccepted"] is not False):
  raise ValueError("F9_FROZEN_RANDOMIZED_CAUSAL_PROTOCOL_DRIFT")
 return p

def context(family,s,action):
 if not f8.f7.valid(s) or action not in ACTIONS:
  raise ValueError("F9_HIDDEN_GRID_OR_ILLEGAL_ACTION")
 clip=f8.f7.clip
 return (family,action,s["Direction"],s["FrontBlocked"],
         clip(s["GoalX"]-s["X"]),clip(s["GoalY"]-s["Y"]))

def basis(family,s,action):
 if not f8.f7.valid(s):raise ValueError("F9_NONPUBLIC_FEATURE")
 dx=f8.f7.clip(s["GoalX"]-s["X"])/2.
 dy=f8.f7.clip(s["GoalY"]-s["Y"])/2.
 a=[float(action==i) for i in ACTIONS]
 v=[1.,float(family=="fourrooms"),*a,
     *(float(s["Direction"]==d) for d in range(4)),
     float(s["FrontBlocked"]),dx,dy]
 for i in ACTIONS:v.extend([a[i]*dx,a[i]*dy])
 v.extend([float(family=="fourrooms")*x for x in a])
 if len(v)!=21:raise ValueError("F9_FROZEN_LINEAR_FEATURE_SIZE")
 return v

class IndependentlyFittedEstimators:
 def __init__(self,training):
  import numpy as np
  value=defaultdict(lambda:[0.,0])
  prior=defaultdict(lambda:[0.,0])
  features=[];rewards=[]
  for record in training:
   family=record["family"];s=record["six_public_before"]
   if set(record["original_source_real_arms"])!={"0","1","2"}:
    raise ValueError("F9_UNMATCHED_REAL_RANDOMIZED_TRAINING")
   for action in ACTIONS:
    z=record["original_source_real_arms"][str(action)]
    if z["intervened_action"]!=action or z["actual_public_action_consequence_trace"][0]["action"]!=action:
     raise ValueError("F9_COUNTERFACTUAL_TRAINING_LABEL")
    reward=z["discounted_true_source_return"]
    if not math.isfinite(reward):raise ValueError("F9_NONFINITE_REAL_REWARD")
    v=value[context(family,s,action)];v[0]+=reward;v[1]+=1
    base=prior[(family,action)];base[0]+=reward;base[1]+=1
    features.append(basis(family,s,action));rewards.append(reward)
  if len(prior)!=6 or any(n[1]<50 for n in prior.values()):
   raise ValueError("F9_NOT_FULLY_TRAINED_CONVENTIONAL_FIT")
  self.value=dict(value);self.prior=dict(prior)
  X=np.asarray(features,dtype="float64")
  y=np.asarray(rewards,dtype="float64")
  regularizer=np.eye(X.shape[1],dtype="float64")*RIDGE
  regularizer[0,0]=0.
  self.linear=np.linalg.solve(X.T@X+regularizer,X.T@y).tolist()
  self.train_actions=len(rewards)
  self.linear_sha256=digest(self.linear)
  self.table_sha256=digest(sorted((list(k),v) for k,v in self.value.items()))
 def scored(self,family,s):
  if not f8.f7.valid(s):raise ValueError("F9_PUBLIC_INPUT_ONLY")
  result=[]
  for a in ACTIONS:
   prior=self.prior[(family,a)]
   if not prior[1]:raise ValueError("F9_UNTRAINED_ACTION")
   b=prior[0]/prior[1]
   local=self.value.get(context(family,s,a),[0.,0])
   estimated=(local[0]+ALPHA*b)/(local[1]+ALPHA)
   linear=sum(x*w for x,w in zip(basis(family,s,a),self.linear))
   result.append({"action":a,"paired_empirical_value":estimated,
                  "fully_trained_action_return":b,
                  "fully_trained_linear_ridge_value":linear,
                  "physical_context_fit_count":local[1]})
  return result

def choose(scores,name):
 return max(ACTIONS,key=lambda a:(scores[a][name],-a))

def execute_family_seeds(family,seeds,phase):
 rows=[]
 for seed in seeds:
  for tick in ANCHORS:
   anchor=f8.original_prefix(family,seed,tick)
   if anchor is None:continue
   if set(anchor["public"])!=set(f8.FIELDS):
    raise ValueError("F9_PUBLIC_ANCHOR_HAS_PRIVILEGED_FIELD")
   # Set execution order by hashed FIT/DEV seed, not prediction or reward.
   order=sorted(ACTIONS,key=lambda a:hashlib.sha256(
     f"{phase}:{family}:{seed}:{tick}:{a}".encode()).hexdigest())
   actually={str(a):f8.execute_real_arm(anchor,a) for a in order}
   if set(actually)!={"0","1","2"}:
    raise ValueError("F9_INCOMPLETE_ACTUAL_PAIRED_ACTIONS")
   rows.append({"family":family,"seed":seed,"anchor_tick":tick,
    "initial_public_sha256":anchor["initial_sha256"],
    "matched_anchor_public_sha256":anchor["anchor_sha256"],
    "six_public_before":anchor["public"],
    "public_teacher_action":anchor["teacher_at_anchor"],
    "original_public_prefix":anchor["prefix"],
    "randomized_actual_action_execution_order":order,
    "original_source_real_arms":actually})
 return rows

def evaluate():
 p=frozen()
 training=[r for family in FAMILIES for r in execute_family_seeds(family,FIT,"FIT")]
 tally={family:sum(z["family"]==family for z in training) for family in FAMILIES}
 # Inadequate training is a transparent scientific NO-GO, not a reason to
 # resample worlds or secretly change preregistered anchors.
 trained=IndependentlyFittedEstimators(training)
 evaluation=[r for family in FAMILIES for r in execute_family_seeds(family,DEV,"DEV")]
 for r in evaluation:
  scores=trained.scored(r["family"],r["six_public_before"])
  r["FIT_only_public_model_scores"]=scores
  r["empirical"]=choose(scores,"paired_empirical_value")
  r["action_prior"]=choose(scores,"fully_trained_action_return")
  r["linear_ridge"]=choose(scores,"fully_trained_linear_ridge_value")
 summary={};criteria={};pooled=[0.,0.,0]
 acceptance=p["design"]["acceptance"]
 for family in FAMILIES:
  cohort=[r for r in evaluation if r["family"]==family]
  if not cohort:raise ValueError("F9_NO_PROSPECTIVE_SOURCE_FAMILY")
  n=len(cohort)
  def actual(r,method,field="discounted_true_source_return"):
   return r["original_source_real_arms"][str(r[method])][field]
  ridge_gain=sum(actual(r,"empirical")-actual(r,"linear_ridge") for r in cohort)/n
  prior_gain=sum(actual(r,"empirical")-actual(r,"action_prior") for r in cohort)/n
  disagreement=sum(r["empirical"]!=r["linear_ridge"] for r in cohort)
  goals={name:sum(bool(actual(r,name,"goal_success")) for r in cohort)
         for name in ("empirical","linear_ridge","action_prior")}
  summary[family]={"FIT_anchor_count":tally[family],
    "DEV_evaluation_anchors":n,"DEV_actual_separate_action_trials":3*n,
    "empirical_vs_fitted_linear_choice_disagreements":disagreement,
    "empirical_minus_linear_mean_actual_return":ridge_gain,
    "empirical_minus_action_prior_mean_actual_return":prior_gain,
    "real_goals":goals,
    "mean_true_return":{name:sum(actual(r,name) for r in cohort)/n
       for name in ("empirical","linear_ridge","action_prior")},
    "mean_actual_steps":{name:sum(actual(r,name,"actual_steps_after_intervention") for r in cohort)/n
       for name in ("empirical","linear_ridge","action_prior")}}
  criteria[family+"_adequate_randomized_FIT_anchors"]=tally[family]>=acceptance["minimumTrainingAnchorsPerFamily"]
  criteria[family+"_adequate_fresh_DEV_anchors"]=n>=acceptance["minimumEvaluationAnchorsPerFamily"]
  criteria[family+"_enough_distinct_FIT_actions"]=disagreement>=acceptance["minimumActualEvaluationDisagreementsVsRidgeEachFamily"]
  criteria[family+"_paired_actual_return_not_worse_than_linear"]=ridge_gain>=acceptance["perFamilyRealReturnGainVsRidge"]
  if family=="fourrooms":
   criteria["FourRooms_source_goal_nonregression"]=goals["empirical"]>=goals["linear_ridge"]
  pooled[0]+=n*ridge_gain
  pooled[1]+=n*prior_gain
  pooled[2]+=n
 criteria["pooled_return_gain_vs_equal_FIT_linear"]=pooled[0]/pooled[2]>=acceptance["pooledRealReturnGainVsRidge"]
 criteria["pooled_return_gain_vs_equal_FIT_action_average"]=pooled[1]/pooled[2]>=acceptance["pooledRealReturnGainVsFittedActionPrior"]
 verdict=acceptance["positive"] if all(criteria.values()) else acceptance["noGo"]
 return {"schema":SCHEMA,"gate":"LCRM01-K4T-F9",
  "result":verdict,"criteria":criteria,"original_source_training":training,
  "original_source_prospective_evaluation":evaluation,"summary":summary,
  "FIT_trained_action_return_count":trained.train_actions,
  "FIT_true_intervention_table_sha256":trained.table_sha256,
  "FIT_true_linear_ridge_sha256":trained.linear_sha256,
  "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
  "original_source_commit":p["source"]["originalMiniGridCommit"],
  "fully_fitted_conventional_same_real_action_exposure":True,
  "same_genuinely_executed_arm_continuation_full_grid_informed":True,
  "R5_native_policy_unchanged":True,"scientific_first_use":False,"scientific_accepted":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 a=parser.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F9_OUTPUT_EXISTS")
 start=time.perf_counter();cpu=time.process_time()
 try:v=evaluate()
 except Exception as e:
  v={"schema":SCHEMA,"gate":"LCRM01-K4T-F9","result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
    "error":str(e),"error_type":type(e).__name__,
    "traceback_tail":traceback.format_exc().splitlines()[-16:],
    "scientific_first_use":False,"scientific_accepted":False}
 v["resources"]={"Python_cpu_seconds":time.process_time()-cpu,
    "whole_process_wall_seconds":time.perf_counter()-start,
    "Python_peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
    "native_subprocesses":0,"energy_measured":False}
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F9_ORIGINAL_ACTION_TRAINING_AND_EVALUATION="+v["result"])
 if "summary" in v:
  print("K4T_F9_NEW_WORLD_SUMMARY="+canon(v["summary"]))
  print("K4T_F9_PREREGISTERED_GATES="+canon(v["criteria"]))
 return int(v["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
