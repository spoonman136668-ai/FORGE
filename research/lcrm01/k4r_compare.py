#!/usr/bin/env python3
"""K4R exact independently generated real interaction records (timing ignored)."""
import argparse
import hashlib
import json
from pathlib import Path
from k4r_minigrid_source import FROZEN,SCHEMA,canon,POLICIES

def projection(r):
    v={k:x for k,x in r.items() if k!="resource"}
    for key in ("CHECK_original_results","DEV_original_results"):
        if key in v:
            v[key]=[{k:x for k,x in row.items() if k!="eval_cpu_seconds"} for row in v[key]]
    return v

def compare(a,b):
    pin=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    allowed={"FIT_PUBLIC_MOTION_SOURCE_INSUFFICIENT_HOLDOUT_UNCONSUMED",
             "COMPLETE_INDEPENDENT_PUBLIC_BENCHMARK"}
    for label,p in (("A",a),("B",b)):
        if (p.get("schema")!=SCHEMA or p.get("gate")!="LCRM01-K4R" or
           p.get("protocol_sha256")!=pin or
           p.get("source_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d" or
           p.get("result") not in allowed or p.get("FIT_source_episodes")!=48 or
           not p.get("FIT_experience_count",0)>0 or
           p.get("original_K4Q_no_go_preserved") is not True or
           p.get("scientific_first_use") is not False or
           p.get("scientific_accepted") is not False):
            raise ValueError("ORIGINAL_K4R_SOURCE_OR_AUTHORITY_NOT_QUALIFIED_"+label)
        if p["result"]=="COMPLETE_INDEPENDENT_PUBLIC_BENCHMARK":
            if (p.get("CHECK_episode_evaluations")!=40 or
               p.get("DEV_episode_evaluations")!=80 or
               len(p.get("CHECK_original_results",[]))!=40 or
               len(p.get("DEV_original_results",[]))!=80 or
               not p.get("fitted_checkpoint_sha256") or
               p.get("source_qualification",{}).get("native_mechanism_tested") is not False):
                raise ValueError("ORIGINAL_HELDOUT_EVALUATION_NOT_COMPLETE_"+label)
        elif (p.get("CHECK_episode_evaluations")!=0 or
              p.get("DEV_episode_evaluations")!=0 or
              "DEV_original_results" in p):
            raise ValueError("K4R_SOURCE_NEGATIVE_MUST_LEAVE_HOLDOUT_UNCONSUMED_"+label)
    left=projection(a);right=projection(b)
    equal=left==right
    changed=sorted(k for k in set(left)|set(right) if left.get(k)!=right.get(k))
    qualified=(equal and all(z["result"]=="COMPLETE_INDEPENDENT_PUBLIC_BENCHMARK" and
       z["source_qualification"]["result"]=="INDEPENDENT_INTERACTIVE_SOURCE_QUALIFIED"
       for z in (a,b)))
    return {"schema":"mass.lcrm01.k4r.original-independent-source-comparison-v1",
      "gate":"LCRM01-K4R",
      "result":"REPEATED_PUBLIC_INTERACTIVE_BENCHMARK_QUALIFIED" if qualified else
               "NO_QUALIFIED_INDEPENDENT_BENCHMARK_YET",
      "exact_original_source_science_agreement":equal,"differing_fields":changed,
      "first_source_outcome":a.get("source_qualification",{}).get("result",a["result"]),
      "second_source_outcome":b.get("source_qualification",{}).get("result",b["result"]),
      "two_fresh_OS_processes":True,"independent_host_replicated":False,
      "scientific_first_use":False,"scientific_accepted":False,
      "new_native_cognition_demonstrated":False}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",required=True,type=Path)
    a.add_argument("--second",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    x=a.parse_args()
    if x.output.exists() or not x.output.parent.is_dir():
        raise RuntimeError("K4R_ORIGINAL_COMPARISON_ALREADY_EXISTS")
    o=compare(json.loads(x.first.read_text()),json.loads(x.second.read_text()))
    x.output.write_text(json.dumps(o,sort_keys=True,indent=2)+"\n")
    print("K4R_CROSS_PROCESS="+o["result"])
    print("K4R_IDENTICAL_ORIGINAL_SCIENCE="+str(o["exact_original_source_science_agreement"]))
    return 0 if o["exact_original_source_science_agreement"] else 1
if __name__=="__main__":
    raise SystemExit(main())
