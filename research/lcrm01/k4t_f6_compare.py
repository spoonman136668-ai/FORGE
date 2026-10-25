#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f6_original_r7_physical import FROZEN,SCHEMA,FIT,CHECK,DEV,METHODS,FAMILIES,contract
from k4t_f5_compare import stable as previous_stable
def stable(x):
 r=previous_stable(x)
 if "native_FIT_custody" in r:
  z=dict(r["native_FIT_custody"])
  z.pop("R7_fit_wall_seconds",None)
  r["native_FIT_custody"]=z
 return r
def compare(a,b):
 frozen=contract()
 hashval=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for name,x in (("A",a),("B",b)):
  if(x.get("schema")!=SCHEMA or x.get("gate")!="LCRM01-K4T-F6"
     or x.get("protocol_sha256")!=hashval
     or x.get("result")!="COMPLETE_R7_GENUINE_PUBLIC_DEVELOPMENT"
     or x.get("source_minigrid_commit")!=frozen["source"]["minigrid"]
     or x.get("original_Wingless_R7_blob")!=frozen["source"]["Wingless_R7_code"]
     or x.get("FIT_public_experience_count")!=12000
     or len(x.get("FIT_original_public_experiences",[]))!=12000
     or any(s["seed"] not in FIT for s in x["FIT_original_public_experiences"])
     or x.get("old_K4Y_F1_F2_F3_F4_F5_no_go_immutable") is not True
     or x.get("scientific_first_use") is not False
     or x.get("scientific_accepted") is not False):
   raise ValueError("F6_FROZEN_ORIGINAL_SOURCE_"+name)
  info=x["native_FIT_custody"]
  for method in ("R5","R6","R7"):
   if(info.get(method+"_true_cold_OS_process") is not True or
      info.get(method+"_FIT_original_native_updates")!=12000):
    raise ValueError("F6_NATIVE_COLD_MODEL_"+method+"_"+name)
  for phase,seeds in (("CHECK",CHECK),("DEV",DEV)):
   rows=x[phase+"_original_public_traces"]
   expect={(fam,seed,method):0 for fam in FAMILIES for seed in seeds for method in METHODS}
   if len(rows)!=len(expect):raise ValueError("F6_REAL_METHOD_COUNT_"+name)
   for row in rows:
    key=(row["family"],row["seed"],row["method"])
    steps=row["actual_public_step_trace"]
    if (key not in expect or len(steps)<1 or len(steps)>192 or
       len(row.get("trace_sha256",""))!=64 or
       any(step["a"] not in (0,1,2) for step in steps)):
     raise ValueError("F6_INCOMPLETE_AUTHENTIC_SOURCE_TRACE_"+name)
    expect[key]+=1
   if any(n!=1 for n in expect.values()):
    raise ValueError("F6_WORLD_PARITY_"+name)
 identical=stable(a)==stable(b)
 good=all(z["r7_preregistered_disposition"]["result"]==frozen["predicates"]["accept"] for z in (a,b))
 return {"schema":"mass.lcrm01.k4t-f6.independent-source-repeat-v1",
         "gate":"LCRM01-K4T-F6","science_identical":identical,
         "result":("REPEATABLE_BOUNDED_R7_PHYSICAL_PUBLIC_DEV_SIGNAL_NOT_NOVELTY"
                   if good and identical else "NO_REPEATABLE_R7_PHYSICAL_ROUTE_ADVANCEMENT"),
         "source_A":a["r7_preregistered_disposition"]["result"],
         "source_B":b["r7_preregistered_disposition"]["result"],
         "scientific_first_use":False,"scientific_accepted":False}
def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F6_NONFRESH_COMPARATOR")
 v=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
 print("K4T_F6_INDEPENDENT_RESULT="+v["result"])
 print("K4T_F6_SCIENCE_IDENTICAL="+str(v["science_identical"]))
 return int(not v["science_identical"])
if __name__=="__main__":raise SystemExit(main())
