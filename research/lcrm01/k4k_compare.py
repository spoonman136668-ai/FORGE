#!/usr/bin/env python3
"""K4K cross-process equality: original physics evidence, excluding only timing."""
import argparse
import hashlib
import json
from pathlib import Path

from k4k_compression import FROZEN,SCHEMA,canonical

TIMING={"per_method_inference_cost","shared_fit_cpu_seconds","shared_fit_wall_seconds","total_shared_cost"}

def scientific_projection(report):
    x={k:v for k,v in report.items() if k not in TIMING}
    if "science_quality_and_cost" in x:
        q=dict(x["science_quality_and_cost"])
        q.pop("primary_inference_cpu_ratio",None)
        q.pop("result",None)
        x["science_quality_and_cost"]=q
    return x

def compare(a,b):
    protocol=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    outcomes={"FIT_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
              "COMPLETE_PUBLIC_COMPRESSION_DEVELOPMENT"}
    for tag,data in (("A",a),("B",b)):
        if (data.get("schema")!=SCHEMA or data.get("gate")!="LCRM01-K4K" or
            data.get("protocol_sha256")!=protocol or data.get("result") not in outcomes or
            data.get("source_commit")!="1045277101a92c506db42704da28f6e7227d401b" or
            data.get("FIT_exposures")!=96 or len(data.get("FIT_rows",[]))!=96 or
            data.get("scientific_first_use") is not False or
            data.get("scientific_accepted") is not False or
            data.get("dispatch_authorized") is not False or
            data.get("original_K4J_preserved") is not True):
            raise ValueError("SOURCE_CUSTODY_OR_AUTHORITY_DRIFT_"+tag)
        if data["result"]=="COMPLETE_PUBLIC_COMPRESSION_DEVELOPMENT":
            if (data.get("CHECK_exposures")!=16 or data.get("DEV_exposures")!=32 or
                len(data.get("CHECK_rows",[]))!=16 or len(data.get("DEV_rows",[]))!=32 or
                not data.get("original_full_checkpoint_sha256") or
                set(data.get("checkpoint_bytes",{}))!=set(
                   ("outcome_aware_4","full_12","coverage_4","uniform_4",
                    "family_mean","ridge","fixed_low"))):
                raise ValueError("ORIGINAL_HOLDOUT_NOT_COMPLETE_"+tag)
        elif (data.get("CHECK_exposures")!=0 or data.get("DEV_exposures")!=0 or
              "DEV_rows" in data):
            raise ValueError("FROZEN_EARLY_STOP_WAS_NOT_RESPECTED_"+tag)
    x=scientific_projection(a)
    y=scientific_projection(b)
    same=x==y
    changed=sorted(k for k in set(x)|set(y) if x.get(k)!=y.get(k))
    both_positive=(same and all(d["result"]=="COMPLETE_PUBLIC_COMPRESSION_DEVELOPMENT"
        and d["science_quality_and_cost"]["result"]==
             "BOUNDED_COMPRESSED_MEMORY_QUALITY_COST_POSITIVE" for d in (a,b)))
    return {"schema":"mass.lcrm01.k4k.cross-process-quality-cost-replication.v1",
       "gate":"LCRM01-K4K",
       "result":"REPLICATED_PUBLIC_COMPRESSION_QUALITY_COST_POSITIVE" if both_positive else
                "NO_REPLICATED_COMPRESSION_PARETO_ADVANCEMENT",
       "exact_source_science_agreement":same,"differing_fields":changed,
       "process_a_disposition":a.get("science_quality_and_cost",{}).get("result",a["result"]),
       "process_b_disposition":b.get("science_quality_and_cost",{}).get("result",b["result"]),
       "two_separate_OS_processes":True,"independent_hosts":False,
       "scientific_first_use":False,"scientific_accepted":False,
       "original_K4J_preserved":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--first",type=Path,required=True)
    ap.add_argument("--second",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("COMPARISON_DESTINATION_NOT_FRESH")
    r=compare(json.loads(args.first.read_text()),json.loads(args.second.read_text()))
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("K4K_CROSS_PROCESS="+r["result"])
    print("K4K_SOURCE_IDENTICAL="+str(r["exact_source_science_agreement"]))
    return 0 if r["exact_source_science_agreement"] else 1
if __name__=="__main__":
    raise SystemExit(main())
