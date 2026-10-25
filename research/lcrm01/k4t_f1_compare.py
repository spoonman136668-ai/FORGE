#!/usr/bin/env python3
"""K4T-F1 exact two-OS-process source/science comparator; no simulator execution."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f1_corrected_prospective import FROZEN,SCHEMA,FIT,CHECK,DEV,METHODS
from k4y_compare import stable


def compare(a,b):
    digest=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    valid={"FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED",
           "COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION"}
    for label,r in (("A",a),("B",b)):
        if (r.get("schema")!=SCHEMA or r.get("gate")!="LCRM01-K4T-F1"
            or r.get("result") not in valid
            or r.get("protocol_sha256")!=digest
            or r.get("source_minigrid_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d"
            or r.get("source_transport_qualified_head")!="228ad22a05bf449b5556ef44aa03f3bd3c52718b"
            or r.get("FIT_public_experience_count")!=12000
            or len(r.get("FIT_original_public_experiences",[]))!=12000
            or r.get("original_K4Y_no_go_unmodified") is not True
            or r.get("original_K4U_K4X_no_go_unmodified") is not True
            or r.get("scientific_accepted") is not False
            or r.get("scientific_first_use") is not False
            or r.get("wingless_only_preregistered_disposition",{}).get("scientific_accepted") is not False):
            raise ValueError("K4T_F1_INCOMPLETE_OR_UNAUTHENTIC_"+label)
        if any(x["seed"] not in FIT for x in r["FIT_original_public_experiences"]):
            raise ValueError("K4T_F1_FIT_COHORT_DRIFT_"+label)
        if r["result"]=="COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION":
            if (r.get("CHECK_episodes")!=72 or r.get("DEV_episodes")!=144
                or len(r.get("CHECK_original_public_traces",[]))!=72
                or len(r.get("DEV_original_public_traces",[]))!=144
                or r.get("native_FIT_custody",{}).get("true_native_cold_restart") is not True):
                raise ValueError("K4T_F1_COLD_RESTORE_OR_HELDOUT_INCOMPLETE_"+label)
            for part,seeds in (("CHECK",CHECK),("DEV",DEV)):
                for row in r[part+"_original_public_traces"]:
                    trace=row["actual_public_step_trace"]
                    if (row["seed"] not in seeds or row["method"] not in METHODS
                        or not trace or len(trace)>192 or len(row["trace_sha256"])!=64):
                        raise ValueError("K4T_F1_REAL_TRACE_INVALID_"+label)
        elif r.get("CHECK_episodes") or r.get("DEV_episodes"):
            raise ValueError("K4T_F1_HELDOUT_EXPOSED_ON_FAILED_FIT_"+label)
    equal=stable(a)==stable(b)
    outcome=a["wingless_only_preregistered_disposition"]["result"]
    pos=(equal and outcome==
       "BOUNDED_CORRECTED_WINGLESS_AFFORDANCE_TRANSFER_DEVELOPMENT_ONLY_NOT_NOVELTY"
       and b["wingless_only_preregistered_disposition"]["result"]==outcome)
    return {"schema":"mass.lcrm01.k4t-f1.original-two-process-science-comparison.v1",
            "gate":"LCRM01-K4T-F1",
            "result":("TWO_PROCESS_CORRECTED_WINGLESS_DEVELOPMENT_ADVANCEMENT_ONLY"
                      if pos else "NO_REPEATABLE_CORRECTED_WINGLESS_TRANSFER_ADVANCEMENT"),
            "science_identical":equal,
            "fields_different":sorted(x for x in set(stable(a))|set(stable(b))
                  if stable(a).get(x)!=stable(b).get(x)),
            "Wingless_A":a["wingless_only_preregistered_disposition"]["result"],
            "Wingless_B":b["wingless_only_preregistered_disposition"]["result"],
            "scientific_accepted":False,"scientific_first_use":False}


def main():
    a=argparse.ArgumentParser()
    for arg in ("first","second","output"):
        a.add_argument("--"+arg,type=Path,required=True)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise ValueError("K4T_F1_COMPARATOR_NOT_FRESH")
    v=compare(json.loads(args.first.read_text()),json.loads(args.second.read_text()))
    args.output.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
    print("K4T_F1_TWO_PROCESS="+v["result"])
    print("K4T_F1_SCIENCE_IDENTICAL="+str(v["science_identical"]))
    return int(not v["science_identical"])


if __name__=="__main__":
    raise SystemExit(main())
