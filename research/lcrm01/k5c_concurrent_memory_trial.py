#!/usr/bin/env python3
"""K5C: authentic concurrent physical MiniGrid MemoryEnv cue binding.

All workgroup environments independently reset before ANY choice. Policies
observe only first-stage opaque slot and original cue, then later receive slot
and actual branch candidate types but NEVER the early cue again. A shared,
public-map shortest-path motor actor executes genuine 0/1/2 environment steps.
No environment hidden success/failure labels or protected controller writes.
"""
import argparse
import copy
import hashlib
import json
import math
import random
import resource
import subprocess
import sys
import time
import traceback
from pathlib import Path
import numpy as np

import k5b_memory_trial as k5b

PIN=Path(__file__).with_name("k5c_frozen_concurrent_memory.json")
SCHEMA="mass.lcrm01.k5c.original-concurrent-physical-cue-memory-v1"
METHODS=("native_R5_slot_memory","native_R5_single_slot_ablation","original_R4_one_cue",
         "conventional_slot_dict","memoryless_top","semantic_rule_upper")
SIZES=(11,13)
CAPACITIES=(4,8)
COHORTS={"CHECK":tuple(range(31000,31016)),"DEV":tuple(range(32000,32064))}
R5_SOURCE_BLOB="4182889a47e31391a95ea3a2f5d8a4b87bcd6359"

def canon(obj):
 return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)
def sha(x):
 return hashlib.sha256(x).hexdigest()

def frozen():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k5c.frozen-original-concurrent-memory-transfer-v1"
  or p["parent_K5B_head"]!="61d023fd48a0701d2ef42c2752afae79bbdbfad9"
  or p["new_cohorts"]["CHECK_seeds"]!=[31000,31015]
  or p["new_cohorts"]["DEV_seeds"]!=[32000,32063]
  or p["new_cohorts"]["capacity_levels"]!=[4,8]
  or p["original_source"]["MemoryEnv_blob"]!="660b0a1b769948034c87bb421759c2b9a4f24548"):
  raise ValueError("K5C_ORIGINAL_SOURCE_OR_COHORT_DRIFT")
 return p

def fit():
 from research.native.itd02.r5.concurrent_cues import ConcurrentCueMemory
 original=ConcurrentCueMemory()
 conventional=k5b.ConventionalMemory()
 rows=[];support={}
 for size in SIZES:
  positives=0;negatives=0;choices=set();cues=set()
  for seed in range(26000,26064):
   choice=random.Random(1417000+size*100000+seed*11).randrange(2)
   physical=k5b.episode(size,seed,None,fit_choice=choice)
   original.fit(physical["cue_token"],physical["selected_candidate"],
       physical["original_terminal_reward"],True)
   conventional.begin(physical["cue_token"])
   conventional.learn(physical["selected_candidate"],physical["original_terminal_reward"])
   rows.append(physical)
   positives+=int(physical["real_goal_success"])
   negatives+=int(not physical["real_goal_success"])
   choices.add(choice);cues.add(physical["cue_token"])
  support[str(size)]={"actual_positive_rewards":positives,"actual_negative_rewards":negatives,
    "legal_selected_arms":sorted(choices),"original_start_cues":sorted(cues)}
 if any(s["actual_positive_rewards"]<16 or s["actual_negative_rewards"]<16
    or s["legal_selected_arms"]!=[0,1] or s["original_start_cues"]!=["ball","key"]
    for s in support.values()):
  return rows,support,None,None
 raw=original.snapshot()
 script="""import json,sys
from research.native.itd02.r5.concurrent_cues import ConcurrentCueMemory
n=ConcurrentCueMemory.restore(sys.stdin.buffer.read())
print(json.dumps({"updates":n.training_events,"slots":len(n.slots),"r4":n.cell.outcomes}))
"""
 cold=subprocess.run([sys.executable,"-B","-c",script],input=raw,
        capture_output=True,timeout=40)
 if cold.returncode or json.loads(cold.stdout)!={"updates":128,"slots":0,"r4":128}:
  raise ValueError("K5C_NATIVE_R5_COLD_OS_RESTORE_FAILED:"+cold.stderr.decode()[-500:])
 original=ConcurrentCueMemory.restore(raw)
 return rows,support,original,conventional

