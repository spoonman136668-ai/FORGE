#!/usr/bin/env python3
"""F10 independently process-repeated true original-state action-exposure audit."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f10_public_history import FROZEN,SCHEMA,FIT,DEV,ANCHORS,HISTORY,ACTIONS,frozen

def stable(x):
 v=dict(x)
 v.pop("resources",None)
 return v
def compare(a,b):
 p=frozen();fingerprint=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for label,v in (("A",a),("B",b)):
  if(v.get("schema")!=SCHEMA or v.get("gate")!="LCRM01-K4T-F10"
   or v.get("result") not in (p["acceptance"]["positive"],p["acceptance"]["noGo"])
   or v.get("protocol_sha256")!=fingerprint
   or v.get("original_source_commit")!=p["source"]["minigridCommit"]
   or v.get("scientific_first_use") is not False
   or v.get("scientific_accepted") is not False
   or v.get("native_R5_untouched") is not True
   or v.get("more_informed_original_BFS_continuation") is not True
   or v.get("true_alternative_actions_actually_executed") is not True):
   raise ValueError("F10_SOURCE_SCIENCE_CUSTODY_"+label)
  for part,allowed in (("FIT",FIT),("DEV",DEV)):
   key="true_randomized_FIT_episodes" if part=="FIT" else "true_randomized_fresh_DEV_episodes"
   cohort=v[key]
   seen=set()
   for row in cohort:
    k=(row["seed"],row["anchor_tick"])
    if(row["seed"] not in allowed or row["anchor_tick"] not in ANCHORS or
       row["family"]!="fourrooms" or k in seen or
       set(row["six_public_before"])!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"} or
       set(row["true_original_interventions"])!={"0","1","2"} or
       len(row["matched_anchor_public_sha256"])!=64 or
       len(row["recent_public_history"])!=HISTORY):
     raise ValueError("F10_REAL_SOURCE_UNMATCHED_OR_LEAKED_"+label)
    seen.add(k)
    for action in ACTIONS:
     trial=row["true_original_interventions"][str(action)]
     events=trial["actual_public_action_consequence_trace"]
     if(not events or trial["intervened_action"]!=action or
       events[0]["action"]!=action or len(trial["trace_sha256"])!=64):
      raise ValueError("F10_ACTION_BRANCH_NOT_REAL_"+label)
     if any(e["action"] not in ACTIONS for e in events):
      raise ValueError("F10_ILLEGAL_SOURCE_ACTION_"+label)
   if not cohort:raise ValueError("F10_NO_ORIGINAL_SOURCE_FAMILY_"+label)
  if(v["all_models_same_true_three_arm_source_FIT_count"]!=
     3*len(v["true_randomized_FIT_episodes"])):
   raise ValueError("F10_UNEQUAL_MODEL_EXPOSURE_"+label)
 same=stable(a)==stable(b)
 qualify=same and all(x["result"]==p["acceptance"]["positive"] for x in (a,b))
 return {"schema":"mass.lcrm01.k4t-f10.two-independent-original-processes-v1",
  "gate":"LCRM01-K4T-F10","science_identical":same,
  "result":("REPEATED_BOUNDED_F10_PUBLIC_HISTORY_DEV_SIGNAL_NOT_NATIVE_R5" if qualify
            else "NO_REPEATABLE_F10_PUBLIC_HISTORY_INFORMATION_GAIN"),
  "source_A":a["result"],"source_B":b["result"],
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 pa=argparse.ArgumentParser()
 for name in ("first","second","output"):
  pa.add_argument("--"+name,required=True,type=Path)
 a=pa.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F10_NONFRESH_REPRO_RESULT")
 x=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(x,sort_keys=True,indent=2)+"\n")
 print("K4T_F10_INDEPENDENT_SCIENTIFIC_RESULT="+x["result"])
 print("K4T_F10_EXACT_ORIGINAL_SOURCE_AGREEMENT="+str(x["science_identical"]))
 return int(not x["science_identical"])
if __name__=="__main__":raise SystemExit(main())
