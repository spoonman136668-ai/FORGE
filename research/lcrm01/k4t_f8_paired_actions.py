#!/usr/bin/env python3
"""F8 true selected-action interventions from identical original-world resets.

Original public expert supplies the *same* prefix and continuation for all
three physically executed action arms. Neither F7 nor conventional controls
receive privileged grid state. This is NOT an R5 policy evaluation.
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

import k4t_f7_delayed_value as f7
import k4x_curriculum_intervention as k4x
import k4r_minigrid_source as src
from k4u_native_minigrid import public_grid
from k4t_f4_sixfield_conventional import fit as fit6,SixFieldConventional

FROZEN=Path(__file__).with_name("k4t_f8_frozen_paired_actions.json")
SCHEMA="mass.lcrm01.k4t-f8.original-matched-public-action-interventions-v1"
FIT=tuple(range(91400,91424))
DEV=tuple(range(101400,101412))
FAMILIES=("empty","fourrooms")
ANCHORS=(0,4,8,12)
ACTIONS=(0,1,2)
STEPS={"empty":96,"fourrooms":192}
GAMMA=.97
COST=.01

def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def contract():
 p=json.loads(FROZEN.read_text())
 if(p["schema"]!="mass.lcrm01.k4t-f8.frozen-paired-actions-v1"
    or p["parentF7Head"]!="83e6d08606f741605c2f8c5e7536b606575a2f11"
    or p["source"]["minigridCommit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
    or p["source"]["F7CodeBlob"]!="f28f0f669a2b6621f2da7083976af0d508803e76"
    or p["source"]["FITSeedRange"]!=[91400,91423]
    or p["source"]["freshInterventionSeedRange"]!=[101400,101411]
    or p["realEpisodes"]["anchorTicks"]!=list(ANCHORS)
    or p["realEpisodes"]["actions"]!=list(ACTIONS)
    or p["governance"]["protectedFirstUse"] is not False
    or p["governance"]["scientificAccepted"] is not False):
  raise ValueError("F8_FROZEN_PROSPECTIVE_CONTRACT_DRIFT")
 return p

class LearnedLoggedValues:
 def __init__(self,stream):
  labelled,audit=f7.samples(stream)
  self.audit=audit
  self.base=defaultdict(lambda:[0.,0])
  self.ctx=defaultdict(lambda:[0.,0])
  for x,y in labelled:
   b=self.base[f7.prior(x)];b[0]+=y;b[1]+=1
   c=self.ctx[f7.features(x)];c[0]+=y;c[1]+=1
  if len(self.base)!=6:raise ValueError("F8_NO_ACTION_SUPPORT_IN_FIT")
 def values(self,family,public):
  if not f7.valid(public):raise ValueError("F8_PRIVILEGED_OR_INVALID_OBSERVATION")
  out=[]
  for action in ACTIONS:
   x={"family":family,"action":action,"before":public}
   b=self.base[f7.prior(x)]
   if not b[1]:raise ValueError("F8_MISSING_FIT_ACTION_PRIOR")
   prior=b[0]/b[1]
   ctx=self.ctx.get(f7.features(x),(0.,0))
   estimated=(ctx[0]+f7.SMOOTH*prior)/(ctx[1]+f7.SMOOTH)
   out.append({"action":action,"F7_logged_return_estimate":estimated,
                "FIT_mean_selected_action_return":prior,
                "FIT_context_count":ctx[1]})
  return out
def argmax(vals,key):
 return max(ACTIONS,key=lambda a:(vals[a][key],-a))
def original_prefix(family,seed,tick):
 env=src.make_env(family)
 try:
  obs,_=env.reset(seed=seed)
  st=src.public(obs)
  initial=st["grid_sha256"]
  prefix=[]
  for t in range(tick):
   a=src.bfs(st,None)
   obs_next,reward,term,trunc,_=env.step(a)
   nxt=src.public(obs_next,st["goal"])
   prefix.append({"t":t,"action":a,"before_sha":st["grid_sha256"],
                  "after_sha":nxt["grid_sha256"],"reward":float(reward),
                  "terminated":bool(term),"truncated":bool(trunc)})
   st=nxt
   if term or trunc:return None
  return {"seed":seed,"family":family,"tick":tick,"initial_sha256":initial,
          "anchor_sha256":st["grid_sha256"],"public":public_grid(st),
          "teacher_at_anchor":src.bfs(st,None),"prefix":prefix}
 finally:env.close()
def execute_real_arm(anchor,action):
 family,seed,tick=anchor["family"],anchor["seed"],anchor["tick"]
 env=src.make_env(family)
 try:
  obs,_=env.reset(seed=seed)
  st=src.public(obs)
  if st["grid_sha256"]!=anchor["initial_sha256"]:
   raise ValueError("F8_SAME_SEED_INITIAL_PUBLIC_GRID_DRIFT")
  for prefix in anchor["prefix"]:
   if st["grid_sha256"]!=prefix["before_sha"]:
    raise ValueError("F8_INTERVENTION_PREFIX_BEFORE_MISMATCH")
   obs,reward,term,trunc,_=env.step(prefix["action"])
   st=src.public(obs,st["goal"])
   if(st["grid_sha256"]!=prefix["after_sha"] or reward!=prefix["reward"]
      or bool(term)!=prefix["terminated"] or bool(trunc)!=prefix["truncated"]):
    raise ValueError("F8_PREFIX_REPLAY_NOT_IDENTICAL")
   if term or trunc:raise ValueError("F8_TERMINAL_PREFIX_REPLAYED")
  if st["grid_sha256"]!=anchor["anchor_sha256"] or public_grid(st)!=anchor["public"]:
   raise ValueError("F8_DIFFERENT_WORLD_STATE_FOR_ACTION_ARM")
  discounted=0.;discount=1.;source_total=0.;rows=[];success=False
  for t in range(tick,STEPS[family]):
   chosen=action if t==tick else src.bfs(st,None)
   if chosen not in ACTIONS:raise ValueError("F8_NONLEGAL_SELECTED_ACTION")
   b=public_grid(st)
   obs,reward,term,trunc,_=env.step(chosen)
   nxt=src.public(obs,st["goal"])
   after=public_grid(nxt)
   if not math.isfinite(float(reward)):raise ValueError("F8_NONFINITE_ACTUAL_SOURCE_REWARD")
   discounted+=discount*(float(reward)-COST)
   discount*=GAMMA
   source_total+=float(reward)
   rows.append({"tick":t,"action":chosen,"before":b,"after":after,
     "reward":float(reward),"terminated":bool(term),"truncated":bool(trunc),
     "before_sha256":st["grid_sha256"],"after_sha256":nxt["grid_sha256"]})
   st=nxt
   if term or trunc:
    success=bool(term and source_total>0.)
    break
  if not rows or rows[0]["action"]!=action:
   raise ValueError("F8_INTERVENED_ACTION_NOT_REAL")
  return {"intervened_action":action,"discounted_true_source_return":discounted,
    "actual_source_reward":source_total,"actual_steps_after_intervention":len(rows),
    "goal_success":success,"actual_public_action_consequence_trace":rows,
    "trace_sha256":sha(canon(rows).encode())}
 finally:env.close()
def evaluate():
 protocol=contract()
 k4x.FIT_SEEDS=FIT
 stream,rows,starts,audit,wall=k4x.fit_stream("public_bfs_demonstration_equal_budget")
 if (len(stream)!=12000 or any(sum(x["family"]==f for x in stream)!=6000 for f in FAMILIES)):
  raise ValueError("F8_ORIGINAL_FIT_EVENT_COUNT")
 fitdigest=sha(f7.canon(stream).encode())
 if fitdigest!="c33b22d30b8be54a695be15f0fa180ce40830d40a3bc3be2dfa3186ba8f9348c":
  raise ValueError("F8_PREVIOUS_F7_SOURCE_FIT_IDENTITY_DRIFT")
 learned=LearnedLoggedValues(stream)
 sixmodel,sixhash=fit6(stream)
 arms=[]
 for family in FAMILIES:
  for seed in DEV:
   for tick in ANCHORS:
    anchor=original_prefix(family,seed,tick)
    if anchor is None:continue
    vals=learned.values(family,anchor["public"])
    model=argmax(vals,"F7_logged_return_estimate")
    prior=argmax(vals,"FIT_mean_selected_action_return")
    conventional=SixFieldConventional(sixmodel).choose(anchor["public"])
    if conventional not in ACTIONS:raise ValueError("F8_CONVENTIONAL_NOT_LEARNED")
    real={str(a):execute_real_arm(anchor,a) for a in ACTIONS}
    if len({v["intervened_action"] for v in real.values()})!=3:
     raise ValueError("F8_NOT_ALL_ACTUAL_ACTION_INTERVENTIONS")
    arms.append({"family":family,"seed":seed,"anchor_tick":tick,
      "initial_public_sha256":anchor["initial_sha256"],
      "matched_anchor_public_sha256":anchor["anchor_sha256"],
      "six_public_before":anchor["public"],"actual_teacher_prefix":anchor["prefix"],
      "model":model,"prior":prior,"sixfield":conventional,
      "more_informed_public_BFS":anchor["teacher_at_anchor"],
      "fit_predicted_action_values":vals,"original_source_real_arms":real})
 summary={};criteria={}
 p=protocol["acceptance"]
 for family in FAMILIES:
  group=[a for a in arms if a["family"]==family]
  if not group:raise ValueError("F8_NO_GENUINE_PAIRED_FAMILY")
  def v(z,method,key="discounted_true_source_return"):
   return z["original_source_real_arms"][str(z[method])][key]
  n=len(group)
  gain_prior=sum(v(z,"model")-v(z,"prior") for z in group)/n
  gain_six=sum(v(z,"model")-v(z,"sixfield") for z in group)/n
  wins=sum(z["model"]!=z["prior"] for z in group)
  modelgoal=sum(v(z,"model","goal_success") for z in group)
  priorgoal=sum(v(z,"prior","goal_success") for z in group)
  summary[family]={"anchors":n,"actual_real_action_interventions":3*n,
   "different_from_trained_action_prior_anchors":wins,
   "mean_real_discounted_return_delta_model_minus_prior":gain_prior,
   "mean_real_discounted_return_delta_model_minus_sixfield":gain_six,
   "model_actual_goals":modelgoal,"prior_actual_goals":priorgoal,
   "sixfield_actual_goals":sum(v(z,"sixfield","goal_success") for z in group),
   "stronger_oracle_actual_goals":sum(v(z,"more_informed_public_BFS","goal_success") for z in group),
   "mean_selected_model_true_return":sum(v(z,"model") for z in group)/n,
   "mean_selected_prior_true_return":sum(v(z,"prior") for z in group)/n,
   "mean_selected_sixfield_true_return":sum(v(z,"sixfield") for z in group)/n}
  criteria[family+"_paired_anchor_minimum"]=n>=p["minimumPairedAnchorsEachFamily"]
  criteria[family+"_minimum_actual_policy_disagreements"]=wins>=p["minimumPredictionDisagreementsWithFITBaselineEachFamily"]
  criteria[family+"_value_gain_vs_fit_action_prior"]=gain_prior>=p["meanPairedRealReturnGainModelVsFITBaselineEachFamily"]
  criteria[family+"_value_gain_vs_equal_sixfield"]=gain_six>=p["meanPairedRealReturnGainModelVsTrainedSixfieldEachFamily"]
  if family=="fourrooms":
   criteria["FourRooms_source_goals_no_regression"]=modelgoal>=priorgoal
 result=p["positive"] if all(criteria.values()) else p["no_go"]
 return {"schema":SCHEMA,"gate":"LCRM01-K4T-F8",
  "result":result,"criteria":criteria,"public_intervention_summary":summary,
  "actual_paired_original_action_interventions":arms,
  "original_frozen_F7_FIT_source_digest":fitdigest,
  "trained_sixfield_conventional_FIT_digest":sixhash,
  "F7_true_selected_action_label_audit":learned.audit,
  "original_FIT_source_records":stream,
  "FIT_source_audit":audit,
  "source_minigrid_commit":protocol["source"]["minigridCommit"],
  "protocol_sha256":sha(FROZEN.read_bytes()),
  "future_common_BFS_continuation_uses_more_public_information":True,
  "not_an_R5_native_policy_comparison":True,
  "actual_separate_real_action_interventions":True,
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F8_NONFRESH_RESULT")
 start=time.perf_counter();cpu=time.process_time()
 try:v=evaluate()
 except Exception as e:
  v={"schema":SCHEMA,"gate":"LCRM01-K4T-F8","result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
    "error_type":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-15:],
    "scientific_first_use":False,"scientific_accepted":False}
 v["resources"]={"Python_process_CPU_seconds":time.process_time()-cpu,
   "wall_seconds":time.perf_counter()-start,
   "Python_peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
   "Go_native_calls":0,"energy_not_measured":True}
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F8_INTERVENTION_RESULT="+v["result"])
 if "public_intervention_summary" in v:
  print("K4T_F8_REAL_PAIRED_SUMMARY="+canon(v["public_intervention_summary"]))
  print("K4T_F8_FROZEN_GATES="+canon(v["criteria"]))
 return int(v["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
