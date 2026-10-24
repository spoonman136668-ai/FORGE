#!/usr/bin/env python3
"""K4X exact original cross-process native curriculum comparison.

Fail closed on original public reward/action sequence divergence. Separate
process timing from source observations and frozen learner dispositions.
"""
import argparse,hashlib,json
from pathlib import Path
from k4x_curriculum_intervention import FROZEN,SCHEMA,CURRICULA,FAMILIES,METHODS

def science_only(report):
 out={k:v for k,v in report.items() if k!="resources"}
 if "FIT" in out:
  new={}
  for regimen,original in out["FIT"].items():
   item=dict(original)
   item.pop("FIT_shared_public_world_wall_seconds",None)
   if "native_source_training" in item:
    info=dict(item["native_source_training"])
    info.pop("total_native_fit_wall_seconds",None)
    info.pop("total_shared_native_fit_python_cpu_seconds",None)
    item["native_source_training"]=info
   new[regimen]=item
  out["FIT"]=new
 for phase in ("CHECK_original_public_traces","DEV_original_public_traces"):
  if phase in out:
   out[phase]=[{k:v for k,v in x.items() if k not in
          ("eval_python_CPU_seconds","eval_wall_seconds")} for x in out[phase]]
 return out

def compare(a,b):
 hashv=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 outcomes={"ORIGINAL_FIT_SOURCE_INSUFFICIENT_HOLDOUT_UNCONSUMED",
           "ORIGINAL_EXPERT_CURRICULUM_INTERVENTION_COMPLETE"}
 for name,r in (("A",a),("B",b)):
  if (r.get("schema")!=SCHEMA or r.get("gate")!="LCRM01-K4X" or
     r.get("result") not in outcomes or
     r.get("source_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d" or
     r.get("wingless_commit")!="cd108800054e7964af845137f0d9d37fae69f5a7" or
     r.get("yggdrasil_commit")!="1b042d6bf4832d885d80ef73f3ab29d8a600bfe2" or
     r.get("protocol_sha256")!=hashv or
     r.get("prior_K4U_NO_GO_preserved") is not True or
     r.get("scientific_first_use") is not False or
     r.get("scientific_accepted") is not False):
   raise ValueError("K4X_SCIENTIFIC_SOURCE_IDENTITY_OR_AUTHORITY_DRIFT_"+name)
  for c in CURRICULA:
   fit=r.get("FIT",{}).get(c,{})
   if (len(fit.get("fit_stream",[]))!=12000 or
       fit.get("FIT_source_gate",{}).get("qualified") is not True or
       any(fit.get("source_balance",{}).get(f,{}).get("public_steps")!=6000
           for f in FAMILIES)):
    if r["result"]!="ORIGINAL_FIT_SOURCE_INSUFFICIENT_HOLDOUT_UNCONSUMED":
     raise ValueError("K4X_WRONG_SOURCE_EXPERIENCE_COUNT_"+name)
  if r["result"]=="ORIGINAL_EXPERT_CURRICULUM_INTERVENTION_COMPLETE":
   if (r.get("CHECK_episodes")!=88 or r.get("DEV_episodes")!=176 or
       len(r.get("CHECK_original_public_traces",[]))!=88 or
       len(r.get("DEV_original_public_traces",[]))!=176 or
       r.get("native_curriculum_disposition",{}).get("scientific_accepted") is not False):
    raise ValueError("K4X_HELDOUT_TRACES_NOT_COMPLETE_"+name)
   for x in r["DEV_original_public_traces"]:
    if (not x.get("actual_public_action_trace") or
       len(x["actual_public_action_trace"])!=x["steps"] or
       x.get("policy") not in METHODS or x.get("seed") not in range(9300,9308)):
     raise ValueError("K4X_REAL_ACTION_TRACE_MISSING_"+name)
  elif (r.get("CHECK_episodes")!=0 or r.get("DEV_episodes")!=0
      or "DEV_original_public_traces" in r):
   raise ValueError("K4X_UNQUALIFIED_FIT_MUST_STOP_"+name)
 left=science_only(a);right=science_only(b)
 identical=left==right
 diff=sorted(k for k in set(left)|set(right) if left.get(k)!=right.get(k))
 positive=identical and all(
    x["result"]=="ORIGINAL_EXPERT_CURRICULUM_INTERVENTION_COMPLETE" and
    x["native_curriculum_disposition"]["result"]=="EXPERT_CURRICULUM_BOUNDED_NATIVE_SOURCE_GAIN"
    for x in (a,b))
 return {"schema":"mass.lcrm01.k4x.original-scientific-source-comparator.v1",
   "gate":"LCRM01-K4X",
   "result":"REPEATED_PUBLIC_CURRICULUM_DEPENDENCE_BOUNDED_POSITIVE" if positive
            else "NO_REPEATABLE_BOUNDED_NATIVE_CURRICULUM_SOURCE_GAIN",
   "exact_original_science_agreement":identical,"differing_fields":diff,
   "a_result":a.get("native_curriculum_disposition",{}).get("result",a["result"]),
   "b_result":b.get("native_curriculum_disposition",{}).get("result",b["result"]),
   "two_processes_one_host":True,"scientific_first_use":False,
   "scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--first",type=Path,required=True)
 p.add_argument("--second",type=Path,required=True)
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise RuntimeError("K4X_ORIGINAL_COMPARISON_OVERWRITE_DENIED")
 r=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print("K4X_INDEPENDENT_PROCESS_STUDY="+r["result"])
 print("K4X_EXACT_ORIGINAL_SCIENCE="+str(r["exact_original_science_agreement"]))
 return int(not r["exact_original_science_agreement"])

if __name__=="__main__":
 raise SystemExit(main())
