#!/usr/bin/env python3
"""F5 exact two-independent-process authentic public evidence comparison."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f5_original_r6_edges import FROZEN,SCHEMA,FIT,CHECK,DEV,METHODS,FAMILIES,contract
from k4t_f4_compare import stable as prior_stable

def stable(q):
 r=prior_stable(q)
 if "native_FIT_custody" in r:
  d=dict(r["native_FIT_custody"])
  d.pop("R6_fit_wall_seconds",None)
  r["native_FIT_custody"]=d
 return r

def compare(a,b):
 c=contract()
 frozen_hash=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for name,q in (("A",a),("B",b)):
  if(q.get("schema")!=SCHEMA or q.get("gate")!="LCRM01-K4T-F5"
     or q.get("protocol_sha256")!=frozen_hash
     or q.get("result")!="COMPLETE_R6_GENUINE_PUBLIC_DEVELOPMENT"
     or q.get("source_minigrid_commit")!=c["sources"]["minigrid"]
     or q.get("original_Wingless_R6_blob")!=c["sources"]["r6_blob"]
     or q.get("FIT_public_experience_count")!=12000
     or len(q.get("FIT_original_public_experiences",[]))!=12000
     or any(x["seed"] not in FIT for x in q["FIT_original_public_experiences"])
     or q.get("old_K4Y_F1_F2_F3_F4_no_go_immutable") is not True
     or q.get("scientific_first_use") is not False
     or q.get("scientific_accepted") is not False
     or len(q.get("trained_sixfield_FIT_sha256",""))!=64):
   raise ValueError("F5_INCOMPLETE_FROZEN_ORIGINAL_SCIENCE_"+name)
  fit=q["native_FIT_custody"]
  if(fit.get("R5_true_cold_OS_process") is not True
     or fit.get("R6_true_cold_OS_process") is not True
     or fit.get("R5_FIT_original_native_updates")!=12000
     or fit.get("R6_FIT_original_native_updates")!=12000):
   raise ValueError("F5_NATIVE_COLD_FIT_CUSTODY_"+name)
  for phase,seeds in (("CHECK",CHECK),("DEV",DEV)):
   rows=q[phase+"_original_public_traces"]
   expected={(fam,seed,m):0 for fam in FAMILIES for seed in seeds for m in METHODS}
   if len(rows)!=len(expected):raise ValueError("F5_MISSING_ACTUAL_METHOD_EPISODE_"+name)
   for x in rows:
    key=(x["family"],x["seed"],x["method"])
    steps=x["actual_public_step_trace"]
    if(key not in expected or not steps or len(steps)>192 or
       len(x.get("trace_sha256",""))!=64 or
       any(y["a"] not in (0,1,2) for y in steps)):
     raise ValueError("F5_INVALID_AUTHENTIC_EPISODE_"+name)
    expected[key]+=1
   if any(v!=1 for v in expected.values()):
    raise ValueError("F5_UNEQUAL_REAL_WORLDS_"+name)
 equals=stable(a)==stable(b)
 positive=all(x["r6_preregistered_disposition"]["result"]==
    c["predicates"]["accept_label"] for x in (a,b))
 return {"schema":"mass.lcrm01.k4t-f5.independent-source-repeat-v1",
  "gate":"LCRM01-K4T-F5","science_identical":equals,
  "result":("REPEATABLE_BOUNDED_R6_PUBLIC_ROUTE_EFFICIENCY_SIGNAL_NOT_NOVELTY"
            if equals and positive else
            "NO_REPEATABLE_R6_PUBLIC_EMPIRICAL_ROUTE_EFFICIENCY_ADVANCEMENT"),
  "source_A":a["r6_preregistered_disposition"]["result"],
  "source_B":b["r6_preregistered_disposition"]["result"],
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 ap=argparse.ArgumentParser()
 for n in ("first","second","output"):ap.add_argument("--"+n,type=Path,required=True)
 a=ap.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F5_NONFRESH_COMPARISON")
 z=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(z,sort_keys=True,indent=2)+"\n")
 print("K4T_F5_INDEPENDENT_RESULT="+z["result"])
 print("K4T_F5_IDENTICAL_ORIGINAL_SCIENCE="+str(z["science_identical"]))
 return int(not z["science_identical"])
if __name__=="__main__":raise SystemExit(main())
