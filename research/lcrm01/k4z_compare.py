#!/usr/bin/env python3
"""K4Z exact genuine original FIT+heldout native science comparison."""
import argparse,hashlib,json
from pathlib import Path
from k4z_episodic_navigation import PIN,SCHEMA,FAMILIES,METHODS

def stable(z):
 c={k:v for k,v in z.items() if k!="resources"}
 c.pop("FIT_shared_world_generation_wall_seconds",None)
 if "native_checkpoint_custody" in c:
  sub=dict(c["native_checkpoint_custody"])
  sub.pop("native_FIT_shared_wall_seconds",None)
  c["native_checkpoint_custody"]=sub
 for section in ("CHECK_original_traces","DEV_original_traces"):
  if section in c:
   c[section]=[{k:v for k,v in row.items() if k!="native_or_control_episode_wall_seconds"}
               for row in c[section]]
 return c

def compare(a,b):
 expected=hashlib.sha256(PIN.read_bytes()).hexdigest()
 allowed={"FIT_SOURCE_UNQUALIFIED_NO_HELDOUT_EXPOSURE",
          "COMPLETE_AUTHENTIC_PROSPECTIVE_EPISODIC_NAVIGATION"}
 for label,r in (("A",a),("B",b)):
  if (r.get("schema")!=SCHEMA
   or r.get("result") not in allowed
   or r.get("FIT_original_experience_count")!=12000
   or len(r.get("FIT_real_source",[]))!=12000
   or r.get("FIT_public_episodes",0)<48
   or r.get("protocol_sha256")!=expected
   or r.get("original_minigrid_source")!="7f5853792ea7f04f75614661006d87fcf949f26d"
   or r.get("native_source_original_R3_git_blob")!="5348238f4ec2183bea29262659883391b5f429fd"
   or r.get("prior_K4Y_scientific_NO_GO_preserved") is not True
   or r.get("scientific_first_use") is not False
   or r.get("scientific_accepted") is not False):
   raise ValueError("K4Z_ORIGINAL_SOURCE_OR_AUTHORITY_DRIFT_"+label)
  if r["result"]=="COMPLETE_AUTHENTIC_PROSPECTIVE_EPISODIC_NAVIGATION":
   if (r.get("CHECK_real_episodes"),r.get("DEV_real_episodes"))!=(56,112):
    raise ValueError("K4Z_REAL_WORLD_CONTROL_PARITY_"+label)
   if (len(r.get("CHECK_original_traces",[]))!=56 or
       len(r.get("DEV_original_traces",[]))!=112 or
       r.get("native_checkpoint_custody",{}).get("true_independent_OS_cold_restore") is not True or
       r.get("study_result",{}).get("scientific_accepted") is not False):
    raise ValueError("K4Z_NATIVE_RESTART_OR_TRACES_MISSING_"+label)
   for row in r["DEV_original_traces"]:
    trace=row["complete_public_action_trace"]
    if (not trace or row["steps"]!=len(trace) or
       row["seed"] not in range(19400,19408) or
       row["method"] not in METHODS or len(row["trace_sha256"])!=64):
     raise ValueError("K4Z_ORIGINAL_DEV_SOURCE_CORRUPT_"+label)
  elif r.get("CHECK_real_episodes")!=0 or r.get("DEV_real_episodes")!=0:
   raise ValueError("K4Z_PREHELDOUT_STOP_NOT_ENFORCED_"+label)
 aa=stable(a);bb=stable(b);same=aa==bb
 positive=(same and all(x["result"]=="COMPLETE_AUTHENTIC_PROSPECTIVE_EPISODIC_NAVIGATION"
  and x["study_result"]["result"]=="BOUNDED_NATIVE_EPISODIC_NAVIGATION_SOURCE_GAIN"
  for x in (a,b)))
 return {"schema":"mass.lcrm01.k4z.original-cross-process-science-v1",
 "result":"REPEATED_BOUNDED_NATIVE_EPISODIC_NAVIGATION_POSITIVE" if positive
          else "NO_REPEATABLE_NATIVE_EPISODIC_NAVIGATION_ADVANCEMENT",
 "exact_original_source_science_agreement":same,
 "different_scientific_fields":sorted(k for k in set(aa)|set(bb) if aa.get(k)!=bb.get(k)),
 "original_A":a.get("study_result",{}).get("result",a["result"]),
 "original_B":b.get("study_result",{}).get("result",b["result"]),
 "two_Python_OS_processes_one_runner":True,"scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):p.add_argument("--"+name,type=Path,required=True)
 o=p.parse_args()
 if o.output.exists() or not o.output.parent.is_dir():raise RuntimeError("K4Z_ORIGINAL_COMPARISON_ALREADY_EXISTS")
 r=compare(json.loads(o.first.read_text()),json.loads(o.second.read_text()))
 o.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print("K4Z_SOURCE_COMPARATOR="+r["result"])
 print("K4Z_IDENTICAL_ORIGINAL_SCIENCE="+str(r["exact_original_source_science_agreement"]))
 return int(not r["exact_original_source_science_agreement"])
if __name__=="__main__":raise SystemExit(main())
