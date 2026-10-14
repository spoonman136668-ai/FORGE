"""Automatically advance verified F5 successor into F6 method engineering.

Both training and validation use PREVIOUSLY CONSUMED F3 development cases,
with disjoint seed halves. No F6 fresh cohort, science, or first-use claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
from learner import fit,TRAIN_SEEDS,CHECK_SEEDS,NEXT_ID
from worker import evaluate,load_source,SOURCE_COMMIT

def canon(x):
    return (json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def main():
    p=argparse.ArgumentParser()
    for k in ("parent","successor","source-root","out"):
        p.add_argument("--"+k,required=True)
    args=p.parse_args()
    raw=Path(args.parent).read_bytes()
    successor_raw=Path(args.successor).read_bytes()
    parent=json.loads(raw)
    successor=json.loads(successor_raw)
    source=load_source(args.source_root)
    model=fit(parent,successor,source)
    result=[]
    for pair in ((8,10),(11,13)):
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in CHECK_SEEDS:
                    for policy in source.POLICIES:
                        result.append(evaluate(source,model,seed,pair,regime,family,policy))
    if len(result)!=96 or any(r["seed"] in TRAIN_SEEDS for r in result):
        raise ValueError("F6_SOURCE_SPLIT_OR_CAPACITY")
    validation={"cases":96,"pre":0,"post":0,"detections":0,
                "steady_errors":0,"rechecks":0}
    for row in result:
        validation["pre"]+=row["pre_mismatch"]
        validation["post"]+=row["post_mismatch"]
        validation["detections"]+=int(row["first_detection"] is not None)
        if row["regime"]=="steady":
            validation["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        validation["rechecks"]+=int(row["sample_trace"]["recheck"])
    # Compare against identically scoped F5 measurements. This does NOT
    # choose a scientific winner; it reports a reused development split.
    expected={arm:{"cases":0,"total":0,"rechecks":0} for arm in (
            "F5-COVERAGE","F5-MEMORY")}
    for row in parent["records"]:
        if row["seed"] not in CHECK_SEEDS or row["arm"] not in expected:
            continue
        item=expected[row["arm"]]
        item["cases"]+=1
        item["total"]+=row["pre_mismatch"]+row["post_mismatch"]
        item["rechecks"]+=int(set(row["sample_trace"]["addresses"][3])==
                              set(row["sample_trace"]["addresses"][4]))
    if any(x["cases"]!=96 for x in expected.values()):
        raise ValueError("F6_HISTORICAL_CONTROLS_MISSING")
    report={
      "schema":"forge.f6.automatic-trained-engineering-evidence.v1",
      "status":"HISTORICAL_F3_USED_ONLY_INDEPENDENT_REVIEW_REQUIRED",
      "successor_id":NEXT_ID,
      "parent_y070_commit":SOURCE_COMMIT,
      "parent_evidence_sha256":hashlib.sha256(raw).hexdigest(),
      "automatic_successor_sha256":hashlib.sha256(successor_raw).hexdigest(),
      "model":model,
      "validation_records":result,
      "validation_summary":validation,
      "matched_f5_validation_controls":expected,
      "new_first_use_claims":0,
      "new_originals":0,
      "new_cohort_accesses":0,
      "paid_api_calls":0,
      "scientific_authority":False,
      "scientific_winner_selected":False
    }
    encoded=canon(report)
    with Path(args.out).open("xb") as fd:fd.write(encoded)
    print("F6_AUTOMATIC_ENGINEERING_FROM_F5_SUCCESSOR=PASS")
    print("F6_LEARNED_PUBLIC_THRESHOLD="+str(model["frozen_threshold"]))
    print("F6_VALIDATION_TRIALS="+str(len(result)))
    print("F6_VALIDATION_SUMMARY="+str(validation))
    print("F6_PARENT_RECORD_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F6_ARCHIVE_SHA256="+hashlib.sha256(encoded).hexdigest())
    print("F6_FIRST_USE_AND_ORIGINALS=ZERO")

if __name__=="__main__":main()
