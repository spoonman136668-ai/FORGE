#!/usr/bin/env python3
"""Independent source first-use, triplicate original interventions and exact science."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f9_randomized_value import FROZEN,SCHEMA,FIT,DEV,FAMILIES,ANCHORS,ACTIONS,canon,frozen

def stable(x):
 y=dict(x);y.pop("resources",None)
 return y
def compare(a,b):
 p=frozen();signature=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for name,x in (("A",a),("B",b)):
  if (x.get("schema")!=SCHEMA or x.get("gate")!="LCRM01-K4T-F9"
   or x.get("result") not in (p["acceptance"]["positive"],
                              p["acceptance"]["noGo"])
   or x.get("original_source_commit")!=p["source"]["originalMiniGridCommit"]
   or x.get("protocol_sha256")!=signature
   or x.get("fully_fitted_conventional_same_real_action_exposure") is not True
   or x.get("same_genuinely_executed_arm_continuation_full_grid_informed") is not True
   or x.get("R5_native_policy_unchanged") is not True
   or x.get("scientific_first_use") is not False
   or x.get("scientific_accepted") is not False):
   raise ValueError("F9_FROZEN_ACTUAL_INTERVENTION_DRIFT_"+name)
  for phase,allowed in (("training",FIT),("prospective_evaluation",DEV)):
   records=x["original_source_"+phase]
   if not records:raise ValueError("F9_MISSING_TRUE_ACTIONS_"+phase)
   seen=set()
   for r in records:
    tag=(r["family"],r["seed"],r["anchor_tick"])
    if (r["family"] not in FAMILIES or r["seed"] not in allowed
       or r["anchor_tick"] not in ANCHORS or tag in seen
       or set(r["original_source_real_arms"])!={"0","1","2"}
       or set(r["six_public_before"])!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"}
       or len(r["matched_anchor_public_sha256"])!=64):
     raise ValueError("F9_REAL_SAME_PREFIX_SOURCE_CUSTODY_"+name)
    seen.add(tag)
    for action,arm in r["original_source_real_arms"].items():
     seq=arm["actual_public_action_consequence_trace"]
     if (arm["intervened_action"]!=int(action)
        or not seq or seq[0]["action"]!=int(action)
        or len(arm["trace_sha256"])!=64
        or any(step["action"] not in ACTIONS for step in seq)):
      raise ValueError("F9_IMPUTED_UNPERFORMED_OR_ILLEGAL_SOURCE_ACTION_"+name)
   for family in FAMILIES:
    if not any(r["family"]==family for r in records):
     raise ValueError("F9_INCOMPLETE_FAMILY_"+name)
  if set(r["seed"] for r in x["original_source_training"]) & set(
      r["seed"] for r in x["original_source_prospective_evaluation"]):
   raise ValueError("F9_COHORT_LEAK_"+name)
  if x["FIT_trained_action_return_count"]!=3*len(x["original_source_training"]):
   raise ValueError("F9_NOT_PAIRED_FIT_EXPOSURE_"+name)
 identical=stable(a)==stable(b)
 qualified=identical and a["result"]==b["result"]==p["acceptance"]["positive"]
 return {"schema":"mass.lcrm01.k4t-f9.independent-real-paired-source-repeat-v1",
         "gate":"LCRM01-K4T-F9","science_identical":identical,
         "result":("REPEATABLE_BOUNDED_F9_REAL_INTERVENTION_GAIN_NO_NATIVE_R5"
           if qualified else "NO_REPEATABLE_F9_RANDOMIZED_ACTION_VALUE_ADVANCEMENT"),
         "source_A":a["result"],"source_B":b["result"],
         "scientific_first_use":False,"scientific_accepted":False}
def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):
  p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F9_NONFRESH_COMPARISON")
 v=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
 print("K4T_F9_INDEPENDENT_RESULT="+v["result"])
 print("K4T_F9_EXACT_SOURCE_SCIENCE_AGREEMENT="+str(v["science_identical"]))
 return int(not v["science_identical"])
if __name__=="__main__":raise SystemExit(main())
