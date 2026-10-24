#!/usr/bin/env python3
"""K4U two independent process science comparison, preserving each resource gate."""
import argparse,json,hashlib
from pathlib import Path
from k4u_native_minigrid import FROZEN,SCHEMA,METHODS,FAMILIES,PHASE_SEEDS


def science(record):
    r={k:v for k,v in record.items() if k!="resource"}
    if "native_FIT_checks" in r:
        z=dict(r["native_FIT_checks"])
        z.pop("total_native_fit_wall_seconds",None)
        z.pop("total_shared_native_fit_python_cpu_seconds",None)
        r["native_FIT_checks"]=z
    for name in ("CHECK_public_outcomes","DEV_public_outcomes"):
        if name in r:
            r[name]=[{k:v for k,v in row.items() if k not in
                   ("process_cpu_seconds","wall_seconds")} for row in r[name]]
    return r


def compare(a,b):
    proto=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    states={"FIT_NATIVE_SOURCE_UNQUALIFIED_HOLDOUT_NOT_CONSUMED",
            "COMPLETE_PROSPECTIVE_NATIVE_MINIGRID_DEVELOPMENT"}
    for label,r in (("A",a),("B",b)):
        if (r.get("schema")!=SCHEMA or r.get("gate")!="LCRM01-K4U"
            or r.get("source_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d"
            or r.get("native_Wingless_commit")!="cd108800054e7964af845137f0d9d37fae69f5a7"
            or r.get("native_Yggdrasil_commit")!="1b042d6bf4832d885d80ef73f3ab29d8a600bfe2"
            or r.get("protocol_sha256")!=proto or r.get("result") not in states
            or r.get("FIT_episodes")!=48 or r.get("FIT_public_experience_count",0)<500
            or len(r.get("FIT_public_experiences",[]))!=r.get("FIT_public_experience_count")
            or r.get("scientific_first_use") is not False
            or r.get("scientific_accepted") is not False
            or r.get("K4R_original_scientific_benchmark_qualified") is not True
            or r.get("K4S_original_source_negative_preserved") is not True):
            raise ValueError("K4U_ORIGINAL_SOURCE_OR_AUTHORITY_UNQUALIFIED_"+label)
        if r["result"]=="COMPLETE_PROSPECTIVE_NATIVE_MINIGRID_DEVELOPMENT":
            expected_check=len(FAMILIES)*len(PHASE_SEEDS["CHECK"])*len(METHODS)
            expected_dev=len(FAMILIES)*len(PHASE_SEEDS["DEV"])*len(METHODS)
            if (r.get("CHECK_evaluations")!=expected_check or
                r.get("DEV_evaluations")!=expected_dev or
                len(r.get("CHECK_public_outcomes",[]))!=expected_check or
                len(r.get("DEV_public_outcomes",[]))!=expected_dev or
                r.get("native_FIT_checks",{}).get("authentic_independent_native_cold_process_restores") is not True or
                r.get("native_science",{}).get("scientific_accepted") is not False):
                raise ValueError("K4U_INCOMPLETE_NEW_SOURCE_CHECK_DEV_"+label)
        elif (r.get("CHECK_evaluations")!=0 or r.get("DEV_evaluations")!=0 or
              "DEV_public_outcomes" in r):
            raise ValueError("K4U_UNQUALIFIED_FIT_MUST_NOT_CONSUME_DEV_"+label)
    x=science(a);y=science(b)
    same=x==y
    differing=sorted(k for k in set(x)|set(y) if x.get(k)!=y.get(k))
    positive=(same and all(r["result"]=="COMPLETE_PROSPECTIVE_NATIVE_MINIGRID_DEVELOPMENT"
       and r["native_science"]["result"]=="BOTH_INDEPENDENT_NATIVE_MINIGRID_SOURCE_POSITIVE"
       for r in (a,b)))
    return {"schema":"mass.lcrm01.k4u.original-source-cross-process.v1",
      "gate":"LCRM01-K4U","result":"REPEATED_BOUNDED_PUBLIC_NATIVE_MINIGRID_POSITIVE"
         if positive else "NO_REPEATABLE_NATIVE_MINIGRID_TRANSFER_ADVANCEMENT",
      "science_identical":same,"differing_scientific_fields":differing,
      "process_a_disposition":a.get("native_science",{}).get("result",a["result"]),
      "process_b_disposition":b.get("native_science",{}).get("result",b["result"]),
      "two_independent_python_processes_one_runner":True,
      "external_host_replication":False,
      "new_scientific_first_use":False,"scientific_accepted":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--second",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("K4U_SOURCE_COMPARISON_ALREADY_EXISTS")
    a=json.loads(args.first.read_text())
    b=json.loads(args.second.read_text())
    d=compare(a,b)
    args.output.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
    print("K4U_CROSS_PROCESS="+d["result"])
    print("K4U_ORIGINAL_SCIENCE_IDENTICAL="+str(d["science_identical"]))
    return 0 if d["science_identical"] else 1

if __name__=="__main__":
    raise SystemExit(main())