def one_group(size,seeds,method,trained,classic,capacity):
 from research.native.itd02.r5.concurrent_cues import ConcurrentCueMemory
 from research.native.itd02.r4.cue_cells import CueCells
 if len(seeds)!=capacity:raise ValueError("K5C_INCOMPLETE_CONCURRENT_TASKS")
 policy=ConcurrentCueMemory.restore(trained.snapshot())
 r4=CueCells.restore(trained.cell.snapshot())
 dictionary={}
 scenarios=[];trace=[]
 begin=time.perf_counter()
 # Physically reset ALL independent original MemoryEnv tasks BEFORE
 # making any decision, then bind their first-stage public cues.
 try:
  for slot,seed in enumerate(seeds):
   env=k5b.make_env(size)
   obs,_=env.reset(seed=seed)
   cue,top,bottom=k5b.read_cue_and_candidates(obs,size)
   dictionary[slot]=cue
   if method=="native_R5_slot_memory":policy.present(slot,cue)
   if method in ("native_R5_single_slot_ablation","original_R4_one_cue"):
    r4.begin(cue) # one-slot overwrite by every newer task
   scenarios.append((env,obs,slot,seed,top,bottom))
  if method=="native_R5_slot_memory":
   if len(policy.slots)!=capacity:raise ValueError("K5C_NATIVE_LOST_PENDING_CONTEXT")
   checkpoint_bytes=len(policy.snapshot())
  else:checkpoint_bytes=len(trained.snapshot()) if method.startswith("native_R5") else 0
  # All rewards withheld until AFTER the entire cue stream is complete.
  for env,obs,slot,seed,top,bottom in reversed(scenarios):
   before=obs
   mid=size//2;bx=size-2
   actual_actions=[]
   obs,prior_reward,premature,trunc=k5b.traverse(env,obs,(size-4,mid),actual_actions)
   if premature or trunc:
    raise ValueError("K5C_REAL_EPISODE_ENDED_BEFORE_DELAYED_CHOICE")
   later_top,later_bottom=top,bottom
   t=time.perf_counter()
   if method=="native_R5_slot_memory":
    choice=policy.choose(slot,later_top,later_bottom)
   elif method in ("native_R5_single_slot_ablation","original_R4_one_cue"):
    choice=r4.choose(later_top,later_bottom)
   elif method=="conventional_slot_dict":
    cue=dictionary[slot]
    def value(c):
     key="match" if cue==c else "different"
     yes,no=classic.table[key]
     return (yes+1)/(yes+no+2)
    choice=int(value(later_bottom)>value(later_top))
   elif method=="memoryless_top":choice=0
   elif method=="semantic_rule_upper":choice=int(later_bottom==dictionary[slot])
   else:raise ValueError("K5C_UNREGISTERED_MODEL")
   inference=time.perf_counter()-t
   if type(choice)is not int or choice not in (0,1):
    raise ValueError("K5C_INVALID_NATIVE_LATE_DECISION")
   dest=(bx,mid-1) if choice==0 else (bx,mid+1)
   obs,reward,terminated,truncated=k5b.traverse(env,obs,dest,actual_actions)
   if not terminated or truncated or tuple(k5b.agent_state(np.asarray(obs["image"]))[:2])!=dest:
    raise ValueError("K5C_ORIGINAL_MEMORY_ENV_NO_PHYSICAL_TERMINAL")
   if not math.isfinite(reward) or not (0<=reward<=1):
    raise ValueError("K5C_UNTRUSTWORTHY_ENVIRONMENT_REWARD")
   if method=="native_R5_slot_memory":policy.release(slot)
   trace.append({"size":size,"capacity":capacity,"seed":seed,
       "policy":method,"opaque_slot":slot,"real_goal_success":reward>0,
       "original_terminal_reward":float(reward),"selected_arm":choice,
       "actual_public_step_trace":actual_actions,"physical_steps":len(actual_actions),
       "trace_sha256":sha(canon(actual_actions).encode()),
       "decision_only_wall_seconds":inference,
       "elapsed_group_wall_seconds":time.perf_counter()-begin,
       "retained_concurrent_checkpoint_bytes":checkpoint_bytes})
  return trace
 finally:
  for env,_,_,_,_,_ in scenarios:env.close()

def eval_cohort(phase,trained,classic):
 all_rows=[]
 for size in SIZES:
  for capacity in CAPACITIES:
   seeds=COHORTS[phase]
   if len(seeds)%capacity:raise ValueError("K5C_COHORT_NOT_MULTIPLE_OF_CONCURRENCY")
   for method in METHODS:
    for offset in range(0,len(seeds),capacity):
     all_rows+=one_group(size,seeds[offset:offset+capacity],method,trained,classic,capacity)
 return all_rows

