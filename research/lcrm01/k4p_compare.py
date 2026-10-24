#!/usr/bin/env python3
"""Fail-closed exact two-process original science comparison for K4P."""
import argparse
import hashlib
import json
from pathlib import Path
from k4p_predictive_state import FROZEN,SCHEMA

TIMING=("per_method_inference_cpu","shared_fit_cpu_seconds",
        "shared_fit_wall_seconds","resource")

def stable(x):
    return {k:v for k,v in x.items() if k not in TIMING}

def compare(a,b):
    protocol_sha=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    outcomes={"FIT_ACTION_INFORMATION_INSUFFICIENT_HOLDOUT_UNCONSUMED",
              "COMPLETE_PUBLIC_PREDICTIVE_STATE_DEVELOPMENT"}
    for name,r in (("A",a),("B",b)):
        if (r.get("schema")!=SCHEMA or r.get("gate")!="LCRM01-K4P" or
            r.get("source_commit")!="1045277101a92c506db42704da28f6e7227d401b" or
            r.get("protocol_sha256")!=protocol_sha or
            r.get("result") not in outcomes or r.get("FIT_episodes")!=96 or
            len(r.get("FIT_rows",[]))!=96 or
            r.get("original_K4N_no_go_preserved") is not True or
            r.get("original_K4O_diagnostic_preserved") is not True or
            r.get("scientific_first_use") is not False or
            r.get("scientific_accepted") is not False):
            raise ValueError("K4P_SCIENCE_IDENTITY_OR_AUTHORITY_FAILED_"+name)
        if r["result"]=="COMPLETE_PUBLIC_PREDICTIVE_STATE_DEVELOPMENT":
            if ((r.get("CHECK_episodes"),r.get("DEV_episodes"))!=(24,96) or
                len(r.get("CHECK_rows",[]))!=24 or len(r.get("DEV_rows",[]))!=96 or
                len(r.get("DEV_scores",[]))!=24 or
                not r.get("checkpoint_sha256") or
                r.get("decision",{}).get("scientific_accepted") is not False):
                raise ValueError("K4P_ORIGINAL_HELDOUT_INCOMPLETE_"+name)
        elif (r.get("CHECK_episodes")!=0 or r.get("DEV_episodes")!=0 or
              "DEV_rows" in r):
            raise ValueError("K4P_HOLDOUT_MUST_BE_UNCONSUMED_"+name)
    x=stable(a);y=stable(b)
    # Main scientific test includes process-dependent CPU comparison; preserve
    # per-process positive/no-go individually and exclude only timing-derived
    # ratio/CPU test when comparing immutable science and decision records.
    for v in (x,y):
        if "decision" in v:
            d=dict(v["decision"])
            d.pop("inference_CPU_ratio",None)
            d.pop("result",None)
            tests=dict(d["tests"])
            tests.pop("inference_CPU_le_twice_raw_mem",None)
            d["tests"]=tests
            v["decision"]=d
    identical=x==y
    changed=sorted(k for k in set(x)|set(y) if x.get(k)!=y.get(k))
    positive=(identical and all(z["result"]=="COMPLETE_PUBLIC_PREDICTIVE_STATE_DEVELOPMENT"
         and z["decision"]["result"]=="BOUNDED_PREDICTIVE_STATE_INTERACTIVE_TRANSFER_POSITIVE"
         for z in (a,b)))
    return {"schema":"mass.lcrm01.k4p.original-cross-process-comparator.v1",
      "gate":"LCRM01-K4P",
      "result":"REPEATED_BOUNDED_PUBLIC_PREDICTIVE_TRANSFER_POSITIVE" if positive
            else "NO_QUALIFIED_REPEATABLE_PREDICTIVE_TRANSFER",
      "exact_original_science_agreement":identical,"changed_fields":changed,
      "process_A_outcome":a.get("decision",{}).get("result",a["result"]),
      "process_B_outcome":b.get("decision",{}).get("result",b["result"]),
      "two_original_Python_processes":True,"independent_host_replicated":False,
      "scientific_first_use":False,"scientific_accepted":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",type=Path,required=True)
    a.add_argument("--second",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    if x.output.exists() or not x.output.parent.is_dir():
        raise RuntimeError("ORIGINAL_COMPARE_MUST_NOT_OVERWRITE")
    r=compare(json.loads(x.first.read_text()),json.loads(x.second.read_text()))
    x.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("K4P_PROSPECTIVE_REPLICATION="+r["result"])
    print("K4P_SCIENTIFIC_SOURCE_AGREEMENT="+str(r["exact_original_science_agreement"]))
    return 0 if r["exact_original_science_agreement"] else 1
if __name__=="__main__":
    raise SystemExit(main())
