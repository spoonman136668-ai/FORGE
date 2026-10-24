"""K5E two original separate-process public causal experiments comparison.

Runtime measurements retained in original reports, excluded from exact
scientific identity. Never turn a structural tie into native novelty.
"""
import argparse,hashlib,json
from pathlib import Path
from k5e_nonlinear_trial import PIN,SCHEMA,METHODS,COHORTS

def stable(o):
 r={k:v for k,v in o.items() if k not in
    ("resources","FIT_shared_source_wall_seconds","per_model_fitting_wall_seconds")}
 if "scientific" in r:
  sci=dict(r["scientific"])
  sci["methods"]={m:{k:v for k,v in vals.items() if k!="inference_wall_seconds"}
                  for m,vals in sci["methods"].items()}
  r["scientific"]=sci
 return r

def compare(a,b):
 protocol=hashlib.sha256(PIN.read_bytes()).hexdigest()
 for label,p in (("A",a),("B",b)):
  if (p.get("schema")!=SCHEMA or
      p.get("result")!="COMPLETE_ORIGINAL_NONLINEAR_INTERLEAVED_STUDY" or
      p.get("frozen_protocol_sha256")!=protocol or
      p.get("source_native_R7_git_blob")!="204ecd993b954b23e66d6d1e8b3568e7c93183c5" or
      p.get("original_micro_world_git_blob")!="a43643ee6435f15e42cc671f54a6e401f7188a98" or
      p.get("source_intervention_count")!=5760 or
      len(p.get("source_interleaved_public_actions",[]))!=5760 or
      p.get("original_native_source_cold_OS") is not True or
      (len(p.get("CHECK_original_action_traces",[])),len(p.get("DEV_original_action_traces",[])))!=(16,64) or
      p.get("scientific_first_use") is not False or
      p.get("scientific_accepted") is not False or
      p.get("scientific",{}).get("scientific_accepted") is not False):
   raise ValueError("K5E_AUTHENTIC_SOURCE_FIRSTUSE_INVALID_"+label)
  source=p["source_interleaved_public_actions"]
  for i in range(192):
   batch=source[i*30:(i+1)*30]
   if (len(batch)!=30 or any(x["source_index"]!=i for x in batch)
    or len({(x["world"],x["action"]) for x in batch})!=30):
    raise ValueError("K5E_NOT_GLOBALLY_INTERLEAVED_"+label)
  for seed in COHORTS["DEV"]:
   x=[z for z in p["DEV_original_action_traces"] if z["seed"]==seed]
   if len(x)!=16 or sorted(z["trial"] for z in x)!=list(range(16)):
    raise ValueError("K5E_NEW_WORLD_OR_SEQUENCE_MISSING_"+label)
   for r in x:
    steps=r["real_action_consequence_trace"]
    if (len(steps) not in (3,5) or r["real_final_state"]!=steps[-1]["actual_after"] or
      len(r["trace_sha256"])!=64 or set(r["predicted_before_execution"])!=set(METHODS)):
     raise ValueError("K5E_INVALID_GENUINE_INTERACTION_"+label)
 same=stable(a)==stable(b)
 positive=(same and a["scientific"]["result"]=="BOUNDED_LEARNED_NONLINEAR_CAUSAL_COMPOSITION"
   and b["scientific"]["result"]==a["scientific"]["result"])
 return {"schema":"mass.lcrm01.k5e.interleaved-public-nonlinear-comparison-v1",
     "result":"REPEATED_BOUNDED_NONLINEAR_CAUSAL_COMPOSITION" if positive
         else "NO_REPEATABLE_NATIVE_NONLINEAR_TRANSFER_ADVANCEMENT",
     "original_scientific_outcomes_identical":same,
     "differing_non_timing_fields":sorted(k for k in set(stable(a))|set(stable(b))
          if stable(a).get(k)!=stable(b).get(k)),
     "native_superiority_not_proven":not bool(
       a["scientific"]["native_architecture_superiority"] and
       b["scientific"]["native_architecture_superiority"]),
     "constructed_nonphysical_research_world":True,
     "two_OS_processes_one_runner":True,
     "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):p.add_argument("--"+name,required=True,type=Path)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise RuntimeError("K5E_COMPARISON_EXISTS")
 c=compare(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
 a.output.write_text(json.dumps(c,sort_keys=True,indent=2)+"\n")
 print("K5E_ORIGINAL_CROSS_PROCESS="+c["result"])
 print("K5E_EXACT_SOURCE_SCIENCE="+str(c["original_scientific_outcomes_identical"]))
 return int(not c["original_scientific_outcomes_identical"])
if __name__=="__main__":raise SystemExit(main())
