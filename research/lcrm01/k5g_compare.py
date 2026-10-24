"""Independent K5G original interactive source matching, timing-neutral replay."""
import argparse,hashlib,json
from pathlib import Path
from k5g_active_sensing import PIN,SCHEMA,CONDITIONS,METHODS,BUDGETS,SEEDS

def stable(o):
 r={k:v for k,v in o.items() if k!="resources"}
 for key in ("CHECK_original_action_traces","DEV_original_action_traces"):
  if key in r:
   r[key]=[{p:v for p,v in row.items() if p not in
      ("policy_decision_wall_seconds","policy_adaptation_wall_seconds","total_episode_wall_seconds")}
      for row in r[key]]
 if "scientific" in r:
  s=dict(r["scientific"]);out={}
  for budget,conds in s["per_budget_condition_method"].items():
   out[budget]={}
   for condition,methods in conds.items():
    out[budget][condition]={}
    for name,data in methods.items():
     out[budget][condition][name]={k:v for k,v in data.items()
         if k not in ("policy_decision_seconds","policy_adaptation_seconds")}
  s["per_budget_condition_method"]=out;r["scientific"]=s
 return r

def compare(a,b):
 expected=hashlib.sha256(PIN.read_bytes()).hexdigest()
 for label,p in (("A",a),("B",b)):
  if (p.get("schema")!=SCHEMA or
    p.get("result")!="COMPLETE_ORIGINAL_BUDGETED_SENSOR_PHYSICAL_STUDY" or
    p.get("frozen_protocol_sha256")!=expected or
    p.get("original_dynamic_obstacle_git_blob")!="68436cecc35116c23c2f196c22fa3a19c6410b95" or
    p.get("original_R3_git_blob")!="5348238f4ec2183bea29262659883391b5f429fd" or
    p.get("original_public_FIT_actions")!=12000 or
    p.get("original_R3_native_checkpoint",{}).get("true_independent_OS_cold_restore") is not True or
    (p.get("CHECK_original_episode_count"),p.get("DEV_original_episode_count"))!=(96,192) or
    len(p.get("CHECK_original_action_traces",[]))!=96 or
    len(p.get("DEV_original_action_traces",[]))!=192 or
    p.get("prior_K5F_evidence_preserved") is not True or
    p.get("scientific_first_use") is not False or p.get("scientific_accepted") is not False):
   raise ValueError("K5G_FROZEN_ORIGINAL_SOURCE_INCOMPLETE_"+label)
  for budget in BUDGETS:
   for kind,_ in CONDITIONS:
    for method in METHODS:
     rows=[x for x in p["DEV_original_action_traces"]
        if x["budget"]==budget and x["condition"]==kind and x["policy"]==method]
     if sorted(x["seed"] for x in rows)!=list(SEEDS["DEV"]):
      raise ValueError("K5G_NEW_WORLD_POLICY_NOT_MATCHED_"+label)
     for row in rows:
      trail=row["original_physical_action_consequences"]
      measured=sum(int(x["scanned_front_this_step"]) for x in trail)
      if (not 1<=len(trail)<=192 or
        len(trail)!=row["physical_action_count"] or
        row["metered_onebit_queries"]>budget or
        (measured!=row["metered_onebit_queries"] and method!="native_R3_full_sensor_upper") or
        len(row["source_trace_sha256"])!=64 or
        any(x["queried_front_bit"] is not None and not x["scanned_front_this_step"] for x in trail)):
       raise ValueError("K5G_INVALID_PHYSICAL_SENSOR_COST_OR_TRACE_"+label)
 same=stable(a)==stable(b)
 ok=same and a["scientific"]["result"]=="BOUNDED_ACTIVE_ONEBIT_SENSING_SAFETY_GAIN" and b["scientific"]["result"]==a["scientific"]["result"]
 return {"schema":"mass.lcrm01.k5g.original-budgeted-causal-sensing-comparator-v1",
   "result":"REPEATED_BOUNDED_ACTIVE_SENSOR_ALLOCATION" if ok
     else "NO_REPEATABLE_NATIVE_ACTIVE_SENSING_ADVANCEMENT",
   "exact_true_non_timing_science_agreement":same,
   "different_non_timing_fields":sorted(k for k in set(stable(a))|set(stable(b))
          if stable(a).get(k)!=stable(b).get(k)),
   "external_heuristic_only":True,"native_architecture_novelty_established":False,
   "two_OS_processes_one_host":True,"scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 for n in ("first","second","output"):p.add_argument("--"+n,type=Path,required=True)
 x=p.parse_args()
 if x.output.exists() or not x.output.parent.is_dir():raise RuntimeError("K5G_EXISTING_RECEIPT")
 result=compare(json.loads(x.first.read_text()),json.loads(x.second.read_text()))
 x.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("K5G_CROSS_ORIGINAL="+result["result"])
 print("K5G_SCIENCE_REPEAT="+str(result["exact_true_non_timing_science_agreement"]))
 return int(not result["exact_true_non_timing_science_agreement"])
if __name__=="__main__":raise SystemExit(main())
