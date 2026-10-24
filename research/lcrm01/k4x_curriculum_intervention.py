#!/usr/bin/env python3
"""K4X: prospective, equal-public-transition native FIT curriculum intervention.

Unmodified Wingless Go and Yggdrasil Python native source. All actual heldout
public transition/action traces are stored, not only their hashes. This tests
teacher-guided source availability, NOT scientific novelty or causal planning.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
import time
import traceback

from k4r_minigrid_source import (
 FAMILIES, make_env, public, recorded_fit_transition, fitted, act, bfs, canon, sha)
from k4u_native_minigrid import WingBridge,train_native,public_grid,native_from_public

HERE=Path(__file__).parent
FROZEN=HERE/"k4x_frozen_curriculum_intervention.json"
SCHEMA="mass.lcrm01.k4x.original-native-source-curriculum-study.v1"
CURRICULA=("random_equal_budget","public_bfs_demonstration_equal_budget")
FIT_SEEDS=tuple(range(7300,7324))
PHASE_SEEDS={"CHECK":tuple(range(8300,8304)),"DEV":tuple(range(9300,9308))}
NATIVE=("wingless_native","yggdrasil_native")
METHODS=tuple(c+"__"+n for c in CURRICULA for n in
             ("wingless_native","yggdrasil_native","learned_model_bfs","tabular_q"))+(
             "public_bfs_expert","uniform_random","fixed_forward")
STEPS={"empty":96,"fourrooms":192}
STEPS_PER_FAMILY=6000


def protocol():
 p=json.loads(FROZEN.read_text(encoding="utf-8"))
 if (p.get("schema")!="mass.lcrm01.k4x.frozen-novel-source-curriculum-intervention.v1"
     or p["parents"]["K4W_head"]!="0bb78beaa07a25a021513548976f765824e6ca22"
     or p["sources"]["minigrid"]["commit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
     or p["intervention"]["training_curricula"]!=list(CURRICULA)
     or p["intervention"]["FIT_public_transition_budget_per_family_per_curriculum"]!=STEPS_PER_FAMILY
     or p["cohort"]["legal_actions"]!=[0,1,2]
     or p["cohort"]["FIT_seeds"]!={"from":7300,"to":7323}
     or p["cohort"]["DEV_seeds"]!={"from":9300,"to":9307}
     or "7 of every 8 source steps" not in p["intervention"]["demonstration"]):
  raise ValueError("K4X_FROZEN_SOURCE_OR_COHORT_DRIFT")
 return p


def fit_stream(curriculum):
 if curriculum not in CURRICULA:raise ValueError("UNREGISTERED_FIT_CURRICULUM")
 out=[];rows=[];starts=[];audit={}
 start=time.perf_counter()
 for fi,family in enumerate(FAMILIES):
  count=0;episode_index=0;successes=0;teacher_steps=0;random_steps=0
  while count<STEPS_PER_FAMILY:
   seed=FIT_SEEDS[episode_index%len(FIT_SEEDS)]
   rng=random.Random(870000+fi*100000+episode_index*300+seed)
   env=make_env(family)
   try:
    obs,_=env.reset(seed=seed)
    st=public(obs)
    starts.append({"family":family,"seed":seed,
      "curriculum":curriculum,"episode_index":episode_index,
      "public_start_sha256":st["grid_sha256"],"public_goal":list(st["goal"])})
    for t in range(STEPS[family]):
     if curriculum==CURRICULA[0] or count%8==7:
      a=rng.randrange(3);random_steps+=1
     else:
      a=bfs(st,None);teacher_steps+=1
     if a not in (0,1,2):raise ValueError("ILLEGAL_PUBLIC_TEACHER_ACTION")
     new_obs,reward,terminated,truncated,_=env.step(a)
     nxt=public(new_obs,st["goal"])
     done=bool(terminated or truncated)
     if not math.isfinite(float(reward)):
      raise ValueError("FIT_PUBLIC_ENVIRONMENT_REWARD_NONFINITE")
     rows.append(recorded_fit_transition(st,a,nxt,reward,family,seed,done))
     out.append({"family":family,"seed":seed,
       "action":a,"before":public_grid(st),"after":public_grid(nxt),
       "reward":float(reward),"terminal":done,
       "start_sha256":st["grid_sha256"],"next_sha256":nxt["grid_sha256"]})
     count+=1
     successes+=int(bool(terminated and float(reward)>0.))
     st=nxt
     if done or count>=STEPS_PER_FAMILY:break
   finally:env.close()
   episode_index+=1
   if episode_index>10000:raise ValueError("FIT_EPISODE_BUDGET_EXHAUSTED")
  audit[family]={"public_steps":count,"episodes_executed":episode_index,
    "distinct_training_seeds":len({v["seed"] for v in starts if v["family"]==family}),
    "positive_goal_rewards":successes,
    "teacher_issued_steps":teacher_steps,
    "source_uniform_steps":random_steps,
    "action_counts":{str(a):sum(v["action"]==a for v in out if v["family"]==family)
                      for a in (0,1,2)}}
  if count!=STEPS_PER_FAMILY:raise ValueError("UNEQUAL_TRAINING_PUBLIC_EXPOSURE")
 return out,rows,starts,audit,time.perf_counter()-start


def cohort_gate(exps,rows,starts,curriculum):
 model=fitted(rows,starts)
 nsteps={f:sum(x["family"]==f for x in exps) for f in FAMILIES}
 action_sets={f:{x["action"] for x in exps if x["family"]==f} for f in FAMILIES}
 qualified=(all(nsteps[f]==STEPS_PER_FAMILY for f in FAMILIES)
   and all(action_sets[f]=={0,1,2} for f in FAMILIES)
   and len(exps)==2*STEPS_PER_FAMILY
   and model["FIT_source_eligible"] is True)
 return model,{"qualified":qualified,"source_steps_by_family":nsteps,
       "legal_actions_by_family":{f:sorted(action_sets[f]) for f in FAMILIES},
       "conventional_FIT_support":model["FIT_support"]}


def open_trained_native(stream,go_exe,ygg_dir):
 import native_policy as native
 win,ygg,winblob,yggblob,info=train_native(stream,go_exe,ygg_dir)
 # Existing original K4U train_native restores Wingless in a fresh Go process
 # and validates Yggdrasil cold Python process. No policy update afterward.
 if info["native_fit_events_each"]!=len(stream):
  win.close();raise ValueError("NATIVE_FIT_EXPOSURE_MISMATCH")
 return win,ygg,info


def study_episode(family,seed,method,controllers,native):
 cpu=time.process_time();wall=time.perf_counter()
 env=make_env(family)
 rows=[];success=False;total=0.;first=None
 try:
  obs,_=env.reset(seed=seed)
  st=public(obs);origin=st["grid_sha256"];original_goal=list(st["goal"])
  for tick in range(STEPS[family]):
   if "__" in method:
    regime,policy=method.split("__",1)
    owner=controllers[regime]
    if policy=="wingless_native":
     a=owner["wingless"].choose(public_grid(st))
    elif policy=="yggdrasil_native":
     a=owner["yggdrasil"].choose(native_from_public(native,st))
    else:
     a=act(family,st,policy,owner["conventional"],seed,tick)
   else:
    a=act(family,st,method,controllers[CURRICULA[0]]["conventional"],seed,tick)
   if type(a)is not int or a not in (0,1,2):
    raise ValueError("HELDOUT_NATIVE_ACTION_NOT_LEGAL")
   if first is None:first=a
   nxtobs,reward,term,trunc,_=env.step(a)
   nxt=public(nxtobs,st["goal"])
   real=float(reward)
   if not math.isfinite(real):raise ValueError("HELDOUT_NONFINITE_REWARD")
   rows.append({"t":tick,"a":a,
      "b":[st["x"],st["y"],st["dir"],int(st["goal"][0]),int(st["goal"][1]),
            int(public_grid(st)["FrontBlocked"])],
      "n":[nxt["x"],nxt["y"],nxt["dir"],int(nxt["goal"][0]),int(nxt["goal"][1]),
            int(public_grid(nxt)["FrontBlocked"])],
      "r":real,"terminated":bool(term),"truncated":bool(trunc)})
   total+=real;st=nxt
   if term or trunc:
    success=bool(term and total>0);break
  return {"family":family,"seed":seed,"policy":method,
    "initial_public_sha256":origin,"public_goal":original_goal,
    "first_action":first,"success":success,"steps":len(rows),
    "total_public_reward":total,
    "actual_public_action_trace":rows,
    "trace_sha256":sha(canon(rows).encode()),
    "eval_python_CPU_seconds":time.process_time()-cpu,
    "eval_wall_seconds":time.perf_counter()-wall}
 finally:env.close()


def eval_phase(phase,controllers,native):
 results=[]
 for family in FAMILIES:
  for seed in PHASE_SEEDS[phase]:
   for method in METHODS:
    results.append(study_episode(family,seed,method,controllers,native))
 return results


def science(rows,controllers):
 out={};checks={}
 for family in FAMILIES:
  per_method={m:[r for r in rows if r["family"]==family and r["policy"]==m]
             for m in METHODS}
  if any(len(v)!=8 for v in per_method.values()):
   raise ValueError("K4X_MISSING_EQUAL_HELDOUT_CONTROL")
  out[family]={
   "wins":{m:sum(x["success"] for x in vals) for m,vals in per_method.items()},
   "mean_real_reward":{m:sum(x["total_public_reward"] for x in vals)/8
                          for m,vals in per_method.items()},
   "first_action_choices":{m:sorted({x["first_action"] for x in vals})
                              for m,vals in per_method.items()}}
 for learner in NATIVE:
  x=CURRICULA[0]+"__"+learner
  y=CURRICULA[1]+"__"+learner
  gates={}
  for family in FAMILIES:
   prev=out[family]["wins"][x];now=out[family]["wins"][y]
   mean=out[family]["mean_real_reward"]
   gates[family+"_teacher_wins_ge_4"]=now>=4
   gates[family+"_teacher_75pct_conventional_reward"]=(
       mean[y]>=.75*mean[CURRICULA[1]+"__learned_model_bfs"])
   gates[family+"_teacher_not_worse_than_random"]=now>=prev
   gates[family+"_teacher_choices_not_constant"]=len(out[family]["first_action_choices"][y])>=2
  improvement=sum(out[f]["wins"][y]-out[f]["wins"][x] for f in FAMILIES)
  gates["at_least_three_additional_genuine_goals"]=improvement>=3
  checks[learner]={"criteria":gates,"absolute_new_goals_vs_random":improvement,
     "qualified":all(gates.values())}
 conventional=all(out[f]["wins"][CURRICULA[1]+"__learned_model_bfs"]>=6
                 for f in FAMILIES)
 valid=conventional and all(c["qualified"] for c in checks.values())
 return {"result":"EXPERT_CURRICULUM_BOUNDED_NATIVE_SOURCE_GAIN" if valid else
    "NO_QUALIFIED_CURRICULUM_RESCUE_OF_NATIVE_NAVIGATION",
   "per_family":out,"candidate_tests":checks,
   "teacher_FIT_learned_planner_qualified":conventional,
   "teacher_is_public_map_planning_extra_information":True,
   "native_new_architecture_discovered":False,
   "scientific_first_use":False,"scientific_accepted":False}


def execute(go_exe,ygg_dir,p):
 import native_policy as native
 clock=time.perf_counter();cpu=time.process_time()
 model={}
 saved={}
 for regime in CURRICULA:
  data,records,starts,source_counts,wall=fit_stream(regime)
  conventional,gate=cohort_gate(data,records,starts,regime)
  entry={"fit_stream":data,"original_public_fit_episodes":starts,
      "source_balance":source_counts,"FIT_source_gate":gate,
      "conventional_state_sha256":sha(canon(conventional).encode()),
      "FIT_shared_public_world_wall_seconds":wall}
  if not gate["qualified"]:
   saved[regime]=entry
   return {"schema":SCHEMA,"gate":"LCRM01-K4X",
       "result":"ORIGINAL_FIT_SOURCE_INSUFFICIENT_HOLDOUT_UNCONSUMED",
       "FIT":saved,"CHECK_episodes":0,"DEV_episodes":0,
       "scientific_first_use":False,"scientific_accepted":False}
  wing,ygg,counts=open_trained_native(data,go_exe,ygg_dir)
  entry["native_source_training"]=counts
  saved[regime]=entry
  model[regime]={"wingless":wing,"yggdrasil":ygg,
                 "conventional":json.loads(canon(conventional))}
 try:
  check=eval_phase("CHECK",model,native)
  dev=eval_phase("DEV",model,native)
  verdict=science(dev,model)
  return {"schema":SCHEMA,"gate":"LCRM01-K4X",
    "result":"ORIGINAL_EXPERT_CURRICULUM_INTERVENTION_COMPLETE",
    "FIT":saved,"CHECK_episodes":len(check),"DEV_episodes":len(dev),
    "CHECK_original_public_traces":check,"DEV_original_public_traces":dev,
    "native_curriculum_disposition":verdict,
    "scientific_first_use":False,"scientific_accepted":False}
 finally:
  for item in model.values():item["wingless"].close()


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--go-binary",type=Path,required=True)
 parser.add_argument("--ygg-source-dir",type=Path,required=True)
 parser.add_argument("--output",type=Path,required=True)
 args=parser.parse_args()
 if args.output.exists() or not args.output.parent.is_dir():
  raise RuntimeError("K4X_EXISTING_OR_INVALID_EVIDENCE_OUTPUT")
 start_cpu=time.process_time();start_wall=time.perf_counter()
 try:
  p=protocol()
  sys.path.insert(0,str(args.ygg_source_dir.resolve()))
  report=execute(args.go_binary,args.ygg_source_dir,p)
  report["source_commit"]=p["sources"]["minigrid"]["commit"]
  report["wingless_commit"]=p["sources"]["wingless"]["commit"]
  report["yggdrasil_commit"]=p["sources"]["yggdrasil"]["commit"]
  report["protocol_sha256"]=sha(FROZEN.read_bytes())
  report["prior_K4U_NO_GO_preserved"]=True
 except Exception as e:
  report={"schema":SCHEMA,"gate":"LCRM01-K4X",
    "result":"SOURCE_OR_ENGINEERING_BLOCKED","error":str(e),
    "error_type":type(e).__name__,
    "traceback_tail":traceback.format_exc().splitlines()[-13:],
    "scientific_first_use":False,"scientific_accepted":False}
 report["resources"]={"Python_process_CPU_seconds":time.process_time()-start_cpu,
    "wall_seconds":time.perf_counter()-start_wall,
    "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
    "Go_IPC_cpu_not_included":True}
 args.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4X_ORIGINAL_OUTCOME="+report["result"])
 if "native_curriculum_disposition" in report:
  print("K4X_SCIENTIFIC_SOURCE="+report["native_curriculum_disposition"]["result"])
  print("K4X_DEV_WINS="+canon(report["native_curriculum_disposition"]["per_family"]))
 if "FIT" in report:
  print("K4X_REAL_FIT_SOURCE="+canon({k:v["source_balance"] for k,v in report["FIT"].items()}))
 return int(report["result"]=="SOURCE_OR_ENGINEERING_BLOCKED")


if __name__=="__main__":
 sys.exit(main())
