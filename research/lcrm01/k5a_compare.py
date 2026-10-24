#!/usr/bin/env python3
"""K5A exact original-source science repeat; costs remain separately measured."""
import argparse,hashlib,json
from pathlib import Path
from k5a_crossing_transfer import PROTOCOL,SCHEMA,METHODS,TASKS,PHASES
TIMES=("policy_inference_wall_seconds","policy_online_adaptation_wall_seconds",
  "whole_python_episode_CPU_seconds","whole_episode_wall_seconds")

def stable(o):
 x={k:v for k,v in o.items() if k!="resources"}
 x.pop("FIT_shared_source_wall_seconds",None)
 if "native_FIT_custody" in x:
  z=dict(x["native_FIT_custody"])
  z.pop("native_FIT_shared_wall_seconds",None)
  x["native_FIT_custody"]=z
 for name in ("CHECK_full_original_public_action_traces",
              "DEV_full_original_public_action_traces"):
  if name in x:
   x[name]=[{k:v for k,v in r.items() if k not in TIMES} for r in x[name]]
 if "science" in x:
  c=dict(x["science"])
  c.pop("native_vs_online_measured_policy_wall_seconds",None)
  by={}
  for kind,methods in c["per_topology"].items():
   by[kind]={}
   for method,dat in methods.items():
    by[kind][method]={k:v for k,v in dat.items()
         if k not in ("total_policy_inference_seconds","total_online_adaptation_seconds")}
  c["per_topology"]=by
  x["science"]=c
 return x

def compare(a,b):
 expected=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
 for tag,r in (("A",a),("B",b)):
  if (r.get("schema")!=SCHEMA
      or r.get("result")!="COMPLETE_NEW_TOPOLOGY_NATIVE_ABLATION_STUDY"
      or r.get("protocol_sha256")!=expected
      or r.get("original_crossing_blob")!="f8c331e5e0e56b3b2a4a3b44dda8533bdabf4272"
      or r.get("original_R3_native_source_blob")!="5348238f4ec2183bea29262659883391b5f429fd"
      or r.get("FIT_real_events")!=12000
      or (r.get("CHECK_real_episodes"),r.get("DEV_real_episodes"))!=(64,128)
      or len(r.get("CHECK_full_original_public_action_traces",[]))!=64
      or len(r.get("DEV_full_original_public_action_traces",[]))!=128
      or r.get("original_K4Z_negative_and_bounded_positive_preserved") is not True
      or r.get("native_FIT_custody",{}).get("true_independent_OS_cold_restore") is not True
      or r.get("scientific_first_use") is not False
      or r.get("scientific_accepted") is not False
      or r.get("science",{}).get("scientific_accepted") is not False):
   raise ValueError("K5A_ORIGINAL_SOURCE_AND_EVALUATION_INVALID_"+tag)
  for kind,_ in TASKS:
   for method in METHODS:
    sample=[z for z in r["DEV_full_original_public_action_traces"] if z["kind"]==kind and z["policy"]==method]
    if sorted(z["seed"] for z in sample)!=list(PHASES["DEV"]):
     raise ValueError("K5A_WRONG_FRESH_DEV_COHORT_"+tag)
    for x in sample:
     if (len(x["actual_public_action_consequence_trace"])!=x["steps"]
      or not 1<=x["steps"]<=192
      or len(x["trace_sha256"])!=64):
      raise ValueError("K5A_MISSING_ORIGINAL_PUBLIC_ACTION_TRACE_"+tag)
 aa=stable(a);bb=stable(b)
 same=aa==bb
 s=a["science"]["disposition"]
 positive=(same and s=="BOUNDED_UNFAMILIAR_CROSSING_TOPOLOGY_TRANSFER"
   and b["science"]["disposition"]==s)
 return {"schema":"mass.lcrm01.k5a.original-two-process-transfer-comparison-v1",
   "result":"REPEATED_BOUNDED_CROSSING_TOPOLOGY_TRANSFER" if positive
      else "NO_REPEATABLE_BOUNDED_NATIVE_TRANSFER_ADVANCEMENT",
   "exact_original_science_agreement":same,
   "different_fields":sorted(k for k in set(aa)|set(bb) if aa.get(k)!=bb.get(k)),
   "source_A_disposition":s,"source_B_disposition":b["science"]["disposition"],
   "two_original_Python_OS_processes_one_runner":True,
   "native_novelty_established":False,
   "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for n in ("first","second","output"):p.add_argument("--"+n,required=True,type=Path)
 q=p.parse_args()
 if q.output.exists() or not q.output.parent.is_dir():raise RuntimeError("K5A_COMPARISON_OVERWRITE_DENIED")
 v=compare(json.loads(q.first.read_text()),json.loads(q.second.read_text()))
 q.output.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
 print("K5A_SOURCE_SCIE_REPETITION="+v["result"])
 print("K5A_SCIENTIFIC_IDENTICAL="+str(v["exact_original_science_agreement"]))
 return int(not v["exact_original_science_agreement"])
if __name__=="__main__":raise SystemExit(main())
