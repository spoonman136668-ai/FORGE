"""K5D independent OS process original causal source comparator; no fake acceptance."""
import argparse,hashlib,json
from pathlib import Path
from k5d_causal_trial import PIN,SCHEMA,METHODS,PHASE_WORLDS

def scientific_only(obj):
 r={k:v for k,v in obj.items() if k!="resources"}
 r.pop("source_shared_FIT_wall_seconds",None)
 if "scientific" in r:
  sci=dict(r["scientific"])
  methods={}
  for method,vals in sci["methods"].items():
   methods[method]={k:v for k,v in vals.items() if k!="measured_prediction_wall_seconds"}
  sci["methods"]=methods
  r["scientific"]=sci
 return r

def compare(a,b):
 h=hashlib.sha256(PIN.read_bytes()).hexdigest()
 for label,r in (("A",a),("B",b)):
  if (r.get("schema")!=SCHEMA or r.get("gate")!="LCRM01-K5D"
   or r.get("result")!="COMPLETE_CONSTRUCTED_PUBLIC_CAUSAL_EXPERIMENT"
   or r.get("frozen_protocol_sha256")!=h
   or r.get("native_R6_original_git_blob")!="236386eab51461343d3c2103851ad1de110769a4"
   or r.get("calibration_source_events")!=210
   or r.get("source_native_cold_OS_restore") is not True
   or r.get("native_original_source_FIT_observations")!=210
   or r.get("CHECK_actual_composed_episodes")!=16
   or r.get("DEV_actual_composed_episodes")!=64
   or len(r.get("DEV_original_public_traces",[]))!=64
   or r.get("scientific_first_use") is not False
   or r.get("scientific_accepted") is not False
   or r.get("scientific",{}).get("scientific_accepted") is not False):
   raise ValueError("K5D_ORIGINAL_PROVENANCE_INVALID_"+label)
  for world in PHASE_WORLDS["DEV"]:
   x=[z for z in r["DEV_original_public_traces"] if z["seed"]==world]
   if len(x)!=16 or sorted(z["trajectory_id"] for z in x)!=list(range(16)):
    raise ValueError("K5D_HELDOUT_WORLD_MISSING_"+label)
   for z in x:
    trail=z["original_actual_action_trace"]
    if (len(trail) not in (3,5) or
     z["actual_terminal"]!=trail[-1]["actual_after"] or
     len(z["full_source_trace_sha256"])!=64 or
     set(z["pre_committed_predictions"])!=set(METHODS)):
     raise ValueError("K5D_NONORIGINAL_PUBLIC_CAUSAL_PATH_"+label)
 same=scientific_only(a)==scientific_only(b)
 good=(same and a["scientific"]["result"]=="BOUNDED_PUBLIC_CAUSAL_COMPOSITION_LEARNED"
  and b["scientific"]["result"]==a["scientific"]["result"])
 return {"schema":"mass.lcrm01.k5d.original-causal-composition-comparator-v1",
 "result":"REPEATED_BOUNDED_CAUSAL_COMPOSITION_LEARNING" if good
     else "NO_REPEATABLE_NOVEL_CAUSAL_LEARNING_ADVANCEMENT",
 "exact_original_public_source_science_identical":same,
 "different_non_timing_fields":sorted(k for k in set(scientific_only(a))|set(scientific_only(b))
    if scientific_only(a).get(k)!=scientific_only(b).get(k)),
 "native_novelty_established":False,
 "synthetic_micro_world_only":True,
 "two_separate_OS_processes_one_runner":True,
 "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for k in ("first","second","output"):p.add_argument("--"+k,required=True,type=Path)
 q=p.parse_args()
 if q.output.exists() or not q.output.parent.is_dir():raise RuntimeError("K5D_COMPARATOR_OUTPUT_EXISTS")
 a=json.loads(q.first.read_text());b=json.loads(q.second.read_text())
 c=compare(a,b)
 q.output.write_text(json.dumps(c,indent=2,sort_keys=True)+"\n")
 print("K5D_ORIGINAL_SCIENTIFIC_CROSS_PROCESS="+c["result"])
 print("K5D_SOURCE_IDENTICAL="+str(c["exact_original_public_source_science_identical"]))
 return int(not c["exact_original_public_source_science_identical"])
if __name__=="__main__":raise SystemExit(main())
