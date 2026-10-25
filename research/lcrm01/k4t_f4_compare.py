#!/usr/bin/env python3
"""F3 independent authentic source full public episode trace comparator."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f4_original_r5_cost import FROZEN,SCHEMA,FIT,CHECK,DEV,METHODS,FAMILIES,contract
from k4y_compare import stable as stable_f2

def stable(q):
 q=stable_f2(q)
 if "native_FIT_custody" in q:
  x=dict(q["native_FIT_custody"])
  for key in ("R3_fit_wall_seconds","R4_fit_wall_seconds","R5_fit_wall_seconds"):
   x.pop(key,None)
  q["native_FIT_custody"]=x
 return q

def compare(a,b):
 freeze=contract()
 digest=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for label,q in (("A",a),("B",b)):
  if(q.get("schema")!=SCHEMA or q.get("gate")!="LCRM01-K4T-F4"
     or q.get("result") not in ("FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED",
                              "COMPLETE_R5_ORIGINAL_SOURCE_PUBLIC_DEVELOPMENT")
     or q.get("protocol_sha256")!=digest
     or q.get("source_minigrid_commit")!=freeze["original"]["minigrid_commit"]
     or q.get("Wingless_R5_source_blob")!=freeze["original"]["Wingless_R5_blob"]
     or q.get("FIT_public_experience_count")!=12000
     or len(q.get("FIT_original_public_experiences",[]))!=12000
     or any(x["seed"] not in FIT for x in q["FIT_original_public_experiences"])
     or q.get("old_K4Y_F1_F2_F3_no_go_preserved") is not True
     or q.get("scientific_first_use") is not False or
        q.get("scientific_accepted") is not False):
   raise ValueError("K4T_F4_INVALID_FROZEN_SOURCE_"+label)
  if q["result"]=="COMPLETE_R5_ORIGINAL_SOURCE_PUBLIC_DEVELOPMENT":
   fit=q["native_FIT_custody"]
   if(q.get("CHECK_episodes")!=112 or q.get("DEV_episodes")!=224 or
      len(q.get("CHECK_original_public_traces",[]))!=112 or
      len(q.get("DEV_original_public_traces",[]))!=224 or
      fit.get("R4_true_cold_OS_process") is not True or
      fit.get("R5_true_cold_OS_process") is not True or
      fit.get("R4_FIT_original_native_updates")!=12000 or
      fit.get("R5_FIT_original_native_updates")!=12000 or
      len(q.get("sixfield_FIT_trained_model_sha256",""))!=64 or
      q["r5_preregistered_disposition"].get("scientific_accepted") is not False):
    raise ValueError("K4T_F4_REAL_NATIVE_AND_CONVENTIONAL_CUSTODY_"+label)
   for name,seeds in (("CHECK",CHECK),("DEV",DEV)):
    rows=q[name+"_original_public_traces"]
    expect={(f,seed,m):0 for f in FAMILIES for seed in seeds for m in METHODS}
    for row in rows:
     key=(row["family"],row["seed"],row["method"])
     trace=row["actual_public_step_trace"]
     if(key not in expect or not trace or len(trace)>192 or
        len(row["trace_sha256"])!=64 or any(s["a"] not in (0,1,2) for s in trace)):
      raise ValueError("K4T_F4_ILLEGAL_REAL_PUBLIC_STEP_"+label)
     expect[key]+=1
    if any(n!=1 for n in expect.values()):
     raise ValueError("K4T_F4_WORLD_AND_METHOD_PARITY_"+label)
  elif q.get("CHECK_episodes") or q.get("DEV_episodes"):
   raise ValueError("K4T_F4_UNQUALIFIED_FIT_EXPOSED_EVALUATION_"+label)
 equal=stable(a)==stable(b)
 success=all(q.get("r5_preregistered_disposition",{}).get("result")==
             freeze["registered_decision"]["development_GO"] for q in (a,b))
 return {"schema":"mass.lcrm01.k4t-f4.independent-original-source-dev-repeat.v1",
         "gate":"LCRM01-K4T-F4",
         "science_identical":equal,
         "result":("TWO_PROCESS_BOUNDED_R5_COST_PUBLIC_DEV_SIGNAL_NOT_NOVELTY"
                   if equal and success else
                   "NO_REPEATABLE_R5_COST_AWARE_NAVIGATION_ADVANCEMENT"),
         "source_A":a.get("r5_preregistered_disposition",{}).get("result",a["result"]),
         "source_B":b.get("r5_preregistered_disposition",{}).get("result",b["result"]),
         "scientific_first_use":False,"scientific_accepted":False}

def main():
 ap=argparse.ArgumentParser()
 for name in ("first","second","output"):ap.add_argument("--"+name,required=True,type=Path)
 a=ap.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise ValueError("K4T_F4_NONFRESH_COMPARATOR")
 v=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
 print("K4T_F4_INDEPENDENT_RESULT="+v["result"])
 print("K4T_F4_EXACT_SCIENCE_AGREEMENT="+str(v["science_identical"]))
 return int(not v["science_identical"])
if __name__=="__main__":raise SystemExit(main())
