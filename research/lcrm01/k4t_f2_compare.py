#!/usr/bin/env python3
"""F2 source-bound independent-process scientific comparison, no world execution."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f2_r3_original_public import (
 FROZEN, SCHEMA, FIT, CHECK, DEV, METHODS, FAMILIES, contract)
from k4y_compare import stable as k4y_stable

def science(p):
 q=k4y_stable(p)
 if "native_FIT_custody" in q:
  v=dict(q["native_FIT_custody"])
  v.pop("R3_fit_wall_seconds",None)
  q["native_FIT_custody"]=v
 return q

def compare(a,b):
 p=contract()
 digest=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for label,q in (("A",a),("B",b)):
  if(q.get("schema")!=SCHEMA or q.get("gate")!="LCRM01-K4T-F2"
     or q.get("result") not in
        ("FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED",
         "COMPLETE_R3_ORIGINAL_SOURCE_PUBLIC_DEVELOPMENT")
     or q.get("protocol_sha256")!=digest
     or q.get("source_minigrid_commit")!=p["original_sources"]["minigrid_upstream"]
     or q.get("source_Wingless_R3_blob")!=p["original_sources"]["original_Wingless_R3_blob"]
     or q.get("FIT_public_experience_count")!=12000
     or len(q.get("FIT_original_public_experiences",[]))!=12000
     or q.get("historical_K4T_F1_and_K4Y_negatives_unchanged") is not True
     or q.get("scientific_first_use") is not False
     or q.get("scientific_accepted") is not False):
   raise ValueError("K4T_F2_UNQUALIFIED_OR_INCOMPLETE_ORIGINAL_"+label)
  if any(x["seed"] not in FIT for x in q["FIT_original_public_experiences"]):
   raise ValueError("K4T_F2_FIT_SOURCE_IDENTITY_DRIFT_"+label)
  if q["result"]=="COMPLETE_R3_ORIGINAL_SOURCE_PUBLIC_DEVELOPMENT":
   if(q.get("CHECK_episodes")!=88 or q.get("DEV_episodes")!=176
      or len(q.get("CHECK_original_public_traces",[]))!=88
      or len(q.get("DEV_original_public_traces",[]))!=176
      or q.get("native_FIT_custody",{}).get("true_native_cold_restart") is not True
      or q["native_FIT_custody"].get("R3_authentic_cold_OS_restore") is not True
      or q["native_FIT_custody"].get("FIT_original_native_R3_completed_updates")!=12000
      or q["r3_preregistered_disposition"]["scientific_accepted"] is not False):
    raise ValueError("K4T_F2_NATIVE_RESTORE_OR_REAL_WORLD_INCOMPLETE_"+label)
   for phase,seeds in (("CHECK",CHECK),("DEV",DEV)):
    rows=q[phase+"_original_public_traces"]
    seen={(f,seed,m):0 for f in FAMILIES for seed in seeds for m in METHODS}
    for x in rows:
     steps=x["actual_public_step_trace"]
     key=(x["family"],x["seed"],x["method"])
     if(key not in seen or not steps or len(steps)>192 or
        len(x["trace_sha256"])!=64 or
        any(y["a"] not in (0,1,2) for y in steps)):
      raise ValueError("K4T_F2_INVALID_AUTHENTIC_TRACE_"+label)
     seen[key]+=1
    if any(v!=1 for v in seen.values()):
     raise ValueError("K4T_F2_UNEQUAL_WORLD_COMPARISON_"+label)
  elif q.get("CHECK_episodes") or q.get("DEV_episodes"):
   raise ValueError("K4T_F2_EVALUATION_AFTER_FIT_FAILURE_"+label)
 equal=science(a)==science(b)
 good=all(q.get("r3_preregistered_disposition",{}).get("result")==
          "BOUNDED_R3_ACTION_MODEL_GOAL_DEVELOPMENT_GAIN_NOT_NOVELTY"
          for q in (a,b))
 return {"schema":"mass.lcrm01.k4t-f2.r3-independent-real-source-comparison.v1",
         "gate":"LCRM01-K4T-F2","exact_original_science_agreement":equal,
         "result":("REPEATABLE_R3_NAVIGATION_DEVELOPMENT_GAIN_ONLY"
                   if equal and good else "NO_REPEATABLE_R3_MODEL_NAVIGATION_ADVANCEMENT"),
         "source_A":a.get("r3_preregistered_disposition",{}).get("result",a["result"]),
         "source_B":b.get("r3_preregistered_disposition",{}).get("result",b["result"]),
         "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for n in ("first","second","output"):p.add_argument("--"+n,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("K4T_F2_NONFRESH_COMPARATOR")
 result=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("K4T_F2_INDEPENDENT_RESULT="+result["result"])
 print("K4T_F2_EXACT_SCIENCE_AGREEMENT="+str(result["exact_original_science_agreement"]))
 return int(not result["exact_original_science_agreement"])
if __name__=="__main__":raise SystemExit(main())
