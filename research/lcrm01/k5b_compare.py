#!/usr/bin/env python3
"""K5B original unchanged source science across two fresh Python OS processes."""
import argparse,hashlib,json
from pathlib import Path
from k5b_memory_trial import PIN,SCHEMA,SIZE,PHASES,METHODS

def stable(r):
 s={k:v for k,v in r.items() if k!="resources"}
 for name in ("FIT","CHECK_full_actual_action_traces","DEV_full_actual_action_traces"):
  if name in s:
   s[name]=[{k:v for k,v in row.items() if k!="whole_episode_wall_seconds"}
       for row in s[name]]
 return s

def compare(a,b):
 h=hashlib.sha256(PIN.read_bytes()).hexdigest()
 for label,p in (("A",a),("B",b)):
  if (p.get("schema")!=SCHEMA
    or p.get("result") not in ("COMPLETE_ORIGINAL_DELAYED_CUE_MEMORY_EXPERIMENT",
         "K5B_FIT_INFORMATION_INSUFFICIENT_HOLDOUT_NOT_CONSUMED")
    or p.get("protocol_sha256")!=h
    or p.get("original_MemoryEnv_git_blob")!="660b0a1b769948034c87bb421759c2b9a4f24548"
    or p.get("original_native_R4_git_blob")!="bb8747e225335affe0e23f57e3c5d692a25bf473"
    or p.get("prior_K5A_no_novelty_preserved") is not True
    or len(p.get("FIT",[]))!=128
    or p.get("scientific_first_use") is not False
    or p.get("scientific_accepted") is not False):
   raise ValueError("K5B_FROZEN_FIRST_USE_SOURCE_DRIFT_"+label)
  if p["result"]=="COMPLETE_ORIGINAL_DELAYED_CUE_MEMORY_EXPERIMENT":
   if (p.get("CHECK_real_episodes"),p.get("DEV_real_episodes"))!=(80,160) or
       len(p.get("CHECK_full_actual_action_traces",[]))!=80 or
       len(p.get("DEV_full_actual_action_traces",[]))!=160 or
       p.get("native_original_cold_OS_restore") is not True or
       p.get("scientific",{}).get("scientific_accepted") is not False):
    raise ValueError("K5B_HELDOUT_CUSTODY_INCOMPLETE_"+label)
   for n in p["DEV_full_actual_action_traces"]:
    if (n["size"] not in SIZE or n["policy"] not in METHODS
      or n["seed"] not in PHASES["DEV"] or
      len(n["actual_public_action_trace"])!=n["physical_step_count"] or
      not 1<=n["physical_step_count"]<=250
      or len(n["trace_sha256"])!=64):
     raise ValueError("K5B_ORIGINAL_TERMINAL_EPISODE_MISSING_"+label)
  elif (p.get("CHECK_real_episodes")!=0 or p.get("DEV_real_episodes")!=0):
   raise ValueError("K5B_FIT_FAIL_CANNOT_CONSUME_HELDOUT_"+label)
 aa=stable(a);bb=stable(b);same=aa==bb
 positive=(same and a["result"]=="COMPLETE_ORIGINAL_DELAYED_CUE_MEMORY_EXPERIMENT"
    and b["result"]==a["result"] and
    a["scientific"]["result"]=="BOUNDED_NATIVE_DELAYED_CUE_RETENTION"
    and b["scientific"]["result"]==a["scientific"]["result"])
 return {"schema":"mass.lcrm01.k5b.original-source-repeated-memory-decision-v1",
 "result":"REPEATED_BOUNDED_CUE_MEMORY_SOURCE_GAIN" if positive
    else "NO_REPEATABLE_NATIVE_CUE_MEMORY_ADVANCEMENT",
 "original_scientific_outcomes_identical":same,
 "differing_scientific_fields":sorted(k for k in set(aa)|set(bb) if aa.get(k)!=bb.get(k)),
 "source_A_disposition":a.get("scientific",{}).get("result",a["result"]),
 "source_B_disposition":b.get("scientific",{}).get("result",b["result"]),
 "two_fresh_OS_processes_one_host":True,
 "native_superior_to_one_bit_conventional":False,
 "autonomous_navigation_demonstrated":False,
 "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):p.add_argument("--"+name,type=Path,required=True)
 q=p.parse_args()
 if q.output.exists() or not q.output.parent.is_dir():
  raise RuntimeError("K5B_ORIGINAL_OUTPUT_ALREADY_EXISTS")
 r=compare(json.loads(q.first.read_text()),json.loads(q.second.read_text()))
 q.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print("K5B_REPEATED_SOURCE="+r["result"])
 print("K5B_EXACT_ORIGINAL_SCIENCE="+str(r["original_scientific_outcomes_identical"]))
 return int(not r["original_scientific_outcomes_identical"])
if __name__=="__main__":raise SystemExit(main())
