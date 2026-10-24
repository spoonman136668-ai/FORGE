#!/usr/bin/env python3
"""Exact cross-process K4J source/decision comparison. Never changes results."""
import argparse
import hashlib
import json
from pathlib import Path

from k4j_replicate import FROZEN,SCHEMA,canonical

IGNORED_METRICS={"whole_run_cost","method_inference_cost","common_fit_cpu_seconds","common_fit_wall_seconds"}
def normalized(data):
    return {k:v for k,v in data.items() if k not in IGNORED_METRICS}
def compare(a,b):
    pin=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    allowed={"COMPLETE_ONE_PROCESS_PUBLIC_DEV","FIT_INFORMATION_NOT_QUALIFIED_HOLDOUT_UNCONSUMED"}
    for name,report in (("A",a),("B",b)):
        if (report.get("schema")!=SCHEMA or report.get("gate")!="LCRM01-K4J" or
            report.get("protocol_sha256")!=pin or report.get("result") not in allowed or
            report.get("scientific_first_use") is not False or
            report.get("scientific_accepted") is not False or
            report.get("original_K4I_outcome_preserved") is not True or
            report.get("FIT_exposures")!=96):
            raise ValueError("K4J_PROVENANCE_OR_CUSTODY_UNVERIFIED_"+name)
        if report["result"]=="COMPLETE_ONE_PROCESS_PUBLIC_DEV":
            if (report.get("CHECK_exposures")!=16 or report.get("DEV_exposures")!=32 or
                len(report.get("DEV_rows",[]))!=32 or len(report.get("CHECK_rows",[]))!=16 or
                report.get("retention_exact") is not True or
                report.get("K4I_model_unchanged") is not True):
                raise ValueError("K4J_HOLDOUT_DATA_INCOMPLETE_"+name)
        else:
            if report.get("CHECK_exposures")!=0 or report.get("DEV_exposures")!=0 or "DEV_rows" in report:
                raise ValueError("K4J_FIT_STOP_VIOLATION_"+name)
    aa=normalized(a);bb=normalized(b)
    matches=aa==bb
    changed=sorted(key for key in set(aa)|set(bb) if aa.get(key)!=bb.get(key))
    both_positive=(matches and a["result"]=="COMPLETE_ONE_PROCESS_PUBLIC_DEV"
        and a["primary_reaching_replication"]["result"]=="REACHING_BOUNDED_POSITIVE_IN_THIS_PROCESS"
        and b["primary_reaching_replication"]["result"]=="REACHING_BOUNDED_POSITIVE_IN_THIS_PROCESS")
    return {"schema":"mass.lcrm01.k4j.independent-os-process-comparison.v1","gate":"LCRM01-K4J",
        "result":"REPLICATED_BOUNDED_PUBLIC_DEV_REACHING_POSITIVE" if both_positive
                 else "NO_INDEPENDENT_REPLICATION_OR_NO_GO",
        "exact_original_evidence_match":matches,
        "different_fields":changed,
        "both_processes_qualified":both_positive,
        "first_process_result":a["result"],"second_process_result":b["result"],
        "first_primary":a.get("primary_reaching_replication"),
        "second_primary":b.get("primary_reaching_replication"),
        "scientific_first_use":False,"scientific_accepted":False,
        "independent_host_replicated":False,
        "native_wingless_yggdrasil_claim":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--second",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("COMPARISON_FILE_ALREADY_EXISTS")
    a=json.loads(args.first.read_text())
    b=json.loads(args.second.read_text())
    result=compare(a,b)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("K4J_REPLICATION="+result["result"])
    print("K4J_EVIDENCE_IDENTICAL="+str(result["exact_original_evidence_match"]))
    return 0 if result["exact_original_evidence_match"] else 1
if __name__=="__main__":
    raise SystemExit(main())