def judge(dev):
 result={};gates={}
 for size in SIZES:
  result[str(size)]={}
  for cap in CAPACITIES:
   key=str(cap)
   result[str(size)][key]={}
   for method in METHODS:
    group=[r for r in dev if r["size"]==size and r["capacity"]==cap and r["policy"]==method]
    if len(group)!=64 or sorted(r["seed"] for r in group)!=list(COHORTS["DEV"]):
     raise ValueError("K5C_UNMATCHED_OR_MISSING_PHYSICAL_DEV_TASK")
    result[str(size)][key][method]={"real_goal_completions":sum(r["real_goal_success"] for r in group),
      "original_mean_reward":sum(r["original_terminal_reward"] for r in group)/64,
      "actual_motor_steps":sum(r["physical_steps"] for r in group),
      "decision_inference_seconds":sum(r["decision_only_wall_seconds"] for r in group),
      "mean_pending_checkpoint_bytes":sum(r["retained_concurrent_checkpoint_bytes"] for r in group)/64}
   item=result[str(size)][key]
   gates[f"{size}_capacity{cap}_at_least_48_goals"]=item["native_R5_slot_memory"]["real_goal_completions"]>=48
   gates[f"{size}_capacity{cap}_within_one_goal_of_dict"]=(
      item["native_R5_slot_memory"]["real_goal_completions"]>=item["conventional_slot_dict"]["real_goal_completions"]-1)
  item=result[str(size)]["8"]
  gates[f"{size}_capacity8_gain_13_goals_vs_one_slot"]=(
    item["native_R5_slot_memory"]["real_goal_completions"]-
    item["native_R5_single_slot_ablation"]["real_goal_completions"]>=13)
 qualified=all(gates.values())
 novel=any(result[str(size)][str(cap)]["native_R5_slot_memory"]["real_goal_completions"] >
           result[str(size)][str(cap)]["conventional_slot_dict"]["real_goal_completions"]
           for size in SIZES for cap in CAPACITIES)
 return {"result":"BOUNDED_CONCURRENT_EPISODIC_CUE_BINDING" if qualified
            else "NO_QUALIFIED_CONCURRENT_EPISODIC_RETENTION",
       "per_size_capacity_method":result,
       "frozen_acceptance_gates":gates,
       "native_beat_dictionary_any_cell":novel,
       "native_architecture_novelty_established":False,
       "autonomous_navigation_not_tested":True,
       "scientific_first_use":False,"scientific_accepted":False}

def study():
 rows,support,native,classic=fit()
 out={"schema":SCHEMA,"gate":"LCRM01-K5C",
      "FIT_original_real_tasks":rows,"FIT_source_support":support,
      "FIT_authentic_physical_episodes":len(rows),
      "CHECK_original_episodes":0,"DEV_original_episodes":0,
      "prior_K5B_science_immutable":True,
      "scientific_first_use":False,"scientific_accepted":False}
 if native is None:
  out["result"]="FIT_SOURCE_UNQUALIFIED_HOLDOUT_NOT_CONSUMED"
  return out
 out["original_R5_cold_OS_restore"]=True
 out["native_FIT_checkpoint_bytes"]=len(native.snapshot())
 out["native_FIT_checkpoint_sha256"]=sha(native.snapshot())
 out["conventional_FIT_counts"]=classic.table
 check=eval_cohort("CHECK",native,classic)
 dev=eval_cohort("DEV",native,classic)
 out.update({"CHECK_original_episodes":len(check),"DEV_original_episodes":len(dev),
    "CHECK_full_original_action_traces":check,"DEV_full_original_action_traces":dev,
    "scientific":judge(dev),
    "result":"COMPLETE_ORIGINAL_CONCURRENT_CUE_INTERFERENCE_STUDY"})
 return out

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--output",type=Path,required=True)
 q=a.parse_args()
 if q.output.exists() or not q.output.parent.is_dir():raise RuntimeError("K5C_EXISTING_RECEIPT")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  p=frozen()
  out=study()
  out["protocol_sha256"]=sha(PIN.read_bytes())
  out["original_R5_native_blob"]=R5_SOURCE_BLOB
  out["original_MemoryEnv_blob"]=p["original_source"]["MemoryEnv_blob"]
 except Exception as e:
  out={"schema":SCHEMA,"gate":"LCRM01-K5C","result":"SOURCE_OR_ENGINEERING_BLOCKED",
    "error_type":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-12:],
    "scientific_first_use":False,"scientific_accepted":False}
 out["resources"]={"whole_python_CPU_seconds":time.process_time()-cpu,
    "whole_wall_seconds":time.perf_counter()-wall,
    "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 q.output.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K5C_ORIGINAL_RESULT="+out["result"])
 if "scientific" in out:
  print("K5C_FROZEN_SCIENCE="+out["scientific"]["result"])
  print("K5C_REAL_GOALS="+canon(out["scientific"]["per_size_capacity_method"]))
 print("K5C_REAL_FIT="+str(out.get("FIT_authentic_physical_episodes",0)))
 return int(out["result"]=="SOURCE_OR_ENGINEERING_BLOCKED")
if __name__=="__main__":raise SystemExit(main())
