#!/usr/bin/env python3
"""Independent complete process comparison for true three-arm public experiments."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f8_paired_actions import FROZEN,SCHEMA,DEV,FAMILIES,ANCHORS,ACTIONS,canon,contract
def stable(x):
 y=dict(x)
 y.pop("resources",None)
 return y
def compare(a,b):
 p=contract()
 identity=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for label,q in (("A",a),("B",b)):
  if(q.get("schema")!=SCHEMA or q.get("gate")!="LCRM01-K4T-F8"
   or q.get("protocol_sha256")!=identity
   or q.get("result") not in (p["acceptance"]["positive"],p["acceptance"]["no_go"])
   or q.get("source_minigrid_commit")!=p["source"]["minigridCommit"]
   or q.get("scientific_first_use") is not False
   or q.get("scientific_accepted") is not False
   or q.get("actual_separate_real_action_interventions") is not True
   or q.get("not_an_R5_native_policy_comparison") is not True
   or q.get("future_common_BFS_continuation_uses_more_public_information") is not True
   or len(q.get("original_FIT_source_records",[]))!=12000
   or len(q.get("original_frozen_F7_FIT_source_digest",""))!=64
   or len(q.get("trained_sixfield_conventional_FIT_digest",""))!=64):
   raise ValueError("F8_UNQUALIFIED_GENUINE_INTERVENTION_"+label)
  rows=q["actual_paired_original_action_interventions"]
  if not rows:raise ValueError("F8_NO_ACTUAL_INTERVENTIONS_"+label)
  seen=set()
  for z in rows:
   key=(z["family"],z["seed"],z["anchor_tick"])
   if(z["family"] not in FAMILIES or z["seed"] not in DEV or
       z["anchor_tick"] not in ANCHORS or key in seen
       or set(z["original_source_real_arms"])!={"0","1","2"}
       or set(z["six_public_before"])!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"}
       or len(z["matched_anchor_public_sha256"])!=64):
    raise ValueError("F8_SOURCE_PREFIX_NOT_MATCHED_"+label)
   seen.add(key)
   for arm,trace in z["original_source_real_arms"].items():
    t=trace["actual_public_action_consequence_trace"]
    if(trace["intervened_action"]!=int(arm) or not t
       or t[0]["action"]!=int(arm) or
       any(step["action"] not in ACTIONS for step in t)
       or len(trace["trace_sha256"])!=64):
     raise ValueError("F8_REAL_ACTION_NOT_EXECUTED_"+label)
  for family in FAMILIES:
   if not any(row["family"]==family for row in rows):
    raise ValueError("F8_NO_FAMILY_INTERVENTION_"+label)
 same=stable(a)==stable(b)
 passed=same and all(q["result"]==p["acceptance"]["positive"] for q in (a,b))
 return {"schema":"mass.lcrm01.k4t-f8.independent-source-real-interventions-v1",
  "science_identical":same,
  "result":("REPEATABLE_BOUNDED_F8_PAIRED_INTERVENTION_GAIN_NO_NATIVE_CLAIM" if passed
     else "NO_REPEATABLE_F8_PAIRED_INTERVENTION_VALUE_ADVANCEMENT"),
  "source_A":a["result"],"source_B":b["result"],
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 parser=argparse.ArgumentParser()
 for name in ("first","second","output"):
  parser.add_argument("--"+name,type=Path,required=True)
 a=parser.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F8_NOT_FRESH_COMPARISON")
 r=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("K4T_F8_INDEPENDENT_RESULT="+r["result"])
 print("K4T_F8_EXACT_SCIENTIFIC_REPEAT="+str(r["science_identical"]))
 return int(not r["science_identical"])
if __name__=="__main__":raise SystemExit(main())
