#!/usr/bin/env python3
"""K5C scientific two-process original physical concurrent memory comparator."""
import argparse,hashlib,json
from pathlib import Path
from k5c_concurrent_memory_trial import PIN,SCHEMA,SIZES,CAPACITIES,METHODS,COHORTS

def stable(obj):
 result={k:v for k,v in obj.items() if k!="resources"}
 for name in ("FIT_original_real_tasks","CHECK_full_original_action_traces",
              "DEV_full_original_action_traces"):
  if name in result:
   result[name]=[{k:v for k,v in row.items() if k not in
         ("decision_only_wall_seconds","elapsed_group_wall_seconds")}
          for row in result[name]]
 if "scientific" in result:
  c=dict(result["scientific"]);items={}
  for sz,caps in c["per_size_capacity_method"].items():
   items[sz]={}
   for cap,methods in caps.items():
    items[sz][cap]={}
    for name,dat in methods.items():
     items[sz][cap][name]={k:v for k,v in dat.items() if k!="decision_inference_seconds"}
  c["per_size_capacity_method"]=items
  result["scientific"]=c
 return result

def compare(a,b):
 protohash=hashlib.sha256(PIN.read_bytes()).hexdigest()
 accepted=("COMPLETE_ORIGINAL_CONCURRENT_CUE_INTERFERENCE_STUDY",
           "FIT_SOURCE_UNQUALIFIED_HOLDOUT_NOT_CONSUMED")
 for label,p in (("A",a),("B",b)):
  if (p.get("schema")!=SCHEMA or p.get("result") not in accepted
      or p.get("protocol_sha256")!=protohash
      or p.get("original_MemoryEnv_blob")!="660b0a1b769948034c87bb421759c2b9a4f24548"
      or p.get("original_R5_native_blob")!="4182889a47e31391a95ea3a2f5d8a4b87bcd6359"
      or p.get("prior_K5B_science_immutable") is not True
      or p.get("FIT_authentic_physical_episodes")!=128
      or len(p.get("FIT_original_real_tasks",[]))!=128
      or p.get("scientific_first_use") is not False
      or p.get("scientific_accepted") is not False):
   raise ValueError("K5C_FROZEN_ORIGINAL_SOURCE_DRIFT_"+label)
  if p["result"]=="COMPLETE_ORIGINAL_CONCURRENT_CUE_INTERFERENCE_STUDY":
   if (p.get("CHECK_original_episodes"),p.get("DEV_original_episodes"))!=(384,1536):
    raise ValueError("K5C_INCOMPLETE_CONCURRENT_EPISODES_"+label)
   if (len(p.get("CHECK_full_original_action_traces",[]))!=384
       or len(p.get("DEV_full_original_action_traces",[]))!=1536
       or p.get("original_R5_cold_OS_restore") is not True
       or p.get("scientific",{}).get("scientific_accepted") is not False):
    raise ValueError("K5C_NATIVE_COLD_OR_ACTION_TRACES_MISSING_"+label)
   for sz in SIZES:
    for cap in CAPACITIES:
     for name in METHODS:
      xs=[z for z in p["DEV_full_original_action_traces"]
          if z["size"]==sz and z["capacity"]==cap and z["policy"]==name]
      if sorted(z["seed"] for z in xs)!=list(COHORTS["DEV"]):
       raise ValueError("K5C_NONMATCHED_DEVELOPMENT_SEED_"+label)
      if any(not x["actual_public_step_trace"] or
        len(x["actual_public_step_trace"])!=x["physical_steps"] or
        len(x["trace_sha256"])!=64 or not isinstance(x["real_goal_success"],bool)
        for x in xs):
       raise ValueError("K5C_FALSE_OR_MISSING_PHYSICAL_OUTCOME_"+label)
  elif p.get("CHECK_original_episodes")!=0 or p.get("DEV_original_episodes")!=0:
   raise ValueError("K5C_FIT_STOP_WOULD_CONSUME_HELDOUT")
 aa=stable(a);bb=stable(b);same=aa==bb
 positive=(same and a["result"]==accepted[0] and b["result"]==accepted[0] and
  a["scientific"]["result"]=="BOUNDED_CONCURRENT_EPISODIC_CUE_BINDING" and
  b["scientific"]["result"]==a["scientific"]["result"])
 return {"schema":"mass.lcrm01.k5c.original-concurrent-memory-repeated-v1",
     "result":"REPEATED_BOUNDED_NATIVE_CONCURRENT_CUE_BINDING" if positive
       else "NO_REPEATABLE_NATIVE_CONCURRENT_MEMORY_ADVANCEMENT",
     "original_physical_science_identical":same,
     "different_scientific_fields":sorted(k for k in set(aa)|set(bb)
                                        if aa.get(k)!=bb.get(k)),
     "source_A":a.get("scientific",{}).get("result",a["result"]),
     "source_B":b.get("scientific",{}).get("result",b["result"]),
     "native_superiority_over_dictionary":False,
     "autonomous_planning_claim":False,"two_OS_processes_one_host":True,
     "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for n in ("first","second","output"):p.add_argument("--"+n,required=True,type=Path)
 x=p.parse_args()
 if x.output.exists() or not x.output.parent.is_dir():raise RuntimeError("K5C_RECEIPT_EXISTS")
 y=compare(json.loads(x.first.read_text()),json.loads(x.second.read_text()))
 x.output.write_text(json.dumps(y,sort_keys=True,indent=2)+"\n")
 print("K5C_REPEATED_ORIGINAL="+y["result"])
 print("K5C_EXACT_PHYSICAL_SCIENCE="+str(y["original_physical_science_identical"]))
 return int(not y["original_physical_science_identical"])
if __name__=="__main__":raise SystemExit(main())
