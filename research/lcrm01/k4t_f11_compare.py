#!/usr/bin/env python3
"""Independent whole-process compare of actual source public-history interventions."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f11_hard_public_memory import (
 FROZEN,SCHEMA,FIT,DEV,FAMILY,CATEGORIES,ACTIONS,contract
)

def stable(x):
 z=dict(x);z.pop("resources",None);return z
def verify(x,name,p):
 if (x.get("schema")!=SCHEMA or x.get("gate")!="LCRM01-K4T-F11"
    or x.get("result") not in (p["decisionGates"]["positive"],p["decisionGates"]["noGo"])
    or x.get("frozen_protocol_sha256")!=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    or x.get("original_Farama_commit")!=p["originalSources"]["miniGridCommit"]
    or x.get("scientific_first_use") is not False
    or x.get("scientific_accepted") is not False
    or x.get("all_counterfactual_branches_actually_executed") is not True
    or x.get("uses_more_informed_BFS_continuation") is not True
    or x.get("native_R5_source_unchanged") is not True):
  raise ValueError("F11_UNQUALIFIED_PUBLIC_SCIENCE_"+name)
 for key,seeds in (("true_FIT_paired_action_training",FIT),("true_fresh_DEV_paired_action_evaluation",DEV)):
  rows=x[key]
  if not rows:raise ValueError("F11_NO_REAL_SOURCE_STATES_"+name)
  seen=set()
  for r in rows:
   z=(r["seed"],r["anchor_tick"])
   if (r["family"]!=FAMILY or r["seed"] not in seeds or z in seen
     or r["prospective_difficulty_label"] not in CATEGORIES
     or set(r["six_public_before"])!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"}
     or set(r["true_source_three_arm_interventions"])!={"0","1","2"}
     or len(r["matched_anchor_public_sha256"])!=64 or
     len(r["initial_public_sha256"])!=64 or
     not r["actual_selected_action_prefix"] or
     len(r["witnessed_action_consequence_history"])>12):
    raise ValueError("F11_NOT_SAME_ORIGINAL_PUBLIC_ANCHOR_"+name)
   seen.add(z)
   for a in ACTIONS:
    value=r["true_source_three_arm_interventions"][str(a)]
    trace=value["actual_public_action_consequence_trace"]
    if(not trace or value["intervened_action"]!=a or trace[0]["action"]!=a
       or len(value["trace_sha256"])!=64
       or any(e["action"] not in ACTIONS for e in trace)):
     raise ValueError("F11_ACTION_NOT_ACTUALLY_PERFORMED_"+name)
   if key=="true_fresh_DEV_paired_action_evaluation":
    if set(r["fully_FIT_trained_public_scores"][0])!={
        "action","current_ridge","memory_ridge","history_empirical",
        "action_prior","historical_context_fit_events"}:
     raise ValueError("F11_MODEL_SCORE_AUDIT_"+name)
 if(x["equal_FIT_action_exposures_for_all_models"]!=
    3*len(x["true_FIT_paired_action_training"])):
  raise ValueError("F11_DIFFERENT_TRAINING_INFORMATION_BUDGET_"+name)
 if {r["seed"] for r in x["true_FIT_paired_action_training"]}&{
     r["seed"] for r in x["true_fresh_DEV_paired_action_evaluation"]}:
  raise ValueError("F11_FIT_DEV_COHORT_LEAK_"+name)

def compare(a,b):
 p=contract();verify(a,"A",p);verify(b,"B",p)
 same=stable(a)==stable(b)
 pass_signal=(same and a["result"]==p["decisionGates"]["positive"]
              and b["result"]==p["decisionGates"]["positive"])
 return {"schema":"mass.lcrm01.k4t-f11.independent-source-public-history-repeat-v1",
  "gate":"LCRM01-K4T-F11","science_identical":same,
  "result":("REPEATED_BOUNDED_F11_HARD_PUBLIC_MEMORY_DEV_SIGNAL_NOT_NATIVE_R5"
    if pass_signal else "NO_REPEATABLE_F11_HARD_PUBLIC_MEMORY_ACTION_VALUE_ADVANCEMENT"),
  "source_A":a["result"],"source_B":b["result"],
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 ap=argparse.ArgumentParser()
 for v in ("first","second","output"):ap.add_argument("--"+v,type=Path,required=True)
 a=ap.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("F11_NONFRESH_COMPARE_RESULT")
 v=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
 print("K4T_F11_INDEPENDENT_RESULT="+v["result"])
 print("K4T_F11_ORIGINAL_SOURCE_EXACT_REPEAT="+str(v["science_identical"]))
 return int(not v["science_identical"])
if __name__=="__main__":raise SystemExit(main())
