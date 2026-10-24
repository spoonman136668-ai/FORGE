#!/usr/bin/env python3
"""K4Q exact across-Python-process original physics and forward-source evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from k4q_causal_observability import FROZEN,SCHEMA

TIMING=("resource","FIT_baseline_train_cpu_seconds")

def compare(a,b):
    digest=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    allowed={"FIT_PHYSICAL_CAUSAL_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
             "PUBLIC_SOURCE_QUALIFICATION_COMPLETE"}
    for tag,p in (("A",a),("B",b)):
        if (p.get("schema")!=SCHEMA or p.get("gate")!="LCRM01-K4Q"
            or p.get("protocol_sha256")!=digest or
            p.get("source_commit")!="1045277101a92c506db42704da28f6e7227d401b"
            or p.get("result") not in allowed or
            p.get("FIT_exposures")!=144 or len(p.get("FIT_rows",[]))!=144
            or p.get("scientific_first_use") is not False
            or p.get("scientific_accepted") is not False
            or p.get("K4P_original_NO_GO_preserved") is not True):
            raise ValueError("ORIGINAL_K4Q_CUSTODY_OR_AUTHORITY_DRIFT_"+tag)
        if p["result"]=="PUBLIC_SOURCE_QUALIFICATION_COMPLETE":
            if (p.get("CHECK_exposures")!=24 or p.get("DEV_exposures")!=48
                or len(p.get("CHECK_rows",[]))!=24
                or len(p.get("DEV_rows",[]))!=48
                or len(p.get("CHECK_scored",[]))!=24
                or len(p.get("DEV_scored",[]))!=48
                or not p.get("fit_model_sha256")
                or p.get("source_qualification",{}).get("science_accepted") is not False):
                raise ValueError("ORIGINAL_K4Q_HELDOUT_INCOMPLETE_"+tag)
        elif (p.get("CHECK_exposures")!=0 or p.get("DEV_exposures")!=0
             or "DEV_rows" in p):
            raise ValueError("FIT_NEGATIVE_MUST_NOT_CONSUME_HELDOUT_"+tag)
    x={k:v for k,v in a.items() if k not in TIMING}
    y={k:v for k,v in b.items() if k not in TIMING}
    same=x==y
    differences=sorted(k for k in set(x)|set(y) if x.get(k)!=y.get(k))
    positive=same and all(p["result"]=="PUBLIC_SOURCE_QUALIFICATION_COMPLETE" and
        p["source_qualification"]["result"]==
        "SOURCE_OBSERVABILITY_AND_BASELINE_LEARNABILITY_QUALIFIED" for p in (a,b))
    return {"schema":"mass.lcrm01.k4q.original-cross-process-source-qualification.v1",
        "gate":"LCRM01-K4Q","result":"REPEATED_PUBLIC_OBSERVABLE_BENCHMARK_QUALIFIED" if positive
            else "NO_QUALIFIED_CAUSAL_OBSERVABILITY_SOURCE",
        "exact_original_science_agreement":same,"differing_fields":differences,
        "first_disposition":a.get("source_qualification",{}).get("result",a["result"]),
        "second_disposition":b.get("source_qualification",{}).get("result",b["result"]),
        "single_host_two_processes":True,"independent_host_replicated":False,
        "scientific_first_use":False,"scientific_accepted":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",type=Path,required=True)
    a.add_argument("--second",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    if x.output.exists() or not x.output.parent.is_dir():
        raise RuntimeError("K4Q_ORIGINAL_COMPARISON_ALREADY_EXISTS")
    v=compare(json.loads(x.first.read_text()),json.loads(x.second.read_text()))
    x.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
    print("K4Q_REPLICATION="+v["result"])
    print("K4Q_EXACT_SCIENCE="+str(v["exact_original_science_agreement"]))
    return 0 if v["exact_original_science_agreement"] else 1

if __name__=="__main__":
    raise SystemExit(main())
