"""K5F independently execute and match original non-timing true obstacle science."""
import argparse,hashlib,json
from pathlib import Path
from k5f_dynamic_obstacles import PIN,SCHEMA,METHODS,CONDS,SEEDS

def stable(o):
 c={k:v for k,v in o.items() if k!="resources"}
 if "source_native_FIT_checkpoint" in c:
  s=dict(c["source_native_FIT_checkpoint"])
  s.pop("native_FIT_shared_wall_seconds",None)
  c["source_native_FIT_checkpoint"]=s
 for key in ("CHECK_full_original_traces","DEV_full_original_traces"):
  if key in c:
   c[key]=[{x:v for x,v in r.items() if x not in
      ("policy_selection_wall_seconds","policy_online_update_wall_seconds","episode_wall_seconds")}
      for r in c[key]]
 if "scientific" in c:
  s=dict(c["scientific"]);m={}
  for condition,methods in s["original_true_experience_results"].items():
   m[condition]={}
   for method,entry in methods.items():
    m[condition][method]={k:v for k,v in entry.items() if k not in
       ("total_policy_selection_seconds","total_policy_update_seconds")}
  s["original_true_experience_results"]=m
  c["scientific"]=s
 return c

def compare(a,b):
 ph=hashlib.sha256(PIN.read_bytes()).hexdigest()
 for label,r in (("A",a),("B",b)):
  if (r.get("schema")!=SCHEMA or
      r.get("result")!="COMPLETE_ORIGINAL_DYNAMIC_OBSTACLES_STUDY" or
      r.get("protocol_sha256")!=ph or
      r.get("upstream_original_dynamic_obstacles_blob")!="68436cecc35116c23c2f196c22fa3a19c6410b95" or
      r.get("original_R3_source_blob")!="5348238f4ec2183bea29262659883391b5f429fd" or
      r.get("original_FIT_true_actions")!=12000 or
      r.get("source_native_FIT_checkpoint",{}).get("true_independent_OS_cold_restore") is not True or
      (r.get("CHECK_real_episodes"),r.get("DEV_real_episodes"))!=(40,80) or
      len(r.get("CHECK_full_original_traces",[]))!=40 or
      len(r.get("DEV_full_original_traces",[]))!=80 or
      r.get("source_original_K5E_nonlinear_findings_preserved") is not True or
      r.get("scientific_first_use") is not False or
      r.get("scientific_accepted") is not False):
   raise ValueError("K5F_ORIGINAL_SOURCE_UNQUALIFIED_"+label)
  for kind,_ in CONDS:
   for method in METHODS:
    rows=[z for z in r["DEV_full_original_traces"] if z["kind"]==kind and z["method"]==method]
    if sorted(z["seed"] for z in rows)!=list(SEEDS["DEV"]):
     raise ValueError("K5F_WRONG_HELDOUT_SOURCE_"+label)
    for x in rows:
     if (not 1<=x["real_action_steps"]<=192 or
       x["real_action_steps"]!=len(x["full_original_action_consequence_trace"]) or
       len(x["trace_sha256"])!=64 or
       any(row["action"] not in (0,1,2) for row in x["full_original_action_consequence_trace"])):
      raise ValueError("K5F_GENUINE_ORIGINAL_ACTION_MISSING_"+label)
 same=stable(a)==stable(b)
 positive=(same and a["scientific"]["result"]=="BOUNDED_EXTERNAL_SENSOR_SAFETY_MITIGATION"
    and b["scientific"]["result"]==a["scientific"]["result"])
 return {"schema":"mass.lcrm01.k5f.original-nonstationary-repeat-v1",
  "result":"REPEATED_BOUNDED_MOVING_OBSTACLE_SAFETY" if positive
     else "NO_REPEATABLE_R3_DYNAMIC_SAFETY_ADVANCEMENT",
  "exact_source_science_agreement":same,
  "differing_non_timing_fields":sorted(k for k in set(stable(a))|set(stable(b))
     if stable(a).get(k)!=stable(b).get(k)),
  "native_architecture_superiority_established":False,
  "two_OS_processes_one_host":True,
  "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for name in ("first","second","output"):p.add_argument("--"+name,required=True,type=Path)
 x=p.parse_args()
 if x.output.exists() or not x.output.parent.is_dir():raise RuntimeError("K5F_RECEIPT_EXISTS")
 result=compare(json.loads(x.first.read_text()),json.loads(x.second.read_text()))
 x.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("K5F_REPEATED="+result["result"])
 print("K5F_NON_TIMING_SOURCE_MATCH="+str(result["exact_source_science_agreement"]))
 return int(not result["exact_source_science_agreement"])
if __name__=="__main__":raise SystemExit(main())
