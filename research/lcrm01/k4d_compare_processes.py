#!/usr/bin/env python3
"""K4D independent-process exact outcome comparison; no re-evaluation."""
import argparse
import json
from pathlib import Path
import sys

from k4d_crossfamily import FROZEN, frozen_cases, SCHEMA

def compare(a,b,protocol):
    frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
    expected=frozen_cases(frozen)
    if len(expected)!=8:
        raise ValueError("FROZEN_CASE_COUNT_DRIFT")
    cases=[]
    for name,data in (("A",a),("B",b)):
        if data.get("schema")!=SCHEMA or data.get("gate")!="LCRM01-K4D" or data.get("result") not in (
                "PASS_ALL_EIGHT", "NEGATIVE_RETAINED", "INFRASTRUCTURE_BLOCKED"):
            raise ValueError("UNRECOGNIZED_REPORT_"+name)
        if (data.get("causalworld_commit")!=frozen["baseline"]["source_commit"] or
            data.get("protocol_sha256")!=protocol or data.get("scientific_first_use") is not False or
            data.get("scientific_accepted") is not False or
            data.get("dispatch_authorized") is not False or
            data.get("learned_transfer") is not False):
            raise ValueError("SOURCE_OR_AUTHORITY_DRIFT_"+name)
        rows=data.get("cases")
        if not isinstance(rows,list) or len(rows)!=8 or [row.get("case") for row in rows]!=expected:
            raise ValueError("MISSING_OR_CHANGED_CASE_"+name)
        cases.append(rows)
    mismatches=[]
    for i,(x,y) in enumerate(zip(*cases)):
        if x!=y:
            mismatches.append({
                "index":i,"case":expected[i],
                "process_a_status":x.get("status"),
                "process_b_status":y.get("status"),
                "differing_fields":sorted(set(x)|set(y)-set()),
            })
    passed = (not mismatches and a["result"]=="PASS_ALL_EIGHT" and b["result"]=="PASS_ALL_EIGHT")
    return {"schema":"mass.lcrm01.k4d.cross-process-replication.v1",
            "gate":"LCRM01-K4D","result":"PASS" if passed else "NOT_QUALIFIED",
            "source_commit":frozen["baseline"]["source_commit"],
            "cases_count":8,"processes_count":2,
            "all_cases_passed":a["result"]=="PASS_ALL_EIGHT" and b["result"]=="PASS_ALL_EIGHT",
            "matching_reports":not mismatches,
            "mismatches":mismatches,"scientific_first_use":False,
            "learned_transfer":False,"scientific_accepted":False,
            "original_negative_preserved":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--second",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or not a.output.parent.is_dir():
        raise RuntimeError("OUTPUT_NOT_FRESH")
    first=json.loads(a.first.read_text(encoding="utf-8"))
    second=json.loads(a.second.read_text(encoding="utf-8"))
    pin=first.get("protocol_sha256")
    result=compare(first,second,pin)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("LCRM01_K4D_REPLICATION="+result["result"])
    return 0 if result["result"]=="PASS" else 1

if __name__=="__main__":
    sys.exit(main())
