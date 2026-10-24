#!/usr/bin/env python3
"""K4E: independent-process evidence comparison. No model/science dispatch."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from k4e_reward_ablation import FROZEN, SCHEMA, BASE, REPAIR, cases

def verify_report(r, frozen, protocol_sha):
    if (not isinstance(r,dict) or r.get("schema")!=SCHEMA or
        r.get("gate")!="LCRM01-K4E" or
        r.get("source_sha")!=frozen["source"]["commit"] or
        r.get("protocol_sha256")!=protocol_sha or
        r.get("scientific_first_use") is not False or
        r.get("scientific_accepted") is not False or
        r.get("learned_transfer") is not False or
        r.get("dispatch_authorized") is not False or
        r.get("K4D_negative_preserved") is not True):
        raise ValueError("K4E_PROVENANCE_OR_AUTHORITY_UNVERIFIED")
    expected=[(case,arm) for case in cases(frozen) for arm in (BASE,REPAIR)]
    rows=r.get("cases")
    if not isinstance(rows,list) or len(rows)!=8 or [(x.get("case"),x.get("arm")) for x in rows]!=expected:
        raise ValueError("K4E_EIGHT_ARM_IDENTITIES_MISMATCH")
    statuses=[x.get("status") for x in rows]
    if any(x not in ("BASELINE_REWARD_DRIFT","BASELINE_DIFFERENT_FINDING",
        "REPAIR_ALL_CHECKS_PASS","REPAIR_FAILED_CONTROL_REPLAY",
        "NEGATIVE","INFRASTRUCTURE_BLOCKED") for x in statuses):
        raise ValueError("K4E_UNKNOWN_CASE_OUTCOME")
    support=all(rows[i*2]["status"]=="BASELINE_REWARD_DRIFT" and
                rows[i*2+1]["status"]=="REPAIR_ALL_CHECKS_PASS" for i in range(4))
    expected_result="HYPOTHESIS_SUPPORTED_FOR_FROZEN_DEV_CASES" if support else (
       "INFRASTRUCTURE_BLOCKED" if any(x=="INFRASTRUCTURE_BLOCKED" for x in statuses) else
       "HYPOTHESIS_NOT_ESTABLISHED_RETAIN_NEGATIVES")
    if r.get("result")!=expected_result:
        raise ValueError("K4E_REPORT_DECISION_NOT_RECONCILED")
    return rows

def compare_reports(a,b):
    frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
    pin=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    ra=verify_report(a,frozen,pin)
    rb=verify_report(b,frozen,pin)
    mismatch=[]
    for i,(x,y) in enumerate(zip(ra,rb)):
        fields=sorted(k for k in set(x)|set(y) if x.get(k)!=y.get(k))
        if fields:
            mismatch.append({"case":x["case"],"arm":x["arm"],"fields":fields,"index":i})
    supported=(not mismatch and a["result"]=="HYPOTHESIS_SUPPORTED_FOR_FROZEN_DEV_CASES"
               and b["result"]=="HYPOTHESIS_SUPPORTED_FOR_FROZEN_DEV_CASES")
    return {"schema":"mass.lcrm01.k4e.independent-process-comparison.v1",
        "gate":"LCRM01-K4E","result":"SUPPORTED_BOUNDED_DEV_CAUSE" if supported else
                 "NOT_QUALIFIED_RETAIN_ORIGINAL_FINDINGS",
        "processes":2,"cases_per_process":8,"exact_process_evidence_match":not mismatch,
        "mismatches":mismatch,
        "first_process_result":a["result"],"second_process_result":b["result"],
        "K4D_negative_preserved":True,"scientific_first_use":False,
        "scientific_accepted":False,"learned_transfer":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--second",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("OUTPUT_ALREADY_EXISTS_OR_PARENT_ABSENT")
    a=json.loads(args.first.read_text(encoding="utf-8"))
    b=json.loads(args.second.read_text(encoding="utf-8"))
    report=compare_reports(a,b)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("K4E_COMPARISON="+report["result"])
    return 0

if __name__=="__main__":
    sys.exit(main())
