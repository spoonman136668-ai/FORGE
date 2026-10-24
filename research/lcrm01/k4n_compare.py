#!/usr/bin/env python3
"""K4N exact two-process original evidence comparison; never promotes science."""
import argparse
import hashlib
import json
from pathlib import Path
from k4n_decision_coreset import FROZEN, SCHEMA

RESOURCE_KEYS=("method_inference_cpu_cost","shared_fitting_cpu_seconds",
               "shared_fitting_wall_seconds","total_resource")

def science_projection(value):
    p={k:v for k,v in value.items() if k not in RESOURCE_KEYS}
    if "quality_cost_decision" in p:
        q=dict(p["quality_cost_decision"])
        q.pop("inference_cpu_ratio",None)
        q.pop("result",None)
        if "requirements" in q:
            t=dict(q["requirements"]);t.pop("inference_CPU_at_most_65pct_full",None)
            q["requirements"]=t
        p["quality_cost_decision"]=q
    return p

def compare(a,b):
    pin=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    allowed={"FIT_ACTION_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
             "PUBLIC_DEVELOPMENT_COMPLETED"}
    for name,v in (("first",a),("second",b)):
        if (v.get("schema")!=SCHEMA or v.get("gate")!="LCRM01-K4N"
          or v.get("protocol_sha256")!=pin or v.get("source_commit")!=
             "1045277101a92c506db42704da28f6e7227d401b"
          or v.get("result") not in allowed or
          v.get("FIT_exposures")!=96 or len(v.get("FIT_rows",[]))!=96 or
          v.get("scientific_first_use") is not False or
          v.get("scientific_accepted") is not False or
          v.get("dispatch_authorized") is not False or
          v.get("original_K4L_negative_preserved") is not True or
          v.get("original_K4M_diagnostic_preserved") is not True):
            raise ValueError("K4N_UNQUALIFIED_SOURCE_OR_AUTHORITY_"+name)
        if v["result"]=="PUBLIC_DEVELOPMENT_COMPLETED":
            if (v.get("CHECK_exposures")!=16 or v.get("DEV_exposures")!=64 or
                len(v.get("CHECK_rows",[]))!=16 or len(v.get("DEV_rows",[]))!=64 or
                len(v.get("DEV_scores",[]))!=16 or
                set(v.get("model_checkpoint_bytes",{}))!=set(
                  ("fit_fidelity_4","coverage_4","outcome_aware_4",
                   "uniform_4","full_12","family_mean","ridge","fixed_low"))):
                raise ValueError("K4N_HOLDOUT_OR_COST_INCOMPLETE_"+name)
        elif (v.get("CHECK_exposures")!=0 or v.get("DEV_exposures")!=0 or "DEV_rows" in v):
            raise ValueError("K4N_UNCONSUMED_HOLDOUT_REPORTED_"+name)
    left=science_projection(a);right=science_projection(b)
    same=left==right
    changed=sorted(k for k in set(left)|set(right) if left.get(k)!=right.get(k))
    local_positive=(
      same and all(v["result"]=="PUBLIC_DEVELOPMENT_COMPLETED"
         and v["quality_cost_decision"]["result"]==
             "K4N_BOUNDED_NEW_SOURCE_DECISION_CORESET_POSITIVE" for v in (a,b)))
    return {"schema":"mass.lcrm01.k4n.cross-process-quality-cost-comparison-v1",
       "gate":"LCRM01-K4N","result":
         "REPLICATED_BOUNDED_PUBLIC_FIT_DECISION_CORESET_POSITIVE" if local_positive else
         "NO_REPLICATED_DECISION_CORESET_ADVANCEMENT",
       "source_and_scientific_records_identical":same,"differing_keys":changed,
       "process1_local":a.get("quality_cost_decision",{}).get("result",a["result"]),
       "process2_local":b.get("quality_cost_decision",{}).get("result",b["result"]),
       "two_fresh_OS_processes":True,"independent_hosts":False,
       "original_K4K_negative_preserved":True,
       "scientific_first_use":False,"scientific_accepted":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--first",required=True,type=Path)
    parser.add_argument("--second",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("EXISTING_COMPARISON_DESTINATION")
    r=compare(json.loads(args.first.read_text()),json.loads(args.second.read_text()))
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("K4N_CROSS_PROCESS="+r["result"])
    print("K4N_SOURCE_IDENTICAL="+str(r["source_and_scientific_records_identical"]))
    return 0 if r["source_and_scientific_records_identical"] else 1
if __name__=="__main__":
    raise SystemExit(main())
