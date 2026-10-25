#!/usr/bin/env python3
"""F12 independently original-source returned-cell action and model custody."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f12_physical_return import (
 FROZEN,SCHEMA,FIT,DEV,FAMILY,CATEGORIES,ACTIONS,contract
)

def stable(v):
 x=dict(v);x.pop("resources",None);return x
def verify(x,label,p):
 if(x.get("schema")!=SCHEMA or x.get("gate")!="LCRM01-K4T-F12"
  or x.get("result") not in (p["acceptance"]["positive"],p["acceptance"]["failure"])
  or x.get("frozen_protocol_sha256")!=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
  or x.get("original_MiniGrid_source_commit")!=p["sources"]["originalMiniGridCommit"]
  or x.get("scientific_first_use") is not False
  or x.get("scientific_accepted") is not False
  or x.get("native_R5_unchanged") is not True
  or x.get("better_informed_common_BFS_follower") is not True
  or x.get("real_all_three_source_action_trials") is not True):
  raise ValueError("F12_FROZEN_SCIENTIFIC_SOURCE_INCOMPLETE_"+label)
 for key,allowed in (("FIT_true_original_source_matched_actions",FIT),
                     ("DEV_true_original_source_matched_actions",DEV)):
  rows=x[key]
  if not rows:raise ValueError("F12_EMPTY_AUTHENTIC_SOURCE_"+label)
  seen=set()
  for row in rows:
   idx=(row["seed"],row["anchor_tick"])
   if(row["family"]!=FAMILY or row["seed"] not in allowed or idx in seen or
      row["prospective_difficulty_label"] not in CATEGORIES or
      set(row["six_public_before"])!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"} or
      set(row["true_source_three_arm_interventions"])!={"0","1","2"} or
      len(row["matched_anchor_public_sha256"])!=64 or
      len(row["initial_public_sha256"])!=64 or
      not row["actual_selected_action_prefix"] or
      len(row["witnessed_action_consequence_history"])>12):
    raise ValueError("F12_REAL_ORIGINAL_SOURCE_PREFIX_INVALID_"+label)
   seen.add(idx)
   for action in ACTIONS:
    arm=row["true_source_three_arm_interventions"][str(action)]
    trace=arm["actual_public_action_consequence_trace"]
    if(not trace or arm["intervened_action"]!=action or
       trace[0]["action"]!=action or len(arm["trace_sha256"])!=64 or
       any(t["action"] not in ACTIONS for t in trace)):
     raise ValueError("F12_ARM_NOT_EXECUTED_OR_NOT_AUTHENTIC_"+label)
   if row["prospective_difficulty_label"]=="actual_physical_reentry":
    prefix=row["actual_selected_action_prefix"]
    hist=row["witnessed_action_consequence_history"]
    # Genuine physical movement into previously vacated cell, not heading.
    if not hist or not hist[-1]["physically_moved"]:
     raise ValueError("F12_FALSE_REVISIT_EVENT_"+label)
  if key=="DEV_true_original_source_matched_actions":
   for row in rows:
    if len(row["all_identical_FIT_source_scoring"])!=3:
     raise ValueError("F12_EQUAL_SOURCE_MODEL_SCORES_MISSING_"+label)
 if(x["all_models_exact_same_actual_source_FIT_exposure"]!=
   3*len(x["FIT_true_original_source_matched_actions"])):
  raise ValueError("F12_MODELS_DIFFERENT_FIT_BUDGET_"+label)
 if {r["seed"] for r in x["FIT_true_original_source_matched_actions"]}&{
    r["seed"] for r in x["DEV_true_original_source_matched_actions"]}:
  raise ValueError("F12_PREVIOUSLY_TRAINED_DEV_LEAK_"+label)
def compare(a,b):
 p=contract()
 verify(a,"A",p);verify(b,"B",p)
 same=stable(a)==stable(b)
 accepted=same and all(v["result"]==p["acceptance"]["positive"] for v in (a,b))
 return {"schema":"mass.lcrm01.k4t-f12.independent-original-physical-return-v1",
  "gate":"LCRM01-K4T-F12","science_identical":same,
  "result":("REPEATABLE_BOUNDED_F12_PHYSICAL_MAP_SOURCE_DEV_GAIN_NOT_NATIVE_R5"
            if accepted else "NO_REPEATABLE_F12_PHYSICAL_RETURN_GRAPH_MEMORY_ADVANCEMENT"),
  "source_A":a["result"],"source_B":b["result"],
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):
  p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F12_NONFRESH_INDEPENDENT_COMPARE")
 v=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
 print("K4T_F12_INDEPENDENT_RESULT="+v["result"])
 print("K4T_F12_BIT_IDENTICAL_TRUE_SOURCE_SCIENCE="+str(v["science_identical"]))
 return int(not v["science_identical"])
if __name__=="__main__":raise SystemExit(main())
