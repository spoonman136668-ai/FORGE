#!/usr/bin/env python3
"""Original independent OS process comparison of native R1/R2 first-use."""
import argparse
import hashlib
import json
from pathlib import Path
from k4y_native_affordance import FROZEN,SCHEMA,METHODS,FAMILIES

def stable(p):
 p={k:v for k,v in p.items() if k!="resources"}
 p.pop("shared_FIT_source_wall_seconds",None)
 if "native_FIT_custody" in p:
  o=dict(p["native_FIT_custody"])
  for key in ("shared_NATIVE_fit_wall_seconds","shared_Python_fit_CPU_seconds_excluding_Go"):
   o.pop(key,None)
  p["native_FIT_custody"]=o
 for name in ("CHECK_original_public_traces","DEV_original_public_traces"):
  if name in p:
   p[name]=[{k:v for k,v in r.items() if k not in
             ("episode_CPU_python_seconds","episode_wall_seconds")}
            for r in p[name]]
 return p

def compare(a,b):
 target=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 possible={"FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED",
           "COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION"}
 for label,r in (("A",a),("B",b)):
  if (r.get("schema")!=SCHEMA or r.get("gate")!="LCRM01-K4Y"
    or r.get("result") not in possible
    or r.get("source_minigrid_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d"
    or r.get("protocol_sha256")!=target
    or r.get("FIT_public_experience_count")!=12000
    or len(r.get("FIT_original_public_experiences",[]))!=12000
    or r.get("K4X_original_scientific_NO_GO_preserved") is not True
    or r.get("scientific_first_use") is not False
    or r.get("scientific_accepted") is not False):
   raise ValueError("K4Y_SOURCE_OR_NEGATIVE_IDENTITY_"+label)
  if r["result"]=="COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION":
   if (r.get("CHECK_episodes"),r.get("DEV_episodes"))!=(72,144) or
      len(r.get("CHECK_original_public_traces",[]))!=72 or
      len(r.get("DEV_original_public_traces",[]))!=144 or
      r.get("native_FIT_custody",{}).get("true_native_cold_restart") is not True
      or r.get("source_science",{}).get("scientific_accepted") is not False):
    raise ValueError("K4Y_ORIGINAL_HELDOUT_INCOMPLETE_"+label)
   for x in r["DEV_original_public_traces"]:
    actual=x["actual_public_step_trace"]
    if (not actual or len(actual)>192
       or x["seed"] not in range(13400,13408)
       or x["method"] not in METHODS
       or len(x["trace_sha256"])!=64):
     raise ValueError("K4Y_REAL_STEP_TRACE_CUSTODY_"+label)
  elif r.get("CHECK_episodes")!=0 or r.get("DEV_episodes")!=0:
   raise ValueError("K4Y_FIT_STOP_VIOLATED")
 a2=stable(a);b2=stable(b)
 eq=a2==b2
 negative=all(r["result"]=="COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION"
  and r["source_science"]["result"]=="BOTH_NATIVE_AFFORDANCES_GAIN_REAL_UNFAMILIAR_TRANSFER"
  for r in (a,b))
 return {"schema":"mass.lcrm01.k4y.original-cross-process-scientific-comparator.v1",
  "gate":"LCRM01-K4Y",
  "result":"REPEATED_PUBLIC_NATIVE_AFFORDANCE_TRANSFER_POSITIVE" if eq and negative
         else "NO_REPEATABLE_NATIVE_AFFORDANCE_TRANSFER_ADVANCEMENT",
  "exact_original_science_agreement":eq,
  "different_fields":sorted(k for k in set(a2)|set(b2) if a2.get(k)!=b2.get(k)),
  "source_A":a.get("source_science",{}).get("result",a["result"]),
  "source_B":b.get("source_science",{}).get("result",b["result"]),
  "two_fresh_Python_OS_processes_one_runner":True,
  "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise RuntimeError("K4Y_EXISTING_COMPARISON")
 r=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print("K4Y_CROSS_PROCESS="+r["result"])
 print("K4Y_SCIENCE_IDENTICAL="+str(r["exact_original_science_agreement"]))
 return int(not r["exact_original_science_agreement"])
if __name__=="__main__":
 raise SystemExit(main())
